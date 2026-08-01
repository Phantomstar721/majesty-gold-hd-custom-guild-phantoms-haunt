"""IMAG animation-set parsing and version 1 TILE rendering.

These are used only by the diagnostic review scripts in this folder, never by
the build. They live here so this repository stands alone: cloning it is enough
to run everything in it, with no sibling repositories on disk.

The routines were previously imported across repository boundaries, which meant
the review scripts failed with a bare ModuleNotFoundError for anyone who had
only cloned this project. They are reproduced from the author's own
majesty-gold-hd-art-asset-extractor, which remains the fuller implementation:
it also handles version 3 tiles, external SPLT palettes and transparency
recovery. Only what the review scripts here actually need is kept.

Structures below were established by reading stock archives, and the field
names match what the extractor documents.
"""

from __future__ import annotations

import struct

from PIL import Image

# IMAG animation-set table
ANIM_HEADER_SIZE = 0x14
IMAGE_SET_ENTRY_SIZE = 8

# Per-direction block inside a frame descriptor
DIR_HEADER_SIZE = 0x30
DIR_GEOMETRY_OFF = 0x14
N_DIRECTION_SLOTS = 8

IMAGE_SET_NAMES = {
    1: "Walk",
    2: "Walk-2",
    3: "Walk-3",
    4: "Walk-4",
    8: "Stand",
    16: "Attack",
    17: "Attack-2",
    18: "Attack-3",
    19: "Attack-4",
    64: "Special",
    65: "Special-2",
    66: "Special-3",
    67: "Special-4",
    80: "Build",
    81: "Build-2",
    82: "Build-3",
    83: "Build-4",
    96: "Die",
    97: "Die-2",
    98: "Die-3",
    99: "Die-4",
    100: "Die-5",
    101: "Die-6",
    102: "Die-7",
    103: "Die-8",
    128: "Cast",
    129: "Cast-2",
    130: "Cast-3",
    131: "Cast-4",
    144: "Carry",
    145: "Carry-2",
    146: "Carry-3",
    147: "Carry-4",
    160: "Recoil",
    161: "Recoil-2",
    162: "Recoil-3",
    163: "Recoil-4",
    176: "Stand-to-Walk",
    177: "Walk-to-Stand",
    178: "Turn-Right",
    179: "Turn-Left",
    192: "Active",
    193: "Active-2",
    194: "Active-3",
    195: "Active-4",
    208: "Inactive",
    209: "Inactive-2",
    210: "Inactive-3",
    211: "Inactive-4",
    224: "Dead",
    240: "Crumble",
    256: "High-Power-Active",
    257: "High-Power-Idle",
    272: "Low-Power-Active",
    273: "Low-Power-Idle",
    288: "Unpowered",
    300: "Minimap",
    316: "Damage",
    332: "Assimilate",
    400: "Hotspot",
    500: "Selection-Underlay",
    550: "Selection-Overlay",
    1000: "Interface",
    1001: "Interface-01",
    1002: "Interface-02",
    2000: "Particle-Birth",
    2100: "Particle-Midlife",
    2200: "Particle-Death",
    4000: "UnitTexture",
}


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def i16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<h", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def image_set_base_id(set_id: int) -> int:
    base_id = set_id & 0xFFFF
    return base_id if base_id else set_id


def parse_anim_set(blob: bytes) -> list[tuple[int, str, int]]:
    """Return (set_id, set_name, relative_offset) for each animation set."""
    if len(blob) < ANIM_HEADER_SIZE + 4:
        return []
    entry_count = u32(blob, ANIM_HEADER_SIZE)
    if entry_count <= 0 or entry_count > 256:
        return []
    pos = ANIM_HEADER_SIZE + 4
    sets: list[tuple[int, str, int]] = []
    for _ in range(entry_count):
        if pos + IMAGE_SET_ENTRY_SIZE > len(blob):
            return []
        set_id = u32(blob, pos)
        rel_off = u32(blob, pos + 4)
        if rel_off >= len(blob):
            return []
        normalized_set_id = image_set_base_id(set_id)
        if set_id in IMAGE_SET_NAMES:
            set_name = IMAGE_SET_NAMES[set_id]
        elif normalized_set_id in IMAGE_SET_NAMES:
            set_name = f"{IMAGE_SET_NAMES[normalized_set_id]}-{set_id >> 16}"
        else:
            set_name = f"set-{set_id}"
        sets.append((set_id, set_name, rel_off))
        pos += IMAGE_SET_ENTRY_SIZE
    return sets


def parse_directional_frame_descriptor(blob: bytes, rel_off: int) -> list[dict[str, object]]:
    """Return one entry per populated direction slot of an animation set.

    Frame count comes from the stride to the next populated slot, since the
    per-direction block is a fixed header plus eight bytes per frame. The last
    populated slot has nothing to measure against, so its frames are read until
    a pair stops looking like (0, plausible tile index).
    """
    if rel_off + 0x38 + (N_DIRECTION_SLOTS * 4) > len(blob):
        return []

    raw_offsets = [i32(blob, rel_off + 0x38 + slot * 4) for slot in range(N_DIRECTION_SLOTS)]
    populated = [(slot, offset) for slot, offset in enumerate(raw_offsets) if offset > 0]
    directions: list[dict[str, object]] = []

    for idx, (slot, dir_rel) in enumerate(populated):
        dir_off = rel_off + dir_rel
        if dir_off + DIR_GEOMETRY_OFF + 8 > len(blob):
            continue
        x_off = i16(blob, dir_off + DIR_GEOMETRY_OFF)
        y_off = i16(blob, dir_off + DIR_GEOMETRY_OFF + 2)
        width = u16(blob, dir_off + DIR_GEOMETRY_OFF + 4)
        height = u16(blob, dir_off + DIR_GEOMETRY_OFF + 6)

        if idx + 1 < len(populated):
            next_dir_off = rel_off + populated[idx + 1][1]
            frame_count = (next_dir_off - dir_off - DIR_HEADER_SIZE) // 8
        else:
            frame_count = 0
            for frame in range(128):
                pair_off = dir_off + DIR_HEADER_SIZE + frame * 8
                if pair_off + 8 > len(blob):
                    break
                flag = u32(blob, pair_off)
                tile_idx = u32(blob, pair_off + 4)
                if flag == 0 and 0 < tile_idx < 500000:
                    frame_count += 1
                    continue
                break

        if frame_count <= 0 or frame_count > 128:
            continue

        tile_indices: list[int] = []
        for frame in range(frame_count):
            pair_off = dir_off + DIR_HEADER_SIZE + frame * 8
            if pair_off + 8 > len(blob):
                break
            tile_indices.append(u32(blob, pair_off + 4))

        directions.append(
            {
                "slot": slot,
                "x_off": x_off,
                "y_off": y_off,
                "width": width,
                "height": height,
                "tile_indices": tile_indices,
            }
        )

    return directions


def load_embedded_palette(data: bytes, offset: int) -> list[tuple[int, int, int]] | None:
    if offset < 0 or offset + 1032 > len(data):
        return None
    return [
        (data[offset + 8 + i * 4], data[offset + 9 + i * 4], data[offset + 10 + i * 4])
        for i in range(256)
    ]


def is_palette_key_color(index: int, red: int, green: int, blue: int) -> bool:
    """Return True for engine control pixels that should not appear in clean art.

    247 is the transition/seam control and 248-250 are shadow bands. Indices
    251-254 are not universally reserved: some building palettes use them for
    ordinary highlights, others put magenta control ramps there.
    """
    if 247 <= index <= 250:
        return True
    if red > 150 and green < 80 and blue > 150 and abs(red - blue) < 60:
        return True
    return green == 0 and red == blue and 120 <= red <= 140


def tile_v1_rgb565_to_image(
    tile_data: bytes, width: int, height: int, row_stride: int
) -> Image.Image | None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels_start = 26
    for y in range(height):
        row_start = pixels_start + y * row_stride
        for x in range(width):
            value = u16(tile_data, row_start + x * 2)
            if value == 0:
                continue
            red = ((value >> 11) & 0x1F) * 255 // 31
            green = ((value >> 5) & 0x3F) * 255 // 63
            blue = (value & 0x1F) * 255 // 31
            image.putpixel((x, y), (red, green, blue, 255))
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def tile_v1_to_image(tile_data: bytes, *, clean_art: bool = True) -> Image.Image | None:
    """Render a version 1 TILE that carries its own palette.

    Tiles that reference an external SPLT palette return None here. The review
    scripts in this folder only inspect raw-texture tiles, which embed theirs.
    """
    if len(tile_data) < 26 or u16(tile_data, 0) != 1:
        return None

    height = u16(tile_data, 2)
    width = u16(tile_data, 4)
    row_stride = u16(tile_data, 6)
    transparent_index = u16(tile_data, 16) & 0xFF
    palette_mode = u16(tile_data, 20)
    palette_value = u32(tile_data, 22)

    if width <= 0 or height <= 0:
        return None
    if row_stride == width * 2 and 26 + height * row_stride <= len(tile_data):
        return tile_v1_rgb565_to_image(tile_data, width, height, row_stride)
    pixel_count = row_stride * height
    if row_stride < width or 26 + pixel_count > len(tile_data):
        return None

    if palette_mode != 1:
        return None
    palette = load_embedded_palette(tile_data, palette_value)
    if palette is None:
        return None

    pixels = tile_data[26 : 26 + pixel_count]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for y in range(height):
        for x in range(width):
            index = pixels[y * row_stride + x]
            if index == transparent_index:
                continue
            red, green, blue = palette[index]
            if clean_art and is_palette_key_color(index, red, green, blue):
                continue
            image.putpixel((x, y), (red, green, blue, 255))
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image
