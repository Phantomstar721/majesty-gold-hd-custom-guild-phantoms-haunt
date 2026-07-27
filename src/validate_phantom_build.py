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

PHANTOM_COWL_TIER_NAMES = (
    "Frozen Cowl",
    "Icy Cowl",
    "Hardened Ice Cowl",
    "Eternal Ice Cowl",
)
PHANTOM_ICEROD_TIER_NAMES = (
    "Black Icerod",
    "Dark Icerod",
    "Deep Icerod",
    "Eternal Icerod",
)


def phantom_equipment_item_records() -> list[tuple[int, str, str, bytes]]:
    records: list[tuple[int, str, str, bytes]] = []
    for family in ("cowl", "icerod"):
        for struct_level in range(4):
            for magic_level in range(4):
                combination = struct_level * 4 + magic_level
                if family == "cowl":
                    item_id = 80 if combination == 0 else 82 + combination
                    agent_name = (
                        "FrozenCowl"
                        if combination == 0
                        else f"PhantomCowlS{struct_level}M{magic_level}"
                    )
                    attribute_name = (
                        "Phantom_Item_FrozenCowl"
                        if combination == 0
                        else f"Phantom_Item_Cowl_S{struct_level}_M{magic_level}"
                    )
                    display_name = PHANTOM_COWL_TIER_NAMES[struct_level]
                    bonus = f"(+{2 + struct_level} armor, +{magic_level} magic armor)"
                else:
                    item_id = 81 if combination == 0 else 97 + combination
                    agent_name = (
                        "BlackIcerod"
                        if combination == 0
                        else f"PhantomIcerodS{struct_level}M{magic_level}"
                    )
                    attribute_name = (
                        "Phantom_Item_BlackIcerod"
                        if combination == 0
                        else f"Phantom_Item_Icerod_S{struct_level}_M{magic_level}"
                    )
                    display_name = PHANTOM_ICEROD_TIER_NAMES[struct_level]
                    bonus = (
                        f"(+{8 + struct_level} damage, +{magic_level} magic, "
                        f"+{5 + struct_level * 5} parry, "
                        f"+{10 + magic_level * 10} cast range)"
                    )
                text = f"{display_name}\n\x01FFDDAA{bonus}".encode("latin-1")
                records.append((item_id, agent_name, attribute_name, text))
    return sorted(records)


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
            b"WRa4Icy Touch",
            b"WRa5Blizzard",
            b"PHo3Ice Lance Hit",
            b"PHo4chill_icon",
            b"PHc3emp_chill_icon",
            b"PHg1Gravechill",
            b"PHg2Gravechill Hit",
            b"PHf1Frost Crystal",
            b"PHf2Frozen Small",
            b"PHf3Frozen Medium",
            b"PHf4Frozen Large",
            b"PHc2Call to Grave",
            b"PHe1Soul Flame Icon",
            b"PHe2Soul Flame",
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
        *((("Unit", agent_name) for _, agent_name, _, _ in phantom_equipment_item_records())),
        ("Unit", "FrostArmorBonus"),
        ("Unit", "MBPhantomGuild"),
    },
    "phantom_actions.xml": {
        ("Action", "WRa2"),
        ("Action", "WRa3"),
        ("Action", "WRa4"),
        ("Action", "WRa5"),
        ("Action", "WRa6"),
        ("Action", "WRa7"),
    },
    "phantom_projectiles.xml": {("Unit", "PHp1")},
    "phantom_overlays.xml": {
        ("Unit", "PHo1"),
        ("Unit", "PHo2"),
        ("Unit", "PHo3"),
        ("Unit", "PHo4"),
        ("Unit", "PH11"),
        ("Unit", "PHo6"),
        ("Unit", "PHo7"),
        ("Unit", "PHo8"),
        ("Unit", "PHo9"),
        ("Unit", "PH10"),
        ("Unit", "PHg1"),
        ("Unit", "PHg2"),
        ("Unit", "PHc2"),
        ("Unit", "PHe1"),
        ("Unit", "PHe2"),
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
    b"PHc3EmpChillTile": (b"PHc3emp_chill_icon", "u32"),
    b"PHg1Skull": (b"PHg1Gravechill", "u32"),
    b"PHg2SkullHit": (b"PHg2Gravechill Hit", "u32"),
    b"PHf1Crystal": (b"PHf1Frost Crystal", "u32"),
    b"PHf2Frozen": (b"PHf2Frozen Small", "u32"),
    b"PHf3Frozen": (b"PHf3Frozen Medium", "u32"),
    b"PHf4Frozen": (b"PHf4Frozen Large", "u32"),
    b"PHc2Portal": (b"PHc2Call to Grave", "u32"),
    b"PHe1FlameIcon": (b"PHe1Soul Flame Icon", "u32"),
    b"PHe2FlameCast": (b"PHe2Soul Flame", "u32"),
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
    b"PHc3EmpChillTile": 29,
    b"PHg1Skull": 29,
    b"PHg2SkullHit": 6,
    b"PHf1Crystal": 29,
    b"PHf2Frozen": 29,
    b"PHf3Frozen": 29,
    b"PHf4Frozen": 29,
    b"PHc2Portal": 22,
    b"PHe1FlameIcon": 29,
    b"PHe2FlameCast": 6,
}

ALIGNED_PHANTOM_DISSOLVE_TILES = {
    f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
    for source_tile in range(4779, 4786)
}

CLIP_SAFE_PHANTOM_DEATH_TILES = {
    *{
        f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        for source_tile in range(4722, 4746)
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
    if count <= 112:
        fail(
            f"{path}: STRT/QITM has {count} strings; "
            "Phantom equipment variants require item IDs through 112"
        )
    expected_items = [
        *((item_id, text) for item_id, _, _, text in phantom_equipment_item_records()),
        (82, b"Frost Armor\n\x01FFDDAA(+10 armor)"),
    ]
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


def validate_phantom_primary_direction_topology(
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

    set_offsets = {
        u32(image, 24 + index * 8): u32(image, 24 + index * 8 + 4)
        for index in range(entry_count)
    }
    tile_index_by_name = {entry.name: entry.index for entry in tiles}
    # Stand and Cast begin with one non-art control frame. The other primary
    # sets begin directly with their first directional body frame.
    contracts = {
        1: (4586, 8, 0x28),   # Walk
        8: (4650, 1, 0x30),   # Stand
        64: (4658, 4, 0x28),  # Special
        16: (4690, 4, 0x28),  # Attack
        96: (4722, 3, 0x28),  # Die
        128: (4746, 4, 0x30), # Cast
    }
    for set_id, (first_source_tile, stride, first_frame_offset) in contracts.items():
        set_offset = set_offsets.get(set_id)
        if set_offset is None or set_offset + 0x60 > len(image):
            fail(f"{path}: Phantom is missing primary animation set {set_id}")
        direction_offsets = [
            struct.unpack_from("<i", image, set_offset + 0x40 + slot * 4)[0]
            for slot in range(8)
        ]
        if any(offset <= 0 for offset in direction_offsets):
            fail(
                f"{path}: primary animation set {set_id} does not have eight "
                "populated direction slots"
            )
        for direction, relative_offset in enumerate(direction_offsets):
            source_tile = first_source_tile + direction * stride
            name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
            expected = tile_index_by_name.get(name)
            if expected is None:
                fail(
                    f"{path}: primary animation set {set_id} direction {direction} "
                    f"is missing custom TILE {name!r}"
                )
            frame_offset = set_offset + relative_offset + first_frame_offset
            actual = u32(image, frame_offset + 4) & 0xFFFF
            if actual != expected:
                fail(
                    f"{path}: primary animation set {set_id} direction {direction} "
                    f"starts with TILE index {actual}; expected {expected}"
                )


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
        struct.unpack_from("<i", image, die_set_offset + 0x40 + slot * 4)[0]
        for slot in range(8)
    ]
    populated = [offset for offset in populated if offset > 0]
    if len(populated) != 8:
        fail(f"{path}: Phantom Die set has {len(populated)} directions; expected eight")

    for direction_index, relative_offset in enumerate(populated):
        frame_table = die_set_offset + relative_offset + 0x28
        expected_source_tiles = (
            4722 + direction_index * 3,
            4723 + direction_index * 3,
            4724 + direction_index * 3,
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
        glow_centers_x2: list[tuple[int, int]] = []
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
            glow_centers_x2.append(
                (glow_left + glow_right, glow_top + glow_bottom)
            )
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
        center_y_values = [center_y for _center_x, center_y in glow_centers_x2]
        if max(center_y_values) - min(center_y_values) > 2:
            fail(
                f"{path}: Phantom Cast direction {direction} glow anchor bounces "
                f"vertically across frames: {glow_centers_x2}"
            )


def validate_phantom_action_size_against_stand(
    path: Path,
    captured: dict[tuple[bytes, bytes], bytes],
) -> None:
    expected_stand_heights = (61, 55, 52, 50, 50, 56, 60, 61)

    def body_geometry(source_tile: int) -> tuple[int, int, int, int, int, int]:
        name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        tile = captured.get((b"TILE", name))
        if tile is None:
            fail(f"{path}: missing normalized Phantom action TILE {name!r}")
        bounds = indexed_v3_body_bounds(tile)
        if bounds is None:
            fail(f"{path}: normalized Phantom action TILE {name!r} has no body")
        left, top, right, bottom = bounds
        _version, canvas_height, canvas_width = struct.unpack_from("<HHH", tile, 0)
        hotspot_y = struct.unpack_from("<H", tile, 12)[0]
        return (
            right - left + 1,
            bottom - top + 1,
            bottom + 1 - hotspot_y,
            left,
            top,
            min(canvas_width - 1 - right, canvas_height - 1 - bottom),
        )

    for direction, expected_height in enumerate(expected_stand_heights):
        stand = body_geometry(4650 + direction)
        if stand[1] != expected_height:
            fail(
                f"{path}: approved Stand direction {direction} is {stand[1]} px high; "
                f"expected {expected_height}"
            )
        for label, source_tiles in (
            (
                "Walk",
                [4586 + direction * 8 + frame for frame in range(8)],
            ),
            (
                "Cast",
                [4746 + direction * 4 + frame for frame in range(4)],
            ),
        ):
            geometries = [body_geometry(source_tile) for source_tile in source_tiles]
            bad_heights = [
                geometry[1]
                for geometry in geometries
                if abs(geometry[1] - expected_height) > 1
            ]
            if bad_heights:
                fail(
                    f"{path}: Phantom {label} direction {direction} heights "
                    f"{[geometry[1] for geometry in geometries]} drift from "
                    f"Stand height {expected_height}"
                )
            if any(
                geometry[3] < 1 or geometry[4] < 1 or geometry[5] < 1
                for geometry in geometries
            ):
                fail(
                    f"{path}: Phantom {label} direction {direction} touches an "
                    "expanded TILE boundary"
                )
            if label == "Cast":
                bad_bases = [
                    geometry[2]
                    for geometry in geometries
                    if abs(geometry[2] - stand[2]) > 1
                ]
                if bad_bases:
                    fail(
                        f"{path}: Phantom Cast direction {direction} body bases "
                        f"{[geometry[2] for geometry in geometries]} drift from "
                        f"Stand base {stand[2]}"
                    )


def validate_call_to_grave_portal_animation(
    path: Path,
    image: bytes,
    tiles: list[Entry],
    captured: dict[tuple[bytes, bytes], bytes],
) -> None:
    if len(image) < 24:
        fail(f"{path}: Call to Grave IMAG is too short")
    entry_count = u32(image, 20)
    sets: dict[int, list[int]] = {}
    for index in range(entry_count):
        set_id = u32(image, 24 + index * 8)
        set_offset = u32(image, 28 + index * 8)
        if set_offset + 68 > len(image):
            fail(f"{path}: Call to Grave set {set_id} is truncated")
        direction_offset = set_offset + u32(image, set_offset + 64)
        frame_count = u32(image, direction_offset + 4) >> 16
        frame_start = direction_offset + 20
        last_tile_end = frame_start + (frame_count - 1) * 8 + 4
        if frame_count <= 0 or last_tile_end > len(image):
            fail(f"{path}: Call to Grave set {set_id} has an invalid frame table")
        sets[set_id] = [
            u32(image, frame_start + frame * 8)
            for frame in range(frame_count)
        ]

    expected_counts = {80: 8, 64: 8, 96: 7}
    actual_counts = {set_id: len(frames) for set_id, frames in sets.items()}
    if actual_counts != expected_counts:
        fail(
            f"{path}: Call to Grave open/hold/close counts are {actual_counts}; "
            f"expected {expected_counts}"
        )

    tile_by_index = {entry.index: entry for entry in tiles}
    phase_widths: dict[int, list[int]] = {}
    for set_id, frame_indices in sets.items():
        phase_widths[set_id] = []
        for tile_index in frame_indices:
            entry = tile_by_index.get(tile_index)
            if entry is None or not entry.name.startswith(b"PHc2Portal"):
                fail(
                    f"{path}: Call to Grave set {set_id} references non-portal "
                    f"TILE index {tile_index}"
                )
            tile = captured.get((b"TILE", entry.name))
            if tile is None:
                fail(f"{path}: Call to Grave TILE {entry.name!r} was not captured")
            _version, height, width = struct.unpack_from("<HHH", tile, 0)
            hotspot = struct.unpack_from("<HH", tile, 10)
            if (width, height, hotspot) != (84, 116, (42, 31)):
                fail(
                    f"{path}: Call to Grave TILE {entry.name!r} has "
                    f"{width}x{height} hotspot {hotspot}; expected "
                    "84x116 hotspot (42, 31)"
                )
            bounds = indexed_v3_body_bounds(tile)
            if bounds is None:
                fail(f"{path}: Call to Grave TILE {entry.name!r} is invisible")
            phase_widths[set_id].append(bounds[2] - bounds[0] + 1)

    if phase_widths[80] != sorted(phase_widths[80]):
        fail(f"{path}: Call to Grave opening widths are not monotonic")
    if len(set(phase_widths[64])) != 1:
        fail(f"{path}: Call to Grave hold frames do not remain fully open")
    if phase_widths[96] != sorted(phase_widths[96], reverse=True):
        fail(f"{path}: Call to Grave closing widths are not monotonic")


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
        "(evaluationScript\teval_enemies_nearby)",
    )
    missing = [value for value in fearless_values if value not in hero_data]
    if missing:
        fail(f"{hero_data_path}: fearless testing profile is missing {missing}")
    if "(evaluationScript\twizard_eval_nearby)" in hero_data:
        fail(f"{hero_data_path}: Phantom still uses the Wizard threat evaluator")

    generated_text = "\n".join((manifest, units, sounds, building_data, hero_data))
    for stale_name in ("Phantoms Guild", "Phantoms_Guild", "Phantom_Guild"):
        if stale_name in generated_text:
            fail(f"{output_root}: generated text retains stale building name {stale_name!r}")


def validate_phantom_item_cleanup(output_root: Path) -> None:
    units_path = output_root / "Data" / "phantom_units.xml"
    tree = parse_xml(units_path)
    item_ids = [
        *(agent_name for _, agent_name, _, _ in phantom_equipment_item_records()),
        "FrostArmorBonus",
    ]
    for item_id in item_ids:
        description = tree.find(f'.//Description[@ID="{item_id}"]')
        if description is None:
            fail(f"{units_path}: Phantom class item {item_id} is missing")
        can_drop = description.find('.//Attribute[@ID="CanDropItem"]')
        if can_drop is None or can_drop.get("Value") != "0":
            fail(
                f"{units_path}: Phantom class item {item_id} must set "
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
        "While ($AgentHasInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent))",
        "$DeleteInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent);",
        "Function Hero_Drop_Quest_Items (agent ThisAgent)",
        'If (ThisAgent\'s "Title" == "Phantom")',
        'If ($isdead(ThisAgent) == False)',
        '$KillThread(ThisAgent\'s "QuestScript");',
        "$Phantom_remove_starter_items(ThisAgent);",
        "While ($AgentHasInventoryItem(WhatItem, ThisAgent))",
        "$DeleteInventoryItem(WhatItem, ThisAgent);",
        "WhatItem != #QItem_Magic_Sword",
        "WhatItem != #MarketItem_Ring_Protection",
        "WhatItem != #MarketItem_Market3_Item",
        "If ($CanDropInventoryItem(WhatItem) == True)",
        "agentType = $GetInventoryItemAgentType(WhatItem);",
        '$SpawnUnit(ThisAgent, agentType, "Override", $Concatenate($MakeInventoryAttribute(WhatItem), 0));',
    )
    missing = [value for value in cleanup_contract if value not in gpl]
    if missing:
        fail(f"{gpl_path}: Phantom starter-item cleanup is missing {missing}")

    if gpl.count("Function Hero_Drop_Quest_Items (agent ThisAgent)") != 1:
        fail(
            f"{gpl_path}: Phantom package must contain exactly one stock-compatible "
            "Hero_Drop_Quest_Items replacement"
        )

    cleanup_helper = gpl.index("function Phantom_remove_starter_items(agent thisagent)")
    drop_function = gpl.index("Function Hero_Drop_Quest_Items (agent ThisAgent)")
    phantom_guard = gpl.index('If (ThisAgent\'s "Title" == "Phantom")', drop_function)
    watcher_stop = gpl.index('$KillThread(ThisAgent\'s "QuestScript");', phantom_guard)
    class_cleanup = gpl.index(
        "$Phantom_remove_starter_items(ThisAgent);",
        watcher_stop,
    )
    stock_loop = gpl.index(
        "While ($AgentHasInventoryItem(WhatItem, ThisAgent))",
        class_cleanup,
    )
    generic_delete = gpl.index(
        "$DeleteInventoryItem(WhatItem, ThisAgent);",
        stock_loop,
    )
    generic_drop_check = gpl.index(
        "If ($CanDropInventoryItem(WhatItem) == True)",
        generic_delete,
    )
    generic_spawn = gpl.index(
        '$SpawnUnit(ThisAgent, agentType, "Override", $Concatenate($MakeInventoryAttribute(WhatItem), 0));',
        generic_drop_check,
    )
    if not (
        cleanup_helper
        < drop_function
        < phantom_guard
        < watcher_stop
        < class_cleanup
        < stock_loop
        < generic_delete
        < generic_drop_check
        < generic_spawn
    ):
        fail(
            f"{gpl_path}: realm-exit cleanup must stop the Phantom watcher and "
            "delete class items before preserving the stock remaining-item loop"
        )


def validate_ice_lance_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    if '<EffectorDuration value="3000"/>' not in actions:
        fail(f"{actions_path}: Ice Lance Chill duration is not 3000")

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHo4" Name="ice_lance_chill_icon"',
        '<ImageIDBase value="PHo4"/>',
        'ID="PH11" Name="ice_lance_empowered_chill_icon"',
        '<ImageIDBase value="PHc3"/>',
    )
    missing_overlay = [value for value in overlay_contract if value not in overlays]
    if missing_overlay:
        fail(f"{overlays_path}: Ice Lance Chill overlay is missing {missing_overlay}")
    if 'ID="PHo5"' in overlays or "ice_lance_chill_visual" in overlays:
        fail(
            f"{overlays_path}: obsolete separate Chill visual remains; the "
            "watcher-owned snowflake must be the only visible Chill effector"
        )
    chill_overlay_start = overlays.index('ID="PHo4" Name="ice_lance_chill_icon"')
    chill_overlay_end = overlays.index("</Description>", chill_overlay_start)
    chill_overlay = overlays[chill_overlay_start:chill_overlay_end]
    if "GPLFunction=" in chill_overlay:
        fail(
            f"{overlays_path}: Chill icon must not own modifier cleanup; "
            "the counter watcher owns the full lifecycle"
        )
    empowered_overlay_start = overlays.index(
        'ID="PH11" Name="ice_lance_empowered_chill_icon"'
    )
    empowered_overlay_end = overlays.index("</Description>", empowered_overlay_start)
    empowered_overlay = overlays[empowered_overlay_start:empowered_overlay_end]
    if "GPLFunction=" in empowered_overlay:
        fail(
            f"{overlays_path}: empowered Chill icon must not own modifier "
            "cleanup; the shared counter watcher owns the lifecycle"
        )

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    if "(castingrange 190)" not in hero_data:
        fail(
            f"{hero_data_path}: Phantom Icerod-equipped casting range is not 190"
        )

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "$spell_attack(thisagent, target, 8);",
        '$createeffector(target, "ice_lance_hit_effector", 0);',
        '$Phantom_Apply_Chill(thisagent, target, $GetSpellAttribute("ice_lance", "effector_duration"));',
        "function Phantom_Apply_Chill(agent source, agent target, integer duration)",
        'If ($HasAttribute("PhantomChillRemaining", target) == False)',
        '$AddAttribute(target, "PhantomChillRemaining", "integer", duration);',
        '$AddAttribute(target, "PhantomChillActive", "boolean", False);',
        '$AddAttribute(target, "PhantomChillTier", "integer", 0);',
        '$AddAttribute(target, "PhantomChillWatch", "function", $Phantom_Chill_Watch);',
        'If ($HasAttribute("PhantomChillIconDelay", target) == False)',
        '$AddAttribute(target, "PhantomChillIconDelay", "integer", 0);',
        'If (target\'s "PhantomChillActive" == False)',
        "#ATTRIB_MovementRateModifier, 50",
        "#ATTRIB_ActionRateModifier, 500",
        "#ATTRIB_MovementRateModifier, 100",
        "#ATTRIB_ActionRateModifier, 1000",
        '$Phantom_Eternal_Soul_Active(source)',
        '$Phantom_Chill_Sync_Icon(target);',
        "function Phantom_Chill_Sync_Icon(agent target)",
        'target\'s "PhantomChillIconDelay" = 200;',
        'If ($CheckEffector(target, "ice_lance_chill_icon") == False)',
        '$CreateEffector(target, "ice_lance_chill_icon", 1, "infinite");',
        'If ($CheckEffector(target, "ice_lance_empowered_chill_icon") == False)',
        '$CreateEffector(target, "ice_lance_empowered_chill_icon", 1, "infinite");',
        'If ($IsRunning(target\'s "PhantomChillWatch") == False)',
        '$NewThread(target\'s "PhantomChillWatch", 100, target);',
        "function Phantom_Chill_Watch(agent thisagent)",
        'thisagent\'s "PhantomChillIconDelay" -= 100;',
        '$Phantom_Chill_Sync_Icon(thisagent);',
        'thisagent\'s "PhantomChillRemaining" -= 100;',
        '$KillThread(thisagent\'s "PhantomChillWatch");',
        'thisagent\'s "PhantomChillActive" = False;',
        'thisagent\'s "PhantomChillTier" = 0;',
        'thisagent\'s "PhantomChillIconDelay" = 0;',
        '$DeleteEffector(thisagent, "ice_lance_chill_icon");',
        '$DeleteEffector(thisagent, "ice_lance_empowered_chill_icon");',
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Ice Lance behavior contract is missing {missing_gpl}")
    if "ice_lance_chill_visual" in gpl:
        fail(f"{gpl_path}: obsolete separate Chill visual callback path remains")
    hit_start = gpl.index("function Ice_Lance_Hit(agent thisagent, agent target)")
    helper_start = gpl.index(
        "function Phantom_Apply_Chill(agent source, agent target, integer duration)",
        hit_start,
    )
    helper_end = gpl.index("function Phantom_Chill_Watch(agent thisagent)", helper_start)
    helper_gpl = gpl[helper_start:helper_end]
    init_guard = helper_gpl.index(
        'If ($HasAttribute("PhantomChillRemaining", target) == False)'
    )
    init_end = helper_gpl.index("\n\tdesired_tier = 1;", init_guard)
    for init_line in (
        '$AddAttribute(target, "PhantomChillRemaining", "integer", duration);',
        '$AddAttribute(target, "PhantomChillActive", "boolean", False);',
        '$AddAttribute(target, "PhantomChillTier", "integer", 0);',
        '$AddAttribute(target, "PhantomChillWatch", "function", $Phantom_Chill_Watch);',
    ):
        if not init_guard < helper_gpl.index(init_line) < init_end:
            fail(
                f"{gpl_path}: Chill dynamic attribute {init_line!r} is not "
                "inside its one-time initialization guard"
            )
    icon_guard = helper_gpl.index(
        'If ($CheckEffector(target, "ice_lance_chill_icon") == False)'
    )
    icon_create = helper_gpl.index(
        '$CreateEffector(target, "ice_lance_chill_icon", 1, "infinite");'
    )
    if not icon_guard < icon_create:
        fail(
            f"{gpl_path}: Chill icon creation is not protected by the "
            "authoritative effector-existence guard"
        )
    for icon_name in (
        "ice_lance_chill_icon",
        "ice_lance_empowered_chill_icon",
    ):
        if helper_gpl.count(
            f'$CreateEffector(target, "{icon_name}", 1, "infinite");'
        ) != 1:
            fail(
                f"{gpl_path}: {icon_name} must have exactly one guarded "
                "persistent creation site"
            )
    forbidden_refresh = (
        '$CreateEffector(target, "ice_lance_chill_icon", duration);',
        '$CreateEffector(target, "ice_lance_empowered_chill_icon", duration);',
        "function Ice_Lance_Chill_End(agent thisagent)",
    )
    present_forbidden_refresh = [
        value for value in forbidden_refresh if value in gpl
    ]
    if present_forbidden_refresh:
        fail(
            f"{gpl_path}: Chill retains unsafe timed-effector refresh machinery "
            f"{present_forbidden_refresh}"
        )
    sync_start = helper_gpl.index("function Phantom_Chill_Sync_Icon(agent target)")
    apply_gpl = helper_gpl[:sync_start]
    sync_gpl = helper_gpl[sync_start:]
    if "$CreateEffector" in apply_gpl or "$DeleteEffector" in apply_gpl:
        fail(
            f"{gpl_path}: Chill application must delegate icon changes to "
            "the delayed synchronization helper"
        )
    for old_icon, new_icon in (
        ("ice_lance_chill_icon", "ice_lance_empowered_chill_icon"),
        ("ice_lance_empowered_chill_icon", "ice_lance_chill_icon"),
    ):
        delete_index = sync_gpl.index(
            f'$DeleteEffector(target, "{old_icon}");'
        )
        delay_index = sync_gpl.index(
            'target\'s "PhantomChillIconDelay" = 200;',
            delete_index,
        )
        return_index = sync_gpl.index("return;", delay_index)
        create_index = sync_gpl.index(
            f'$CreateEffector(target, "{new_icon}", 1, "infinite");',
            return_index,
        )
        if not delete_index < delay_index < return_index < create_index:
            fail(
                f"{gpl_path}: {old_icon} to {new_icon} handoff does not "
                "separate deletion and creation across watcher ticks"
            )
    hit_gpl = gpl[hit_start:helper_start]
    centered_unit_impact = hit_gpl.index(
        '$createeffector(target, "ice_lance_hit_effector", 0);'
    )
    building_branch = hit_gpl.index(
        'If (target\'s "Type" == "Building" || target\'s "Type" == "Lair")'
    )
    chill_application = hit_gpl.index(
        '$Phantom_Apply_Chill(thisagent, target, $GetSpellAttribute("ice_lance", "effector_duration"));'
    )
    if not centered_unit_impact < building_branch < chill_application:
        fail(
            f"{gpl_path}: native hit overlay must apply before the "
            "building/lair Chill guard"
        )


def validate_icy_touch_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    icy_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRa4" Name="icy_touch"'
    )
    blizzard_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRa5" Name="endless_winter"',
        icy_start,
    )
    icy_action = actions[icy_start:blizzard_start]
    action_contract = (
        '<ImageSet value="Attack"/>',
        '<CompletionImageSet value="Stand"/>',
        '<Sound value="Fire_Blast"/>',
        '<SoundPhase begin="Begin"/>',
        'GPLFunction="Icy_Touch_Cast"',
        '<TimeoutDuration value="5000"/>',
        '<SpellType value="Attack"/>',
        '<CharacterLevel value="4"/>',
        '<SpellRank value="3"/>',
        '<ValidationScript value="Icy_Touch_Check"/>',
    )
    missing_action = [value for value in action_contract if value not in icy_action]
    if missing_action:
        fail(f"{actions_path}: Icy Touch action is missing {missing_action}")
    forbidden_action = (
        '<ImageSet value="Cast"/>',
        '<EffectorDuration value="3000"/>',
        'GPLFunction="Icy_Touch_Hit"',
    )
    present_forbidden_action = [
        value for value in forbidden_action if value in icy_action
    ]
    if present_forbidden_action:
        fail(
            f"{actions_path}: Icy Touch still contains old custom action "
            f"fields {present_forbidden_action}"
        )

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if '<Spell ID="2" Value="icy_touch"/>' not in units:
        fail(f"{units_path}: Phantom does not list Icy Touch as an allowed spell")

    projectiles_path = output_root / "Data" / "phantom_projectiles.xml"
    projectiles = projectiles_path.read_text(encoding="utf-8")
    forbidden_projectile = (
        "icy_touch_missile",
        'ID="PHp2"',
        '<ImageIDBase value="PHp2"/>',
    )
    present_projectile = [
        value for value in forbidden_projectile if value in projectiles
    ]
    if present_projectile:
        fail(
            f"{projectiles_path}: obsolete Icy Touch projectile remains "
            f"{present_projectile}"
        )

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHg1" Name="gravechill_icon"',
        '<ImageIDBase value="PHg1"/>',
        '<StackPriority value="1"/>',
    )
    missing_overlay = [value for value in overlay_contract if value not in overlays]
    if missing_overlay:
        fail(
            f"{overlays_path}: Gravechill status overlay is missing "
            f"{missing_overlay}"
        )
    gravechill_overlay_start = overlays.index(
        'ID="PHg1" Name="gravechill_icon"'
    )
    gravechill_overlay_end = overlays.index(
        "</Description>",
        gravechill_overlay_start,
    )
    gravechill_overlay = overlays[
        gravechill_overlay_start:gravechill_overlay_end
    ]
    if "GPLFunction=" in gravechill_overlay:
        fail(
            f"{overlays_path}: Gravechill icon must not own modifier cleanup; "
            "the counter watcher owns the full lifecycle"
        )
    hit_overlay_contract = (
        'ID="PHg2" Name="gravechill_hit_effector"',
        '<ImageIDBase value="PHg2"/>',
        '<AttachmentPointID value="2"/>',
        '<StackPriority value="0"/>',
        '<Flags value="TransparentToMouse"/>',
    )
    missing_hit_overlay = [
        value for value in hit_overlay_contract if value not in overlays
    ]
    if missing_hit_overlay:
        fail(
            f"{overlays_path}: Gravechill hit overlay is missing "
            f"{missing_hit_overlay}"
        )
    if "icy_touch_cooldown" in overlays:
        fail(f"{overlays_path}: obsolete Icy Touch cooldown overlay remains")

    maindata_path = output_root / "Data" / "phantom_maindata.cam"
    sections, captured = validate_archive(maindata_path)
    custom_tiles = sections[b"TILE"]
    gravechill_tiles = [
        entry
        for entry in custom_tiles
        if entry.name.startswith(b"PHg1Skull")
    ]
    for entry in gravechill_tiles:
        tile = captured.get((b"TILE", entry.name))
        if tile is None or indexed_v3_body_bounds(tile) is None:
            fail(f"{maindata_path}: {entry.label} is an empty Gravechill icon frame")
    gravechill_hit_tiles = [
        entry
        for entry in custom_tiles
        if entry.name.startswith(b"PHg2SkullHit")
    ]
    for entry in gravechill_hit_tiles:
        tile = captured.get((b"TILE", entry.name))
        if tile is None or indexed_v3_body_bounds(tile) is None:
            fail(f"{maindata_path}: {entry.label} is an empty Gravechill hit frame")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    obsolete_symbols = (
        "Icy_Touch_Disabled",
        "Phantom_Try_Icy_Touch",
        "icy_touch_cooldown",
        "icy_touch_hit_effector",
        "icy_touch_missile",
    )
    present_obsolete = [value for value in obsolete_symbols if value in gpl]
    if present_obsolete:
        fail(
            f"{gpl_path}: obsolete custom Icy Touch machinery remains "
            f"{present_obsolete}"
        )

    icy_start = gpl.index("function Icy_Touch_Check(agent thisagent) is integer")
    icy_end = gpl.index("function Blizzard_Check(agent thisagent) is integer", icy_start)
    icy_gpl = gpl[icy_start:icy_end]
    baseline_contract = (
        "function Icy_Touch_Check(agent thisagent) is integer",
        'target = thisagent\'s "Target";',
        "If ($NotValid(target))",
        "If ($IsDead(target))",
        'If (target\'s "Type" == "Building" || target\'s "Type" == "Lair")',
        "distance = $DistanceBetweenAgents(thisagent, target);",
        "If (distance <= #Phantom_Icy_Touch_Range)",
        "return 1;",
        "return 0;",
        "function Icy_Touch_Cast(agent thisagent, agent action_target)",
        "agent target;",
        'target = thisagent\'s "Target";',
        "$make_attack(thisagent, target);",
        "If ($NotValid(target))",
        "If ($IsDead(target))",
        "$spell_attack(thisagent, target, 30);",
        '$Phantom_Apply_Chill(thisagent, target, $GetSpellAttribute("ice_lance", "effector_duration"));',
        '$CreateEffector(target, "gravechill_hit_effector", 0);',
        "$Phantom_Apply_Gravechill(target, 8000);",
        "function Phantom_Apply_Gravechill(agent target, integer duration)",
        'If ($HasAttribute("PhantomGravechillRemaining", target) == False)',
        '$AddAttribute(target, "PhantomGravechillRemaining", "integer", duration);',
        '$AddAttribute(target, "PhantomGravechillActive", "boolean", False);',
        '$AddAttribute(target, "PhantomGravechillWatch", "function", $Phantom_Gravechill_Watch);',
        'target\'s "PhantomGravechillRemaining" = duration;',
        'If (target\'s "PhantomGravechillActive" == False)',
        "$MagicalAdjustAttribute(target, #ATTRIB_Strength, -5);",
        "$MagicalAdjustAttribute(target, #ATTRIB_Parry, -2);",
        "$MagicalAdjustAttribute(target, #ATTRIB_MagicResistance, -2);",
        'If ($CheckEffector(target, "gravechill_icon") == False)',
        '$CreateEffector(target, "gravechill_icon", 1, "infinite");',
        'If ($IsRunning(target\'s "PhantomGravechillWatch") == False)',
        '$NewThread(target\'s "PhantomGravechillWatch", 100, target);',
        "function Phantom_Gravechill_Watch(agent thisagent)",
        'thisagent\'s "PhantomGravechillRemaining" -= 100;',
        '$KillThread(thisagent\'s "PhantomGravechillWatch");',
        'thisagent\'s "PhantomGravechillActive" = False;',
        "$MagicalAdjustAttribute(thisagent, #ATTRIB_Strength, 5);",
        "$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, 2);",
        "$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, 2);",
        '$DeleteEffector(thisagent, "gravechill_icon");',
    )
    missing_baseline = [value for value in baseline_contract if value not in icy_gpl]
    if missing_baseline:
        fail(
            f"{gpl_path}: stock monster-style Icy Touch callback is "
            f"missing {missing_baseline}"
        )
    if "$createmissile" in icy_gpl:
        fail(f"{gpl_path}: Icy Touch must not depend on a missile callback")
    if icy_gpl.count("$make_attack(thisagent, target);") != 1:
        fail(f"{gpl_path}: Icy Touch must resolve exactly one stock weapon attack")
    if icy_gpl.count("$spell_attack(thisagent, target, 30);") != 1:
        fail(f"{gpl_path}: Icy Touch must resolve exactly one inline magic attack")
    if icy_gpl.count('$CreateEffector(target, "gravechill_hit_effector", 0);') != 1:
        fail(f"{gpl_path}: Icy Touch must create exactly one skull hit animation")
    if icy_gpl.count(
        '$CreateEffector(target, "gravechill_icon", 1, "infinite");'
    ) != 1:
        fail(f"{gpl_path}: Gravechill must create exactly one persistent icon")
    forbidden_helpers = (
        "function Icy_Touch_Hit",
        "$Icy_Touch_Hit",
        "$Does_Resist_Fire",
        "wither_effector",
        "$AdjustAttribute(target, #ATTRIB_Armor_Basic_Damage, -2);",
        "$AdjustAttribute(target, #ATTRIB_Armor_Magic_Bonus, -2);",
        "$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 2);",
        "$AdjustAttribute(thisagent, #ATTRIB_Armor_Magic_Bonus, 2);",
    )
    present_helpers = [value for value in forbidden_helpers if value in icy_gpl]
    if present_helpers:
        fail(
            f"{gpl_path}: Icy Touch still contains intermediary or "
            f"player-spell machinery {present_helpers}"
        )
    gravechill_helper_start = icy_gpl.index(
        "function Phantom_Apply_Gravechill(agent target, integer duration)"
    )
    gravechill_watcher_start = icy_gpl.index(
        "function Phantom_Gravechill_Watch(agent thisagent)",
        gravechill_helper_start,
    )
    gravechill_helper = icy_gpl[
        gravechill_helper_start:gravechill_watcher_start
    ]
    gravechill_init_guard = gravechill_helper.index(
        'If ($HasAttribute("PhantomGravechillRemaining", target) == False)'
    )
    gravechill_init_end = gravechill_helper.index(
        'target\'s "PhantomGravechillRemaining" = duration;',
        gravechill_init_guard,
    )
    for init_line in (
        '$AddAttribute(target, "PhantomGravechillRemaining", "integer", duration);',
        '$AddAttribute(target, "PhantomGravechillActive", "boolean", False);',
        '$AddAttribute(target, "PhantomGravechillWatch", "function", $Phantom_Gravechill_Watch);',
    ):
        if not (
            gravechill_init_guard
            < gravechill_helper.index(init_line)
            < gravechill_init_end
        ):
            fail(
                f"{gpl_path}: Gravechill dynamic attribute {init_line!r} is "
                "not inside its one-time initialization guard"
            )
    gravechill_icon_guard = gravechill_helper.index(
        'If ($CheckEffector(target, "gravechill_icon") == False)'
    )
    gravechill_icon_create = gravechill_helper.index(
        '$CreateEffector(target, "gravechill_icon", 1, "infinite");'
    )
    if not gravechill_icon_guard < gravechill_icon_create:
        fail(
            f"{gpl_path}: Gravechill icon creation is not protected by the "
            "authoritative effector-existence guard"
        )
    if gravechill_helper.count(
        "$MagicalAdjustAttribute(target, #ATTRIB_Strength, -5);"
    ) != 1:
        fail(
            f"{gpl_path}: Gravechill must apply its modifiers exactly once "
            "inside the inactive guard"
        )
    forbidden_gravechill_refresh = (
        '$DeleteEffector(target, "gravechill_icon");',
        '$CreateEffector(target, "gravechill_icon", 8000);',
        "function Gravechill_End(agent thisagent)",
    )
    present_forbidden_refresh = [
        value for value in forbidden_gravechill_refresh if value in icy_gpl
    ]
    if present_forbidden_refresh:
        fail(
            f"{gpl_path}: Gravechill retains unsafe timed-effector refresh "
            f"machinery {present_forbidden_refresh}"
        )
    if "expression #Phantom_Icy_Touch_Range 24" not in gpl:
        fail(f"{gpl_path}: Icy Touch melee range must be the stock-style 24 units")
    forbidden_behavior = (
        "$compile_enemies",
        "$listmember",
        "target1",
        "target2",
        "target3",
        "$hit(",
        "$damage(",
        "$spelldamage(",
        "#Multiple_Unit_Attack_Range",
        "$move(",
        "$travel_to",
        "$PerformAction",
    )
    present_forbidden_behavior = [
        value for value in forbidden_behavior if value in icy_gpl
    ]
    if present_forbidden_behavior:
        fail(
            f"{gpl_path}: Icy Touch contains obsolete multi-target, melee, "
            f"or weapon behavior {present_forbidden_behavior}"
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
    frost_overlay_start = overlays.index(
        'ID="PHo1" Name="frost_armor_effector"'
    )
    frost_overlay_end = overlays.index("</Description>", frost_overlay_start)
    frost_overlay = overlays[frost_overlay_start:frost_overlay_end]
    if '<StackPriority value="1"/>' not in frost_overlay:
        fail(
            f"{overlays_path}: visible Frost Armor ward must participate in "
            "the standard status-effect stack"
        )

    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    if "(Lived_In_Script Phantom_Lived_In)" not in building_data:
        fail(f"{building_data_path}: full-health Frost Armor recharge wrapper is missing")

    items_data_path = output_root / "GPL" / "Phantom_Items_Data.dat"
    items_data = items_data_path.read_text(encoding="utf-8")
    item_data_contract = (
        "[FrostArmorBonus]",
        "(Title\t\tFrostArmorBonus)",
    )
    missing_item_data = [value for value in item_data_contract if value not in items_data]
    if missing_item_data:
        fail(
            f"{items_data_path}: visible Frost Armor armor item is missing "
            f"{missing_item_data}"
        )

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "If ($Phantom_Try_Frost_Armor(thisagent) == False)",
        "$Wizard_tree(thisagent);",
        "function Frost_Armor_Begin(agent thisagent, agent target)",
        'thisagent\'s "Reborn_Counter" = 1;',
        '$createeffector(thisagent, "frost_armor_effector", 180000);',
        "#ATTRIB_Armor_Basic_Damage, 10000",
        "#ATTRIB_Armor_Magic_Bonus, 10000",
        '$clearlist(thisagent\'s "Hostiles");',
        'targets = $compile_enemies(thisagent, 240);',
        '$Frost_Armor_Begin(thisagent, thisagent);',
        '$PerformAction(thisagent, "Basic_Cast", thisagent);',
        "function Phantom_Arm_Frost_Armor_In_Combat(agent thisagent) is boolean",
        'thisagent\'s "ActiveScript" != $Attack_object',
        'thisagent\'s "BackScript" != $Attack_object',
        "function Phantom_Frost_Armor_Watch(agent thisagent)",
        "function Phantom_Grant_Frost_Armor_Bonus(agent thisagent)",
        "If ($GetAttribute(thisagent, #ATTRIB_ExperienceLevel) < 3)",
        "If ($AgentHasInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent))",
        "$CreateNewInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent, #Allow_Cloned_Quest_Item);",
        "$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);",
        "$Phantom_Grant_Frost_Armor_Bonus(thisagent);",
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
        '$CreateEffector(target, "frost_armor_frozen_small", 2700);',
        '$CreateEffector(target, "frost_armor_frozen_medium", 2700);',
        '$CreateEffector(target, "frost_armor_frozen_large", 2700);',
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
    if gpl.count("$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);") != 1:
        fail(
            f"{gpl_path}: persistent Frost Armor must contain exactly one "
            "guarded +10 armor adjustment"
        )
    if gpl.count(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, 10000);"
    ) != 1:
        fail(
            f"{gpl_path}: active Frost Armor must contain exactly one "
            "+10000 magical-armor adjustment"
        )
    if gpl.count(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, -10000);"
    ) != 2:
        fail(
            f"{gpl_path}: active Frost Armor magical armor must be removed "
            "on both consumption and death"
        )
    if "$Phantom_Ensure_Frost_Armor_Passive" in gpl:
        fail(f"{gpl_path}: legacy level-1 passive-armor implementation is present")
    if "$Phantom_Wizard_Tree" in gpl or "$Phantom_Purchase_Equipment" in gpl:
        fail(
            f"{gpl_path}: unstable local Wizard-tree potion wrapper is still present"
        )
    frost_arm_start = gpl.index(
        "function Phantom_Arm_Frost_Armor_In_Combat(agent thisagent) is boolean"
    )
    frost_arm_end = gpl.index(
        "function Phantom_Frost_Armor_Watch(agent thisagent)", frost_arm_start
    )
    frost_arm_gpl = gpl[frost_arm_start:frost_arm_end]
    if (
        'targets = $compile_enemies(thisagent, thisagent\'s "castingrange");'
        in frost_arm_gpl
    ):
        fail(
            f"{gpl_path}: Frost Armor combat detection is incorrectly limited "
            "to Ice Lance casting range"
        )
    if (
        "targets = $compile_enemies("
        "thisagent, $GetAttribute(thisagent, #ATTRIB_SightRange));"
    ) in frost_arm_gpl:
        fail(
            f"{gpl_path}: unsafe nested native call is present in Frost Armor "
            "combat detection"
        )

    consume = gpl.index('thisagent\'s "Reborn_Counter" = 2;')
    incoming_filter = gpl.index('If (hostile\'s "Target" == thisagent)')
    range_filter = gpl.index(
        '$DistanceBetweenAgents(hostile, thisagent) <= attack_range + 24'
    )
    building_guard = gpl.index(
        'If (attacker\'s "Type" == "Building" || attacker\'s "Type" == "Lair")'
    )
    freeze = gpl.index("$Frost_Armor_Freeze(attacker);")
    consume_basic_cleanup = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, -10000);",
        consume,
    )
    consume_magic_cleanup = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, -10000);",
        consume_basic_cleanup,
    )
    if not (
        incoming_filter
        < range_filter
        < consume
        < consume_basic_cleanup
        < consume_magic_cleanup
        < building_guard
        < freeze
    ):
        fail(
            f"{gpl_path}: Frost Armor must validate an in-range incoming "
            "attacker, remove both ward defenses, then apply the building/lair "
            "freeze exclusion"
        )

    ward_begin = gpl.index("function Frost_Armor_Begin(agent thisagent, agent target)")
    ward_basic_grant = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10000);",
        ward_begin,
    )
    ward_magic_grant = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, 10000);",
        ward_basic_grant,
    )
    ward_hostile_clear = gpl.index(
        '$clearlist(thisagent\'s "Hostiles");',
        ward_magic_grant,
    )
    death = gpl.index("function Phantom_death(agent thisagent)")
    death_basic_cleanup = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, -10000);",
        death,
    )
    death_magic_cleanup = gpl.index(
        "$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, -10000);",
        death_basic_cleanup,
    )
    death_state_reset = gpl.index('thisagent\'s "Reborn_Counter" = 0;', death)
    if not (
        death
        < death_basic_cleanup
        < death_magic_cleanup
        < death_state_reset
        < ward_begin
        < ward_basic_grant
        < ward_magic_grant
        < ward_hostile_clear
    ):
        fail(
            f"{gpl_path}: Frost Armor must add and remove its basic and "
            "magical ward armor as a matched pair"
        )

    bonus_function = gpl.index(
        "function Phantom_Grant_Frost_Armor_Bonus(agent thisagent)"
    )
    bonus_level_gate = gpl.index(
        "If ($GetAttribute(thisagent, #ATTRIB_ExperienceLevel) < 3)",
        bonus_function,
    )
    bonus_item_guard = gpl.index(
        "If ($AgentHasInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent))",
        bonus_level_gate,
    )
    bonus_item_grant = gpl.index(
        "$CreateNewInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent, #Allow_Cloned_Quest_Item);",
        bonus_item_guard,
    )
    bonus_adjustment = gpl.index(
        "$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);",
        bonus_item_grant,
    )
    watcher = gpl.index("function Phantom_Frost_Armor_Watch(agent thisagent)")
    watcher_bonus_call = gpl.index(
        "$Phantom_Grant_Frost_Armor_Bonus(thisagent);",
        watcher,
    )
    watcher_recharge_call = gpl.index(
        "$Phantom_Frost_Armor_Recharge_Check(thisagent);",
        watcher,
    )
    watcher_arm_call = gpl.index(
        "If ($Phantom_Arm_Frost_Armor_In_Combat(thisagent))",
        watcher,
    )
    if not (
        bonus_function
        < bonus_level_gate
        < bonus_item_guard
        < bonus_item_grant
        < bonus_adjustment
        < watcher
        < watcher_bonus_call
        < watcher_recharge_call
        < watcher_arm_call
    ):
        fail(
            f"{gpl_path}: persistent Frost Armor must be level-gated, "
            "item-guarded, and granted before reactive ward processing"
        )

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    stat_contract = (
        '<Vitality value="8"/>',
        '<MagicResistance value="25"/>',
        '<Strength value="8"/>',
        '<Parry value="20"/>',
        '<Dodge value="25"/>',
        '<WeaponBasicDamage value="0"/>',
        '<ArmorBasicDamage value="0"/>',
    )
    missing_stats = [value for value in stat_contract if value not in units]
    if missing_stats:
        fail(f"{units_path}: Phantom rebalance stats are missing {missing_stats}")

    item_contract = (
        '$AdjustAttribute (thisagent, #ATTRIB_Armor_Basic_Damage, 2);',
        '$AdjustAttribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);',
        '$MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);',
        '$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);',
    )
    missing_items = [value for value in item_contract if value not in gpl]
    if missing_items:
        fail(f"{gpl_path}: Phantom starter-item bonuses are missing {missing_items}")
    grant = gpl.index("$Phantom_grant_starter_items(thisagent);")
    item_guard = gpl.index(
        "If ($Phantom_has_icerod_item(thisagent) == False)",
    )
    damage_adjustment = gpl.index(
        "$AdjustAttribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);",
        item_guard,
    )
    parry_adjustment = gpl.index(
        "$MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);",
        damage_adjustment,
    )
    if not grant < item_guard < damage_adjustment < parry_adjustment:
        fail(
            f"{gpl_path}: Black Icerod damage and stock-path Parry bonuses "
            "must be applied within the guarded starter-item grant"
        )
    if gpl.count("$MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);") != 1:
        fail(
            f"{gpl_path}: Black Icerod must contain exactly one guarded "
            "stock-path +5 Parry adjustment"
        )
    if "$AdjustAttribute(thisagent, #ATTRIB_Parry, 5);" in gpl:
        fail(
            f"{gpl_path}: Black Icerod uses ordinary rather than stock "
            "MagicalAdjustAttribute Parry mutation"
        )
    if '<Strength value="8"/>' not in units:
        fail(
            f"{units_path}: Strength must be at least strength_div (8) when "
            "weapon damage is zero, or stock target evaluation divides by zero"
        )
    if "$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 1);" in gpl:
        fail(f"{gpl_path}: old Frozen Cowl +1 bonus is still present")
    if 'thisagent\'s "castingrange" +=' in gpl:
        fail(f"{gpl_path}: unsafe runtime casting-range mutation is present")
    if 'Special_Boolean' in gpl:
        fail(f"{gpl_path}: experimental passive-armor item state is still present")


def validate_phantom_spell_confidence_contract(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    confidence_start = gpl.index(
        "function spell_extra_value(agent thisagent) is integer"
    )
    confidence_end = gpl.index("\nfunction DEAL_DEMON()", confidence_start)
    confidence = gpl[confidence_start:confidence_end]

    expressions = (
        "expression #Phantom_Ice_Lance_Confidence 10",
        "expression #Phantom_Frost_Armor_Confidence 10",
        "expression #Phantom_Icy_Touch_Confidence 25",
        "expression #Phantom_Call_To_Grave_Confidence 10",
        "expression #Phantom_Eternal_Soul_Confidence 25",
        "expression #Phantom_Endless_Winter_Confidence 30",
    )
    missing_expressions = [value for value in expressions if value not in gpl]
    if missing_expressions:
        fail(
            f"{gpl_path}: Phantom spell-confidence weights are missing "
            f"{missing_expressions}"
        )

    stock_contract = (
        ("energy_blast", "10"),
        ("fire_blast", "30"),
        ("fire_ball", "30"),
        ("teleport", "5"),
        ("resist_magic", "5"),
        ("meteor_storm", "30"),
        ("drain_life", "30"),
        ("sun_scorch", "30"),
    )
    missing_stock = [
        spell
        for spell, value in stock_contract
        if (
            f'if ($isspellavailable(thisagent,"{spell}",1))\n'
            f"\t\tvalue += {value};"
        )
        not in confidence
    ]
    if missing_stock:
        fail(
            f"{gpl_path}: stock spell-confidence behavior changed for "
            f"{missing_stock}"
        )

    phantom_contract = (
        ("ice_lance", "#Phantom_Ice_Lance_Confidence"),
        ("frost_armor", "#Phantom_Frost_Armor_Confidence"),
        ("icy_touch", "#Phantom_Icy_Touch_Confidence"),
        ("call_to_grave", "#Phantom_Call_To_Grave_Confidence"),
        ("eternal_soul", "#Phantom_Eternal_Soul_Confidence"),
        ("endless_winter", "#Phantom_Endless_Winter_Confidence"),
    )
    phantom_guard = confidence.index('if (thisagent\'s "Title" == "Phantom")')
    for spell, value in phantom_contract:
        check = f'if ($isspellavailable(thisagent,"{spell}",1))'
        value_adjustment = f"value += {value};"
        if confidence.count(check) != 1 or confidence.count(value_adjustment) != 1:
            fail(
                f"{gpl_path}: {spell} confidence must have exactly one "
                "availability check and one value adjustment"
            )
        check_index = confidence.index(check)
        value_index = confidence.index(value_adjustment, check_index)
        if not phantom_guard < check_index < value_index:
            fail(
                f"{gpl_path}: {spell} confidence is not contained in the "
                "Phantom-only branch"
            )

    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    if (
        'ID="WRa5" Name="endless_winter" Description="Endless Winter"'
        not in actions
    ):
        fail(f"{actions_path}: level-7 placeholder is not named Endless Winter")
    if 'Name="blizzard"' in actions:
        fail(f"{actions_path}: obsolete Blizzard action name is still present")

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if 'Value="endless_winter"' in units:
        fail(
            f"{units_path}: unfinished Endless Winter placeholder must not be "
            "learnable before its implementation pass"
        )


def validate_call_to_grave_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    action_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRa6" '
        'Name="call_to_grave"'
    )
    action_end = actions.index("</Description>", action_start)
    action = actions[action_start:action_end]
    action_contract = (
        '<ImageSet value="Cast"/>',
        '<CompletionImageSet value="Stand"/>',
        'GPLFunction="Call_To_Grave_Effect"',
        '<EffectorDuration value="1200"/>',
        '<TimeoutDuration value="5000"/>',
        '<SpellType value="4"/>',
        '<CharacterLevel value="5"/>',
        '<SpellRank value="4"/>',
        '<ValidationScript value="Call_To_Grave_Check"/>',
    )
    missing_action = [value for value in action_contract if value not in action]
    if missing_action:
        fail(f"{actions_path}: Call to Grave action is missing {missing_action}")
    forbidden_action = (
        "<Sound ",
        "<SoundPhase ",
        'GPLFunction="Call_To_Grave_Begin"',
        '<TimeoutDuration value="1000"/>',
        '<TimeoutDuration value="36500"/>',
        '<SpellType value="Travel"/>',
        '<CharacterLevel value="1"/>',
        '<SpellRank value="5"/>',
    )
    present_forbidden_action = [value for value in forbidden_action if value in action]
    if present_forbidden_action:
        fail(
            f"{actions_path}: Call to Grave retains obsolete "
            f"action fields {present_forbidden_action}"
        )

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if '<Spell ID="3" Value="call_to_grave"/>' not in units:
        fail(f"{units_path}: Phantom does not list Call to Grave as an allowed spell")

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHc2" Name="call_to_grave_effector"',
        '<ImageIDBase value="PHc2"/>',
        '<AttachmentPointID value="3"/>',
        '<DefaultSound value="Teleport"/>',
    )
    missing_overlay = [value for value in overlay_contract if value not in overlays]
    if missing_overlay:
        fail(f"{overlays_path}: Call to Grave overlay is missing {missing_overlay}")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "expression #Phantom_Call_To_Grave_Range 50000",
        "expression #Phantom_Call_To_Grave_Min_Distance 500",
        "function Call_To_Grave_Check(agent thisagent) is integer",
        'if (thisagent\'s "taskname" != "go_home")',
        'if (thisagent\'s "target" != thisagent\'s "home")',
        'if (thisagent\'s "Target" == thisagent)',
        'destination = thisagent\'s "destination";',
        'if ($isvalidgamepiece(thisagent\'s "target"))',
        'destination = $locationof(thisagent\'s "target");',
        "else\n\t\t\treturn 0;",
        "if ($distancebetweencoords(destination,$locationof(thisagent)) > #Phantom_Call_To_Grave_Min_Distance)",
        "function Call_To_Grave_Effect(agent thisagent, agent target)",
        'theTimePeriod = $GetSpellAttribute("call_to_grave","effector_duration");',
        '$createeffector(thisagent,"call_to_grave_effector",theTimePeriod);',
        'thisagent\'s "teleportScript" = $Call_To_Grave_DoMove;',
        '$RunThread(thisagent\'s "teleportScript",theTimePeriod/2,thisagent,#Phantom_Call_To_Grave_Range);',
        "function Call_To_Grave_DoMove(agent thisagent, integer theRange)",
        "If ($IsDead(ThisAgent))",
        'if (thisagent\'s "Target" == thisagent)',
        '$TeleportToPoint(thisagent,theRange,thisagent\'s "destination");',
        'if ($isvalidgamepiece(thisagent\'s "target"))',
        '$TeleportToUnit(thisagent,theRange,thisagent\'s "Target",thisagent\'s "castingrange");',
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Call to Grave GPL is missing {missing_gpl}")
    check_start = gpl.index("function Call_To_Grave_Check(agent thisagent) is integer")
    check_end = gpl.index("\nfunction Call_To_Grave_Effect", check_start)
    check_function = gpl[check_start:check_end]
    if 'thisagent\'s "taskname" = "go_home";' in check_function:
        fail(f"{gpl_path}: Call to Grave validation mutates the stock home task")
    forbidden_gpl = (
        "expression #Phantom_Call_To_Grave_Walk_Range",
        "function Phantom_Is_Returning_Home(",
        "function Phantom_Return_Home(",
        "function Phantom_Return_Home_Safe(",
        "function Phantom_Try_Call_To_Grave(",
        "function Call_To_Grave_Begin(",
        "function Call_To_Grave_Move(",
        "function use_building(",
        "function use_building_safe(",
        "$TeleportToUnit(thisagent, 50000, home, 0);",
        "return $main_teleport_check(thisagent,#Teleport_Range);",
        "return $main_teleport_check(thisagent,#Teleport_Short_Range);",
        '$RunThread(thisagent\'s "teleportScript",theTimePeriod/2,thisagent,#Teleport_Range);',
        '$LearnSpell(thisagent, "call_to_grave");',
    )
    present_forbidden_gpl = [value for value in forbidden_gpl if value in gpl]
    if present_forbidden_gpl:
        fail(
            f"{gpl_path}: Call to Grave retains custom home-recall hooks "
            f"{present_forbidden_gpl}"
        )


def validate_eternal_soul_contract(output_root: Path) -> None:
    actions_path = output_root / "Data" / "phantom_actions.xml"
    actions = actions_path.read_text(encoding="utf-8")
    action_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRa7" '
        'Name="eternal_soul"'
    )
    action_end = actions.index("</Description>", action_start)
    action = actions[action_start:action_end]
    action_contract = (
        '<ImageSet value="Cast"/>',
        '<CompletionImageSet value="Stand"/>',
        'GPLFunction="Eternal_Soul_Begin"',
        '<EffectorDuration value="25000"/>',
        '<TimeoutDuration value="30000"/>',
        '<SpellType value="Attack"/>',
        '<CharacterLevel value="6"/>',
        '<SpellRank value="5"/>',
    )
    missing_action = [value for value in action_contract if value not in action]
    if missing_action:
        fail(f"{actions_path}: Eternal Soul action is missing {missing_action}")
    if '<CharacterLevel value="1"/>' in action:
        fail(f"{actions_path}: Eternal Soul retains its temporary test level")

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if '<Spell ID="4" Value="eternal_soul"/>' not in units:
        fail(f"{units_path}: Eternal Soul is not in the Phantom spell list")

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHe1" Name="eternal_soul_icon"',
        '<ImageIDBase value="PHe1"/>',
        'GPLFunction="Eternal_Soul_End"',
        'ID="PHe2" Name="eternal_soul_effector"',
        '<ImageIDBase value="PHe2"/>',
    )
    missing_overlays = [value for value in overlay_contract if value not in overlays]
    if missing_overlays:
        fail(
            f"{overlays_path}: Eternal Soul overlay contract is missing "
            f"{missing_overlays}"
        )
    eternal_overlay_start = overlays.index(
        'ID="PHe1" Name="eternal_soul_icon"'
    )
    eternal_overlay_end = overlays.index("</Description>", eternal_overlay_start)
    eternal_cast_start = overlays.index(
        'ID="PHe2" Name="eternal_soul_effector"'
    )
    eternal_cast_end = overlays.index("</Description>", eternal_cast_start)
    eternal_overlays = (
        overlays[eternal_overlay_start:eternal_overlay_end]
        + overlays[eternal_cast_start:eternal_cast_end]
    )
    if '<ImageIDBase value="LRa1"/>' in eternal_overlays or (
        '<ImageIDBase value="LRa2"/>' in eternal_overlays
    ):
        fail(f"{overlays_path}: Eternal Soul still borrows stock Shield of Light art")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gpl_contract = (
        "function Phantom_Eternal_Soul_Active(agent thisagent) is boolean",
        "function Eternal_Soul_Begin(agent thisagent, agent target)",
        'If ($HasAttribute("PhantomEternalSoulActive", thisagent) == False)',
        '$AddAttribute(thisagent, "PhantomEternalSoulActive", "boolean", False);',
        '$AddAttribute(thisagent, "PhantomEternalSoulMaxHPBonus", "integer", 0);',
        "bonus_max_hp = (base_max_hp * 30) / 100;",
        '$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, 15);',
        '$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, 15);',
        '$AdjustAttribute(thisagent, #ATTRIB_MaxHP, bonus_max_hp);',
        '$SetAttribute(thisagent, #ATTRIB_HP, boosted_hp);',
        '$CreateEffector(thisagent, "eternal_soul_icon", $GetSpellAttribute("eternal_soul", "effector_duration"));',
        '$CreateEffector(thisagent, "eternal_soul_effector", 0);',
        "function Eternal_Soul_End(agent thisagent)",
        '$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, -15);',
        '$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, -15);',
        '$AdjustAttribute(thisagent, #ATTRIB_MaxHP, -bonus_max_hp);',
        '$SetAttribute(thisagent, #ATTRIB_HP, restored_hp);',
        "function Phantom_Apply_Chill(agent source, agent target, integer duration)",
        '$AddAttribute(target, "PhantomChillTier", "integer", 0);',
        'If ($Phantom_Eternal_Soul_Active(source))',
        "#ATTRIB_MovementRateModifier, 100",
        "#ATTRIB_ActionRateModifier, 1000",
        'If (thisagent\'s "PhantomChillTier" == 2)',
        'If (target\'s "PhantomChillTier" != 2)',
        'thisagent\'s "PhantomChillTier" = 0;',
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Eternal Soul behavior is missing {missing_gpl}")

    begin_start = gpl.index("function Eternal_Soul_Begin(agent thisagent, agent target)")
    end_start = gpl.index("function Eternal_Soul_End(agent thisagent)", begin_start)
    chill_start = gpl.index(
        "function Phantom_Apply_Chill(agent source, agent target, integer duration)",
        end_start,
    )
    begin_gpl = gpl[begin_start:end_start]
    end_gpl = gpl[end_start:chill_start]
    if begin_gpl.count("#ATTRIB_Parry, 15") != 1 or begin_gpl.count(
        "#ATTRIB_MagicResistance, 15"
    ) != 1:
        fail(f"{gpl_path}: Eternal Soul defensive bonuses can stack during begin")
    if end_gpl.count("#ATTRIB_Parry, -15") != 1 or end_gpl.count(
        "#ATTRIB_MagicResistance, -15"
    ) != 1:
        fail(f"{gpl_path}: Eternal Soul does not reverse its bonuses exactly once")
    if "PhantomChillSource" in gpl:
        fail(
            f"{gpl_path}: Chill must not add a runtime agent attribute to stock "
            "targets; tier precedence is integer-only"
        )


def validate_phantom_flee_home_contract(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    flee_start = gpl.index(
        "function flee_part_II(agent thisagent, list places, integer intent)"
    )
    flee_end = gpl.index("\nfunction Phantom_tree", flee_start)
    flee_function = gpl[flee_start:flee_end]
    contract = (
        'if (thisagent\'s "Title" == "Phantom" && '
        '$isvalidgamepiece(thisagent\'s "home"))',
        'go_here = thisagent\'s "home";',
        "else if ($listsize(places) > 0)",
        "go_here = $pick_closest(thisagent,places);",
        "$go_berserk(thisagent);",
        'if (go_here == thisagent\'s "home")',
        'thisagent\'s "taskname" = "go_home";',
        'thisagent\'s "taskname" = "visiting";',
        "$SpecifyIntent(ThisAgent,intent);",
        'thisagent\'s "Activescript" = $use_building_safe;',
        'thisagent\'s "backscript" = $use_building_safe;',
        'thisagent\'s "target" = go_here;',
        'thisagent\'s "destination" = $locationof(thisagent\'s "target");',
        '$createeffector(thisagent,"thought_bubble_danger",#danger_bubble_time);',
        '$say(thisagent,"VFX_FLEE_COMBAT");',
    )
    missing = [value for value in contract if value not in flee_function]
    if missing:
        fail(f"{gpl_path}: Phantom flee-home override is missing {missing}")
    forbidden = (
        "function flee(agent thisagent",
        "function flee_absolute(agent thisagent",
        "function wizard_eval_nearby(agent thisagent",
        "function use_building_safe(agent thisagent",
        "function travel_to_safe(agent thisagent",
    )
    present_forbidden = [value for value in forbidden if value in gpl]
    if present_forbidden:
        fail(
            f"{gpl_path}: Phantom flee-home behavior overrides broader stock "
            f"functions {present_forbidden}"
        )


def validate_phantom_potion_purchase_contract(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    contract = (
        "Function Potion_Check(agent thisagent, list potentials) is boolean",
        'If (thisagent\'s "Title" == "Phantom")',
        "$GetAttribute(thisagent, #ATTRIB_NumHealingPotions) >= #Max_Heal_Potions",
        "$Total_Gold(thisagent) < #Heal_Potion_Price",
        "potentials = $List_Attribs(potentials, #ATTRIB_ResearchHealingPotions);",
        "intel_roll = $RandomNumber(30) + 1;",
        'thisagent\'s "TaskName" = "visiting";',
        'thisagent\'s "Target" = $Loyalty_Mod_Pick_Closest(thisagent, potentials);',
        "$SpecifyIntent(thisagent, #Intent_purchasing_heal_potions);",
    )
    missing = [value for value in contract if value not in gpl]
    if missing:
        fail(f"{gpl_path}: Phantom Potion_Check override is missing {missing}")

    function = gpl.index(
        "Function Potion_Check(agent thisagent, list potentials) is boolean"
    )
    guard = gpl.index('If (thisagent\'s "Title" == "Phantom")', function)
    rejected = gpl.index("return False;", guard)
    potion_count = gpl.index(
        "$GetAttribute(thisagent, #ATTRIB_NumHealingPotions) >= #Max_Heal_Potions",
        function,
    )
    target = gpl.index(
        'thisagent\'s "Target" = $Loyalty_Mod_Pick_Closest(thisagent, potentials);',
        function,
    )
    intent = gpl.index(
        "$SpecifyIntent(thisagent, #Intent_purchasing_heal_potions);", function
    )
    if not function < guard < rejected < potion_count < target < intent:
        fail(
            f"{gpl_path}: Phantom must be rejected by Potion_Check before "
            "stock shopping state is evaluated or assigned"
        )
    if "$Phantom_Wizard_Tree" in gpl or "$Phantom_Purchase_Equipment" in gpl:
        fail(
            f"{gpl_path}: unstable local Wizard-tree potion wrapper is present"
        )
    if "$Wizard_tree(thisagent);" not in gpl:
        fail(f"{gpl_path}: Phantom no longer uses the stock Wizard tree")


def validate_phantom_equipment_upgrade_contract(output_root: Path) -> None:
    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    eligibility_contract = (
        '<AllowedWeapon value="Staff"/>',
        '<AllowedArmor value="Leather"/>',
    )
    missing = [value for value in eligibility_contract if value not in units]
    if missing:
        fail(f"{units_path}: stock equipment eligibility is missing {missing}")

    tree = parse_xml(units_path)
    for _, agent_name, attribute_name, _ in phantom_equipment_item_records():
        description = tree.find(f'.//Description[@ID="{agent_name}"]')
        if description is None:
            fail(f"{units_path}: equipment variant {agent_name} is missing")
        item_attribute = description.find(f'.//Attribute[@ID="{attribute_name}"]')
        if item_attribute is None:
            fail(
                f"{units_path}: equipment variant {agent_name} does not map "
                f"inventory attribute {attribute_name}"
            )

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    for preference in (
        "(Upgrade_Armor_Chance\t100)",
        "(Upgrade_Weapon_Chance\t100)",
    ):
        if preference not in hero_data:
            fail(f"{hero_data_path}: Phantom shop preference {preference!r} is missing")

    items_data_path = output_root / "GPL" / "Phantom_Items_Data.dat"
    items_data = items_data_path.read_text(encoding="utf-8")
    for _, agent_name, _, _ in phantom_equipment_item_records():
        if f"[{agent_name}]" not in items_data or f"(Title\t\t{agent_name})" not in items_data:
            fail(f"{items_data_path}: special-item data for {agent_name} is missing")

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    contract = (
        "Function WizGuild_Check(agent ThisAgent, string Equipment, integer Bonus, list WizGuilds) is boolean",
        'If (ThisAgent\'s "Title" == "Phantom" && Equipment == "Armor")',
        "Bonus = $Phantom_cowl_magic_level(ThisAgent);",
        "Function Obtain_Upgrade(agent ThisAgent)",
        "Old_Upgrade = $GetAttribute(ThisAgent, What_To_Upgrade);",
        "Parry_Increase = (Upgrade - Old_Upgrade) * 5;",
        "$MagicalAdjustAttribute(ThisAgent, #ATTRIB_Parry, Parry_Increase);",
        "$Phantom_sync_icerod_item(ThisAgent);",
        "$Phantom_sync_cowl_item(ThisAgent);",
        "Function Obtain_Enchantment(agent ThisAgent)",
        "Current_Upgrade = $Phantom_cowl_magic_level(ThisAgent);",
        'ThisAgent\'s "Reborn_Counter" == 1',
        "Stored_Upgrade += 10000;",
        "$SetAttribute(ThisAgent, What_To_Upgrade, Stored_Upgrade);",
        "function Phantom_cowl_magic_level(agent thisagent) is integer",
        "magic_level -= 10000;",
        "function Phantom_effective_casting_range(agent thisagent) is integer",
        "return 190 + (magic_level * 10);",
        "function Phantom_sync_cowl_item(agent thisagent)",
        "item_id = 82 + combination;",
        "function Phantom_sync_icerod_item(agent thisagent)",
        "item_id = 97 + combination;",
        "function attack_object(agent thisagent)",
        "attackrange = $Phantom_effective_casting_range(thisagent);",
        "function getattackrange(agent thisagent) is integer",
        "arrivedist = $Phantom_effective_casting_range(thisagent);",
        "function Phantom_remove_cowl_items(agent thisagent)",
        "function Phantom_remove_icerod_items(agent thisagent)",
    )
    missing = [value for value in contract if value not in gpl]
    if missing:
        fail(f"{gpl_path}: Phantom equipment upgrade contract is missing {missing}")

    for item_id, _, attribute_name, _ in phantom_equipment_item_records():
        expression = f"expression #{attribute_name} {item_id}"
        if expression not in gpl:
            fail(f"{gpl_path}: inventory expression {expression!r} is missing")

    if gpl.count("Function Obtain_Upgrade(agent ThisAgent)") != 1:
        fail(f"{gpl_path}: exactly one stock-compatible Obtain_Upgrade override is required")
    if gpl.count("Function Obtain_Enchantment(agent ThisAgent)") != 1:
        fail(
            f"{gpl_path}: exactly one stock-compatible Obtain_Enchantment override is required"
        )
    if gpl.count(
        "Function WizGuild_Check(agent ThisAgent, string Equipment, integer Bonus, list WizGuilds) is boolean"
    ) != 1:
        fail(f"{gpl_path}: exactly one Frost-aware WizGuild_Check override is required")
    if 'thisagent\'s "castingrange" +=' in gpl or 'thisagent\'s "castingrange" =' in gpl:
        fail(f"{gpl_path}: runtime castingrange mutation is unsafe")


def validate_phantom_healing_contract(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    contract = (
        "Function Bazaar_Item_Check ( agent ThisAgent, integer item, list potentials, integer Item_cost ) is boolean",
        'If (ThisAgent\'s "Title" == "Phantom" && item == #Bazaar_Item_Four)',
        "Function Heal( Agent ThisAgent, Agent Target, integer Healing_Amount )",
        'If (Target\'s "Title" == "Phantom")',
        'If (ThisAgent\'s "Title" != "Priestess")',
        "$Healing_Shared(Target, Healing_Amount);",
        "Function Player_Heal( Agent Target, integer Healing_Amount )",
        "function Regeneration_elixer_effect ( agent thisagent, agent target )",
        "$DeleteInventoryItem(#Bazaar_Item_Four, ThisAgent);",
        '$ForgetSpell(ThisAgent, "Regeneration_Elixer");',
        "function Healing_Wind ()",
        'If (hero\'s "Title" != "Phantom")',
        "Function Eval_For_Healing(agent ThisAgent, integer Distance) is Agent",
        'If (Hero\'s "Title" != "Phantom")',
        "Injured_Heroes << Hero;",
        "function Healer_Heal_Effect(agent thisagent, agent target)",
        'If (target\'s "Title" == "Phantom")',
        "$Reset_Tasks(thisagent);",
        "$CreateEffector(target, \"healer_healing_effector\", 0);",
        "$Heal(ThisAgent, Target, Healing);",
        "function Drain_Life_Hit(agent thisagent, agent target)",
        'Phantoms = $ListTitles(Phantoms, "Phantom");',
        "If ($GetPlayerTeamNumber(Phantom) == $GetPlayerTeamNumber(ThisAgent))",
        "Best_Phantom = Phantom;",
        "If ($IsValidGamePiece(Best_Phantom))",
        '$CreateEffector(Best_Phantom, "life_drain_effector2", Effector_Duration);',
        "$Heal(ThisAgent, Best_Phantom, 5);",
        'My_Skeletons = $ListTitles(My_Skeletons, "Skeleton");',
        "If ($IsValidGamePiece(Best_Skeleton))",
        "$Heal(ThisAgent, Best_Skeleton, 5);",
        "$Spell_Attack(ThisAgent, Target, 15);",
    )
    missing = [value for value in contract if value not in gpl]
    if missing:
        fail(f"{gpl_path}: Phantom healing contract is missing {missing}")

    for signature in (
        "Function Bazaar_Item_Check ( agent ThisAgent, integer item, list potentials, integer Item_cost ) is boolean",
        "Function Heal( Agent ThisAgent, Agent Target, integer Healing_Amount )",
        "Function Player_Heal( Agent Target, integer Healing_Amount )",
        "function Regeneration_elixer_effect ( agent thisagent, agent target )",
        "function Healing_Wind ()",
        "Function Eval_For_Healing(agent ThisAgent, integer Distance) is Agent",
        "function Healer_Heal_Effect(agent thisagent, agent target)",
        "function Drain_Life_Hit(agent thisagent, agent target)",
    ):
        if gpl.count(signature) != 1:
            fail(f"{gpl_path}: exactly one override is required for {signature}")

    bazaar_check = gpl.index(
        "Function Bazaar_Item_Check ( agent ThisAgent, integer item, list potentials, integer Item_cost ) is boolean"
    )
    regeneration_purchase_guard = gpl.index(
        'If (ThisAgent\'s "Title" == "Phantom" && item == #Bazaar_Item_Four)',
        bazaar_check,
    )
    first_bazaar_task_assignment = gpl.index(
        'ThisAgent\'s "TaskName" = $Get_Bazaar_Task_Name(item);',
        regeneration_purchase_guard,
    )
    if not (
        bazaar_check
        < regeneration_purchase_guard
        < first_bazaar_task_assignment
    ):
        fail(
            f"{gpl_path}: the stock Bazaar item check must reject only Phantom "
            "Regeneration Elixir purchases before assigning a shopping task"
        )

    heal = gpl.index(
        "Function Heal( Agent ThisAgent, Agent Target, integer Healing_Amount )"
    )
    heal_target_guard = gpl.index('If (Target\'s "Title" == "Phantom")', heal)
    priestess_exception = gpl.index(
        'If (ThisAgent\'s "Title" != "Priestess")', heal_target_guard
    )
    blocked_heal_return = gpl.index("return;", priestess_exception)
    shared_agent_heal = gpl.index(
        "$Healing_Shared(Target, Healing_Amount);", blocked_heal_return
    )
    player_heal = gpl.index(
        "Function Player_Heal( Agent Target, integer Healing_Amount )",
        shared_agent_heal,
    )
    player_target_guard = gpl.index(
        'If (Target\'s "Title" == "Phantom")', player_heal
    )
    blocked_player_return = gpl.index("return;", player_target_guard)
    shared_player_heal = gpl.index(
        "$Healing_Shared(Target, Healing_Amount);", blocked_player_return
    )
    if not (
        heal
        < heal_target_guard
        < priestess_exception
        < blocked_heal_return
        < shared_agent_heal
        < player_heal
        < player_target_guard
        < blocked_player_return
        < shared_player_heal
    ):
        fail(
            f"{gpl_path}: ordinary healing must reject Phantoms except when "
            "cast by a Priestess, and player healing must always reject them"
        )

    regeneration = gpl.index(
        "function Regeneration_elixer_effect ( agent thisagent, agent target )"
    )
    regeneration_guard = gpl.index(
        'If (thisagent\'s "Title" == "Phantom")', regeneration
    )
    regeneration_delete = gpl.index(
        "$DeleteInventoryItem(#Bazaar_Item_Four, ThisAgent);",
        regeneration_guard,
    )
    regeneration_forget = gpl.index(
        '$ForgetSpell(ThisAgent, "Regeneration_Elixer");',
        regeneration_delete,
    )
    regeneration_return = gpl.index("return;", regeneration_forget)
    regeneration_effect = gpl.index(
        '$CreateEffector(thisagent, "Regeneration_elixer_effector", 0);',
        regeneration_return,
    )
    if not (
        regeneration
        < regeneration_guard
        < regeneration_delete
        < regeneration_forget
        < regeneration_return
        < regeneration_effect
    ):
        fail(
            f"{gpl_path}: a Phantom must consume a Regeneration Elixir without "
            "receiving its regeneration effect"
        )

    healing_wind = gpl.index("function Healing_Wind ()")
    wind_guard = gpl.index('If (hero\'s "Title" != "Phantom")', healing_wind)
    wind_effect = gpl.index(
        '$CreateEffector(hero, "Regeneration_elixer_effector", 0);',
        wind_guard,
    )
    if not healing_wind < wind_guard < wind_effect:
        fail(
            f"{gpl_path}: Healing Wind must exclude Phantoms before applying "
            "its regeneration effect"
        )

    evaluation = gpl.index(
        "Function Eval_For_Healing(agent ThisAgent, integer Distance) is Agent"
    )
    phantom_exclusion = gpl.index('If (Hero\'s "Title" != "Phantom")', evaluation)
    injured_append = gpl.index("Injured_Heroes << Hero;", phantom_exclusion)
    healer_effect = gpl.index("function Healer_Heal_Effect(agent thisagent, agent target)")
    healer_guard = gpl.index('If (target\'s "Title" == "Phantom")', healer_effect)
    healer_reset = gpl.index("$Reset_Tasks(thisagent);", healer_guard)
    healer_return = gpl.index("return;", healer_reset)
    healer_visual = gpl.index(
        '$CreateEffector(target, "healer_healing_effector", 0);', healer_return
    )
    healer_heal = gpl.index("$Heal(ThisAgent, Target, Healing);", healer_visual)
    if not (
        evaluation
        < phantom_exclusion
        < injured_append
        < healer_effect
        < healer_guard
        < healer_reset
        < healer_return
        < healer_visual
        < healer_heal
    ):
        fail(
            f"{gpl_path}: Healers must reject Phantoms during selection and "
            "again before applying their healing effect"
        )

    drain = gpl.index("function Drain_Life_Hit(agent thisagent, agent target)")
    self_heal_check = gpl.index(
        "If ($GetAttribute(ThisAgent, #ATTRIB_HP) < $GetAttribute(ThisAgent, #ATTRIB_MaxHP))",
        drain,
    )
    self_heal = gpl.index("$Heal(ThisAgent, ThisAgent, 5);", self_heal_check)
    phantom_list = gpl.index('Phantoms = $ListTitles(Phantoms, "Phantom");', self_heal)
    phantom_target = gpl.index("Best_Phantom = Phantom;", phantom_list)
    phantom_heal = gpl.index("$Heal(ThisAgent, Best_Phantom, 5);", phantom_target)
    skeleton_list = gpl.index(
        'My_Skeletons = $ListTitles(My_Skeletons, "Skeleton");', phantom_heal
    )
    skeleton_target = gpl.index("Best_Skeleton = Skeleton;", skeleton_list)
    skeleton_heal = gpl.index(
        "$Heal(ThisAgent, Best_Skeleton, 5);", skeleton_target
    )
    drain_damage = gpl.index("$Spell_Attack(ThisAgent, Target, 15);", skeleton_heal)
    if not (
        drain
        < self_heal_check
        < self_heal
        < phantom_list
        < phantom_target
        < phantom_heal
        < skeleton_list
        < skeleton_target
        < skeleton_heal
        < drain_damage
    ):
        fail(
            f"{gpl_path}: Drain Life healing priority must be Priestess self, "
            "then allied Phantom, then controlled Skeleton"
        )

    if "Function Healing_Shared" in gpl:
        fail(
            f"{gpl_path}: Phantom healing rules must not override global "
            "Healing_Shared and accidentally block Priestess healing"
        )


def validate_deal_demon_test_setup(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    contract = (
        'phantoms_haunt = $SpawnUnit(palace, "Phantoms_Haunt"',
        'elf_guild = $SpawnUnit(palace, "Elven_Bungalow"',
        'agrela_temple = $SpawnUnit(palace, "Temple_Agrela1"',
        "Foreach Guild in Guilds do",
        'Guild\'s "SpecialScript" = $Hero_Generator;',
        '$NewThread( Guild\'s "SpecialScript", 60000 + $randomnumber(60000), Guild );',
    )
    missing = [value for value in contract if value not in gpl]
    if missing:
        fail(
            f"{gpl_path}: Deal with the Demon test setup is missing {missing}"
        )

    deal = gpl.index("function DEAL_DEMON()")
    deal_end = gpl.index("Function Potion_Check", deal)
    deal_gpl = gpl[deal:deal_end]
    forbidden_player_generators = (
        'phantoms_haunt\'s "SpecialScript"',
        'elf_guild\'s "SpecialScript"',
        'agrela_temple\'s "SpecialScript"',
    )
    present_forbidden = [
        value for value in forbidden_player_generators if value in deal_gpl
    ]
    if present_forbidden:
        fail(
            f"{gpl_path}: player-owned Deal with the Demon test guilds must "
            f"not auto-recruit through Hero_Generator: {present_forbidden}"
        )
    stock_loop = deal_gpl.index("Foreach Guild in Guilds do")
    stock_generator = deal_gpl.index(
        'Guild\'s "SpecialScript" = $Hero_Generator;',
        stock_loop,
    )
    stock_thread = deal_gpl.index(
        '$NewThread( Guild\'s "SpecialScript", 60000 + $randomnumber(60000), Guild );',
        stock_generator,
    )
    phantom_spawn = deal_gpl.index(
        'phantoms_haunt = $SpawnUnit(palace, "Phantoms_Haunt"',
        stock_thread,
    )
    elf_spawn = deal_gpl.index(
        'elf_guild = $SpawnUnit(palace, "Elven_Bungalow"',
        phantom_spawn,
    )
    agrela_spawn = deal_gpl.index(
        'agrela_temple = $SpawnUnit(palace, "Temple_Agrela1"',
        elf_spawn,
    )
    if not (
        stock_loop
        < stock_generator
        < stock_thread
        < phantom_spawn
        < elf_spawn
        < agrela_spawn
    ):
        fail(
            f"{gpl_path}: stock enemy guild generation and player test "
            "building spawn order are malformed"
        )
    if '$SpawnUnit(palace, "Temple_Agrela",' in gpl:
        fail(
            f"{gpl_path}: Temple_Agrela is a runtime title; scripted spawning "
            "must use the level-one prototype Temple_Agrela1"
        )


def validate(output_root: Path) -> None:
    if not output_root.is_dir():
        fail(f"{output_root}: build output directory does not exist")
    validate_manifest(output_root)
    validate_descriptions(output_root)
    validate_bcd_copy(output_root)
    validate_phantoms_haunt_identity(output_root)
    validate_phantom_item_cleanup(output_root)
    validate_ice_lance_contract(output_root)
    validate_icy_touch_contract(output_root)
    validate_frost_armor_contract(output_root)
    validate_phantom_spell_confidence_contract(output_root)
    validate_call_to_grave_contract(output_root)
    validate_eternal_soul_contract(output_root)
    validate_phantom_flee_home_contract(output_root)
    validate_phantom_potion_purchase_contract(output_root)
    validate_phantom_equipment_upgrade_contract(output_root)
    validate_phantom_healing_contract(output_root)
    validate_deal_demon_test_setup(output_root)

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
    validate_phantom_primary_direction_topology(
        maindata_path,
        phantom_image,
        sections.get(b"TILE", []),
    )
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
    validate_phantom_action_size_against_stand(maindata_path, captured)
    call_to_grave_image = captured.get((b"IMAG", b"PHc2Call to Grave"))
    if call_to_grave_image is None:
        fail(f"{maindata_path}: IMAG/PHc2Call to Grave was not found")
    validate_call_to_grave_portal_animation(
        maindata_path,
        call_to_grave_image,
        sections.get(b"TILE", []),
        captured,
    )
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
