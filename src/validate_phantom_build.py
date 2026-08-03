from __future__ import annotations

import argparse
import mmap
import re
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import build_phantom_guild as builder


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
SHARED_PRIESTESS_PHANTOM_GIVENS = (
    "Aster", "Ash", "Aven", "Briar", "Corin", "Cinder", "Eiren", "Elian",
    "Ember", "Fen", "Hollis", "Isen", "Jorin", "Kael", "Lark", "Hallow",
    "Kestrel", "Nyven", "Onyx", "Haven", "Quinn", "Riven", "Rowan", "Sable",
    "Seren", "Syl", "Taren", "Vale", "Vesper", "Wren", "Rune", "Zeph",
)
SHARED_PRIESTESS_PHANTOM_ENDINGS = (
    "Blackblood", "Darksoul", "Lifesbane", "Shadowfriend", "Soulstealer",
    "Spiritvoid", "Darkmoon", "Shadespawn", "Deepnight", "Gravewhisper",
    "Gravesong", "Graveward", "Coldshadow", "Coldheart", "Frostmark",
    "Frostveil", "Frostbound", "Winterdark", "Nightbloom", "Nightveil",
    "Gloamward", "Hollowmoon", "Gloamsong", "Nightshade", "Veilkeeper",
    "Mournsong", "of the Last Veil", "of Winter's Wake",
    "of the Quiet Grave", "of the Long Night", "the Gravewise", "the Veiled",
)
STOCK_GUILD_DIALOG_BACKING_TILES = {466, 474, 495}


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
        b"STRT": {b"QITM", b"AITX", b"HPTX", b"HN41", b"HN42"},
    },
    "phantom_miscdata.cam": {
        b"DATA": {b"BDEP"},
    },
    "phantom_maindata.cam": {
        b"IMAG": {
            b"PHM1Phantom",
            b"PHG1Phantom Guild",
            b"PHG2Phantom Guild L2",
            b"PHG3Phantom Guild L3",
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
            b"PHw1Winter Storm",
            b"PHw2Winter Hit",
            b"PHw3Winter Missile",
            b"PHw4Winter Flakes",
            b"PHw5Missile Flakes",
            b"PHw6Winter Anchor",
        },
        b"TILE": set(),
        b"SPLT": set(),
    },
    "phantom_interfacedata.cam": {
        b"IMAG": {
            b"PHTIraw textures",
        },
        b"TILE": set(),
    },
    # phantom_mx_interfacedata.cam was removed. It carried 753 tiles, every one
    # byte-identical to stock, zero custom tiles, and a single unchanged copy of
    # the stock INBwicons weapons record. It contributed nothing but 25.7 MB and
    # an unnecessary override of a stock interface record.
    "phantom_voices.cam": {
        b"WAVE": {
            b"PHS1",
            b"PHD1",
            b"PHI1",
            b"PHH1",
            b"PHC1",
            b"PHF1",
            b"PHR1",
            b"PHN1",
            b"PHC2",
            b"PHL1",
            b"PH10",
            b"PHE1",
            b"PHDH",
            b"PHA1",
            b"PHGS",
        },
    },
    "phantom_sounddesc.cam": {
        b"DSND": {b"PV01Phantom_Voice", b"PH01Phantom_Hired"},
    },
}

EXPECTED_DESCRIPTION_IDS = {
    "phantom_units.xml": {
        ("Unit", "PHM1"),
        *((("Unit", agent_name) for _, agent_name, _, _ in phantom_equipment_item_records())),
        ("Unit", "FrostArmorBonus"),
        ("Unit", "PHW1"),
        ("Unit", "PHG1"),
        ("Unit", "PHG2"),
        ("Unit", "PHG3"),
    },
    "phantom_actions.xml": {
        ("Action", "WRg1"),
        ("Action", "WRa2"),
        ("Action", "WRa3"),
        ("Action", "WRa4"),
        ("Action", "WRa5"),
        ("Action", "WRa6"),
        ("Action", "WRa7"),
    },
    "phantom_projectiles.xml": {
        ("Unit", "PHp1"),
        ("Unit", "PHW2"),
        ("Unit", "PHW7"),
        ("Unit", "PHW8"),
    },
    "phantom_particles.xml": {("Unit", "PHW4"), ("Unit", "PHW5")},
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
        ("Unit", "PHW3"),
        ("Unit", "PHW6"),
    },
    "phantom_sounds.xml": {
        ("Sound", "PV01"),
        ("Sound", "PH01"),
        ("Sound", "PH02"),
    },
}

CUSTOM_TILE_OWNERS = {
    b"PHG1Profile": (b"PHG1Phantom Guild", "low16"),
    b"PHG1BuildIcon": (b"PHG1Phantom Guild", "low16"),
    b"PHG1Bld": (b"PHG1Phantom Guild", "low16"),
    b"PHG1Act": (b"PHG1Phantom Guild", "low16"),
    b"PHG2Bld": (b"PHG2Phantom Guild L2", "low16"),
    b"PHG2Act": (b"PHG2Phantom Guild L2", "low16"),
    b"PHG3Bld": (b"PHG3Phantom Guild L3", "low16"),
    b"PHG3Act": (b"PHG3Phantom Guild L3", "low16"),
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
    b"PHw1Storm": (b"PHw1Winter Storm", "u32"),
    b"PHw2Hit": (b"PHw2Winter Hit", "u32"),
    b"PHw3Snow": (b"PHw3Winter Missile", "u32"),
    b"PHw4Flake": (b"PHw4Winter Flakes", "u32"),
    b"PHw5Flake": (b"PHw5Missile Flakes", "u32"),
    b"PHw6Anchor": (b"PHw6Winter Anchor", "u32"),
}

EXPECTED_CUSTOM_TILE_COUNTS = {
    b"PHG1Profile": 1,
    b"PHG1BuildIcon": 1,
    b"PHG1Bld": 14,
    b"PHG1Act": 8,
    b"PHG2Bld": 13,
    b"PHG2Act": 8,
    b"PHG3Bld": 13,
    b"PHG3Act": 8,
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
    b"PHw1Storm": 15,
    b"PHw2Hit": 8,
    b"PHw3Snow": 4,
    b"PHw4Flake": 13,
    b"PHw5Flake": 7,
    b"PHw6Anchor": 1,
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
    b"PHG2Bld0000",
    *(f"PHG2Bld{index:04d}".encode("ascii") for index in range(7, 13)),
    *(f"PHG2Act{index:02d}".encode("ascii") for index in range(8)),
    b"PHG3Bld0000",
    *(f"PHG3Bld{index:04d}".encode("ascii") for index in range(7, 13)),
    *(f"PHG3Act{index:02d}".encode("ascii") for index in range(8)),
}

LOWER_LEFT_BALCONY_PIT_TILES = {
    b"PHG1Bld0003",
    *(f"PHG1Act{index:02d}".encode("ascii") for index in range(8)),
}

CONSTRUCTION_BUILDING_TILES = {
    *(f"PHG1Bld{index:04d}".encode("ascii") for index in range(3)),
    b"PHG2Bld0010",
    b"PHG2Bld0011",
    b"PHG3Bld0010",
    b"PHG3Bld0011",
}

TRANSITIONAL_DESTRUCTION_TILES = {
    b"PHG1Bld0012",  # source tile 1530, Damaged B
    b"PHG1Bld0013",  # source tile 1531, Collapsed Intermediate
    b"PHG2Bld0008",  # source tile 1533, Damaged B
    b"PHG2Bld0009",  # source tile 1534, Collapsed Intermediate
    b"PHG3Bld0008",  # source tile 1536, Damaged B
    b"PHG3Bld0009",  # source tile 1537, Collapsed Intermediate
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
    manifest_path = output_root / "CustomGuildPhantomsHaunt.mmxml"
    tree = parse_xml(manifest_path)
    root = tree.getroot()
    mods = root.findall("./Mod")
    if len(mods) != 1:
        fail(
            f"{manifest_path}: package must expose exactly one selectable mod; "
            f"found {len(mods)}"
        )
    configurations = mods[0].findall("./DataConfiguration")
    if len(configurations) != 1:
        fail(
            f"{manifest_path}: mod must contain exactly one DataConfiguration; "
            f"found {len(configurations)}"
        )
    datasets = configurations[0].findall("./Dataset")
    if len(datasets) != 1 or datasets[0].get("base") != "Any":
        dataset_bases = [dataset.get("base") for dataset in datasets]
        fail(
            f"{manifest_path}: universal package must contain exactly one "
            f'Dataset with base="Any"; found {dataset_bases}'
        )

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
                if size == 0 and extension != b"TILE":
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

        for entry in sections.get(b"DATA", []):
            if entry.name == b"BDEP":
                captured[(entry.section, entry.name)] = bytes(
                    data[entry.offset : entry.offset + entry.size]
                )

        for entry in sections.get(b"SMNU", []):
            if entry.name == b"AP07":
                captured[(entry.section, entry.name)] = bytes(
                    data[entry.offset : entry.offset + entry.size]
                )

        for entry in sections.get(b"WAVE", []):
            payload = bytes(data[entry.offset : entry.offset + entry.size])
            validate_wave(path, entry, payload)
            if path.name == "phantom_voices.cam":
                captured[(entry.section, entry.name)] = payload

        for entry in sections.get(b"DSND", []):
            payload = bytes(data[entry.offset : entry.offset + entry.size])
            validate_dsnd(path, entry, payload)
            if entry.name == b"PH01Phantom_Hired":
                required = (
                    b"DSND",
                    b"PH01",
                    b"Phantom_Hired",
                    b"EBE0",
                    b"PHS1",
                    b"SG14",
                )
                missing = [value for value in required if value not in payload]
                if missing or b"RM01" in payload or b"Rage_of_Krolm" in payload:
                    fail(
                        f"{path}: custom Phantom DSND is malformed; "
                        f"missing {missing}"
                    )
                captured[(entry.section, entry.name)] = payload
            elif entry.name == b"PV01Phantom_Voice":
                required = (
                    b"DSND",
                    b"PV01",
                    b"Phantom_Voice",
                    b"GVC0",
                    b"PHC1",
                    b"SG04",
                    b"GVF0",
                    b"PHF1",
                    b"SG05",
                    b"GVD0",
                    b"PHD1",
                    b"SG06",
                    b"GVR0",
                    b"PHR1",
                    b"SG11",
                    b"GVO0",
                    b"PHN1",
                    b"SG09",
                    b"GVS0",
                    b"PHI1",
                    b"SG14",
                    b"GVP0",
                    b"PHC2",
                    b"SG21",
                    b"EDH0",
                    b"PHDH",
                    b"SG02",
                    b"GVL0",
                    b"PHL1",
                    b"SG08",
                    b"GVH0",
                    b"PHH1",
                    b"SG07",
                    b"GVS4",
                    b"PH10",
                    b"EG01",
                    b"PHE1",
                )
                missing = [value for value in required if value not in payload]
                forbidden = (
                    b"WZ01",
                    b"Wizard",
                    b"WZGT",
                    b"WZFT",
                    b"WZDO",
                    b"WZDG",
                    b"WZFL",
                    b"WZSS",
                    b"WZCL",
                    b"WZDH",
                    b"WZGL",
                    b"WZSE",
                    b"WZTL",
                    b"WZE1",
                )
                retained = [value for value in forbidden if value in payload]
                if missing or retained:
                    fail(
                        f"{path}: Phantom voice DSND is malformed; "
                        f"missing {missing}, retained stock identity/targets {retained}"
                    )
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


def validate_wave(path: Path, entry: Entry, data: bytes) -> None:
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        fail(f"{path}: {entry.label} is not a RIFF/WAVE payload")
    if data[12:16] != b"fmt " or struct.unpack_from("<I", data, 16)[0] != 16:
        fail(f"{path}: {entry.label} does not use the expected PCM fmt chunk")
    audio_format, channels = struct.unpack_from("<HH", data, 20)
    sample_rate = struct.unpack_from("<I", data, 24)[0]
    bits_per_sample = struct.unpack_from("<H", data, 34)[0]
    if (audio_format, channels, sample_rate, bits_per_sample) != (1, 1, 22050, 16):
        fail(
            f"{path}: {entry.label} must be mono 22050 Hz 16-bit PCM; got "
            f"format={audio_format} channels={channels} rate={sample_rate} "
            f"bits={bits_per_sample}"
        )


def validate_dsnd(path: Path, entry: Entry, data: bytes) -> None:
    if len(data) < 64 or data[:4] != b"DSND" or data[16:20] != b"DATA":
        fail(f"{path}: {entry.label} is not a stock-shaped DSND payload")
    if struct.unpack_from("<I", data, 4)[0] != len(data) - 16:
        fail(f"{path}: {entry.label} has an invalid DSND size")
    if struct.unpack_from("<I", data, 20)[0] != len(data) - 32:
        fail(f"{path}: {entry.label} has an invalid DATA size")

    head_offset = data.find(b"HEAD", 32)
    prim_offset = data.find(b"PRIM", 32)
    if head_offset < 0 or prim_offset < 0:
        fail(f"{path}: {entry.label} is missing its HEAD or PRIM block")
    head_size = struct.unpack_from("<I", data, head_offset + 4)[0]
    expected_prim = head_offset + 16 + head_size
    if prim_offset != expected_prim:
        fail(
            f"{path}: {entry.label} declares a {head_size}-byte HEAD body, "
            f"which places PRIM at {expected_prim}, not {prim_offset}"
        )


def strt_text_by_fourcc(data: bytes, fourcc: str) -> bytes | None:
    record_id = int.from_bytes(fourcc.encode("ascii"), "little")
    count = struct.unpack_from("<H", data, 0)[0]
    for index in range(count):
        offset = struct.unpack_from("<I", data, 4 + index * 4)[0]
        if struct.unpack_from("<I", data, offset)[0] == record_id:
            end = data.index(b"\x00", offset + 4)
            return data[offset + 4 : end]
    return None


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


def validate_shared_priestess_phantom_names(
    path: Path,
    givens_data: bytes,
    endings_data: bytes,
) -> None:
    expected_tables = (
        (b"HN41", givens_data, SHARED_PRIESTESS_PHANTOM_GIVENS),
        (
            b"HN42",
            endings_data,
            tuple(f" {ending}" for ending in SHARED_PRIESTESS_PHANTOM_ENDINGS),
        ),
    )
    for table_name, data, expected in expected_tables:
        count = struct.unpack_from("<H", data, 0)[0]
        if count != len(expected):
            fail(
                f"{path}: STRT/{table_name.decode()} has {count} strings; "
                f"expected {len(expected)}"
            )
        actual: list[str] = []
        for index in range(count):
            offset = struct.unpack_from("<I", data, 4 + index * 4)[0]
            record_id = struct.unpack_from("<I", data, offset)[0]
            if record_id != index:
                fail(
                    f"{path}: STRT/{table_name.decode()} slot {index} "
                    f"contains record ID {record_id}"
                )
            end = data.index(b"\x00", offset + 4)
            actual.append(data[offset + 4 : end].decode("cp1252"))
        if tuple(actual) != expected:
            fail(f"{path}: STRT/{table_name.decode()} name pool is not approved")


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
        expected_dimensions = (276, 229)
    elif entry.name.startswith(b"PHG2Act"):
        expected_dimensions = (276, 250)
    elif entry.name.startswith(b"PHG3Act"):
        expected_dimensions = (276, 275)
    elif entry.name == b"PHTIPanel0001":
        expected_dimensions = (200, 245)
    if expected_dimensions and (width, height) != expected_dimensions:
        fail(
            f"{path}: {entry.label} is {width}x{height}; "
            f"expected {expected_dimensions[0]}x{expected_dimensions[1]}"
        )

    building_hotspots = {
        b"PHG1Bld0000": (136, 80),
        b"PHG1Bld0001": (137, 80),
        b"PHG1Bld0002": (137, 80),
        b"PHG1Bld0003": (137, 80),
        b"PHG1Bld0004": (134, 11),
        b"PHG1Bld0005": (55, 56),
        b"PHG1Bld0006": (55, 56),
        b"PHG1Bld0007": (55, 56),
        b"PHG1Bld0008": (55, 56),
        b"PHG1Bld0009": (55, 56),
        b"PHG1Bld0010": (55, 56),
        b"PHG1Bld0011": (137, 80),
        b"PHG1Bld0012": (137, 76),
        b"PHG1Bld0013": (137, 58),
    }
    expected_hotspot = building_hotspots.get(entry.name)
    if entry.name.startswith(b"PHG1Act"):
        expected_hotspot = (137, 80)
    if expected_hotspot is not None:
        if row_stride != width:
            fail(
                f"{path}: {entry.label} retains stale row stride {row_stride}; "
                f"expected native width {width}"
            )
        actual_hotspot = struct.unpack_from("<HH", tile, 10)
        if actual_hotspot != expected_hotspot:
            fail(
                f"{path}: {entry.label} has hotspot {actual_hotspot}; "
                f"expected reduced-envelope hotspot {expected_hotspot}"
            )
    elif entry.name.startswith((b"PHG2Bld", b"PHG2Act", b"PHG3Bld", b"PHG3Act")):
        if row_stride != width:
            fail(
                f"{path}: {entry.label} retains stale row stride {row_stride}; "
                f"expected native width {width}"
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
        # Reducing the Level 1 TILE from the inherited 301-pixel Fervus
        # envelope to the Haunt's 276-pixel envelope rescales and recenters
        # this known balcony notch. Keep the regression check on the notch
        # itself instead of the obsolete stock-canvas coordinates.
        pit_x_start = 44 if width == 276 else 58
        pit_y_start = 136
        pit_values = [
            pixels[y][x]
            for y in range(pit_y_start, pit_y_start + 3)
            for x in range(pit_x_start, pit_x_start + 9)
        ]
        transparent = sum(value == 0 for value in pit_values)
        red = sum(value == 247 for value in pit_values)
        magenta = sum(248 <= value <= 250 for value in pit_values)
        if transparent:
            fail(
                f"{path}: {entry.label} lower-left balcony pit "
                f"x={pit_x_start}..{pit_x_start + 8},"
                f"y={pit_y_start}..{pit_y_start + 2} "
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


def validate_no_redistributed_stock_art(
    path: Path,
    sections: dict[bytes, list[Entry]],
) -> None:
    """Reject tile slots that carry payload the package does not reference.

    Majesty addresses tiles by their position in a CAM's TILE section, so a mod
    appending custom tiles must emit an entry for every slot below the highest
    index it uses. Those unused entries must have zero-length payloads so the
    engine falls back to the installed stock archive. This exact check prevents
    unrelated artwork from being carried in the generated package.
    """
    tiles = sections.get(b"TILE")
    if not tiles:
        return

    data = path.read_bytes()
    referenced: set[int] = set()
    for entry in sections.get(b"IMAG", []):
        image = data[entry.offset : entry.offset + entry.size]
        referenced |= referenced_indices(image, "full", len(tiles))
        referenced |= referenced_indices(image, "low16", len(tiles))

    allowed_unreferenced = {
        "phantom_maindata.cam": builder.maindata_engine_addressed_tile_indices(),
    }.get(path.name, set())
    offenders = [
        entry.index
        for entry in tiles
        if entry.index not in referenced
        and entry.index not in allowed_unreferenced
        and entry.size > 0
    ]
    if not offenders:
        return

    by_index = {entry.index: entry.size for entry in tiles}
    carried = sum(by_index[index] for index in offenders)
    fail(
        f"{path}: {len(offenders)} unexpected unreferenced tile slots carry "
        f"{carried} bytes of payload at indices {offenders[:20]}. Only emitted "
        f"IMAG references and the archive's exact engine-addressed allowlist may "
        f"carry TILE data."
    )


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
    references = referenced_indices(image, "u32", len(tiles))
    if panel_entries[0].index not in references:
        fail(f"{path}: IMAG/PHTIraw textures does not reference PHTIPanel0001")
    stale_backings = references & STOCK_GUILD_DIALOG_BACKING_TILES
    if stale_backings:
        fail(
            f"{path}: IMAG/PHTIraw textures still references stock guild "
            f"dialog backing TILEs {sorted(stale_backings)}"
        )


def validate_bcd_copy(output_root: Path) -> None:
    data_bcd = output_root / "Data" / "Phantom.bcd"
    gpl_bcd = output_root / "GPL" / "Phantom.bcd"
    if not gpl_bcd.is_file() or gpl_bcd.stat().st_size == 0:
        fail(f"{gpl_bcd}: compiled GPL output is missing or empty")
    if data_bcd.read_bytes() != gpl_bcd.read_bytes():
        fail(f"{data_bcd}: does not match the compiled GPL/Phantom.bcd")


def validate_phantoms_haunt_identity(output_root: Path) -> None:
    manifest_path = output_root / "CustomGuildPhantomsHaunt.mmxml"
    manifest = manifest_path.read_text(encoding="utf-8")
    if (
        '<DisplayName lang="en_US">Custom Guild: Phantoms Haunt</DisplayName>'
        not in manifest
    ):
        fail(f"{manifest_path}: missing public Phantoms Haunt display name")

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    units_tree = parse_xml(units_path)
    phantom = units_tree.find('.//Description[@ID="PHM1"]')
    phantom_help = phantom.find("./Game/HelpID") if phantom is not None else None
    if phantom_help is None or phantom_help.get("value") != "hPH0":
        fail(f"{units_path}: Phantom must use its dedicated hPH0 help page")
    phantom_game = phantom.find("./Game") if phantom is not None else None
    phantom_engine = phantom.find("./Engine") if phantom is not None else None
    phantom_movement = (
        phantom_engine.find('./Attachment[@kind="Movement"]')
        if phantom_engine is not None
        else None
    )
    phantom_speed = phantom_game.find("./Speed") if phantom_game is not None else None
    if (
        phantom_movement is None
        or phantom_movement.get("type") != "Walk"
        or phantom_movement.get("ID") != "Class 1"
        or phantom_speed is None
        or phantom_speed.get("value") != "1"
    ):
        fail(f"{units_path}: Phantom must use the tuned Walk/Class 1, Speed 1 profile")
    phantom_cost = phantom_game.find("./Cost") if phantom_game is not None else None
    phantom_recruit = (
        phantom_game.find("./RecruitDelay") if phantom_game is not None else None
    )
    if (
        phantom_cost is None
        or phantom_cost.get("value") != "700"
        or phantom_recruit is None
        or phantom_recruit.get("value") != "16000"
    ):
        fail(
            f"{units_path}: Phantom must cost 700 gold and recruit in 16000 ms"
        )
    expected_building_identity = (
        'ID="PHG1" Name="Phantoms_Haunt" Description="Phantoms Haunt"'
    )
    if expected_building_identity not in units:
        fail(f"{units_path}: building identity was not renamed to Phantoms Haunt")
    if '<DefaultSound value="Phantoms_Haunt"/>' not in units:
        fail(f"{units_path}: building sound name was not renamed to Phantoms_Haunt")

    sounds_path = output_root / "Data" / "phantom_sounds.xml"
    sounds = sounds_path.read_text(encoding="utf-8")
    if 'ID="PH02" Name="Phantoms_Haunt"' not in sounds:
        fail(f"{sounds_path}: building sound description retains the old name")
    sounds_tree = parse_xml(sounds_path)
    phantom_sound = sounds_tree.find('.//Description[@ID="PV01"]')
    hired_sound = sounds_tree.find('.//Description[@ID="PH01"]')
    recruitment_phase = (
        hired_sound.find('./Engine/Phase[@ID="Begin"]')
        if hired_sound is not None
        else None
    )
    recruitment_wave = (
        recruitment_phase.find("./Wave") if recruitment_phase is not None else None
    )
    recruitment_group = (
        recruitment_phase.find("./Group") if recruitment_phase is not None else None
    )
    if (
        recruitment_wave is None
        or recruitment_wave.get("value") != "PHS1"
        or recruitment_group is None
        or recruitment_group.get("value") != "Voice_Special_1_Group"
        or recruitment_phase.find("./DistanceModifier") is not None
    ):
        fail(
            f"{sounds_path}: Phantom_Hired/Begin must use PHS1 with the stock "
            "hero voice group and spatial-distance policy"
        )
    if phantom_sound is None or phantom_sound.get("Name") != "Phantom_Voice":
        fail(f"{sounds_path}: Phantom hero sound name must be globally unique")
    if hired_sound is None or hired_sound.get("Name") != "Phantom_Hired":
        fail(f"{sounds_path}: recruitment sound must use unique Phantom_Hired name")
    expected_voice_phases = {
        "VFX_GO_COMBAT": ("PHC1", "Enter_Combat_Group"),
        "VFX_FLEE_COMBAT": ("PHF1", "Flee_Combat_Group"),
        "VFX_DECIDING": ("PHD1", "Deciding_Group"),
        "VFX_GO_REWARD": ("PHR1", "GoReward_Group"),
        "VFX_FIND_COOL": ("PHN1", "Find_Cool_Group"),
        "VFX_SPECIAL1": ("PHI1", "Voice_Special_1_Group"),
        "VFX_CAST_SPELL1": ("PHC2", "Hero_Cast_Voice_Group"),
        "Death": ("PHDH", "Death_Group"),
        "VFX_GAIN_LEVEL": ("PHL1", "Up-Level_Group"),
        "VFX_SEE_HOSTILE": ("PHH1", "See_hostile_Group"),
        "GetHit": ("PHA1", "GetHit_Group"),
        "Attack": ("PHA1", "Attack_Group"),
        "VFX_LEVEL_10": ("PH10", None),
        "Easter_Egg": ("PHE1", None),
    }
    actual_phase_ids = {
        phase.get("ID") for phase in phantom_sound.findall("./Engine/Phase")
    }
    if actual_phase_ids != set(expected_voice_phases):
        fail(
            f"{sounds_path}: Phantom voice phase set differs from the approved "
            f"stock-compatible set; got {sorted(actual_phase_ids)}"
        )
    for phase in phantom_sound.findall("./Engine/Phase"):
        phase_id = phase.get("ID")
        wave_node = phase.find("./Wave")
        group_node = phase.find("./Group")
        expected_wave, expected_group = expected_voice_phases[phase_id]
        if wave_node is None or wave_node.get("value") != expected_wave:
            fail(
                f"{sounds_path}: {phase_id} must use Phantom WAVE {expected_wave}"
            )
        actual_group = group_node.get("value") if group_node is not None else None
        if actual_group != expected_group:
            fail(
                f"{sounds_path}: {phase_id} must use group {expected_group!r}, "
                f"got {actual_group!r}"
            )
        if wave_node is not None and wave_node.get("value") == "PHS1":
            fail(f"{sounds_path}: PHS1 must be recruitment-only")
    if '<DefaultSound value="Phantom_Voice"/>' not in units:
        fail(f"{units_path}: Phantom must retain its unique default voice identity")

    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    if "[Phantoms_Haunt]" not in building_data or "(title Phantoms_Haunt)" not in building_data:
        fail(f"{building_data_path}: building data section was not renamed to Phantoms_Haunt")

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    playtest_values = (
        "(PercentageHPRetreat 20)",
        "(enemy_estimation 1.0)",
        "(self_estimation 1.4)",
        "(Loyalty 30)",
        "(evaluationScript\teval_enemies_nearby)",
    )
    missing = [value for value in playtest_values if value not in hero_data]
    if missing:
        fail(f"{hero_data_path}: approved playtest profile is missing {missing}")
    if "(evaluationScript\twizard_eval_nearby)" in hero_data:
        fail(f"{hero_data_path}: Phantom still uses the Wizard threat evaluator")

    generated_text = "\n".join((manifest, units, sounds, building_data, hero_data))
    for stale_name in ("Phantoms Guild", "Phantoms_Guild", "Phantom_Guild"):
        if stale_name in generated_text:
            fail(f"{output_root}: generated text retains stale building name {stale_name!r}")


def validate_phantoms_haunt_upgrade_contract(output_root: Path) -> None:
    units_path = output_root / "Data" / "phantom_units.xml"
    tree = parse_xml(units_path)
    expected_levels = (
        (
            "PHG1",
            "Phantoms_Haunt",
            "PHG1",
            None,
            "Phantoms_Haunt2",
            False,
            "hP34",
            "1400",
        ),
        (
            "PHG2",
            "Phantoms_Haunt2",
            "PHG2",
            "Phantoms_Haunt",
            "Phantoms_Haunt3",
            True,
            "hP35",
            "1800",
        ),
        (
            "PHG3",
            "Phantoms_Haunt3",
            "PHG3",
            "Phantoms_Haunt2",
            None,
            True,
            "hP36",
            "2200",
        ),
    )
    for (
        description_id,
        unit_name,
        image_base,
        upgrade_from,
        upgrade_to,
        not_buildable,
        help_id,
        cost,
    ) in expected_levels:
        description = tree.find(f'.//Description[@ID="{description_id}"]')
        if description is None or description.get("Name") != unit_name:
            fail(
                f"{units_path}: missing or malformed Haunt upgrade description "
                f"{description_id}/{unit_name}"
            )
        image = description.find("./Engine/ImageIDBase")
        if image is None or image.get("value") != image_base:
            fail(
                f"{units_path}: {description_id} must use ImageIDBase={image_base}"
            )
        game = description.find("./Game")
        if game is None:
            fail(f"{units_path}: {description_id} has no Game block")
        actual_help = game.find("./HelpID")
        if actual_help is None or actual_help.get("value") != help_id:
            fail(
                f"{units_path}: {description_id} must use help page {help_id}"
            )
        actual_cost = game.find("./Cost")
        actual_multiplier = game.find("./Multiplier")
        actual_income = game.find("./IncomeAmount")
        if (
            actual_cost is None
            or actual_cost.get("value") != cost
            or actual_multiplier is None
            or actual_multiplier.get("value") != "2.0"
            or actual_income is None
            or actual_income.get("value") != "40"
        ):
            fail(
                f"{units_path}: {description_id} must cost {cost} gold and "
                "use stock Krypta repeat-build multiplier 2.0 and income 40"
            )
        actual_from = game.find("./UpgradeFrom")
        actual_to = game.find("./UpgradeTo")
        if (
            (actual_from.get("value") if actual_from is not None else None)
            != upgrade_from
            or (actual_to.get("value") if actual_to is not None else None)
            != upgrade_to
        ):
            fail(
                f"{units_path}: {description_id} upgrade links are malformed"
            )
        flags = {flag.get("value") for flag in game.findall("./Flags")}
        if ("NotBuildable" in flags) != not_buildable:
            fail(
                f"{units_path}: {description_id} has incorrect NotBuildable state"
            )
        produced = {unit.get("ID") for unit in game.findall("./Produces/Unit")}
        if produced != {"Phantom"}:
            fail(f"{units_path}: {description_id} must recruit only Phantoms")

    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    building_contract = (
        "[Phantoms_Haunt]",
        "(Level 1)",
        "[Phantoms_Haunt2]",
        "(Level 2)",
        "[Phantoms_Haunt3]",
        "(Level 3)",
    )
    missing_building = [
        value for value in building_contract if value not in building_data
    ]
    if missing_building:
        fail(
            f"{building_data_path}: three-level Haunt data is missing "
            f"{missing_building}"
        )
    if "(max_level 1)" in building_data:
        fail(f"{building_data_path}: Haunt is still capped at level 1")
    if building_data.count("(upgradescript basic_upgrade)") != 2:
        fail(
            f"{building_data_path}: exactly levels 1 and 2 must use basic_upgrade"
        )

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    gameplay_contract = (
        "Function Phantom_Player_Max_Completed_Haunt_Level(agent ThisAgent) is integer",
        '$GetAttribute(Haunt, #ATTRIB_CurrentStageBuilt) == 1',
        'If (Haunt\'s "Level" > Best_Level)',
        "Function Phantom_Haunt_Player_Perk_Watch(agent Palace)",
        '$LearnSpell(Phantom, "icy_touch");',
        '$ForgetSpell(Phantom, "icy_touch");',
        '$LearnSpell(Phantom, "endless_winter");',
        '$ForgetSpell(Phantom, "endless_winter");',
        '#CheckTitles,\n\t\t"Priestess"',
        "expression #Phantom_Rush_Movement_Bonus -22",
        "expression #Phantom_Rush_Action_Bonus -10",
        "expression #Phantom_Rush_Range_Bonus 60",
        "expression #Phantom_Base_Movement_Bonus -15",
        "Function Phantom_Rush_Unto_Death_Begin(agent ThisAgent)",
        "#ATTRIB_MovementRateModifier,\n\t\t#Phantom_Rush_Movement_Bonus",
        "#ATTRIB_ActionRateModifier,\n\t\t#Phantom_Rush_Action_Bonus",
        "#ATTRIB_MaxAttackRange,\n\t\t#Phantom_Rush_Range_Bonus",
        'ThisAgent\'s "castingrange" += #Phantom_Rush_Range_Bonus;',
        "$SetAttribute(ThisAgent, #ATTRIB_HasEffectWingedFeet, 1);",
        "Function Phantom_Rush_Unto_Death_End(agent ThisAgent)",
        "#ATTRIB_MovementRateModifier,\n\t\t- #Phantom_Rush_Movement_Bonus",
        "#ATTRIB_ActionRateModifier,\n\t\t- #Phantom_Rush_Action_Bonus",
        "#ATTRIB_MaxAttackRange,\n\t\t- #Phantom_Rush_Range_Bonus",
        'ThisAgent\'s "castingrange" -= #Phantom_Rush_Range_Bonus;',
        "$SetAttribute(ThisAgent, #ATTRIB_HasEffectWingedFeet, 0);",
        "$Phantom_Rush_Unto_Death_Begin(Priestess);",
        "$Phantom_Rush_Unto_Death_End(Priestess);",
        "Function Phantom_Sync_Speed_Profile(agent ThisAgent)",
        "Function Phantom_Ensure_Behavior_Watch(agent ThisAgent)",
        '"PhantomFrostArmorWatch",',
        "$Phantom_Frost_Armor_Watch",
        '$IsRunning(ThisAgent\'s "PhantomFrostArmorWatch") == False',
        '$NewThread(ThisAgent\'s "PhantomFrostArmorWatch", 100, ThisAgent);',
        '$HasAttribute("PhantomBaseMovementApplied", ThisAgent)',
        'ThisAgent\'s "PhantomBaseMovementApplied" = True;',
        "#ATTRIB_MovementRateModifier,\n\t\t\t\t#Phantom_Base_Movement_Bonus",
        '$GetSpellAttribute(\n\t\t"call_to_grave",\n\t\t"character_level"',
        "$SetAttribute(ThisAgent, #ATTRIB_Speed, 5);",
        "$SetAttribute(ThisAgent, #ATTRIB_Speed, 1);",
        "$Phantom_Sync_Speed_Profile(Phantom);",
        "$Phantom_Ensure_Behavior_Watch(Phantom);",
        "$Phantom_Sync_Speed_Profile(thisagent);",
        'Priestess\'s "PhantomRushUntoDeathActive" = True;',
        'Priestess\'s "PhantomRushUntoDeathActive" = False;',
        "function Phantom_Priestess_Follow_Support_Check(agent ThisAgent, string WhatToSupport, integer Chance) is boolean",
        "If ($ListSize(Guards) < 2)",
        "Best_One = $Pick_Closest(ThisAgent, Potentials);",
        'ThisAgent\'s "BasicScript" = $Phantom_Priestess_Follow_Support;',
        'ThisAgent\'s "BackScript" = $Phantom_Priestess_Follow_Support;',
        'ThisAgent\'s "ActiveScript" = $Phantom_Priestess_Follow_Support;',
        "function Phantom_Priestess_Follow_Support(agent ThisAgent)",
        '#ATTRIB_MaxAttackRange) -\n\t\t\t\t\t\t\t#follow_support_buffer',
        'ThisAgent\'s "Destination" = $LocationOf(Target);',
        'ThisAgent\'s "Target" = ThisAgent;',
        'ThisAgent\'s "Destination",\n\t\t\t\t\t\t\t\t"avoid_vehicles"',
        'New_Target\'s "Type" == "Building"',
        'New_Target\'s "Type" == "Lair"',
        'If (Target\'s "ActiveScript" == $Attack_Object)',
        "Join_Attack = True;",
        "If (Join_Attack)",
        "Function Phantom_Priestess_Follow_Check(agent ThisAgent) is boolean",
        "If ($Phantom_Player_Max_Completed_Haunt_Level(ThisAgent) < 3)",
        "$Phantom_Priestess_Follow_Support_Check(",
        '"Phantom",',
        "function Priestess_tree(agent ThisAgent)",
        "$Build_Horde(ThisAgent, 95) == False",
        "$Phantom_Priestess_Follow_Check(ThisAgent) == False",
        # The two expansion-only decisions must go through the guarded
        # wrappers, never be called directly. Purchase_Bazaar and
        # Hall_Champs_Check do not exist in Original Majesty, and calling them
        # there kills the Priestess decision chain mid-tree.
        "$Phantom_Priestess_Bazaar_Check(ThisAgent, 70) == False",
        "$Phantom_Priestess_Champs_Check(ThisAgent, 40) == False",
        'Bazaars,\n\t\t#MyPlayer,\n\t\t#CheckTitles,\n\t\t"Magic_Bazaar"',
        'Halls,\n\t\t#MyPlayer,\n\t\t#CheckTitles,\n\t\t"HallOfChampions"',
        "function follow_support_check(agent ThisAgent, string WhatToSupport, integer Chance) is boolean",
        'If (ThisAgent\'s "Title" == "Phantom")',
        "$Raid_lair(thisagent,80)",
        "$raid_enemy_building(thisagent,65)",
        "$Combat_wandering(thisagent,90)",
        "$combat_wandering_heroes(thisagent,75)",
        "$Explore_Map(thisagent,75)",
        '$check_library(thisagent,15, "Train_magic_resist")',
        "$Go_Home(thisagent,30)",
        "Healing = 10;",
    )
    missing_gameplay = [value for value in gameplay_contract if value not in gpl]
    if missing_gameplay:
        fail(
            f"{gpl_path}: Haunt level perk contract is missing "
            f"{missing_gameplay}"
        )
    perk_watcher_start = gpl.index(
        "Function Phantom_Haunt_Player_Perk_Watch(agent Palace)"
    )
    perk_watcher_end = gpl.index(
        "Function Phantoms_Haunt_Construction_Birth(agent ThisAgent)",
        perk_watcher_start,
    )
    perk_watcher = gpl[perk_watcher_start:perk_watcher_end]
    if "#ATTRIB_MovementRateModifier" in perk_watcher:
        fail(
            f"{gpl_path}: Rush unto Death applies its modifier directly in "
            "the watcher instead of routing through the stock-shaped clone"
        )
    if "#ATTRIB_Speed" in perk_watcher:
        fail(
            f"{gpl_path}: Rush unto Death bypasses stock Winged Feet with a "
            "direct write to the AI-facing Speed attribute"
        )
    forbidden_rush_transform = (
        "$ChangeUnitType(",
        "$RevertUnitType(",
        "Phantom_Rush_Priestess",
    )
    present_rush_transform = [
        value for value in forbidden_rush_transform if value in perk_watcher
    ]
    if present_rush_transform:
        fail(
            f"{gpl_path}: Rush unto Death still contains the rejected "
            f"unit-type transformation path {present_rush_transform}"
        )
    rush_begin_start = gpl.index(
        "Function Phantom_Rush_Unto_Death_Begin(agent ThisAgent)"
    )
    rush_end = gpl.index(
        "Function Phantom_Start_Player_Perk_Watch(agent ThisAgent)",
        rush_begin_start,
    )
    rush_functions = gpl[rush_begin_start:rush_end]
    if rush_functions.count("#ATTRIB_MaxAttackRange") != 2:
        fail(
            f"{gpl_path}: Rush unto Death must apply and remove exactly one "
            "maximum-attack-range bonus"
        )
    if rush_functions.count(
        'ThisAgent\'s "castingrange" += #Phantom_Rush_Range_Bonus;'
    ) != 1 or rush_functions.count(
        'ThisAgent\'s "castingrange" -= #Phantom_Rush_Range_Bonus;'
    ) != 1:
        fail(
            f"{gpl_path}: Rush unto Death casting-range bonus is not paired "
            "and reversible"
        )
    forbidden_rush_visuals = (
        "$TurnOnSpeedTrail",
        "$TurnOffSpeedTrail",
        "$CreateEffector",
        "winged_feet_icon",
        "winged_feet_effector",
    )
    present_rush_visuals = [
        value for value in forbidden_rush_visuals if value in rush_functions
    ]
    if present_rush_visuals:
        fail(
            f"{gpl_path}: invisible Rush unto Death clone contains visible "
            f"Winged Feet behavior {present_rush_visuals}"
        )
    forbidden_pointer_forcing = (
        'Priestess\'s "BasicScript" = $Phantom_Priestess_Tree;',
        'Priestess\'s "StartingScript" = $Phantom_Priestess_Tree;',
        'Priestess\'s "ActiveScript" = $Phantom_Priestess_Tree;',
    )
    present_forcing = [value for value in forbidden_pointer_forcing if value in gpl]
    if present_forcing:
        fail(
            f"{gpl_path}: stock-shaped Priestess experiment still contains "
            f"watcher pointer forcing {present_forcing}"
        )
    support_wrapper_start = gpl.index(
        "Function Phantom_Priestess_Follow_Check(agent ThisAgent) is boolean"
    )
    support_wrapper_end = gpl.index(
        "function Priestess_tree(agent ThisAgent)",
        support_wrapper_start,
    )
    support_wrapper = gpl[support_wrapper_start:support_wrapper_end]
    if "$ListObjects" in support_wrapper or "Potentials" in support_wrapper:
        fail(
            f"{gpl_path}: Priestess support wrapper drifted from the proven "
            "stock Follow_Support selector into custom candidate logic"
        )
    if "expression #support_max 2" in gpl:
        fail(
            f"{gpl_path}: Priestess follower cap leaks into the global stock "
            "support_max expression"
        )
    priestess_selector_start = gpl.index(
        "function Phantom_Priestess_Follow_Support_Check("
    )
    priestess_selector_end = gpl.index(
        "function Phantom_Priestess_Follow_Support(agent ThisAgent)",
        priestess_selector_start,
    )
    priestess_selector = gpl[priestess_selector_start:priestess_selector_end]
    if "Best_One = $ListMember(Potentials, 1);" in priestess_selector:
        fail(
            f"{gpl_path}: Priestess selector still chooses arbitrary list "
            "order instead of the closest eligible Phantom"
        )
    active_follow_start = gpl.index(
        "function Phantom_Priestess_Follow_Support(agent ThisAgent)"
    )
    active_follow_end = gpl.index(
        "Function Phantom_Priestess_Assigned_To(agent Phantom) is boolean",
        active_follow_start,
    )
    active_follow = gpl[active_follow_start:active_follow_end]
    if 'Target\'s "ActiveScript" == $Travel_To' in active_follow:
        fail(
            f"{gpl_path}: Priestess active follow clone still contains the "
            "disproved moving-target distance condition"
        )
    building_gate = active_follow.index('New_Target\'s "Type" == "Building"')
    active_attack_gate = active_follow.index(
        'If (Target\'s "ActiveScript" == $Attack_Object)', building_gate
    )
    join_attack = active_follow.index("If (Join_Attack)", active_attack_gate)
    if not building_gate < active_attack_gate < join_attack:
        fail(
            f"{gpl_path}: Priestess building support must wait until the "
            "followed Phantom is actively attacking"
        )
    priestess_tree = gpl.index("function Priestess_tree(agent ThisAgent)")
    build_horde = gpl.index("$Build_Horde(ThisAgent, 95) == False", priestess_tree)
    support_check = gpl.index(
        "$Phantom_Priestess_Follow_Check(ThisAgent) == False",
        build_horde,
    )
    nearby_check = gpl.index("$Check_Nearby(ThisAgent) == False", support_check)
    if not priestess_tree < build_horde < support_check < nearby_check:
        fail(
            f"{gpl_path}: stock Priestess_tree must call Phantom support "
            "immediately after skeleton upkeep and before nearby decisions"
        )
    if gpl.count(
        "If ($Phantom_Player_Max_Completed_Haunt_Level(thisagent) < 2)"
    ) < 2:
        fail(f"{gpl_path}: Icy Touch is not gated in both check and cast paths")
    if gpl.count(
        "If ($Phantom_Player_Max_Completed_Haunt_Level(thisagent) < 3)"
    ) < 2:
        fail(
            f"{gpl_path}: Endless Winter is not gated in both check and cast paths"
        )


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
        "function Phantom_Hero_Death(agent thisagent)",
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
        'If ($HasAttribute("PhantomFrostArmorWatch", ThisAgent))',
        'If ($IsRunning(ThisAgent\'s "PhantomFrostArmorWatch"))',
        '$KillThread(ThisAgent\'s "PhantomFrostArmorWatch");',
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
    watcher_stop = gpl.index(
        '$KillThread(ThisAgent\'s "PhantomFrostArmorWatch");', phantom_guard
    )
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
        "$Phantom_Apply_Chill_Tier(target, duration, desired_tier);",
        "function Phantom_Apply_Chill_Tier(agent target, integer duration, integer desired_tier)",
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
    init_end = helper_gpl.index(
        'If ($HasAttribute("PhantomChillIconDelay", target) == False)',
        init_guard,
    )
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
    icy_end = gpl.index(
        "function Endless_Winter_Hit(agent thisagent, agent target)",
        icy_start,
    )
    icy_gpl = gpl[icy_start:icy_end]
    baseline_contract = (
        "function Icy_Touch_Check(agent thisagent) is integer",
        'target = thisagent\'s "Target";',
        "If ($NotValid(target))",
        "If ($IsDead(target))",
        'If (target\'s "Type" == "Building" || target\'s "Type" == "Lair")',
        "distance = $DistanceBetweenAgents(thisagent, target);",
        "target_range = #Phantom_Icy_Touch_Range;",
        'If (target\'s "attacktype" == 1)',
        "$GetAttribute(target, #ATTRIB_MaxAttackRange)",
        "distance <= target_range ||",
        "$IsAdjacent(thisagent, target)",
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
    if "Daemonwood" in icy_gpl:
        fail(
            f"{gpl_path}: Icy Touch contact handling must use stock melee "
            "classification without target-specific reach rules"
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
        "$Raid_lair(thisagent,80)",
        "$raid_enemy_building(thisagent,65)",
        "$Combat_wandering(thisagent,90)",
        "$combat_wandering_heroes(thisagent,75)",
        "$Explore_Map(thisagent,75)",
        "$Go_Home(thisagent,30)",
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
        'hostile\'s "Type" == "Hero" || hostile\'s "Type" == "Monster"',
        'If (hostile\'s "castingrange" > attack_range)',
        'attack_range = hostile\'s "castingrange";',
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
    weapon_range = gpl.index(
        "attack_range = $GetAttribute(hostile, #ATTRIB_MaxAttackRange);",
        incoming_filter,
    )
    casting_range = gpl.index(
        'If (hostile\'s "castingrange" > attack_range)', weapon_range
    )
    effective_range = gpl.index(
        'attack_range = hostile\'s "castingrange";', casting_range
    )
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
        < weapon_range
        < casting_range
        < effective_range
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
    death = gpl.index("function Phantom_Hero_Death(agent thisagent)")
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
    watcher_end = gpl.index(
        "\nfunction Phantom_Frost_Armor_Recharge_Check", watcher
    )
    if "$Phantom_Sync_Speed_Profile" in gpl[watcher:watcher_end]:
        fail(
            f"{gpl_path}: Frost Armor watcher still polls the Phantom speed profile"
        )
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
        '<Experience value="1600"/>',
        '<NameGenType value="NM11"/>',
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
    confidence_end = gpl.index("\nFunction Potion_Check", confidence_start)
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
        check = f'$isspellavailable(thisagent,"{spell}",1)'
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
        fail(f"{actions_path}: Phantom storm action is not named Endless Winter")
    action_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRa5" '
        'Name="endless_winter"'
    )
    action_end = actions.index("</Description>", action_start)
    action = actions[action_start:action_end]
    action_contract = (
        '<ImageSet value="Cast"/>',
        '<CompletionImageSet value="Stand"/>',
        '<Sound value="Meteor_Storm"/>',
        '<SoundPhase begin="Begin"/>',
        'GPLFunction="Endless_Winter_Hit"',
        '<EffectorDuration value="21000"/>',
        '<TimeoutDuration value="55000"/>',
        '<SpellType value="Attack"/>',
        '<CharacterLevel value="7"/>',
        '<SpellRank value="7"/>',
        '<ValidationScript value="Endless_Winter_Check"/>',
    )
    missing_action_fields = [
        value for value in action_contract if value not in action
    ]
    if missing_action_fields:
        fail(
            f"{actions_path}: Endless Winter action is missing "
            f"{missing_action_fields}"
        )
    forbidden_action_fields = (
        '<ValidationScript value="Blizzard_Check"/>',
        'GPLFunction="Blizzard_Hit"',
    )
    present_forbidden_action = [
        value for value in forbidden_action_fields if value in action
    ]
    if present_forbidden_action:
        fail(
            f"{actions_path}: Endless Winter leaks stock Wizard behavior "
            f"{present_forbidden_action}"
        )

    units_path = output_root / "Data" / "phantom_units.xml"
    units = units_path.read_text(encoding="utf-8")
    if '<Spell ID="5" Value="endless_winter"/>' not in units:
        fail(
            f"{units_path}: Phantom does not list its level-7 Endless Winter "
            "spell"
        )
    unit_contract = (
        'ID="PHW1" Name="endless_winter_storm"',
        '<ImageIDBase value="PHw6"/>',
        'GPLFunction="Endless_Winter_Unit_Created"',
        '<Attachment kind="Movement" type="Walk" ID="Class 1"/>',
    )
    missing_unit_fields = [
        value for value in unit_contract if value not in units
    ]
    if missing_unit_fields:
        fail(
            f"{units_path}: Phantom-only stock storm visual unit is missing "
            f"{missing_unit_fields}"
        )
    if '<Spell ID="5" Value="meteor_storm"/>' in units or 'ID="WVg1"' in units:
        fail(f"{units_path}: mod attempts to replace the global Wizard storm unit")

    projectiles_path = output_root / "Data" / "phantom_projectiles.xml"
    projectiles = projectiles_path.read_text(encoding="utf-8")
    projectile_contract = (
        'ID="PHW2" Name="endless_winter_missile"',
        'GPLFunction="Endless_Winter_Inner_Missile_Hit"',
        'ID="PHW7" Name="endless_winter_missile_middle"',
        'GPLFunction="Endless_Winter_Middle_Missile_Hit"',
        'ID="PHW8" Name="endless_winter_missile_outer"',
        'GPLFunction="Endless_Winter_Outer_Missile_Hit"',
    )
    missing_projectile_fields = [
        value for value in projectile_contract if value not in projectiles
    ]
    if missing_projectile_fields:
        fail(
            f"{projectiles_path}: Phantom-only stock-speed visual projectile "
            f"is missing {missing_projectile_fields}"
        )
    if (
        projectiles.count('<ImageIDBase value="PHw3"/>') != 3
        or projectiles.count(
            '<Attachment kind="Movement" type="Walk" ID="fast missile"/>'
        )
        != 3
    ):
        fail(
            f"{projectiles_path}: all three radial-tier projectiles must reuse "
            "the same Endless Winter art and stock fast-missile movement"
        )
    if 'ID="WPg3"' in projectiles or 'Name="meteor_storm_missile"' in projectiles:
        fail(f"{projectiles_path}: mod attempts to replace the stock Wizard missile")

    particles_path = output_root / "Data" / "phantom_particles.xml"
    particles = particles_path.read_text(encoding="utf-8")
    particle_contract = (
        'ID="PHW4" Name="endless_winter_storm_attachment"',
        '<ImageIDBase value="PHw4"/>',
        '<Rate value="8.0"/>',
        'ID="PHW5" Name="endless_winter_missile_attachment"',
        '<ImageIDBase value="PHw5"/>',
        '<Rate value="18.0"/>',
    )
    missing_particle_fields = [
        value for value in particle_contract if value not in particles
    ]
    if missing_particle_fields:
        fail(
            f"{particles_path}: Phantom-only snowflake particle systems are "
            f"missing {missing_particle_fields}"
        )
    if 'ID="XL20"' in particles or 'ID="XL21"' in particles:
        fail(
            f"{particles_path}: mod attempts to replace stock Wizard meteor "
            "particle systems"
        )

    overlays_path = output_root / "Data" / "phantom_overlays.xml"
    overlays = overlays_path.read_text(encoding="utf-8")
    overlay_contract = (
        'ID="PHW3" Name="endless_winter_hit_effector"',
        '<ImageIDBase value="PHw2"/>',
        '<AttachmentPointID value="2"/>',
        'ID="PHW6" Name="endless_winter_vortex_effector"',
        '<ImageIDBase value="PHw1"/>',
    )
    missing_overlay_fields = [
        value for value in overlay_contract if value not in overlays
    ]
    if missing_overlay_fields:
        fail(
            f"{overlays_path}: Phantom-only hit overlay is missing "
            f"{missing_overlay_fields}"
        )
    if 'ID="WRg2"' in overlays or 'Name="meteor_storm_effector2"' in overlays:
        fail(f"{overlays_path}: mod attempts to replace the stock Wizard impact")

    wizard_action_start = actions.index(
        '<Description type="Action" subType="Standard" ID="WRg1" '
        'Name="meteor_storm"'
    )
    wizard_action_end = actions.index("</Description>", wizard_action_start)
    wizard_action = actions[wizard_action_start:wizard_action_end]
    wizard_action_contract = (
        '<ImageSet value="Cast"/>',
        '<CompletionImageSet value="Stand"/>',
        '<Sound value="Meteor_Storm"/>',
        '<SoundPhase begin="Begin"/>',
        'GPLFunction="meteor_storm_hit"',
        '<EffectorDuration value="21000"/>',
        '<TimeoutDuration value="55000"/>',
        '<SpellType value="Attack"/>',
        '<CharacterLevel value="7"/>',
        '<SpellRank value="7"/>',
        '<ValidationScript value="meteor_storm_check"/>',
    )
    missing_wizard_action_fields = [
        value for value in wizard_action_contract if value not in wizard_action
    ]
    if missing_wizard_action_fields:
        fail(
            f"{actions_path}: sound-enabled stock Wizard Meteor Storm action "
            f"is missing {missing_wizard_action_fields}"
        )

    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    hero_data = hero_data_path.read_text(encoding="utf-8")
    spell_data_contract = (
        "[endless_winter_storm]",
        "(type\t\tspell)",
        "(subtype\tspell)",
        "(activeScript\tEndless_Winter_Active)",
    )
    missing_spell_data = [
        value for value in spell_data_contract if value not in hero_data
    ]
    if missing_spell_data:
        fail(
            f"{hero_data_path}: custom visual storm lacks its explicit stock-style "
            f"active-script mapping {missing_spell_data}"
        )

    birth_start = gpl.index("function Phantom_Hero_Birth (agent thisagent)")
    birth_end = gpl.index(
        "\nfunction Phantom_has_cowl_item",
        birth_start,
    )
    birth = gpl[birth_start:birth_end]
    if '$LearnSpell(thisagent, "endless_winter");' in birth:
        fail(
            f"{gpl_path}: Phantom birth still grants the temporary level-1 "
            "Endless Winter test spell"
        )
    recruitment_voice_contract = (
        'Home = thisagent\'s "home";',
        "$isvalidgamepiece(Home)",
        'Home\'s "title" == "Phantoms_Haunt"',
        '$HasAttribute("PhantomRecruitmentVoice", thisagent) == False',
        '"PhantomRecruitmentVoice",',
        "$Phantom_Recruitment_Voice",
        "$RandomNumber(100) + 1 <= 20",
        'thisagent\'s "PhantomRecruitmentVoice",',
        "250,",
        "function Phantom_Recruitment_Voice(agent thisagent)",
        '$PlaySound(thisagent, "Phantom_Hired", "Begin");',
    )
    missing_recruitment_voice = [
        value for value in recruitment_voice_contract if value not in birth
    ]
    if missing_recruitment_voice:
        fail(
            f"{gpl_path}: 20-percent one-shot Haunt recruitment voice contract "
            f"is missing {missing_recruitment_voice}"
        )
    if '$PlaySound(thisagent, "Phantom_Voice", "VFX_SPECIAL1");' in gpl:
        fail(f"{gpl_path}: recruitment audio must not use the stock idle phase")
    runtime_contract = (
        "function Endless_Winter_Hit(agent thisagent, agent target)",
        "function Endless_Winter_Check(agent thisagent) is integer",
        "cast_range = $Phantom_effective_casting_range(thisagent);",
        "targets = $compile_enemies(thisagent, cast_range);",
        "closest_enemy = $Pick_Closest(thisagent, targets);",
        "If ($isvalidgamepiece(target))",
        "If ($IsDead(target) == False)",
        "If ($AgentInList(target, targets))",
        "closest_distance = $DistanceBetweenAgents(thisagent, closest_enemy);",
        "target_distance = $DistanceBetweenAgents(thisagent, target);",
        "If (target_distance == closest_distance)",
        "closest_enemy = target;",
        '$CreateSpellUnit(thisagent, "endless_winter_storm", closest_enemy);',
        "function Endless_Winter_Unit_Created(agent thisagent, agent target)",
        "$SetParent(thisagent, target);",
        '$GetSpellAttribute("endless_winter", "effector_duration")',
        '"endless_winter_vortex_effector"',
        '$AddAttribute(',
        '"EndlessWinterTracking"',
        "$Endless_Winter_Track",
        '"EndlessWinterCleanup"',
        '"function"',
        "$Endless_Winter_Cleanup",
        '$RunThread(',
        'thisagent\'s "EndlessWinterCleanup"',
        "duration + 100",
        '$NewThread(thisagent\'s "EndlessWinterTracking", 25, thisagent);',
        '$NewThread(thisagent\'s "activeScript", 1600, thisagent);',
        "$Endless_Winter_Track(thisagent);",
        "$Endless_Winter_Active(thisagent);",
        "function Endless_Winter_Cleanup(agent thisagent)",
        '$KillThread(thisagent\'s "EndlessWinterTracking");',
        '$KillThread(thisagent\'s "activeScript");',
        "$DeleteGamePiece(thisagent);",
        "function Endless_Winter_Track(agent thisagent)",
        "function Endless_Winter_Active(agent thisagent)",
        "tracked_target = $Parent(thisagent);",
        "anchor_location = $LocationOf(thisagent);",
        "target_location = $LocationOf(tracked_target);",
        "$GetX(anchor_location) != $GetX(target_location)",
        "$GetY(anchor_location) != $GetY(target_location)",
        "$TeleportToUnit(thisagent, 50000, tracked_target, 0);",
        "targets = $compile_enemies(thisagent, 175);",
        "distance = $DistanceBetweenCoords(",
        "$LocationOf(thisagent),",
        "$LocationOf(target)",
        "distance <= #Phantom_Icy_Touch_Range",
        '$CreateMissile("endless_winter_missile", thisagent, target);',
        "distance <= 80",
        '$CreateMissile("endless_winter_missile_middle", thisagent, target);',
        '$CreateMissile("endless_winter_missile_outer", thisagent, target);',
        "function Endless_Winter_Inner_Missile_Hit(agent thisagent, agent target)",
        "$Endless_Winter_Missile_Hit(target, 8, 2);",
        "function Endless_Winter_Middle_Missile_Hit(agent thisagent, agent target)",
        "$Endless_Winter_Missile_Hit(target, 6, 1);",
        "function Endless_Winter_Outer_Missile_Hit(agent thisagent, agent target)",
        "$Endless_Winter_Missile_Hit(target, 4, 1);",
        "function Endless_Winter_Missile_Hit(agent target, integer damage, integer chill_tier)",
        '$CreateEffector(target, "endless_winter_hit_effector", 0);',
        "$player_spell_attack(target, damage, damage);",
        "$Phantom_Apply_Chill_Tier(",
        '$GetSpellAttribute("ice_lance", "effector_duration")',
    )
    missing_runtime = [
        value for value in runtime_contract if value not in gpl
    ]
    if missing_runtime:
        fail(
            f"{gpl_path}: Endless Winter diverges from its finalized runtime "
            f"contract {missing_runtime}"
        )
    runtime_start = gpl.index(
        "function Endless_Winter_Hit(agent thisagent, agent target)"
    )
    runtime_end = gpl.index(
        "function Blizzard_Check(agent thisagent) is integer",
        runtime_start,
    )
    runtime = gpl[runtime_start:runtime_end]
    forbidden_runtime = (
        '"EndlessWinterTarget"',
        "$Phantom_Apply_Chill(",
        "$spell_attack(",
        "$DistanceBetweenAgents(thisagent, tracked_target)",
        '$CreateSpellUnit(thisagent, "endless_winter_storm", thisagent);',
        "meteor_storm_unit_created",
        "$meteor_storm_active(",
        '"meteor_storm_missile"',
        '"meteor_storm_effector2"',
        '$NewThread(thisagent\'s "activeScript", 1600, thisagent, target);',
        "function Endless_Winter_Active(agent thisagent, agent tracked_target)",
        'thisagent\'s "Target" = target;',
    )
    present_forbidden_runtime = [
        value for value in forbidden_runtime if value in runtime
    ]
    if present_forbidden_runtime:
        fail(
            f"{gpl_path}: Phantom visual shell contains non-stock mechanics "
            f"{present_forbidden_runtime}"
        )
    selection_start = runtime.index(
        "function Endless_Winter_Hit(agent thisagent, agent target)"
    )
    closest_pick = runtime.index(
        "closest_enemy = $Pick_Closest(thisagent, targets);",
        selection_start,
    )
    current_valid = runtime.index(
        "If ($isvalidgamepiece(target))",
        closest_pick,
    )
    current_alive = runtime.index(
        "If ($IsDead(target) == False)",
        current_valid,
    )
    current_eligible = runtime.index(
        "If ($AgentInList(target, targets))",
        current_alive,
    )
    closest_distance = runtime.index(
        "closest_distance = $DistanceBetweenAgents(thisagent, closest_enemy);",
        current_eligible,
    )
    current_distance = runtime.index(
        "target_distance = $DistanceBetweenAgents(thisagent, target);",
        closest_distance,
    )
    tied_distance = runtime.index(
        "If (target_distance == closest_distance)",
        current_distance,
    )
    prefer_current = runtime.index(
        "closest_enemy = target;",
        tied_distance,
    )
    create_storm = runtime.index(
        '$CreateSpellUnit(thisagent, "endless_winter_storm", closest_enemy);',
        prefer_current,
    )
    if not (
        closest_pick
        < current_valid
        < current_alive
        < current_eligible
        < closest_distance
        < current_distance
        < tied_distance
        < prefer_current
        < create_storm
    ):
        fail(
            f"{gpl_path}: Endless Winter must retain stock closest-target "
            "selection and prefer the current live eligible combat target only "
            "when its stock distance exactly ties the closest candidate"
        )
    if (
        runtime.count("closest_enemy = target;") != 1
        or runtime.count("If (target_distance == closest_distance)") != 1
    ):
        fail(
            f"{gpl_path}: Endless Winter current-target tie preference must "
            "occur exactly once"
        )
    active_start = runtime.index(
        "function Endless_Winter_Active(agent thisagent)"
    )
    inner_tier = runtime.index(
        "distance <= #Phantom_Icy_Touch_Range"
        , active_start
    )
    inner_missile = runtime.index(
        '$CreateMissile("endless_winter_missile", thisagent, target);',
        inner_tier,
    )
    middle_tier = runtime.index(
        "distance <= 80",
        inner_missile,
    )
    middle_missile = runtime.index(
        '$CreateMissile("endless_winter_missile_middle", thisagent, target);',
        middle_tier,
    )
    outer_missile = runtime.index(
        '$CreateMissile("endless_winter_missile_outer", thisagent, target);',
        middle_missile,
    )
    inner_callback = runtime.index(
        "function Endless_Winter_Inner_Missile_Hit(agent thisagent, agent target)",
        outer_missile,
    )
    active_block = runtime[active_start:inner_callback]
    if "$DistanceBetweenAgents(" in active_block:
        fail(
            f"{gpl_path}: Endless Winter radial damage tiers must use "
            "center-to-center coordinate distance, not agent-edge distance"
        )
    inner_route = runtime.index(
        "$Endless_Winter_Missile_Hit(target, 8, 2);",
        inner_callback,
    )
    middle_callback = runtime.index(
        "function Endless_Winter_Middle_Missile_Hit(agent thisagent, agent target)",
        inner_route,
    )
    middle_route = runtime.index(
        "$Endless_Winter_Missile_Hit(target, 6, 1);",
        middle_callback,
    )
    outer_callback = runtime.index(
        "function Endless_Winter_Outer_Missile_Hit(agent thisagent, agent target)",
        middle_route,
    )
    outer_route = runtime.index(
        "$Endless_Winter_Missile_Hit(target, 4, 1);",
        outer_callback,
    )
    common_hit = runtime.index(
        "function Endless_Winter_Missile_Hit(agent target, integer damage, integer chill_tier)",
        outer_route,
    )
    damage_application = runtime.index(
        "$player_spell_attack(target, damage, damage);",
        common_hit,
    )
    chill_application = runtime.index(
        "$Phantom_Apply_Chill_Tier(",
        damage_application,
    )
    if not (
        inner_tier
        < inner_missile
        < middle_tier
        < middle_missile
        < outer_missile
        < inner_callback
        < inner_route
        < middle_callback
        < middle_route
        < outer_callback
        < outer_route
        < common_hit
        < damage_application
        < chill_application
    ):
        fail(
            f"{gpl_path}: Endless Winter must select the radial tier at the "
            "storm anchor before launch, route each identical-looking missile "
            "to its fixed damage/Chill callback, then apply Chill after damage"
        )
    if (
        runtime.count("$DistanceBetweenCoords(") != 1
        or runtime.count("$LocationOf(thisagent),") != 1
        or runtime.count("$LocationOf(target)") != 1
        or runtime.count(
            '$CreateMissile("endless_winter_missile", thisagent, target);'
        )
        != 1
        or runtime.count(
            '$CreateMissile("endless_winter_missile_middle", thisagent, target);'
        )
        != 1
        or runtime.count(
            '$CreateMissile("endless_winter_missile_outer", thisagent, target);'
        )
        != 1
        or runtime.count("$Endless_Winter_Missile_Hit(target, 8, 2);") != 1
        or runtime.count("$Endless_Winter_Missile_Hit(target, 6, 1);") != 1
        or runtime.count("$Endless_Winter_Missile_Hit(target, 4, 1);") != 1
        or runtime.count("$Phantom_Apply_Chill_Tier(") != 1
    ):
        fail(
            f"{gpl_path}: Endless Winter radial routing must be exclusive and "
            "must use one center-to-center coordinate measurement and apply "
            "exactly one fixed damage/Chill tier per impact"
        )
    schedule = runtime.index(
        '$NewThread(thisagent\'s "activeScript", 1600, thisagent);'
    )
    tracking_schedule = runtime.index(
        '$NewThread(thisagent\'s "EndlessWinterTracking", 25, thisagent);'
    )
    cleanup_schedule = runtime.index(
        'thisagent\'s "EndlessWinterCleanup"',
    )
    immediate_tracking = runtime.index(
        "$Endless_Winter_Track(thisagent);",
        tracking_schedule,
    )
    immediate_pulse = runtime.index(
        "$Endless_Winter_Active(thisagent);",
        schedule,
    )
    cleanup_start = runtime.index(
        "function Endless_Winter_Cleanup(agent thisagent)"
    )
    cleanup_tracking_kill = runtime.index(
        '$KillThread(thisagent\'s "EndlessWinterTracking");',
        cleanup_start,
    )
    cleanup_active_kill = runtime.index(
        '$KillThread(thisagent\'s "activeScript");',
        cleanup_tracking_kill,
    )
    cleanup_delete = runtime.index(
        "$DeleteGamePiece(thisagent);",
        cleanup_active_kill,
    )
    tracking_start = runtime.index(
        "function Endless_Winter_Track(agent thisagent)",
        cleanup_delete,
    )
    tracking_read = runtime.index(
        "tracked_target = $Parent(thisagent);",
        tracking_start,
    )
    anchor_location_read = runtime.index(
        "anchor_location = $LocationOf(thisagent);",
        tracking_read,
    )
    target_location_read = runtime.index(
        "target_location = $LocationOf(tracked_target);",
        anchor_location_read,
    )
    x_guard = runtime.index(
        "$GetX(anchor_location) != $GetX(target_location)",
        target_location_read,
    )
    y_guard = runtime.index(
        "$GetY(anchor_location) != $GetY(target_location)",
        x_guard,
    )
    relocation = runtime.index(
        "$TeleportToUnit(thisagent, 50000, tracked_target, 0);",
        y_guard,
    )
    active_start = runtime.index(
        "function Endless_Winter_Active(agent thisagent)",
        relocation,
    )
    pulse_scan = runtime.index(
        "targets = $compile_enemies(thisagent, 175);",
        active_start,
    )
    if not (
        cleanup_schedule
        < tracking_schedule
        < schedule
        < immediate_tracking
        < immediate_pulse
        < cleanup_start
        < cleanup_tracking_kill
        < cleanup_active_kill
        < cleanup_delete
        < tracking_start
        < tracking_read
        < anchor_location_read
        < target_location_read
        < x_guard
        < y_guard
        < relocation
        < active_start
        < pulse_scan
    ):
        fail(
            f"{gpl_path}: Endless Winter must recover its engine-managed parent "
            "target, explicitly terminate its periodic thread and host at the "
            "visual lifetime boundary, track exact world-coordinate movement "
            "independently from damage, skip Majesty's unsafe zero-distance "
            "teleport, relocate when needed, then scan the impact radius on "
            "the stock pulse cadence"
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
        "else\n\t\t\t\treturn 0;",
        "if ($distancebetweencoords(destination,$locationof(thisagent)) > #Phantom_Call_To_Grave_Min_Distance)",
        "function Call_To_Grave_Effect(agent thisagent, agent target)",
        'theTimePeriod = $GetSpellAttribute("call_to_grave","effector_duration");',
        '$createeffector(thisagent,"call_to_grave_effector",theTimePeriod);',
        'thisagent\'s "teleportScript" = $Call_To_Grave_DoMove;',
        '$RunThread(thisagent\'s "teleportScript",theTimePeriod/2,thisagent,#Phantom_Call_To_Grave_Range);',
        "function Call_To_Grave_DoMove(agent thisagent, integer theRange)",
        "If ($IsValidGamePiece(ThisAgent) == False)",
        "If ($IsDead(ThisAgent) || $GetAttribute(ThisAgent, #ATTRIB_HP) <= 0)",
        'if (thisagent\'s "Target" == thisagent)',
        '$TeleportToPoint(thisagent,theRange,thisagent\'s "destination");',
        'if ($isvalidgamepiece(thisagent\'s "target"))',
        '$TeleportToUnit(thisagent,theRange,thisagent\'s "Target",thisagent\'s "castingrange");',
        "function travel_to_safe(agent thisagent)",
        'thisagent\'s "Title" == "Phantom"',
        '$isspellavailable(thisagent,"call_to_grave",1)',
        "$Call_To_Grave_Check(thisagent) == 1",
        '$cast(thisagent,"call_to_grave",thisagent, "");',
        "$hasLowHP(thisagent) == FALSE",
        "$TryTravelSpell(thisagent);",
        "$heal_self_fleeing(thisagent);",
        '$clearlist(thisagent\'s "hostiles");',
    )
    missing_gpl = [value for value in gpl_contract if value not in gpl]
    if missing_gpl:
        fail(f"{gpl_path}: Call to Grave GPL is missing {missing_gpl}")
    flee_start = gpl.index(
        "function flee_part_II(agent thisagent, list places, integer intent)"
    )
    flee_end = gpl.index("\nfunction Phantom_tree", flee_start)
    watcher_start = gpl.index("function Phantom_Frost_Armor_Watch(agent thisagent)")
    watcher_end = gpl.index(
        "\nfunction Phantom_Frost_Armor_Recharge_Check", watcher_start
    )
    if "call_to_grave" in gpl[flee_start:flee_end]:
        fail(f"{gpl_path}: flee_part_II bypasses the stock travel-spell path")
    if "call_to_grave" in gpl[watcher_start:watcher_end]:
        fail(f"{gpl_path}: behavior watcher bypasses the stock travel-spell path")
    check_start = gpl.index("function Call_To_Grave_Check(agent thisagent) is integer")
    check_end = gpl.index("\nfunction Call_To_Grave_Effect", check_start)
    check_function = gpl[check_start:check_end]
    if 'thisagent\'s "taskname" = "go_home";' in check_function:
        fail(f"{gpl_path}: Call to Grave validation mutates the stock home task")
    travel_start = gpl.index("function travel_to_safe(agent thisagent)")
    travel_end = gpl.index("\nfunction Call_To_Grave_Check", travel_start)
    travel_function = gpl[travel_start:travel_end]
    travel_order = (
        'thisagent\'s "Title" == "Phantom"',
        '$isspellavailable(thisagent,"call_to_grave",1)',
        "$Call_To_Grave_Check(thisagent) == 1",
        '$cast(thisagent,"call_to_grave",thisagent, "");',
        "$hasLowHP(thisagent) == FALSE",
        "$TryTravelSpell(thisagent);",
        "$heal_self_fleeing(thisagent);",
        '$clearlist(thisagent\'s "hostiles");',
    )
    travel_positions = [travel_function.index(value) for value in travel_order]
    if travel_positions != sorted(travel_positions):
        fail(
            f"{gpl_path}: Phantom Call to Grave must precede the unchanged "
            "stock low-HP and generic travel-spell branches"
        )
    self_target = check_function.index('thisagent\'s "Target" == thisagent')
    saved_destination = check_function.index(
        'destination = thisagent\'s "destination";', self_target
    )
    home_target = check_function.index(
        'thisagent\'s "target" != thisagent\'s "home"', saved_destination
    )
    if not self_target < saved_destination < home_target:
        fail(
            f"{gpl_path}: Call to Grave rejects stock self-target travel state "
            "before reading its saved destination"
        )
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
    if "call_to_grave" in flee_function:
        fail(
            f"{gpl_path}: Phantom flee-home override must leave Call to Grave "
            "to stock TryTravelSpell handling"
        )
    forbidden = (
        "function flee(agent thisagent",
        "function flee_absolute(agent thisagent",
        "function wizard_eval_nearby(agent thisagent",
        "function use_building_safe(agent thisagent",
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
    phantom_tree_start = gpl.index("function Phantom_tree (agent thisagent)")
    phantom_tree_end = gpl.index("\nfunction Phantom_Hero_Birth", phantom_tree_start)
    phantom_tree = gpl[phantom_tree_start:phantom_tree_end]
    if "$Wizard_tree(thisagent);" in phantom_tree:
        fail(f"{gpl_path}: Phantom still delegates decisions to the stock Wizard tree")
    speed_sync = phantom_tree.index("$Phantom_Sync_Speed_Profile(thisagent);")
    first_decision = phantom_tree.index("$Phantom_Try_Frost_Armor(thisagent)")
    if speed_sync > first_decision:
        fail(
            f"{gpl_path}: Phantom speed profile must synchronize before its "
            "normal decision chain"
        )


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
        "Healing = 5;",
        "If ($Phantom_Player_Max_Completed_Haunt_Level(ThisAgent) >= 2)",
        "Healing = 10;",
        "$Heal(ThisAgent, Best_Phantom, Healing);",
        'My_Skeletons = $ListTitles(My_Skeletons, "Skeleton");',
        "If ($IsValidGamePiece(Best_Skeleton))",
        "$Heal(ThisAgent, Best_Skeleton, Healing);",
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
    self_heal = gpl.index(
        "$Heal(ThisAgent, ThisAgent, Healing);",
        self_heal_check,
    )
    phantom_list = gpl.index('Phantoms = $ListTitles(Phantoms, "Phantom");', self_heal)
    phantom_target = gpl.index("Best_Phantom = Phantom;", phantom_list)
    phantom_heal = gpl.index(
        "$Heal(ThisAgent, Best_Phantom, Healing);",
        phantom_target,
    )
    skeleton_list = gpl.index(
        'My_Skeletons = $ListTitles(My_Skeletons, "Skeleton");', phantom_heal
    )
    skeleton_target = gpl.index("Best_Skeleton = Skeleton;", skeleton_list)
    skeleton_heal = gpl.index(
        "$Heal(ThisAgent, Best_Skeleton, Healing);",
        skeleton_target,
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


def validate_paladin_recruitment_restriction(output_root: Path) -> None:
    building_data_path = output_root / "GPL" / "Phantom_Building_Data.dat"
    building_data = building_data_path.read_text(encoding="utf-8")
    building_contract = (
        "(birthscript Phantoms_Haunt_Construction_Birth)",
        "(birthScript2 Phantoms_Haunt_Birth)",
        "(IGdeathscript Phantoms_Haunt_Destroyed)",
    )
    missing_building_contract = [
        value for value in building_contract if value not in building_data
    ]
    if missing_building_contract:
        fail(
            f"{building_data_path}: Paladin availability lifecycle is missing "
            f"{missing_building_contract}"
        )
    stale_lifecycle = (
        "(birthscript basic_birth)",
        "(birthScript2 Guild_Birth)",
        "(IGdeathscript guild_destroyed_a)",
    )
    present_stale = [value for value in stale_lifecycle if value in building_data]
    if present_stale:
        fail(
            f"{building_data_path}: Phantoms Haunt still bypasses its Paladin "
            f"availability wrappers {present_stale}"
        )

    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    required_functions = (
        "Function Phantom_Player_Has_Placed_Haunt(agent ThisAgent) is boolean",
        "Function Phantoms_Haunt_Construction_Birth(agent ThisAgent)",
        "Function Phantoms_Haunt_Birth(agent ThisAgent)",
        "Function Phantoms_Haunt_Destroyed(agent ThisAgent)",
        "Function Random_Warriors_Guild_Hero_Type(agent ThisAgent) is string",
        "Function Random_Hero_Type(agent ThisAgent) is string",
    )
    missing_functions = [value for value in required_functions if value not in gpl]
    if missing_functions:
        fail(
            f"{gpl_path}: Paladin recruitment restriction is missing "
            f"{missing_functions}"
        )
    duplicated_functions = [
        value for value in required_functions if gpl.count(value) != 1
    ]
    if duplicated_functions:
        fail(
            f"{gpl_path}: Paladin restriction functions must each appear once "
            f"{duplicated_functions}"
        )
    if "Function Embassy_Spawn" in gpl:
        fail(
            f"{gpl_path}: Embassy_Spawn must remain stock; restrict only its "
            "random hero selectors"
        )

    predicate_start = gpl.index(required_functions[0])
    predicate_end = gpl.index(required_functions[1], predicate_start)
    predicate = gpl[predicate_start:predicate_end]
    predicate_contract = (
        '#CheckTitles,\n\t\t"Phantoms_Haunt"',
        "return ($ListSize(Haunts) > 0);",
    )
    missing_predicate = [
        value for value in predicate_contract if value not in predicate
    ]
    if missing_predicate:
        fail(
            f"{gpl_path}: placed same-player Haunt predicate is malformed "
            f"{missing_predicate}"
        )
    if "#ATTRIB_FirstStageBuilt" in predicate:
        fail(
            f"{gpl_path}: placed-Haunt restriction must include unfinished "
            "foundations"
        )

    construction_start = gpl.index(required_functions[1])
    construction_end = gpl.index(required_functions[2], construction_start)
    construction = gpl[construction_start:construction_end]
    construction_contract = (
        "$basic_birth(ThisAgent);",
        '"Hero",',
        '"Paladin"',
        '$DisableUnitType("Paladin");',
        "If ($ListSize(Haunts) == 0)",
        "If ($ListSize(Paladins) > 0)",
        "#Phantom_Paladin_Warning_Message",
        "$MessageFlag(",
        '"Advisor_Message_Arrive"',
        "$LocalChatMessage(",
    )
    missing_construction = [
        value for value in construction_contract if value not in construction
    ]
    if missing_construction:
        fail(
            f"{gpl_path}: Haunt foundation restriction/warning is malformed "
            f"{missing_construction}"
        )
    if not (
        construction.index("$basic_birth(ThisAgent);")
        < construction.index("$ListObjects(")
        < construction.rindex("$ListObjects(")
        < construction.index('$DisableUnitType("Paladin");')
        < construction.index("$MessageFlag(")
        < construction.rindex("$LocalChatMessage(")
    ):
        fail(
            f"{gpl_path}: Haunt construction must preserve basic_birth before "
            "enumerating Haunts and Paladins, disabling recruitment, and warning "
            "the player"
        )
    if construction.count("$ListObjects(") != 2:
        fail(
            f"{gpl_path}: Haunt construction must enumerate exactly the existing "
            "Haunts and living Paladins before deciding whether to warn"
        )

    birth_start = gpl.index(required_functions[2])
    birth_end = gpl.index(required_functions[3], birth_start)
    birth = gpl[birth_start:birth_end]
    birth_contract = (
        "$Guild_Birth(ThisAgent);",
        '"Hero",',
        '"Paladin"',
        "Foreach Paladin in Paladins do",
        "If ($IsDead(Paladin) == False)",
        "$Unit_Dismissed(Paladin);",
    )
    missing_birth = [value for value in birth_contract if value not in birth]
    if missing_birth:
        fail(
            f"{gpl_path}: completed Haunt Paladin dismissal is malformed "
            f"{missing_birth}"
        )
    if not (
        birth.index("$Guild_Birth(ThisAgent);")
        < birth.index("$ListObjects(")
        < birth.index("Foreach Paladin in Paladins do")
        < birth.index("$Unit_Dismissed(Paladin);")
    ):
        fail(
            f"{gpl_path}: completion must preserve Guild_Birth before "
            "irreversibly dismissing living Paladins"
        )

    death_start = gpl.index(required_functions[3])
    death_end = gpl.index(required_functions[4], death_start)
    death = gpl[death_start:death_end]
    death_contract = (
        'If ($ListSize(Haunts) == 0)',
        '$EnableUnitType("Paladin");',
        "$guild_destroyed_common(ThisAgent, $Homeless);",
    )
    missing_death = [value for value in death_contract if value not in death]
    if missing_death:
        fail(
            f"{gpl_path}: last-placed-Haunt destruction contract is "
            f"malformed {missing_death}"
        )
    if "#ATTRIB_FirstStageBuilt" in death:
        fail(
            f"{gpl_path}: foundation destruction must restore Paladins when "
            "the final placed Haunt is removed"
        )
    if not (
        death.index("$ListObjects(")
        < death.index('$EnableUnitType("Paladin");')
        < death.index("$guild_destroyed_common(ThisAgent, $Homeless);")
    ):
        fail(
            f"{gpl_path}: Haunt destruction must re-enable Paladins before "
            "running the stock guild destruction flow"
        )

    warriors_start = gpl.index(required_functions[4])
    warriors_end = gpl.index(required_functions[5], warriors_start)
    warriors = gpl[warriors_start:warriors_end]
    warriors_filtered_end = warriors.index("Random = $RandomNumber(3) + 1;")
    warriors_filtered = warriors[:warriors_filtered_end]
    if (
        "Random = $RandomNumber(2) + 1;" not in warriors_filtered
        or '"Paladin"' in warriors_filtered
        or 'return "Paladin";' not in warriors[warriors_filtered_end:]
    ):
        fail(
            f"{gpl_path}: Warriors Guild Embassy selection must omit Paladins "
            "only while a placed Haunt exists"
        )

    random_start = gpl.index(required_functions[5])
    random_end = gpl.index("function spell_extra_value", random_start)
    random_hero = gpl[random_start:random_end]
    random_filtered_end = random_hero.index("Random = $RandomNumber(17) + 1;")
    random_filtered = random_hero[:random_filtered_end]
    random_stock = random_hero[random_filtered_end:]
    random_guard = (
        'ThisAgent\'s "Title" == "Embassy" || '
        'ThisAgent\'s "Subtype" == "Outpost"'
    )
    if (
        random_guard not in random_filtered
        or "Random = $RandomNumber(16) + 1;" not in random_filtered
        or '"Paladin"' in random_filtered
        or 'return "Phantom";' not in random_filtered
        or 'return "Paladin";' not in random_stock
        or 'return "Phantom";' not in random_stock
    ):
        fail(
            f"{gpl_path}: Embassy/Outpost random hero selection must include "
            "Phantoms, omit Paladins while a Haunt exists, and preserve "
            "Paladins in the stock-compatible fallback"
        )


def validate_quest_compatibility(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    hero_data_path = output_root / "GPL" / "Phantom_Hero_Data.dat"
    gpl = gpl_path.read_text(encoding="utf-8")
    hero_data = hero_data_path.read_text(encoding="utf-8")

    if (
        "(birthScript\tPhantom_Hero_Birth)" not in hero_data
        or "(IGdeathscript\tPhantom_Hero_Death)" not in hero_data
        or "function Phantom_Hero_Birth (agent thisagent)" not in gpl
        or "function Phantom_Hero_Death(agent thisagent)" not in gpl
        or "function Phantom_birth" in gpl
        or "function Phantom_death" in gpl
    ):
        fail(
            f"{gpl_path}: Phantom hero birth/death functions must use "
            "quest-safe names that do not collide with Balance of Twilight"
        )

    disabled_quests = (
        "DARK_FOREST",
        "DAY_OF_RECKONING",
        "SLAY_DRAGON",
        "FORSAKEN_LANDS",
        "SAVE_PRINCE",
        "WIZARDS_CURSE",
        "VIGIL",
        "VAMPIRIC_REVENGE",
    )
    for function_name in disabled_quests:
        marker = f"function {function_name}"
        start = gpl.find(marker)
        if start < 0:
            fail(f"{gpl_path}: missing quest override {function_name}")
        next_lower = gpl.find("\nfunction ", start + len(marker))
        next_upper = gpl.find("\nFunction ", start + len(marker))
        candidates = [value for value in (next_lower, next_upper) if value >= 0]
        end = min(candidates) if candidates else len(gpl)
        quest_override = gpl[start:end]
        if function_name == "DARK_FOREST":
            expected_pair = (
                '$disableunittype("Gnome_hovel");\n'
                '\t$DisableUnitType("Phantoms_Haunt");'
            )
            if expected_pair not in quest_override:
                fail(
                    f"{gpl_path}: Dark Forest must place the Haunt directly "
                    "in the stock unit-type lock list"
                )
            if "$Phantom_Lock_Haunt_For_Quest();" in quest_override:
                fail(
                    f"{gpl_path}: Dark Forest must not route its stock-shaped "
                    "unit-type lock through the shared helper"
                )
        elif "$Phantom_Lock_Haunt_For_Quest();" not in quest_override:
            fail(
                f"{gpl_path}: {function_name} must apply the quest's native "
                "unit-type restriction through the shared Haunt helper"
            )

    temple_available_quests = (
        "BARREN_WASTE",
        "BELL_BOOK_CANDLE",
        "LICHE_QUEEN",
        "SCIONS_CHAOS",
        "SIEGE",
    )
    present_overrides = [
        function_name
        for function_name in temple_available_quests
        if re.search(rf"(?im)^function\s+{function_name}\s*\(", gpl)
    ]
    if present_overrides:
        fail(
            f"{gpl_path}: Haunt has quest overrides where its temple "
            f"classification remains available {present_overrides}"
        )
    lock_start = gpl.index("Function Phantom_Lock_Haunt_For_Quest()")
    lock_end = gpl.index("Function Phantom_Player_Has_Placed_Haunt", lock_start)
    if '$DisableUnitType("Phantoms_Haunt");' not in gpl[lock_start:lock_end]:
        fail(f"{gpl_path}: quest lock helper must use stock DisableUnitType")

    slay_start = gpl.find("function SLAY_DRAGON")
    slay_end = gpl.find("\nfunction ", slay_start + 1)
    slay = gpl[slay_start:slay_end]
    if (
        '$SpawnUnit(Palace, "Phantoms_Haunt"' not in slay
        or "#Monster_Player" not in slay
        or slay.index('$SpawnUnit(Palace, "Phantoms_Haunt"')
        > slay.index("$SetUp_Rescue_Buildings (Palace);")
    ):
        fail(
            f"{gpl_path}: Slay the Mighty Dragon must seed a foreign Haunt "
            "before stock rescue-building setup runs"
        )

    dark_victory_start = gpl.find("function dark_forest_victory")
    dark_victory_end = gpl.find("\nfunction ", dark_victory_start + 1)
    dark_victory = gpl[dark_victory_start:dark_victory_end]
    expected_dark_unlock = (
        '$enableunittype("Gnome_hovel");\n'
        '\t\t\t\t\t$EnableUnitType("Phantoms_Haunt");'
    )
    if dark_victory_start < 0 or expected_dark_unlock not in dark_victory:
        fail(
            f"{gpl_path}: Dark Forest must place the Haunt directly in the "
            "stock guild and temple unlock list"
        )
    if "$Phantom_Unlock_Haunt_For_Quest();" in dark_victory:
        fail(
            f"{gpl_path}: Dark Forest must not route its stock-shaped "
            "unit-type unlock through the shared helper"
        )

    siege_start = gpl.find("function SIEGE")
    if siege_start >= 0:
        siege_end = gpl.find("\nfunction ", siege_start + 1)
        if '$DisableUnitType("Phantoms_Haunt");' in gpl[siege_start:siege_end]:
            fail(f"{gpl_path}: The Siege must leave Haunts available")


def validate_release_playtest_contract(output_root: Path) -> None:
    gpl_path = output_root / "GPL" / "Phantom.gpl"
    gpl = gpl_path.read_text(encoding="utf-8")
    forbidden_test_scaffolding = (
        "function DEAL_DEMON()",
        "function RISE_RATMEN()",
        'phantoms_haunt = $SpawnUnit(palace, "Phantoms_Haunt"',
        'dauros_temple = $SpawnUnit(palace, "Temple_Dauros1"',
        'fervus_temple = $SpawnUnit(palace, "Temple_Fervus1"',
        'krypta_temple = $SpawnUnit(palace, "Temple_Krypta1"',
        'warriors_guild = $SpawnUnit(palace, "Warriors_Guild"',
        'embassy = $SpawnUnit(palace, "Embassy"',
    )
    present_test_scaffolding = [
        value for value in forbidden_test_scaffolding if value in gpl
    ]
    if present_test_scaffolding:
        fail(
            f"{gpl_path}: release playtest package retains forced quest "
            f"test structures {present_test_scaffolding}"
        )

    forbidden_dynamic_toggles = (
        "Function Phantom_Palace_Haunt_Availability_Watch",
        "Function Palace_Birth(agent ThisAgent)",
        "Function Palace_upgrade2(agent ThisAgent)",
    )
    present_toggles = [value for value in forbidden_dynamic_toggles if value in gpl]
    if present_toggles:
        fail(
            f"{gpl_path}: release GPL must preserve the stock Palace lifecycle; "
            f"found {present_toggles}"
        )

    construction_start = gpl.index(
        "Function Phantoms_Haunt_Construction_Birth(agent ThisAgent)"
    )
    construction_end = gpl.index("\nFunction ", construction_start + 1)
    construction = gpl[construction_start:construction_end]
    if "$basic_birth(ThisAgent);" not in construction:
        fail(f"{gpl_path}: Haunt construction must retain stock basic_birth")
    forbidden_construction_gate = (
        'Palace = $GetPalace(ThisAgent);',
        'Palace\'s "Level" < 2',
        "PhantomHauntQuestDisabled",
        "#Phantom_Palace_Level_Message",
        "#Phantom_Quest_Locked_Message",
        "#Phantom_Haunt_Base_Cost",
        "$Clean_Palace_Construction_Lists(ThisAgent);",
        "$DeleteGamePiece(ThisAgent);",
    )
    present_construction_gate = [
        value for value in forbidden_construction_gate if value in construction
    ]
    if present_construction_gate:
        fail(
            f"{gpl_path}: construction contains obsolete Palace-gating hacks "
            f"{present_construction_gate}"
        )


def validate_building_dependencies_against_stock(
    path: Path,
    building_dependencies: bytes,
    stock_data: bytes,
) -> None:
    try:
        expected = builder.append_haunt_building_dependency(stock_data)
    except ValueError as exc:
        fail(f"{path}: cannot establish the expected stock BDEP prefix: {exc}")
    if building_dependencies != expected:
        mismatch = next(
            (
                index
                for index, (actual, wanted) in enumerate(
                    zip(building_dependencies, expected)
                )
                if actual != wanted
            ),
            min(len(building_dependencies), len(expected)),
        )
        fail(
            f"{path}: DATA/BDEP differs from the complete stock table plus the "
            f"single Haunt dependency at byte {mismatch} "
            f"(built={len(building_dependencies)} bytes, expected={len(expected)} bytes)"
        )


def validate(output_root: Path, game_path: Path) -> None:
    if not output_root.is_dir():
        fail(f"{output_root}: build output directory does not exist")
    validate_manifest(output_root)
    validate_descriptions(output_root)
    validate_bcd_copy(output_root)
    validate_phantoms_haunt_identity(output_root)
    validate_phantoms_haunt_upgrade_contract(output_root)
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
    validate_paladin_recruitment_restriction(output_root)
    validate_quest_compatibility(output_root)
    validate_release_playtest_contract(output_root)

    archive_results: dict[str, tuple[dict[bytes, list[Entry]], dict[tuple[bytes, bytes], bytes]]] = {}
    for filename in EXPECTED_CAM_ENTRIES:
        path = output_root / "Data" / filename
        if not path.is_file():
            fail(f"{path}: required archive is missing")
        result = validate_archive(path)
        validate_expected_entries(path, result[0])
        validate_no_redistributed_stock_art(path, result[0])
        archive_results[filename] = result

    gpltext_path = output_root / "Data" / "phantom_gpltext.cam"
    qitm = archive_results["phantom_gpltext.cam"][1].get((b"STRT", b"QITM"))
    if qitm is None:
        fail(f"{gpltext_path}: STRT/QITM was not found")
    validate_indexed_item_strings(gpltext_path, qitm)
    name_givens = archive_results["phantom_gpltext.cam"][1].get(
        (b"STRT", b"HN41")
    )
    name_endings = archive_results["phantom_gpltext.cam"][1].get(
        (b"STRT", b"HN42")
    )
    if name_givens is None or name_endings is None:
        fail(f"{gpltext_path}: shared Priestess/Phantom name tables were not found")
    validate_shared_priestess_phantom_names(
        gpltext_path,
        name_givens,
        name_endings,
    )
    advisor_text = archive_results["phantom_gpltext.cam"][1].get(
        (b"STRT", b"AITX")
    )
    if advisor_text is None:
        fail(f"{gpltext_path}: STRT/AITX was not found")
    advisor_count = struct.unpack_from("<H", advisor_text, 0)[0]
    if advisor_count <= 177:
        fail(
            f"{gpltext_path}: STRT/AITX has {advisor_count} strings; "
            "the Paladin construction warning requires slot 177"
        )
    warning_offset = struct.unpack_from("<I", advisor_text, 4 + 177 * 4)[0]
    warning_id = struct.unpack_from("<I", advisor_text, warning_offset)[0]
    warning_end = advisor_text.index(b"\x00", warning_offset + 4)
    warning_text = advisor_text[warning_offset + 4 : warning_end]
    if warning_id != 177 or b"\x01" in warning_text or (
        b"Completing this Phantoms Haunt will cause all Paladins to leave Ardania"
        not in warning_text
    ):
        fail(
            f"{gpltext_path}: STRT/AITX slot 177 is not the known-good "
            "plain-text Paladin construction warning"
        )
    miscdata_path = output_root / "Data" / "phantom_miscdata.cam"
    building_dependencies = archive_results["phantom_miscdata.cam"][1].get(
        (b"DATA", b"BDEP")
    )
    if building_dependencies is None:
        fail(f"{miscdata_path}: DATA/BDEP was not found")
    haunt_rule = b"PHG1 : ABJ2 ABJ3 NOT NOT ||"
    if building_dependencies.count(haunt_rule) != 1:
        fail(
            f"{miscdata_path}: BDEP must contain exactly one native level-2 "
            "Palace dependency for PHG1"
        )
    required_stock_rules = (
        b"ABP1 : ABJ2 ABJ3 NOT NOT ||",
        b"ABQ1 : ABJ2 ABJ3 NOT NOT ||",
        b"ABY1 : ABJ2 ABJ3 NOT NOT ||",
        b"ABk1 : ABJ2 ABJ3 NOT NOT ||",
    )
    missing_stock_rules = [
        rule for rule in required_stock_rules if rule not in building_dependencies
    ]
    if missing_stock_rules:
        fail(
            f"{miscdata_path}: BDEP did not preserve the stock dependency table; "
            f"missing {missing_stock_rules}"
        )
    if not building_dependencies.endswith(haunt_rule + b"\r\n"):
        fail(
            f"{miscdata_path}: Haunt BDEP rule must be last and retain the "
            "parser's required blank final line"
        )
    source_miscdata = game_path / "Data" / "miscdata.cam"
    if not source_miscdata.is_file():
        fail(f"{source_miscdata}: stock miscdata archive was not found")
    stock_dependencies = builder.read_cam_entry(
        source_miscdata,
        b"DATA",
        b"BDEP",
    ).data
    validate_building_dependencies_against_stock(
        miscdata_path,
        building_dependencies,
        stock_dependencies,
    )

    textdata_path = output_root / "Data" / "phantom_textdata.cam"
    textdata_captured = archive_results["phantom_textdata.cam"][1]
    unit_names = textdata_captured.get((b"STRT", b"UNTN"))
    guild_menu = textdata_captured.get((b"SMNU", b"AP07"))
    guild_strings = textdata_captured.get((b"STRT", b"AP07"))
    guild_menu_bytes = bytes(guild_menu) if guild_menu is not None else None
    guild_strings_bytes = bytes(guild_strings) if guild_strings is not None else None
    if unit_names is None or b"Phantoms Haunt" not in unit_names:
        fail(f"{textdata_path}: unit names do not contain Phantoms Haunt")
    if guild_strings_bytes is None or b"PHANTOMS HAUNT" not in guild_strings_bytes:
        fail(f"{textdata_path}: recruit dialog does not contain PHANTOMS HAUNT")
    if (
        guild_menu_bytes is None
        or len(guild_menu_bytes) != 3572
        or b"PHM1" not in guild_menu_bytes
        or b"PHTI" not in guild_menu_bytes
        or b"AVC1" in guild_menu_bytes
    ):
        fail(
            f"{textdata_path}: AP07 is not the expected Phantom-remapped "
            "stock AP10 upgradable menu layout"
        )
    spell_rect = struct.unpack_from("<4I", guild_menu_bytes, 0x0D34)
    if spell_rect != (103, 162, 0, 0):
        fail(
            f"{textdata_path}: AP07 retains a clickable AP10 temple-spell "
            f"control: {spell_rect}"
        )
    guild_string_count = struct.unpack_from("<H", guild_strings_bytes, 0)[0]
    if (
        guild_string_count != 31
        or b"LVL" in guild_strings_bytes
        or b"SPELLS" in guild_strings_bytes
    ):
        fail(
            f"{textdata_path}: AP07 strings retain unsafe AP10-only level or "
            "temple-spell controls"
        )
    help_text = archive_results["phantom_gpltext.cam"][1].get((b"STRT", b"HPTX"))
    expected_help = {
        "hPH0": (
            b"Durable ranged spellcaster specializing in combat against melee foes",
            b"can pair with a Priestess to drain the life of others",
            b"boundary between life and death as more of a suggestion than a law",
        ),
        "hP34": (
            b"Recruits Phantoms",
            b"Paladins refuse to remain",
            b"Upgrading the Haunt adds",
        ),
        "hP35": (
            b"Icy Touch, a punishing close-range strike",
            b"Gravekeeper doubles the restorative power",
            b"galleries fill with memorials",
        ),
        "hP36": (
            b"Allows veteran Phantoms to master Endless Winter",
            b"may draw them to support Phantoms in combat",
            b"crown of deathless ice",
        ),
    }
    if help_text is None:
        fail(f"{gpltext_path}: STRT/HPTX help table is missing")
    for help_id, phrases in expected_help.items():
        page = strt_text_by_fourcc(help_text, help_id)
        if page is None or any(phrase not in page for phrase in phrases):
            fail(
                f"{gpltext_path}: help page {help_id} is missing approved "
                "Phantom/Haunt copy"
            )

    maindata_path = output_root / "Data" / "phantom_maindata.cam"
    sections, captured = archive_results["phantom_maindata.cam"]
    validate_custom_tile_references(maindata_path, sections, captured)
    profile_entry = next(
        (
            entry
            for entry in sections.get(b"TILE", [])
            if entry.name == b"PHG1Profile"
        ),
        None,
    )
    if profile_entry is None:
        fail(f"{maindata_path}: custom Haunt profile TILE was not found")
    tile_count = len(sections.get(b"TILE", []))
    for building_image_name in (
        b"PHG1Phantom Guild",
        b"PHG2Phantom Guild L2",
        b"PHG3Phantom Guild L3",
    ):
        building_image = captured.get((b"IMAG", building_image_name))
        if (
            building_image is None
            or profile_entry.index
            not in referenced_indices(building_image, "low16", tile_count)
        ):
            fail(
                f"{maindata_path}: IMAG/{building_image_name!r} does not "
                "retain the custom Haunt profile after upgrading"
            )
    required_winter_images = (
        b"PHw1Winter Storm",
        b"PHw2Winter Hit",
        b"PHw3Winter Missile",
        b"PHw4Winter Flakes",
        b"PHw5Missile Flakes",
        b"PHw6Winter Anchor",
    )
    missing_winter_images = [
        name for name in required_winter_images if (b"IMAG", name) not in captured
    ]
    if missing_winter_images:
        fail(
            f"{maindata_path}: Phantom-only Endless Winter images are missing "
            f"{missing_winter_images}"
        )
    forbidden_stock_winter_images = (
        b"WRg1meteor_swarm_E1",
        b"WRg2meteor_blast",
        b"WPg3meteor_missile",
        b"XL20MeteorStrmEffct",
        b"XL21MeteorStrmMiss",
    )
    present_stock_winter_images = [
        name
        for name in forbidden_stock_winter_images
        if (b"IMAG", name) in captured
    ]
    if present_stock_winter_images:
        fail(
            f"{maindata_path}: mod overrides stock Wizard Meteor Storm images "
            f"{present_stock_winter_images}"
        )
    winter_storm_image = captured[(b"IMAG", b"PHw1Winter Storm")]
    winter_missile_image = captured[(b"IMAG", b"PHw3Winter Missile")]
    winter_anchor_image = captured[(b"IMAG", b"PHw6Winter Anchor")]
    if b"XL20" in winter_storm_image or b"PHW4" not in winter_storm_image:
        fail(
            f"{maindata_path}: Endless Winter storm still references the "
            "stock orange XL20 particle attachment"
        )
    if b"XL21" in winter_missile_image or b"PHW5" not in winter_missile_image:
        fail(
            f"{maindata_path}: Endless Winter missile still references the "
            "stock orange XL21 particle attachment"
        )
    if b"PHW4" in winter_anchor_image or b"XL20" in winter_anchor_image:
        fail(
            f"{maindata_path}: invisible Endless Winter anchor still contains "
            "a visible storm particle attachment"
        )
    winter_tile_groups = {
        prefix: [
            entry.name.rstrip(b"\x00")
            for entry in sections.get(b"TILE", [])
            if entry.name.rstrip(b"\x00").startswith(prefix)
        ]
        for prefix in (
            b"PHw1Storm",
            b"PHw2Hit",
            b"PHw3Snow",
            b"PHw4Flake",
            b"PHw5Flake",
            b"PHw6Anchor",
        )
    }
    expected_winter_tile_counts = {
        b"PHw1Storm": 15,
        b"PHw2Hit": 8,
        b"PHw3Snow": 4,
        b"PHw4Flake": 13,
        b"PHw5Flake": 7,
        b"PHw6Anchor": 1,
    }
    wrong_winter_counts = {
        prefix: len(winter_tile_groups[prefix])
        for prefix, expected in expected_winter_tile_counts.items()
        if len(winter_tile_groups[prefix]) != expected
    }
    if wrong_winter_counts:
        fail(
            f"{maindata_path}: Phantom-only Endless Winter TILE counts are "
            f"wrong {wrong_winter_counts}"
        )
    minimum_unique_winter_frames = {
        b"PHw1Storm": 10,
        b"PHw2Hit": 6,
        b"PHw3Snow": 4,
        b"PHw4Flake": 8,
        b"PHw5Flake": 5,
    }
    for prefix, minimum_unique in minimum_unique_winter_frames.items():
        frames = [
            captured[(b"TILE", name)] for name in winter_tile_groups[prefix]
        ]
        unique_count = len(set(frames))
        if unique_count < minimum_unique:
            fail(
                f"{maindata_path}: {prefix!r} has only {unique_count} unique "
                f"frames; expected at least {minimum_unique} animated phases"
            )
        frame_dimensions = {
            (
                struct.unpack_from("<H", frame, 4)[0],
                struct.unpack_from("<H", frame, 2)[0],
            )
            for frame in frames
        }
        if len(frame_dimensions) != 1:
            fail(
                f"{maindata_path}: {prefix!r} does not use a fixed frame "
                f"canvas; dimensions={sorted(frame_dimensions)}"
            )
    invisible_snowflake_tiles = [
        entry.name.rstrip(b"\x00")
        for entry in sections.get(b"TILE", [])
        if entry.name.rstrip(b"\x00").startswith(b"PHw3Snow")
        and indexed_v3_body_bounds(captured[(b"TILE", entry.name.rstrip(b"\x00"))])
        is None
    ]
    if invisible_snowflake_tiles:
        fail(
            f"{maindata_path}: Phantom-only snowflake missile has blank phases "
            f"{invisible_snowflake_tiles}"
        )
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
    for building_image_name in (
        b"PHG1Phantom Guild",
        b"PHG2Phantom Guild L2",
        b"PHG3Phantom Guild L3",
    ):
        building_image = captured.get((b"IMAG", building_image_name))
        if building_image is None:
            fail(f"{maindata_path}: IMAG/{building_image_name!r} was not found")
        validate_building_destruction_attachments(maindata_path, building_image)

    interface_path = output_root / "Data" / "phantom_interfacedata.cam"
    sections, captured = archive_results["phantom_interfacedata.cam"]
    validate_interface_panel_reference(interface_path, sections, captured)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated Phantoms Haunt package.")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--game-path",
        required=True,
        type=Path,
        help="Game root used to compare DATA/BDEP byte-for-byte with stock.",
    )
    args = parser.parse_args()
    try:
        validate(
            args.output_root.resolve(),
            args.game_path.resolve(),
        )
    except ValidationError as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    print("Verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
