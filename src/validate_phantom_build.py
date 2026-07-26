from __future__ import annotations

import argparse
import mmap
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


MAGIC = b"CYLBPC  \x01\x00\x01\x00"
HEADER_SIZE = 20
DIR_ENTRY_SIZE = 8
SECTION_HEADER_SIZE = 8
ENTRY_HEADER_SIZE = 28


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    section: bytes
    name: bytes
    offset: int
    size: int
    index: int

    @property
    def label(self) -> str:
        section = self.section.decode("ascii", errors="replace")
        name = self.name.decode("ascii", errors="replace")
        return f"{section}/{name}"


EXPECTED_CAM_ENTRIES: dict[str, dict[bytes, set[bytes]]] = {
    "phantom_textdata.cam": {
        b"SMNU": {b"AP07"},
        b"STRT": {b"UNTN", b"ACTN", b"AP07"},
    },
    "phantom_gpltext.cam": {
        b"STRT": {b"QITM", b"HPTX"},
    },
    "phantom_maindata.cam": {
        b"IMAG": {
            b"PHM1Phantom",
            b"PHG1Phantom Guild",
            b"WRa2Ice Lance",
            b"PHp1fire_blast_M",
            b"WRa3Frost Armor",
            b"WRa4Blizzard",
            b"PHo3Ice Lance Hit",
            b"PHo4chill_icon",
            b"PHf1Frost Crystal",
            b"PHf2Frozen Small",
            b"PHf3Frozen Medium",
            b"PHf4Frozen Large",
        },
        b"TILE": set(),
        b"SPLT": set(),
    },
    "phantom_interfacedata.cam": {
        b"IMAG": {
            b"INTnChar spell icon",
            b"INBwicons weapons",
            b"INBaarmor icons",
            b"PHTIraw textures",
        },
        b"TILE": set(),
    },
    "phantom_mx_interfacedata.cam": {
        b"IMAG": {b"INBwicons weapons"},
        b"TILE": set(),
    },
    "phantom_voices.cam": {
        b"WAVE": {b"PHD1", b"PHS1", b"PHDH", b"PHA1", b"PHGS"},
    },
}

EXPECTED_DESCRIPTION_IDS = {
    "phantom_units.xml": {
        ("Unit", "PHM1"),
        ("Unit", "FrozenCowl"),
        ("Unit", "BlackIcerod"),
        ("Unit", "MBPhantomGuild"),
    },
    "phantom_actions.xml": {
        ("Action", "WRa2"),
        ("Action", "WRa3"),
        ("Action", "WRa4"),
    },
    "phantom_projectiles.xml": {("Unit", "PHp1")},
    "phantom_overlays.xml": {
        ("Unit", "PHo1"),
        ("Unit", "PHo2"),
        ("Unit", "PHo3"),
        ("Unit", "PHo4"),
        ("Unit", "PHo5"),
        ("Unit", "PHo6"),
        ("Unit", "PHo7"),
        ("Unit", "PHo8"),
        ("Unit", "PHo9"),
        ("Unit", "PH10"),
    },
    "phantom_sounds.xml": {
        ("Sound", "PH01"),
        ("Sound", "PH02"),
    },
}

CUSTOM_TILE_OWNERS = {
    b"PHG1Profile": (b"PHG1Phantom Guild", "low16"),
    b"PHG1BuildIcon": (b"PHG1Phantom Guild", "low16"),
    b"PHG1Bld": (b"PHG1Phantom Guild", "low16"),
    b"PHG1Act": (b"PHG1Phantom Guild", "low16"),
    b"PHp1IceTile": (b"PHp1fire_blast_M", "u32"),
    b"PHM1PhantomTile": (b"PHM1Phantom", "low16"),
    b"PHM1CastGlow": (b"PHM1Phantom", "low16"),
    b"PHo3IceTile": (b"PHo3Ice Lance Hit", "u32"),
    b"PHc1ChillTile": (b"PHo4chill_icon", "u32"),
    b"PHf1Crystal": (b"PHf1Frost Crystal", "u32"),
    b"PHf2Frozen": (b"PHf2Frozen Small", "u32"),
    b"PHf3Frozen": (b"PHf3Frozen Medium", "u32"),
    b"PHf4Frozen": (b"PHf4Frozen Large", "u32"),
}

EXPECTED_CUSTOM_TILE_COUNTS = {
    b"PHG1Profile": 1,
    b"PHG1BuildIcon": 1,
    b"PHG1Bld": 14,
    b"PHG1Act": 8,
    b"PHp1IceTile": 128,
    b"PHM1PhantomTile": 204,
    b"PHM1CastGlow": 32,
    b"PHo3IceTile": 6,
    b"PHc1ChillTile": 29,
    b"PHf1Crystal": 29,
    b"PHf2Frozen": 29,
    b"PHf3Frozen": 29,
    b"PHf4Frozen": 29,
}

ALIGNED_PHANTOM_DISSOLVE_TILES = {
    f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
    for source_tile in range(4779, 4786)
}

CLIP_SAFE_PHANTOM_DEATH_TILES = {
    *{
        f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        for source_tile in range(4723, 4741)
    },
    *ALIGNED_PHANTOM_DISSOLVE_TILES,
    b"PHM1PhantomTile201",
}

SHADOWED_BUILDING_TILES = {
    *(f"PHG1Bld{index:04d}".encode("ascii") for index in range(5)),
    *(f"PHG1Bld{index:04d}".encode("ascii") for index in range(11, 14)),
    *(f"PHG1Act{index:02d}".encode("ascii") for index in range(8)),
}

LOWER_LEFT_BALCONY_PIT_TILES = {
    b"PHG1Bld0003",
    *(f"PHG1Act{index:02d}".encode("ascii") for index in range(8)),
}

CONSTRUCTION_BUILDING_TILES = {
    *(f"PHG1Bld{index:04d}".encode("ascii") for index in range(3)),
}

TRANSITIONAL_DESTRUCTION_TILES = {
    b"PHG1Bld0012",  # source tile 1530, Damaged B
    b"PHG1Bld0013",  # source tile 1531, Collapsed Intermediate
}

EXPECTED_BUILDING_DESTRUCTION_ATTACHMENTS = {
    0x03000063: (35, 25),
    0x03000064: (35, 25),
    0x03000065: (35, 25),
    0x03000066: (35, 25),
    0x03000067: (35, 25),
}


def fail(message: str) -> None:
    raise ValidationError(message)


def u32(data: mmap.mmap | bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def parse_xml(path: Path) -> ET.ElementTree:
    try:
        return ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        fail(f"{path}: invalid XML: {exc}")


def validate_manifest(output_root: Path) -> None:
    manifest_path = output_root / "PhantomGuildPoc.mmxml"
    tree = parse_xml(manifest_path)
    referenced: set[Path] = set()
    for element_name in ("CAM", "Descriptions", "Target", "Source"):
        for element in tree.findall(f".//{element_name}"):
            if element.text and element.text.strip():
                relative = Path(element.text.strip().replace("\\", "/"))
                referenced.add(relative)
                target = output_root / relative
                if not target.is_file():
                    fail(f"{manifest_path}: referenced file is missing: {relative}")
                if target.stat().st_size == 0:
                    fail(f"{manifest_path}: referenced file is empty: {relative}")

    expected = {
        Path("Data") / name for name in EXPECTED_CAM_ENTRIES
    } | {
        Path("Data") / name for name in EXPECTED_DESCRIPTION_IDS
    } | {
        Path("Data/Phantom.bcd"),
        Path("GPL/Phantom_Building_Data.dat"),
        Path("GPL/Phantom_Hero_Data.dat"),
        Path("GPL/Phantom_Items_Data.dat"),
        Path("GPL/Phantom.gpl"),
    }
    missing_references = expected - referenced
    if missing_references:
        paths = ", ".join(str(path) for path in sorted(missing_references))
        fail(f"{manifest_path}: required files are not referenced: {paths}")


def validate_descriptions(output_root: Path) -> None:
    seen_global: set[tuple[str, str]] = set()
    for filename, expected in EXPECTED_DESCRIPTION_IDS.items():
        path = output_root / "Data" / filename
        tree = parse_xml(path)
        actual: set[tuple[str, str]] = set()
        for description in tree.findall(".//Description"):
            key = (description.get("type", ""), description.get("ID", ""))
            if not all(key):
                fail(f"{path}: Description is missing type or ID")
            if key in actual:
                fail(f"{path}: duplicate Description type/ID: {key[0]}/{key[1]}")
            if key in seen_global:
                fail(f"{path}: Description type/ID is duplicated across files: {key[0]}/{key[1]}")
            actual.add(key)
            seen_global.add(key)
        if actual != expected:
            missing = expected - actual
            extra = actual - expected
            fail(f"{path}: unexpected Description IDs; missing={sorted(missing)}, extra={sorted(extra)}")


def validate_archive(path: Path) -> tuple[dict[bytes, list[Entry]], dict[tuple[bytes, bytes], bytes]]:
    try:
        handle = path.open("rb")
    except OSError as exc:
        fail(f"{path}: cannot open archive: {exc}")

    captured: dict[tuple[bytes, bytes], bytes] = {}
    with handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
        file_size = len(data)
        if file_size < HEADER_SIZE or data[: len(MAGIC)] != MAGIC:
            fail(f"{path}: not a CYLBPC CAM archive")

        section_count = u32(data, 12)
        content_header_size = u32(data, 16)
        directory_end = HEADER_SIZE + section_count * DIR_ENTRY_SIZE
        content_end = directory_end + content_header_size
        if not 1 <= section_count <= 32:
            fail(f"{path}: unreasonable section count: {section_count}")
        if directory_end > file_size or content_end > file_size:
            fail(f"{path}: header extends beyond end of file")

        section_directory: list[tuple[bytes, int]] = []
        seen_sections: set[bytes] = set()
        for index in range(section_count):
            cursor = HEADER_SIZE + index * DIR_ENTRY_SIZE
            extension = bytes(data[cursor : cursor + 4])
            offset = u32(data, cursor + 4)
            if extension in seen_sections:
                fail(f"{path}: duplicate section: {extension!r}")
            if offset < directory_end or offset + SECTION_HEADER_SIZE > content_end:
                fail(f"{path}: section {extension!r} header offset is out of bounds: {offset}")
            seen_sections.add(extension)
            section_directory.append((extension, offset))

        sections: dict[bytes, list[Entry]] = {}
        metadata_ranges: list[tuple[int, int, str]] = []
        data_ranges: list[tuple[int, int, str]] = []
        for extension, section_offset in section_directory:
            entry_count = u32(data, section_offset)
            table_start = section_offset + SECTION_HEADER_SIZE
            table_end = table_start + entry_count * ENTRY_HEADER_SIZE
            if table_end > content_end:
                fail(f"{path}: {extension!r} entry table extends beyond the content header")
            metadata_ranges.append((section_offset, table_end, extension.decode(errors="replace")))

            entries: list[Entry] = []
            seen_names: set[bytes] = set()
            for entry_index in range(entry_count):
                cursor = table_start + entry_index * ENTRY_HEADER_SIZE
                raw_name = bytes(data[cursor : cursor + 20])
                name = raw_name.rstrip(b"\x00")
                offset = u32(data, cursor + 20)
                size = u32(data, cursor + 24)
                if not name and extension != b"SPLT":
                    fail(f"{path}: {extension!r} entry {entry_index} has an empty name")
                if name and name in seen_names:
                    fail(f"{path}: duplicate entry: {extension.decode(errors='replace')}/{name!r}")
                if size == 0:
                    fail(f"{path}: {extension.decode(errors='replace')}/{name!r} is empty")
                if offset < content_end or offset + size > file_size:
                    fail(
                        f"{path}: {extension.decode(errors='replace')}/{name.decode(errors='replace')} "
                        f"data range {offset}+{size} is outside the archive"
                    )
                if name:
                    seen_names.add(name)
                entry = Entry(extension, name, offset, size, entry_index)
                entries.append(entry)
                data_ranges.append((offset, offset + size, entry.label))
            sections[extension] = entries

        for ranges, range_kind in ((metadata_ranges, "metadata"), (data_ranges, "entry data")):
            ranges.sort()
            for previous, current in zip(ranges, ranges[1:]):
                if current[0] < previous[1]:
                    fail(f"{path}: overlapping {range_kind}: {previous[2]} and {current[2]}")

        if metadata_ranges:
            if metadata_ranges[0][0] != directory_end:
                fail(f"{path}: first section header does not begin after the section directory")
            for previous, current in zip(metadata_ranges, metadata_ranges[1:]):
                if previous[1] != current[0]:
                    fail(f"{path}: gap between section headers for {previous[2]} and {current[2]}")
            if metadata_ranges[-1][1] != content_end:
                fail(f"{path}: section headers do not fill the declared content header")

        if data_ranges:
            if data_ranges[0][0] != content_end:
                fail(f"{path}: first entry data does not begin after the content header")
            for previous, current in zip(data_ranges, data_ranges[1:]):
                if previous[1] != current[0]:
                    fail(f"{path}: gap between entry data for {previous[2]} and {current[2]}")
            if data_ranges[-1][1] != file_size:
                fail(f"{path}: trailing bytes after the last CAM entry")

        for entry in sections.get(b"STRT", []):
            payload = bytes(data[entry.offset : entry.offset + entry.size])
            validate_strt(path, entry, payload)
            captured[(entry.section, entry.name)] = payload

        imag_names = {
            owner[0] for owner in CUSTOM_TILE_OWNERS.values()
        } | {b"PHTIraw textures"}
        for entry in sections.get(b"IMAG", []):
            if entry.name in imag_names:
                captured[(entry.section, entry.name)] = bytes(data[entry.offset : entry.offset + entry.size])

        tile_entries = sections.get(b"TILE", [])
        palette_count = len(sections.get(b"SPLT", []))
        for entry in tile_entries:
            if custom_tile_owner(entry.name) is not None or entry.name == b"PHTIPanel0001":
                payload = bytes(data[entry.offset : entry.offset + entry.size])
                validate_tile(path, entry, payload, palette_count)
                captured[(entry.section, entry.name)] = payload

    return sections, captured


def validate_strt(path: Path, entry: Entry, data: bytes) -> None:
    if len(data) < 4:
        fail(f"{path}: {entry.label} is too short for an STRT header")
    count = struct.unpack_from("<H", data, 0)[0]
    offsets_end = 4 + count * 4
    if offsets_end > len(data):
        fail(f"{path}: {entry.label} offset table extends beyond the entry")
    offsets = [struct.unpack_from("<I", data, 4 + index * 4)[0] for index in range(count)]
    previous = offsets_end
    for index, offset in enumerate(offsets):
        if offset < offsets_end or offset + 5 > len(data):
            fail(f"{path}: {entry.label} string {index} has an invalid offset: {offset}")
        if offset < previous:
            fail(f"{path}: {entry.label} string offsets are not ordered at index {index}")
        record_end = offsets[index + 1] if index + 1 < count else len(data)
        if record_end <= offset + 4:
            fail(f"{path}: {entry.label} string {index} overlaps the next record")
        if data.find(b"\x00", offset + 4, record_end) == -1:
            fail(f"{path}: {entry.label} string {index} is not null terminated")
        previous = offset


def validate_indexed_item_strings(path: Path, data: bytes) -> None:
    count = struct.unpack_from("<H", data, 0)[0]
    if count <= 81:
        fail(f"{path}: STRT/QITM has {count} strings; item IDs 80 and 81 require at least 82")
    expected_items = (
        (80, b"Frozen Cowl\n\x01FFDDAA(+1 armor)"),
        (81, b"Black Icerod\n\x01FFDDAA(+8 damage)"),
    )
    for item_id, expected_text in expected_items:
        offset = struct.unpack_from("<I", data, 4 + item_id * 4)[0]
        record_id = struct.unpack_from("<I", data, offset)[0]
        end = data.index(b"\x00", offset + 4)
        text = data[offset + 4 : end]
        if record_id != item_id:
            fail(f"{path}: STRT/QITM slot {item_id} contains record ID {record_id}")
        if text != expected_text:
            fail(f"{path}: STRT/QITM slot {item_id} is not the known-good item text")


def validate_tile(path: Path, entry: Entry, tile: bytes, palette_count: int) -> None:
    if len(tile) < 26:
        fail(f"{path}: {entry.label} is only {len(tile)} bytes; expected a 26-byte TILE header")
    version, height, width, row_stride = struct.unpack_from("<HHHH", tile, 0)
    if height == 0 or width == 0:
        fail(f"{path}: {entry.label} has invalid dimensions {width}x{height}")
    expected_dimensions = None
    if entry.name == b"PHG1Profile":
        expected_dimensions = (100, 100)
    elif entry.name == b"PHG1BuildIcon":
        expected_dimensions = (25, 25)
    elif entry.name.startswith(b"PHG1Act"):
        expected_dimensions = (301, 229)
    elif entry.name == b"PHTIPanel0001":
        expected_dimensions = (200, 245)
    if expected_dimensions and (width, height) != expected_dimensions:
        fail(
            f"{path}: {entry.label} is {width}x{height}; "
            f"expected {expected_dimensions[0]}x{expected_dimensions[1]}"
        )

    palette_mode = struct.unpack_from("<H", tile, 20)[0]
    palette_value = struct.unpack_from("<I", tile, 22)[0]
    if palette_mode == 0 and palette_count and palette_value >= palette_count:
        fail(f"{path}: {entry.label} references missing palette {palette_value} of {palette_count}")
    if palette_mode == 1 and not 26 <= palette_value < len(tile):
        fail(f"{path}: {entry.label} has invalid embedded palette offset {palette_value}")

    if version == 1:
        plane_end = 26 + row_stride * height
        if row_stride < width or plane_end > len(tile):
            fail(
                f"{path}: {entry.label} has invalid v1 plane "
                f"({width}x{height}, stride {row_stride}, {len(tile)} bytes)"
            )
        if palette_mode == 1 and palette_value < plane_end:
            fail(f"{path}: {entry.label} embedded palette overlaps its image plane")
        return

    if version != 3:
        fail(f"{path}: {entry.label} uses unsupported TILE version {version}")

    table_end = 26 + height * 4
    pixel_end = palette_value if palette_mode == 1 else len(tile)
    if table_end > pixel_end:
        fail(f"{path}: {entry.label} v3 row table extends beyond pixel data")
    offsets = [struct.unpack_from("<I", tile, 26 + row * 4)[0] for row in range(height)]
    if offsets != sorted(offsets):
        fail(f"{path}: {entry.label} v3 row offsets are not ordered")
    shadow_pixels = 0
    invalid_reserved_pixels = 0
    split_shadow_tile = (
        entry.name in SHADOWED_BUILDING_TILES
        or (
            entry.name.startswith(b"PHM1PhantomTile")
            and palette_mode == 0
            and palette_value == 32
        )
    )
    decoded_rows = (
        [[0 for _column in range(width)] for _row in range(height)]
        if entry.name in SHADOWED_BUILDING_TILES
        or entry.name in ALIGNED_PHANTOM_DISSOLVE_TILES
        or entry.name in CLIP_SAFE_PHANTOM_DEATH_TILES
        else None
    )
    for row, relative_start in enumerate(offsets):
        start = 26 + relative_start
        end = 26 + offsets[row + 1] if row + 1 < height else pixel_end
        if start < table_end or start > end or end > pixel_end:
            fail(f"{path}: {entry.label} v3 row {row} has an invalid byte range")
        cursor = start
        terminated = False
        while cursor < end:
            if cursor + 4 > end:
                fail(f"{path}: {entry.label} v3 row {row} has a truncated segment header")
            x_end, count, flags = struct.unpack_from("<HBB", tile, cursor)
            cursor += 4
            if x_end < count or x_end > width:
                fail(
                    f"{path}: {entry.label} v3 row {row} segment "
                    f"ends at {x_end} with count {count} for width {width}"
                )
            if cursor + count > end:
                fail(f"{path}: {entry.label} v3 row {row} has truncated pixel data")
            values = tile[cursor : cursor + count]
            if decoded_rows is not None:
                x_start = x_end - count
                decoded_rows[row][x_start:x_end] = values
            shadow_pixels += sum(247 <= value <= 250 for value in values)
            invalid_reserved_pixels += sum(251 <= value <= 255 for value in values)
            if split_shadow_tile:
                segment_has_shadow = any(247 <= value <= 250 for value in values)
                segment_has_body = any(1 <= value <= 246 for value in values)
                if segment_has_shadow and segment_has_body:
                    fail(
                        f"{path}: {entry.label} v3 row {row} mixes shadow controls "
                        "and body pixels in one segment"
                    )
            cursor += count
            if flags & 0x80:
                terminated = True
                break
        if not terminated:
            fail(f"{path}: {entry.label} v3 row {row} has no terminating segment")
        if cursor != end:
            fail(f"{path}: {entry.label} v3 row {row} has {end - cursor} unexpected trailing bytes")
    if entry.name in SHADOWED_BUILDING_TILES and shadow_pixels < 100:
        fail(
            f"{path}: {entry.label} has only {shadow_pixels} shadow-key pixels; "
            "expected a generated building shadow"
        )
    if entry.name in SHADOWED_BUILDING_TILES and invalid_reserved_pixels:
        fail(
            f"{path}: {entry.label} uses {invalid_reserved_pixels} unsupported reserved "
            "palette pixels outside shadow indices 247-250"
        )
    shadowless_hero_effect_tiles = {
        *{
            f"PHM1PhantomTile{offset}".encode("ascii")
            for offset in range(4741 - 4586, 4746 - 4586)
        },
        b"PHM1PhantomTile202",
        b"PHM1PhantomTile203",
        b"PHM1PhantomTile204",
        b"PHM1PhantomTile205",
        *{
            f"PHM1PhantomTile{offset}".encode("ascii")
            for offset in range(4659 - 4586, 4682 - 4586)
        },
    }
    if (
        split_shadow_tile
        and entry.name not in SHADOWED_BUILDING_TILES
        and entry.name not in shadowless_hero_effect_tiles
        and shadow_pixels == 0
    ):
        fail(f"{path}: {entry.label} lost its stock hero shadow control mask")
    if entry.name in SHADOWED_BUILDING_TILES and decoded_rows is not None:
        validate_shadow_body_seam(path, entry, decoded_rows)
    if entry.name in ALIGNED_PHANTOM_DISSOLVE_TILES and decoded_rows is not None:
        validate_phantom_dissolve_baseline(path, entry, tile, decoded_rows)
    if entry.name in CLIP_SAFE_PHANTOM_DEATH_TILES and decoded_rows is not None:
        validate_phantom_death_frame_clearance(path, entry, decoded_rows)


def validate_phantom_dissolve_baseline(
    path: Path,
    entry: Entry,
    tile: bytes,
    pixels: list[list[int]],
) -> None:
    hotspot_y = struct.unpack_from("<H", tile, 12)[0]
    body_rows = [
        y
        for y, row in enumerate(pixels)
        if any(value != 0 and not 247 <= value <= 250 for value in row)
    ]
    if not body_rows:
        fail(f"{path}: {entry.label} has no ordinary body/effect pixels")
    body_base_delta = max(body_rows) + 1 - hotspot_y
    if not 6 <= body_base_delta <= 8:
        fail(
            f"{path}: {entry.label} body base is {body_base_delta:+d} pixels from its "
            "hotspot; expected +6 through +8 after the two-pixel safety margin"
        )


def validate_phantom_death_frame_clearance(
    path: Path,
    entry: Entry,
    pixels: list[list[int]],
) -> None:
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    body_points = [
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value != 0 and not 247 <= value <= 250
    ]
    if not body_points:
        fail(f"{path}: {entry.label} has no visible death artwork")
    clipped = [
        (x, y)
        for x, y in body_points
        if x in (0, width - 1) or y in (0, height - 1)
    ]
    if clipped:
        fail(
            f"{path}: {entry.label} death artwork touches a TILE boundary at "
            f"{clipped[:8]}"
        )


def validate_shadow_body_seam(path: Path, entry: Entry, pixels: list[list[int]]) -> None:
    """Reject a missing red seam pixel at any literal magenta/body contact."""
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    bottom_gutter = 3 if entry.name in CONSTRUCTION_BUILDING_TILES else 2
    if entry.name in CONSTRUCTION_BUILDING_TILES:
        clipped_rows = [
            y
            for y, row in enumerate(pixels)
            if row[0] != 0 or row[-1] != 0
        ]
        if clipped_rows:
            fail(
                f"{path}: {entry.label} touches a fixed TILE side boundary "
                f"on rows {clipped_rows[:12]}"
            )
    if entry.name in TRANSITIONAL_DESTRUCTION_TILES:
        clipped_rows = [
            y
            for y, row in enumerate(pixels)
            if row[0] != 0 or row[-1] != 0
        ]
        if clipped_rows or any(pixels[0]):
            fail(
                f"{path}: {entry.label} transitional destruction art touches a "
                f"fixed TILE boundary (side rows={clipped_rows[:12]})"
            )
    for y in range(height - bottom_gutter, height):
        if any(pixels[y]):
            fail(
                f"{path}: {entry.label} writes nontransparent pixels into reserved "
                f"{bottom_gutter}-row bottom gutter at row {y}"
            )
    for y, row in enumerate(pixels):
        if y >= height - bottom_gutter:
            continue
        for x, value in enumerate(row):
            if value != 0:
                continue
            neighbors = [
                pixels[neighbor_y][neighbor_x]
                for neighbor_y in range(max(0, y - 1), min(height, y + 2))
                for neighbor_x in range(max(0, x - 1), min(width, x + 2))
                if (neighbor_x, neighbor_y) != (x, y)
            ]
            if any(248 <= neighbor <= 250 for neighbor in neighbors) and any(
                1 <= neighbor <= 246 for neighbor in neighbors
            ):
                fail(
                    f"{path}: {entry.label} has transparent index 0 at ({x}, {y}) "
                    "touching both magenta shadow and building artwork"
                )

    if entry.name in LOWER_LEFT_BALCONY_PIT_TILES:
        pit_values = [
            pixels[y][x]
            for y in range(136, 139)
            for x in range(58, 67)
        ]
        transparent = sum(value == 0 for value in pit_values)
        red = sum(value == 247 for value in pit_values)
        magenta = sum(248 <= value <= 250 for value in pit_values)
        if transparent:
            fail(
                f"{path}: {entry.label} lower-left balcony pit x=58..66,y=136..138 "
                f"still contains {transparent} transparent pixels"
            )
        if not red or not magenta:
            fail(
                f"{path}: {entry.label} lower-left balcony pit lacks its explicit "
                f"shadow/seam fill (red={red}, magenta={magenta})"
            )

    if entry.name in CONSTRUCTION_BUILDING_TILES:
        validate_construction_shadow_pits(path, entry, pixels)
        validate_enclosed_construction_shadow_holes(path, entry, pixels)


def validate_construction_shadow_pits(
    path: Path,
    entry: Entry,
    pixels: list[list[int]],
) -> None:
    """Reject short zero-index runs bounded by construction art and shadow."""
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    max_gap = 14
    pits: list[tuple[int, int, int, int, int]] = []

    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y < height

    def is_body(value: int) -> bool:
        return 1 <= value <= 246

    def is_shadow_or_seam(value: int) -> bool:
        return 247 <= value <= 250

    # A real pit is a finite transparent run directly separating the two
    # classes. Open exterior terrain has no opposite nonzero boundary and is
    # intentionally ignored.
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        for y in range(height):
            for x in range(width):
                if pixels[y][x] != 0:
                    continue
                previous_x = x - dx
                previous_y = y - dy
                if in_bounds(previous_x, previous_y) and pixels[previous_y][previous_x] == 0:
                    continue
                before = pixels[previous_y][previous_x] if in_bounds(previous_x, previous_y) else 0
                end_x, end_y = x, y
                run_length = 0
                while (
                    run_length < max_gap
                    and in_bounds(end_x, end_y)
                    and pixels[end_y][end_x] == 0
                ):
                    run_length += 1
                    end_x += dx
                    end_y += dy
                if not in_bounds(end_x, end_y) or pixels[end_y][end_x] == 0:
                    continue
                after = pixels[end_y][end_x]
                if (
                    is_shadow_or_seam(before)
                    and is_body(after)
                ) or (
                    is_body(before)
                    and is_shadow_or_seam(after)
                ):
                    pits.append((x, y, dx, dy, run_length))
    if pits:
        fail(
            f"{path}: {entry.label} contains {len(pits)} transparent construction "
            f"shadow/body runs of at most {max_gap} pixels; "
            f"examples=(x,y,dx,dy,length) {pits[:12]}"
        )


def validate_enclosed_construction_shadow_holes(
    path: Path,
    entry: Entry,
    pixels: list[list[int]],
) -> None:
    """Reject transparent islands whose complete boundary is shadow control."""
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    transparent = {
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value == 0
    }
    enclosed_holes: list[tuple[int, int, int]] = []
    while transparent:
        component: set[tuple[int, int]] = set()
        pending = [transparent.pop()]
        touches_exterior = False
        boundary_values: list[int] = []
        while pending:
            x, y = pending.pop()
            component.add((x, y))
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                touches_exterior = True
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    if (neighbor_x, neighbor_y) == (x, y):
                        continue
                    neighbor = (neighbor_x, neighbor_y)
                    if neighbor in transparent:
                        transparent.remove(neighbor)
                        pending.append(neighbor)
                    elif neighbor not in component and pixels[neighbor_y][neighbor_x] != 0:
                        boundary_values.append(pixels[neighbor_y][neighbor_x])
        if (
            not touches_exterior
            and boundary_values
            and all(247 <= value <= 250 for value in boundary_values)
            and any(248 <= value <= 250 for value in boundary_values)
        ):
            first_x, first_y = min(component, key=lambda point: (point[1], point[0]))
            enclosed_holes.append((first_x, first_y, len(component)))

    if enclosed_holes:
        fail(
            f"{path}: {entry.label} contains transparent islands enclosed by "
            f"shadow controls; examples=(x,y,size) {enclosed_holes[:12]}"
        )



def custom_tile_owner(name: bytes) -> tuple[bytes, str] | None:
    for prefix, owner in CUSTOM_TILE_OWNERS.items():
        if name == prefix or name.startswith(prefix):
            return owner
    return None


def validate_expected_entries(path: Path, sections: dict[bytes, list[Entry]]) -> None:
    expected_sections = EXPECTED_CAM_ENTRIES[path.name]
    if set(sections) != set(expected_sections):
        fail(
            f"{path}: unexpected sections; "
            f"expected={sorted(expected_sections)}, actual={sorted(sections)}"
        )
    for section, expected_names in expected_sections.items():
        if not expected_names:
            continue
        actual_names = {entry.name for entry in sections[section]}
        if actual_names != expected_names:
            fail(
                f"{path}: unexpected {section.decode()} entries; "
                f"missing={sorted(expected_names - actual_names)}, "
                f"extra={sorted(actual_names - expected_names)}"
            )


def referenced_indices(image: bytes, mode: str, tile_count: int) -> set[int]:
    values: set[int] = set()
    for offset in range(0, len(image) - 3, 4):
        value = struct.unpack_from("<I", image, offset)[0]
        if mode == "low16":
            value &= 0xFFFF
        if value < tile_count:
            values.add(value)
    return values


def validate_custom_tile_references(
    path: Path,
    sections: dict[bytes, list[Entry]],
    captured: dict[tuple[bytes, bytes], bytes],
) -> None:
    tiles = sections.get(b"TILE", [])
    owner_indices: dict[tuple[bytes, str], list[int]] = {}
    for entry in tiles:
        owner = custom_tile_owner(entry.name)
        if owner:
            owner_indices.setdefault(owner, []).append(entry.index)

    if not owner_indices:
        fail(f"{path}: no custom Phantom TILE entries were found")

    for prefix, expected_count in EXPECTED_CUSTOM_TILE_COUNTS.items():
        count = sum(entry.name.startswith(prefix) for entry in tiles)
        if count != expected_count:
            fail(
                f"{path}: expected {expected_count} {prefix.decode()} custom tiles, found {count}"
            )

    for owner, indices in owner_indices.items():
        image_name, mode = owner
        image = captured.get((b"IMAG", image_name))
        if image is None:
            fail(f"{path}: custom tiles have no owning IMAG entry {image_name!r}")
        used = referenced_indices(image, mode, len(tiles))
        unused = sorted(set(indices) - used)
        if unused:
            fail(
                f"{path}: {image_name.decode(errors='replace')} does not reference "
                f"custom TILE indices {unused[:12]}"
            )

    for entry in tiles:
        if entry.name not in SHADOWED_BUILDING_TILES:
            continue
        tile = captured.get((b"TILE", entry.name))
        if tile is None or len(tile) < 26:
            fail(f"{path}: {entry.label} was not available for palette verification")
        palette_index = struct.unpack_from("<I", tile, 22)[0]
        if palette_index != 560:
            fail(f"{path}: {entry.label} references palette {palette_index}; expected 560")


def validate_phantom_die_directional_sequence(
    path: Path,
    image: bytes,
    tiles: list[Entry],
) -> None:
    if len(image) < 24:
        fail(f"{path}: Phantom IMAG is too short for an animation-set table")

    entry_count = u32(image, 20)
    table_end = 24 + entry_count * 8
    if entry_count <= 0 or table_end > len(image):
        fail(f"{path}: Phantom IMAG has an invalid animation-set table")

    die_set_offset = next(
        (
            u32(image, 24 + index * 8 + 4)
            for index in range(entry_count)
            if u32(image, 24 + index * 8) == 96
        ),
        None,
    )
    if die_set_offset is None or die_set_offset + 0x58 > len(image):
        fail(f"{path}: Phantom IMAG has no readable Die animation set")

    tile_index_by_name = {entry.name: entry.index for entry in tiles}
    populated = [
        struct.unpack_from("<i", image, die_set_offset + 0x38 + slot * 4)[0]
        for slot in range(8)
    ]
    populated = [offset for offset in populated if offset > 0]
    if len(populated) != 6:
        fail(f"{path}: Phantom Die set has {len(populated)} directions; expected six")

    for direction_index, relative_offset in enumerate(populated):
        frame_table = die_set_offset + relative_offset + 0x30
        expected_source_tiles = (
            4723 + direction_index * 3,
            4724 + direction_index * 3,
            4725 + direction_index * 3,
        )
        expected_indices = []
        for source_tile in expected_source_tiles:
            name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
            if name not in tile_index_by_name:
                fail(f"{path}: Phantom Die direction is missing custom TILE {name!r}")
            expected_indices.append(tile_index_by_name[name])

        actual = [
            u32(image, frame_table + frame_index * 8 + 4) & 0xFFFF
            for frame_index in range(6)
        ]
        expected = [
            expected_indices[0],
            expected_indices[1],
            expected_indices[2],
            expected_indices[2],
            expected_indices[2],
            expected_indices[2],
        ]
        if actual != expected:
            fail(
                f"{path}: Phantom Die direction {direction_index} begins {actual}; "
                f"expected directional sequence {expected}"
            )


def validate_phantom_cast_glow_sequence(
    path: Path,
    image: bytes,
    tiles: list[Entry],
) -> None:
    if len(image) < 24:
        fail(f"{path}: Phantom IMAG is too short for an animation-set table")

    entry_count = u32(image, 20)
    table_end = 24 + entry_count * 8
    if entry_count <= 0 or table_end > len(image):
        fail(f"{path}: Phantom IMAG has an invalid animation-set table")

    cast_set_offset = next(
        (
            u32(image, 24 + index * 8 + 4)
            for index in range(entry_count)
            if u32(image, 24 + index * 8) == 128
        ),
        None,
    )
    if cast_set_offset is None or cast_set_offset + 0x58 > len(image):
        fail(f"{path}: Phantom IMAG has no readable Cast animation set")

    populated = [
        struct.unpack_from("<i", image, cast_set_offset + 0x40 + slot * 4)[0]
        for slot in range(8)
    ]
    populated = [offset for offset in populated if offset > 0]
    if len(populated) != 8:
        fail(f"{path}: Phantom Cast set has {len(populated)} directions; expected eight")

    tile_index_by_name = {entry.name: entry.index for entry in tiles}
    effect_stages = (0, 1, 2, 1, 3)
    for direction_index, relative_offset in enumerate(populated):
        frame_table = cast_set_offset + relative_offset + 0x30
        attachment_offsets = [
            u32(image, frame_table + frame_index * 8)
            for frame_index in range(8, 13)
        ]
        expected_attachment_offset = struct.unpack("<I", struct.pack("<hh", 2, -5))[0]
        if any(value != expected_attachment_offset for value in attachment_offsets):
            fail(
                f"{path}: Phantom Cast direction {direction_index} has unexpected "
                f"staff-glow offsets: {[hex(value) for value in attachment_offsets]}"
            )
        actual = [
            u32(image, frame_table + frame_index * 8 + 4) & 0xFFFF
            for frame_index in range(8, 13)
        ]
        expected = []
        for stage in effect_stages:
            name = f"PHM1CastGlowD{direction_index}F{stage}".encode("ascii")
            if name not in tile_index_by_name:
                fail(f"{path}: Phantom Cast direction is missing custom TILE {name!r}")
            expected.append(tile_index_by_name[name])
        if actual != expected:
            fail(
                f"{path}: Phantom Cast direction {direction_index} ends {actual}; "
                f"expected staff-glow sequence {expected}"
            )
        recovery_name = f"PHM1PhantomTile{direction_index * 8}".encode("ascii")
        if recovery_name not in tile_index_by_name:
            fail(f"{path}: Phantom Cast recovery is missing custom TILE {recovery_name!r}")
        recovery_actual = [
            u32(image, frame_table + frame_index * 8 + 4) & 0xFFFF
            for frame_index in range(13, 16)
        ]
        recovery_expected = [tile_index_by_name[recovery_name]] * 3
        if recovery_actual != recovery_expected:
            fail(
                f"{path}: Phantom Cast direction {direction_index} recovers through "
                f"{recovery_actual}; expected matching directional pose {recovery_expected}"
            )


def indexed_v3_body_bounds(tile: bytes) -> tuple[int, int, int, int] | None:
    if len(tile) < 26:
        return None
    version, height, width = struct.unpack_from("<HHH", tile, 0)
    if version != 3:
        return None
    palette_mode = struct.unpack_from("<H", tile, 20)[0]
    pixel_end = struct.unpack_from("<I", tile, 22)[0] if palette_mode == 1 else len(tile)
    offsets = [u32(tile, 26 + row * 4) for row in range(height)]
    points: list[tuple[int, int]] = []
    for row, relative_start in enumerate(offsets):
        cursor = 26 + relative_start
        end = 26 + offsets[row + 1] if row + 1 < height else pixel_end
        while cursor + 4 <= end:
            x_end, count, flags = struct.unpack_from("<HBB", tile, cursor)
            cursor += 4
            x_start = x_end - count
            for column, value in enumerate(tile[cursor : cursor + count], x_start):
                if 1 <= value <= 246:
                    points.append((column, row))
            cursor += count
            if flags & 0x80:
                break
    if not points:
        return None
    return (
        min(x for x, _y in points),
        min(y for _x, y in points),
        max(x for x, _y in points),
        max(y for _x, y in points),
    )


def validate_phantom_cast_tile_geometry(
    path: Path,
    captured: dict[tuple[bytes, bytes], bytes],
) -> None:
    for direction in range(8):
        geometry: list[tuple[int, int, int]] = []
        for stage in range(4):
            body_name = f"PHM1PhantomTile{4746 + direction * 4 + stage - 4586}".encode("ascii")
            body_tile = captured.get((b"TILE", body_name))
            if body_tile is None:
                fail(f"{path}: missing cast body TILE {body_name!r}")
            bounds = indexed_v3_body_bounds(body_tile)
            if bounds is None:
                fail(f"{path}: cast body TILE {body_name!r} has no readable body pixels")
            left, top, right, bottom = bounds
            hotspot_y = struct.unpack_from("<H", body_tile, 12)[0]
            geometry.append((right - left + 1, bottom - top + 1, bottom - hotspot_y))

            glow_name = f"PHM1CastGlowD{direction}F{stage}".encode("ascii")
            glow_tile = captured.get((b"TILE", glow_name))
            if glow_tile is None:
                fail(f"{path}: missing cast glow TILE {glow_name!r}")
            glow_bounds = indexed_v3_body_bounds(glow_tile)
            if glow_bounds is None:
                fail(f"{path}: cast glow TILE {glow_name!r} has no visible glow pixels")
            glow_left, glow_top, glow_right, glow_bottom = glow_bounds
            _version, glow_height, glow_width = struct.unpack_from("<HHH", glow_tile, 0)
            if (
                glow_left < 1
                or glow_top < 1
                or glow_right >= glow_width - 1
                or glow_bottom >= glow_height - 1
            ):
                fail(f"{path}: cast glow TILE {glow_name!r} touches its canvas edge")

        if len(set(geometry)) != 1:
            fail(
                f"{path}: Phantom Cast direction {direction} changes body geometry "
                f"across frames: {geometry}"
            )


def validate_building_destruction_attachments(path: Path, image: bytes) -> None:
    if len(image) < 24:
        fail(f"{path}: Phantoms Haunt IMAG is too short for an animation-set table")

    entry_count = u32(image, 20)
    table_start = 24
    table_end = table_start + entry_count * 8
    if entry_count <= 0 or table_end > len(image):
        fail(f"{path}: Phantoms Haunt IMAG has an invalid animation-set table")

    actual: dict[int, tuple[int, int]] = {}
    for index in range(entry_count):
        entry_offset = table_start + index * 8
        set_id = u32(image, entry_offset)
        if set_id not in EXPECTED_BUILDING_DESTRUCTION_ATTACHMENTS:
            continue

        set_offset = u32(image, entry_offset + 4)
        if set_offset < table_end or set_offset + 68 > len(image):
            fail(f"{path}: destruction attachment set {set_id:#010x} has an invalid offset")
        direction_offset = set_offset + u32(image, set_offset + 64)
        coordinate_offset = direction_offset
        if coordinate_offset + 4 > len(image):
            fail(f"{path}: destruction attachment set {set_id:#010x} has invalid coordinate data")
        actual[set_id] = struct.unpack_from("<hh", image, coordinate_offset)

    if actual != EXPECTED_BUILDING_DESTRUCTION_ATTACHMENTS:
        fail(
            f"{path}: unexpected Phantoms Haunt destruction fire anchors; "
            f"expected={EXPECTED_BUILDING_DESTRUCTION_ATTACHMENTS}, actual={actual}"
        )


def validate_interface_panel_reference(
    path: Path,
    sections: dict[bytes, list[Entry]],
    captured: dict[tuple[bytes, bytes], bytes],
) -> None:
    tiles = sections.get(b"TILE", [])
    panel_entries = [entry for entry in tiles if entry.name == b"PHTIPanel0001"]
    if len(panel_entries) != 1:
        fail(f"{path}: expected exactly one PHTIPanel0001 TILE, found {len(panel_entries)}")
    image = captured.get((b"IMAG", b"PHTIraw textures"))
    if image is None:
        fail(f"{path}: IMAG/PHTIraw textures was not found")
    if panel_entries[0].index not in referenced_indices(image, "u32", len(tiles)):
        fail(f"{path}: IMAG/PHTIraw textures does not reference PHTIPanel0001")


def validate_bcd_copy(output_root: Path) -> None:
    data_bcd = output_root / "Data" / "Phantom.bcd"
    gpl_bcd = output_root / "GPL" / "Phantom.bcd"
    if not gpl_bcd.is_file() or gpl_bcd.stat().st_size == 0:
        fail(f"{gpl_bcd}: compiled GPL output is missing or empty")
    if data_bcd.read_bytes() != gpl_bcd.read_bytes():
        fail(f"{data_bcd}: does not match the compiled GPL/Phantom.bcd")


def validate_phantoms_haunt_identity(output_root: Path) -> None:
    manifest_path = output_root / "PhantomGuildPoc.mmxml"
    manifest = manifest_path.read_text(encoding="utf-8")
    if "<DisplayName lang=\"en_US\">Phantoms Haunt POC</DisplayName>" not in manifest:
        fail(f"{manifest_path}: missing Phantoms Haunt display name")

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    expected_building_identity = (
        'ID="MBPhantomGuild" Name="Phantoms_Haunt" Description="Phantoms Haunt"'
    )
    if expected_building_identity not in units:
        fail(f"{units_path}: building identity was not renamed to Phantoms Haunt")
    if '<DefaultSound value="Phantoms_Haunt"/>' not in units:
        fail(f"{units_path}: building sound name was not renamed to Phantoms_Haunt")

    sounds_path = output_root / "Data" / "phantom_sounds.xml"
    sounds = sounds_path.read_text(encoding="utf-8")
    if 'ID="PH02" Name="Phantoms_Haunt"' not in sounds:
        fail(f"{sounds_path}: building sound description retains the old name")

    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    if "[Phantoms_Haunt]" not in building_data or "(title Phantoms_Haunt)" not in building_data:
        fail(f"{building_data_path}: building data section was not renamed to Phantoms_Haunt")

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    fearless_values = (
        "(PercentageHPRetreat 0)",
        "(enemy_estimation 0.1)",
        "(self_estimation 10.0)",
    )
    missing = [value for value in fearless_values if value not in hero_data]
    if missing:
        fail(f"{hero_data_path}: fearless testing profile is missing {missing}")

    generated_text = "\n".join((manifest, units, sounds, building_data, hero_data))
    for stale_name in ("Phantoms Guild", "Phantoms_Guild", "Phantom_Guild"):
        if stale_name in generated_text:
            fail(f"{output_root}: generated text retains stale building name {stale_name!r}")


def validate_phantom_item_cleanup(output_root: Path) -> None:
    units_path = output_root / "Data" / "phantom_units.xml"
    tree = parse_xml(units_path)
    for item_id in ("FrozenCowl", "BlackIcerod"):
        description = tree.find(f'.//Description[@ID="{item_id}"]')
        if description is None:
            fail(f"{units_path}: Phantom starter item {item_id} is missing")
        can_drop = description.find('.//Attribute[@ID="CanDropItem"]')
        if can_drop is None or can_drop.get("Value") != "0":
            fail(
                f"{units_path}: Phantom starter item {item_id} must set "
                "CanDropItem=0 so realm exit deletes it instead of spawning loot"
            )

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    cleanup_contract = (
        "function Phantom_death(agent thisagent)",
        "$Phantom_remove_starter_items(thisagent);",
        "$gravestone(thisagent);",
        "function Phantom_remove_starter_items(agent thisagent)",
        "While ($AgentHasInventoryItem(#Phantom_Item_FrozenCowl, thisagent))",
        "$DeleteInventoryItem(#Phantom_Item_FrozenCowl, thisagent);",
        "While ($AgentHasInventoryItem(#Phantom_Item_BlackIcerod, thisagent))",
        "$DeleteInventoryItem(#Phantom_Item_BlackIcerod, thisagent);",
    )
    missing = [value for value in cleanup_contract if value not in gpl]
    if missing:
        fail(f"{gpl_path}: Phantom starter-item cleanup is missing {missing}")


def validate_ice_lance_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    if '<EffectorDuration value="3000"/>' not in actions:
        fail(f"{actions_path}: Ice Lance Chill duration is not 3000")

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHo4" Name="ice_lance_chill_icon"',
        '<Info value="NotVisibleInISOView"/>',
        '<ImageIDBase value="PHo3"/>',
        'GPLFunction="Ice_Lance_Chill_End"',
    )
    missing_overlay = [value for value in overlay_contract if value not in overlays]
    if missing_overlay:
        fail(f"{overlays_path}: Ice Lance Chill overlay is missing {missing_overlay}")
    visual_overlay_contract = (
        'ID="PHo5" Name="ice_lance_chill_visual"',
        '<ImageIDBase value="PHo4"/>',
    )
    missing_visual_overlay = [value for value in visual_overlay_contract if value not in overlays]
    if missing_visual_overlay:
        fail(f"{overlays_path}: Ice Lance Chill visual is missing {missing_visual_overlay}")

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    if "(castingrange 180)" not in hero_data:
        fail(f"{hero_data_path}: Phantom base casting range is not 180")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "$spell_attack(thisagent, target, 8);",
        '$createeffector(target, "ice_lance_hit_effector", 0);',
        'If ($CheckEffector(target, "ice_lance_chill_icon"))',
        '$DeleteEffector(target, "ice_lance_chill_icon");',
        "#ATTRIB_MovementRateModifier, 50",
        "#ATTRIB_ActionRateModifier, 500",
        '$CreateEffector(target, "ice_lance_chill_icon", $GetSpellAttribute("ice_lance", "effector_duration"));',
        'If ($CheckEffector(target, "ice_lance_chill_visual"))',
        '$DeleteEffector(target, "ice_lance_chill_visual");',
        '$CreateEffector(target, "ice_lance_chill_visual", $GetSpellAttribute("ice_lance", "effector_duration"));',
        "function Ice_Lance_Chill_End(agent thisagent)",
        "#ATTRIB_MovementRateModifier, -50",
        "#ATTRIB_ActionRateModifier, -500",
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Ice Lance behavior contract is missing {missing_gpl}")
    centered_unit_impact = gpl.index(
        '$createeffector(target, "ice_lance_hit_effector", 0);'
    )
    building_branch = gpl.index(
        'If (target\'s "Type" == "Building" || target\'s "Type" == "Lair")'
    )
    chill_application = gpl.index(
        'If ($CheckEffector(target, "ice_lance_chill_icon"))'
    )
    if not centered_unit_impact < building_branch < chill_application:
        fail(
            f"{gpl_path}: native hit overlay must apply before the "
            "building/lair Chill guard"
        )


def validate_frost_armor_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    action_contract = (
        'ID="WRa3" Name="frost_armor"',
        '<EffectorDuration value="21000"/>',
        '<SpellType value="CombatUtility"/>',
        '<CharacterLevel value="3"/>',
        '<ValidationScript value="Frost_Armor_Check"/>',
    )
    missing_action = [value for value in action_contract if value not in actions]
    if missing_action:
        fail(f"{actions_path}: Frost Armor action is missing {missing_action}")

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if '<Spell ID="1" Value="frost_armor"/>' not in units:
        fail(f"{units_path}: Phantom does not list Frost Armor as an allowed spell")

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHo1" Name="frost_armor_effector"',
        '<ImageIDBase value="PHf1"/>',
        'ID="PHo2" Name="frost_armor_icon"',
        'ID="PHo6" Name="frost_armor_spent"',
        'ID="PHo7" Name="frost_armor_frozen_timer"',
        'GPLFunction="Frost_Armor_Frozen_End"',
        'ID="PHo8" Name="frost_armor_frozen_small"',
        '<ImageIDBase value="PHf2"/>',
        'ID="PHo9" Name="frost_armor_frozen_medium"',
        '<ImageIDBase value="PHf3"/>',
        'ID="PH10" Name="frost_armor_frozen_large"',
        '<ImageIDBase value="PHf4"/>',
    )
    missing_overlay = [value for value in overlay_contract if value not in overlays]
    if missing_overlay:
        fail(f"{overlays_path}: Frost Armor overlays are missing {missing_overlay}")

    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    if "(Lived_In_Script Phantom_Lived_In)" not in building_data:
        fail(f"{building_data_path}: full-health Frost Armor recharge wrapper is missing")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "If ($Phantom_Try_Frost_Armor(thisagent) == False)",
        "$Wizard_tree(thisagent);",
        "function Frost_Armor_Begin(agent thisagent, agent target)",
        'thisagent\'s "Reborn_Counter" = 1;',
        '$createeffector(thisagent, "frost_armor_effector", 180000);',
        "#ATTRIB_Armor_Basic_Damage, 10000",
        '$clearlist(thisagent\'s "Hostiles");',
        '$Frost_Armor_Begin(thisagent, thisagent);',
        '$PerformAction(thisagent, "Basic_Cast", thisagent);',
        "function Phantom_Arm_Frost_Armor_In_Combat(agent thisagent) is boolean",
        'thisagent\'s "ActiveScript" != $Attack_object',
        'thisagent\'s "BackScript" != $Attack_object',
        "function Phantom_Frost_Armor_Watch(agent thisagent)",
        "$Phantom_Frost_Armor_Recharge_Check(thisagent);",
        "If ($Phantom_Arm_Frost_Armor_In_Combat(thisagent))",
        'If (thisagent\'s "Reborn_Counter" != 1)',
        'If ($CheckEffector(thisagent, "frost_armor_effector") == False)',
        'Foreach hostile in thisagent\'s "Hostiles" do',
        'If (hostile\'s "Target" == thisagent)',
        'attack_range = $GetAttribute(hostile, #ATTRIB_MaxAttackRange);',
        '$DistanceBetweenAgents(hostile, thisagent) <= attack_range + 24',
        '$ClearList(thisagent\'s "Hostiles");',
        'thisagent\'s "Reborn_Counter" = 2;',
        '$DeleteEffector(thisagent, "frost_armor_effector");',
        'If (attacker\'s "Type" == "Building" || attacker\'s "Type" == "Lair")',
        "$Frost_Armor_Freeze(attacker);",
        "$Freeze_Unit(target);",
        '$CreateEffector(target, "frost_armor_frozen_small", 3000);',
        '$CreateEffector(target, "frost_armor_frozen_medium", 3000);',
        '$CreateEffector(target, "frost_armor_frozen_large", 3000);',
        '$CreateEffector(target, "frost_armor_frozen_timer", 3000);',
        "$UnFreeze_Unit(thisagent);",
        "function Phantom_Frost_Armor_Recharge_Check(agent thisagent)",
        'If (thisagent\'s "Reborn_Counter" != 2)',
        "$InsideBuilding(thisagent) == False",
        'thisagent\'s "ActiveScript" == $rest_at_inn',
        'thisagent\'s "ActiveScript" == $Done_resting_inn',
        'thisagent\'s "ActiveScript" == $Rest_at_guild',
        'thisagent\'s "ActiveScript" == $Phantom_Rest_At_Guild',
        'thisagent\'s "ActiveScript" == $Done_resting_guild',
        "function Phantom_Rest_At_Guild(agent thisagent)",
        "$Rest_At_Guild(thisagent);",
        'thisagent\'s "Reborn_Counter" = 0;',
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Frost Armor behavior contract is missing {missing_gpl}")
    if "$Phantom_Ensure_Frost_Armor_Passive" in gpl:
        fail(f"{gpl_path}: level-1 Frost Armor watcher still invokes passive armor")

    consume = gpl.index('thisagent\'s "Reborn_Counter" = 2;')
    incoming_filter = gpl.index('If (hostile\'s "Target" == thisagent)')
    range_filter = gpl.index(
        '$DistanceBetweenAgents(hostile, thisagent) <= attack_range + 24'
    )
    building_guard = gpl.index(
        'If (attacker\'s "Type" == "Building" || attacker\'s "Type" == "Lair")'
    )
    freeze = gpl.index("$Frost_Armor_Freeze(attacker);")
    if not incoming_filter < range_filter < consume < building_guard < freeze:
        fail(
            f"{gpl_path}: Frost Armor must validate an in-range incoming "
            "attacker, consume, then apply the building/lair freeze exclusion"
        )

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    stat_contract = (
        '<Vitality value="8"/>',
        '<MagicResistance value="25"/>',
        '<Parry value="20"/>',
        '<Dodge value="25"/>',
    )
    missing_stats = [value for value in stat_contract if value not in units]
    if missing_stats:
        fail(f"{units_path}: Phantom rebalance stats are missing {missing_stats}")

    item_contract = (
        '#ATTRIB_Armor_Basic_Damage, 1',
        '#ATTRIB_Weapon_Basic_Damage, 8',
    )
    missing_items = [value for value in item_contract if value not in gpl]
    if missing_items:
        fail(f"{gpl_path}: Phantom starter-item bonuses are missing {missing_items}")
    if "#ATTRIB_Parry, 5" in gpl:
        fail(f"{gpl_path}: experimental Black Icerod Parry bonus is still present")
    if 'thisagent\'s "castingrange" +=' in gpl:
        fail(f"{gpl_path}: unsafe runtime casting-range mutation is present")
    if 'Special_Boolean' in gpl:
        fail(f"{gpl_path}: experimental passive-armor item state is still present")


def validate(output_root: Path) -> None:
    if not output_root.is_dir():
        fail(f"{output_root}: build output directory does not exist")
    validate_manifest(output_root)
    validate_descriptions(output_root)
    validate_bcd_copy(output_root)
    validate_phantoms_haunt_identity(output_root)
    validate_phantom_item_cleanup(output_root)
    validate_ice_lance_contract(output_root)
    validate_frost_armor_contract(output_root)

    archive_results: dict[str, tuple[dict[bytes, list[Entry]], dict[tuple[bytes, bytes], bytes]]] = {}
    for filename in EXPECTED_CAM_ENTRIES:
        path = output_root / "Data" / filename
        if not path.is_file():
            fail(f"{path}: required archive is missing")
        result = validate_archive(path)
        validate_expected_entries(path, result[0])
        archive_results[filename] = result

    gpltext_path = output_root / "Data" / "phantom_gpltext.cam"
    qitm = archive_results["phantom_gpltext.cam"][1].get((b"STRT", b"QITM"))
    if qitm is None:
        fail(f"{gpltext_path}: STRT/QITM was not found")
    validate_indexed_item_strings(gpltext_path, qitm)

    textdata_path = output_root / "Data" / "phantom_textdata.cam"
    textdata_captured = archive_results["phantom_textdata.cam"][1]
    unit_names = textdata_captured.get((b"STRT", b"UNTN"))
    guild_strings = textdata_captured.get((b"STRT", b"AP07"))
    if unit_names is None or b"Phantoms Haunt" not in unit_names:
        fail(f"{textdata_path}: unit names do not contain Phantoms Haunt")
    if guild_strings is None or b"PHANTOMS HAUNT" not in guild_strings:
        fail(f"{textdata_path}: recruit dialog does not contain PHANTOMS HAUNT")
    help_text = archive_results["phantom_gpltext.cam"][1].get((b"STRT", b"HPTX"))
    if help_text is None or b"The Phantoms Haunt gathers" not in help_text:
        fail(f"{gpltext_path}: building help text was not renamed to Phantoms Haunt")

    maindata_path = output_root / "Data" / "phantom_maindata.cam"
    sections, captured = archive_results["phantom_maindata.cam"]
    validate_custom_tile_references(maindata_path, sections, captured)
    phantom_image = captured.get((b"IMAG", b"PHM1Phantom"))
    if phantom_image is None:
        fail(f"{maindata_path}: IMAG/PHM1Phantom was not found")
    validate_phantom_die_directional_sequence(
        maindata_path,
        phantom_image,
        sections.get(b"TILE", []),
    )
    validate_phantom_cast_glow_sequence(
        maindata_path,
        phantom_image,
        sections.get(b"TILE", []),
    )
    validate_phantom_cast_tile_geometry(maindata_path, captured)
    building_image = captured.get((b"IMAG", b"PHG1Phantom Guild"))
    if building_image is None:
        fail(f"{maindata_path}: IMAG/PHG1Phantom Guild was not found")
    validate_building_destruction_attachments(maindata_path, building_image)

    interface_path = output_root / "Data" / "phantom_interfacedata.cam"
    sections, captured = archive_results["phantom_interfacedata.cam"]
    validate_interface_panel_reference(interface_path, sections, captured)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated Phantoms Haunt package.")
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        validate(args.output_root.resolve())
    except ValidationError as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    print("Verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
