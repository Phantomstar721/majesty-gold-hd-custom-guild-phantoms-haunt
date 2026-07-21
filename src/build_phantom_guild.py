from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
import struct
import uuid
import wave


MAGIC = b"CYLBPC  \x01\x00\x01\x00"
HEADER_SIZE = 20
DIR_ENTRY_SIZE = 8
SECTION_HEADER_PREFIX_SIZE = 8
ENTRY_HEADER_SIZE = 28

MOD_ID = uuid.UUID("8c48289e-7c70-4426-8913-133f3544a182")
HERO_ID = "PHM1"
BUILDING_ID = "PHG1"
SOURCE_HERO_IMAGE = b"AVJ1Rogue"
SOURCE_BUILDING_IMAGE = b"ABX1Rogue Guild1"
PHANTOM_HERO_IMAGE = b"PHM1Phantom"
PHANTOM_BUILDING_IMAGE = b"PHG1Phantom Guild"
HERO_PORTRAIT_TILE = 4994
BUILDING_TEST_TILE = 59


@dataclass(frozen=True)
class CamEntry:
    name: bytes
    data: bytes


@dataclass(frozen=True)
class CamSection:
    extension: bytes
    padding: bytes
    entries: tuple[CamEntry, ...]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-path", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    data_dir = args.output_root / "Data"
    gpl_dir = args.output_root / "GPL"
    data_dir.mkdir(parents=True, exist_ok=True)
    gpl_dir.mkdir(parents=True, exist_ok=True)

    source_textdata = args.game_path / "Data" / "textdata.cam"
    source_maindata = args.game_path / "Data" / "maindata.cam"
    if not source_textdata.exists():
        raise FileNotFoundError(source_textdata)
    if not source_maindata.exists():
        raise FileNotFoundError(source_maindata)

    write_textdata_cam(source_textdata, data_dir / "phantom_textdata.cam")
    write_maindata_cam(source_maindata, data_dir / "phantom_maindata.cam")
    write_voices_cam(data_dir / "phantom_voices.cam")

    (data_dir / "phantom_units.xml").write_text(phantom_units_xml(), encoding="utf-8")
    (data_dir / "phantom_sounds.xml").write_text(phantom_sounds_xml(), encoding="utf-8")
    (gpl_dir / "Phantom_Building_Data.dat").write_text(phantom_building_data(), encoding="utf-8")
    (gpl_dir / "Phantom_Hero_Data.dat").write_text(phantom_hero_data(), encoding="utf-8")
    (gpl_dir / "Phantom.gpl").write_text(phantom_gpl(), encoding="utf-8")
    (gpl_dir / "Phantom.gplproj").write_text(phantom_gplproj(), encoding="utf-8")
    (args.output_root / "PhantomGuildPoc.mmxml").write_text(mod_xml(), encoding="utf-8")
    return 0


def phantom_units_xml() -> str:
    return """<Majesty>
\t<Description type="Unit" subType="Character" ID="PHM1" Name="Phantom" Description="Phantom">
\t\t<Engine version="1">
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="6"/>
\t\t\t<ImageIDBase value="PHM1"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="Class 2"/>
\t\t\t<DefaultSound value="Phantom"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="AP20"/>
\t\t\t<Cost value="1"/>
\t\t\t<Experience value="1000"/>
\t\t\t<MaxHP value="35"/>
\t\t\t<SightRange value="220"/>
\t\t\t<Speed value="4"/>
\t\t\t<AttackRange min="100" max="130"/>
\t\t\t<Vitality value="12"/>
\t\t\t<Artifice value="25"/>
\t\t\t<WillPower value="15"/>
\t\t\t<Intelligence value="18"/>
\t\t\t<Strength value="10"/>
\t\t\t<RangedAttack value="60"/>
\t\t\t<Parry value="35"/>
\t\t\t<Dodge value="60"/>
\t\t\t<WeaponBasicDamage value="10"/>
\t\t\t<ArmorBasicDamage value="2"/>
\t\t\t<RecruitDelay value="1000"/>
\t\t\t<NameGenType value="NM13"/>
\t\t\t<Flags value="Heals"/>
\t\t\t<Flags value="HasHPBar"/>
\t\t\t<Flags value="CanHighlight"/>
\t\t\t<HelpID value="h017"/>
\t\t\t<AllowedWeapon value="Crossbow"/>
\t\t\t<AllowedArmor value="Leather"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Building" ID="PHG1" Name="Phantoms_Guild1" Description="Phantom's Guild">
\t\t<Engine version="1">
\t\t\t<Info value="BlockGround"/>
\t\t\t<Info value="BlockFlying"/>
\t\t\t<Info value="ModifyTerrainTextureOnPlacement"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="2"/>
\t\t\t<ImageIDBase value="PHG1"/>
\t\t\t<DefaultSound value="Phantom_Guild"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="AP48"/>
\t\t\t<Cost value="1"/>
\t\t\t<Multiplier value="1.0"/>
\t\t\t<IncomeType value="2"/>
\t\t\t<IncomeAmount value="5"/>
\t\t\t<MaxHP value="250"/>
\t\t\t<MaxGuildMembers value="4"/>
\t\t\t<SightRange value="150"/>
\t\t\t<Flags value="IsGuild"/>
\t\t\t<Flags value="HasHPBar"/>
\t\t\t<Flags value="HasGoldToolTip"/>
\t\t\t<HelpID value="h034"/>
\t\t\t<Produces>
\t\t\t\t<Unit ID="Phantom"/>
\t\t\t</Produces>
\t\t</Game>
\t</Description>
</Majesty>
"""


def phantom_sounds_xml() -> str:
    return """<Majesty>
\t<Description type="Sound" subType="Standard" ID="PH01" Name="Phantom">
\t\t<Engine version="1">
\t\t\t<Category value="0"/>
\t\t\t<Phase ID="VFX_DECIDING">
\t\t\t\t<Wave value="PHD1"/>
\t\t\t\t<Group value="Deciding_Group"/>
\t\t\t</Phase>
\t\t\t<Phase ID="VFX_SPECIAL1">
\t\t\t\t<Wave value="PHS1"/>
\t\t\t\t<Group value="Voice_Special_1_Group"/>
\t\t\t</Phase>
\t\t\t<Phase ID="Death">
\t\t\t\t<Wave value="PHDH"/>
\t\t\t\t<Group value="Death_Group"/>
\t\t\t\t<DistanceModifier value="10001.0"/>
\t\t\t</Phase>
\t\t\t<Phase ID="Attack">
\t\t\t\t<Wave value="PHA1"/>
\t\t\t\t<Group value="Attack_Group"/>
\t\t\t</Phase>
\t\t</Engine>
\t</Description>
\t<Description type="Sound" subType="Standard" ID="PH02" Name="Phantom_Guild">
\t\t<Engine version="1">
\t\t\t<Category value="0"/>
\t\t\t<Phase ID="Select">
\t\t\t\t<Wave value="PHGS"/>
\t\t\t\t<DistanceModifier value="10000.0"/>
\t\t\t</Phase>
\t\t</Engine>
\t</Description>
</Majesty>
"""


def phantom_hero_data() -> str:
    return """[Phantom]
\t{Hero
\t\t(type\thero)
\t\t(subtype hero)
\t\t(title Phantom)
\t\t(original_type Hero)
\t\t(EnemyType monster)
\t\t(Idle_action\tbasic_idle)
\t\t(attack_action rogue_bolt)
\t\t(Cast_Action Basic_Cast)
\t\t(Pickup_Action Basic_Pickup)
\t\t(PrimaryStat ATTRIB_Willpower)
\t\t(Friend\txx)
\t\t(attacktype 2)
\t\t(castingrange 25)
\t\t(PercentageHPRetreat 30)
\t\t(enemy_estimation 1.1)
\t\t(self_estimation 1.0)
\t\t(Loyalty 20)
\t\t(Greed 12)
\t\t(Luck 20)
\t\t(Upgrade_Armor_Chance\t100)
\t\t(Upgrade_Weapon_Chance\t100)
\t\t(Poison_Weapon_Chance\t100)
\t\t(evaluationScript\teval_enemies_nearby)
\t\t(activeScript\tPhantom_tree)
\t\t(basicscript\tPhantom_tree)
\t\t(StartingScript\tPhantom_tree)
\t\t(birthScript\tPhantom_birth)
\t\t(IGdeathscript\tgravestone)
\t}
[end]
"""


def phantom_building_data() -> str:
    return """[Phantoms_Guild1]
\t{Guild
\t\t(type building)
\t\t(subtype Guild)
\t\t(title Phantoms_Guild)
\t\t(Level 1)
\t\t(member_title Phantom)
\t\t(member_basicscript Phantom_tree)
\t\t(max_members 4)
\t\t(Lived_In_Script Lived_In)
\t\t(Sleep_for 30000)
\t\t(birthscript basic_birth)
\t\t(birthScript2 Guild_Birth)
\t\t(IGdeathscript guild_destroyed_a)
\t}
[end]
"""


def phantom_gpl() -> str:
    return """function Phantom_tree (agent thisagent)

declare

begin
\t$DebugOut("Phantom deciding");
\t$Rogue_tree(thisagent);
end

function Phantom_birth (agent thisagent)

declare

begin
\t$PlaySound(thisagent, "Phantom", "VFX_SPECIAL1");
\t$hero_birth(thisagent);
end
"""


def phantom_gplproj() -> str:
    return """data="Phantom_Building_Data.dat"
data="Phantom_Hero_Data.dat"

source="Phantom.gpl"
"""


def mod_xml() -> str:
    return f"""<Majesty>
\t<Mod id="{{{MOD_ID}}}">
\t\t<Name>PhantomGuildPoc</Name>
\t\t<DisplayName lang="en_US">Phantom Guild POC</DisplayName>
\t\t<Description lang="en_US">
\t\t\t<Short>Adds a test Phantom's Guild and recruitable Phantom hero.</Short>
\t\t\t<Long/>
\t\t</Description>
\t\t<DataConfiguration>
\t\t\t<Dataset base="Any">
\t\t\t\t<Load>
\t\t\t\t\t<Descriptions>Data\\phantom_units.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_sounds.xml</Descriptions>
\t\t\t\t\t<CAM>Data\\phantom_textdata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_maindata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_voices.cam</CAM>
\t\t\t\t\t<GPL>
\t\t\t\t\t\t<Target>Data\\Phantom.bcd</Target>
\t\t\t\t\t\t<Source>GPL\\Phantom_Building_Data.dat</Source>
\t\t\t\t\t\t<Source>GPL\\Phantom_Hero_Data.dat</Source>
\t\t\t\t\t\t<Source>GPL\\Phantom.gpl</Source>
\t\t\t\t\t</GPL>
\t\t\t\t</Load>
\t\t\t</Dataset>
\t\t</DataConfiguration>
\t</Mod>
</Majesty>
"""


def write_textdata_cam(source_textdata: Path, output_path: Path) -> None:
    unit_names = read_cam_entry(source_textdata, b"STRT", b"UNTN")
    patched_unit_names = patch_strt_strings(
        unit_names.data,
        {
            fourcc_id(HERO_ID): "Phantom",
            fourcc_id(BUILDING_ID): "Phantom's Guild",
        },
    )
    write_cam(
        (
            CamSection(
                extension=b"STRT",
                padding=b"\x00\x00\x00\x00",
                entries=(CamEntry(name=pad_name(b"UNTN"), data=patched_unit_names),),
            ),
        ),
        output_path,
    )


def write_maindata_cam(source_maindata: Path, output_path: Path) -> None:
    hero_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_HERO_IMAGE).data
    building_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_BUILDING_IMAGE).data
    tiles = read_cam_entries(source_maindata, b"TILE")
    palettes = read_cam_entries(source_maindata, b"SPLT")

    tile_indices = referenced_tile_indices(hero_imag, len(tiles))
    tile_indices.update(referenced_tile_indices(building_imag, len(tiles)))
    tile_indices.update((HERO_PORTRAIT_TILE, BUILDING_TEST_TILE))
    max_tile_index = max(tile_indices)

    hero_tile = generated_phantom_tile(tiles[HERO_PORTRAIT_TILE].data, palettes)
    building_tile = generated_phantom_tile(tiles[BUILDING_TEST_TILE].data, palettes)

    palette_indices: set[int] = set()
    tile_entries: list[CamEntry] = []
    for tile_index in range(max_tile_index + 1):
        if tile_index == HERO_PORTRAIT_TILE:
            tile = hero_tile
        elif tile_index == BUILDING_TEST_TILE:
            tile = building_tile
        else:
            tile = tiles[tile_index].data

        palette_index = tile_palette_index(tile)
        if palette_index is not None and palette_index < len(palettes):
            palette_indices.add(palette_index)
        tile_entries.append(CamEntry(name=tiles[tile_index].name, data=tile))

    max_palette_index = max(palette_indices)
    palette_entries = tuple(
        CamEntry(name=palettes[index].name, data=palettes[index].data)
        for index in range(max_palette_index + 1)
    )
    write_cam(
        (
            CamSection(
                extension=b"IMAG",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(PHANTOM_HERO_IMAGE), data=hero_imag),
                    CamEntry(name=pad_name(PHANTOM_BUILDING_IMAGE), data=building_imag),
                ),
            ),
            CamSection(extension=b"TILE", padding=b"\x01\x00\x00\x00", entries=tuple(tile_entries)),
            CamSection(extension=b"SPLT", padding=b"\x00\x00\x00\x00", entries=palette_entries),
        ),
        output_path,
    )


def generated_phantom_tile(original_tile: bytes, palettes: list[CamEntry]) -> bytes:
    if len(original_tile) < 26 or struct.unpack_from("<H", original_tile, 0)[0] != 1:
        return original_tile

    width = struct.unpack_from("<H", original_tile, 2)[0]
    height = struct.unpack_from("<H", original_tile, 4)[0]
    palette_index = struct.unpack_from("<H", original_tile, 22)[0]
    if palette_index >= len(palettes):
        return original_tile

    colors = splt_palette_colors(palettes[palette_index].data)
    black = nearest_palette_index(2, 4, 8, colors)
    cyan = nearest_palette_index(0, 220, 255, colors)
    blue = nearest_palette_index(0, 80, 180, colors)
    white = nearest_palette_index(210, 255, 255, colors)

    output = bytearray(original_tile[:26])
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    radius = min(width, height) * 0.28

    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            distance = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            ring = abs(distance - radius) < 2.0
            diagonal = abs(math.sin(angle * 4.0)) > 0.94 and distance < radius * 1.9
            core = distance < radius * 0.38
            spark = (x * 17 + y * 31) % 97 == 0

            if core:
                output.append(blue)
            elif ring or diagonal:
                output.append(cyan)
            elif spark:
                output.append(white)
            else:
                output.append(black)

    return bytes(output)


def write_voices_cam(output_path: Path) -> None:
    entries = (
        CamEntry(name=pad_name(b"PHD1"), data=generated_wave(220.0, 0.20, 0.25)),
        CamEntry(name=pad_name(b"PHS1"), data=generated_wave(330.0, 0.22, 0.35)),
        CamEntry(name=pad_name(b"PHDH"), data=generated_wave(120.0, 0.28, 0.40)),
        CamEntry(name=pad_name(b"PHA1"), data=generated_wave(520.0, 0.10, 0.30)),
        CamEntry(name=pad_name(b"PHGS"), data=generated_wave(180.0, 0.25, 0.30)),
    )
    write_cam((CamSection(extension=b"WAVE", padding=b"\x00\x00\x00\x00", entries=entries),), output_path)


def generated_wave(freq: float, seconds: float, volume: float) -> bytes:
    sample_rate = 22050
    frame_count = int(sample_rate * seconds)
    frames = bytearray()
    for i in range(frame_count):
        t = i / sample_rate
        envelope = 1.0 - (i / frame_count)
        wobble = math.sin(2.0 * math.pi * freq * 0.5 * t) * 0.25
        sample = math.sin(2.0 * math.pi * (freq + freq * wobble) * t)
        value = int(sample * envelope * volume * 32767)
        frames += struct.pack("<h", value)

    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


def read_cam_entry(path: Path, section_ext: bytes, entry_name: bytes) -> CamEntry:
    entries = read_cam_entries(path, section_ext)
    for entry in entries:
        if entry.name.rstrip(b"\x00") == entry_name:
            return entry
    raise ValueError(f"Could not find {section_ext.decode(errors='ignore')}/{entry_name!r} in {path}")


def read_cam_entries(path: Path, section_ext: bytes) -> list[CamEntry]:
    data = path.read_bytes()
    if data[: len(MAGIC)] != MAGIC:
        raise ValueError(f"{path} is not a CYLBPC CAM archive")

    section_count = u32(data, 12)
    cursor = HEADER_SIZE
    sections: list[tuple[bytes, int]] = []
    for _ in range(section_count):
        sections.append((data[cursor : cursor + 4], u32(data, cursor + 4)))
        cursor += DIR_ENTRY_SIZE

    for extension, section_offset in sections:
        cursor = section_offset
        count = u32(data, cursor)
        cursor += SECTION_HEADER_PREFIX_SIZE
        entries: list[CamEntry] = []
        for _ in range(count):
            raw_name = data[cursor : cursor + 20]
            offset = u32(data, cursor + 20)
            size = u32(data, cursor + 24)
            cursor += ENTRY_HEADER_SIZE
            entries.append(CamEntry(name=raw_name, data=data[offset : offset + size]))
        if extension == section_ext:
            return entries

    raise ValueError(f"Could not find {section_ext.decode(errors='ignore')} section in {path}")


def write_cam(sections: tuple[CamSection, ...], path: Path) -> None:
    section_count = len(sections)
    file_header_size = HEADER_SIZE + section_count * DIR_ENTRY_SIZE
    content_header_size = sum(
        SECTION_HEADER_PREFIX_SIZE + len(section.entries) * ENTRY_HEADER_SIZE
        for section in sections
    )
    content_start = file_header_size + content_header_size

    offsets: list[list[int]] = []
    cursor = content_start
    for section in sections:
        section_offsets: list[int] = []
        for entry in section.entries:
            section_offsets.append(cursor)
            cursor += len(entry.data)
        offsets.append(section_offsets)

    output = bytearray()
    output += MAGIC
    output += struct.pack("<I", section_count)
    output += struct.pack("<I", content_header_size)

    section_header_offset = file_header_size
    for section in sections:
        output += section.extension
        output += struct.pack("<I", section_header_offset)
        section_header_offset += SECTION_HEADER_PREFIX_SIZE + len(section.entries) * ENTRY_HEADER_SIZE

    for section_index, section in enumerate(sections):
        output += struct.pack("<I", len(section.entries))
        output += section.padding
        for entry_index, entry in enumerate(section.entries):
            output += entry.name
            output += struct.pack("<I", offsets[section_index][entry_index])
            output += struct.pack("<I", len(entry.data))

    for section in sections:
        for entry in section.entries:
            output += entry.data

    path.write_bytes(bytes(output))


def patch_strt_strings(data: bytes, replacements: dict[int, str]) -> bytes:
    count = struct.unpack_from("<H", data, 0)[0]
    version = data[2:4]
    offsets = list(struct.unpack_from(f"<{count}I", data, 4))
    records: list[tuple[int, bytes]] = []
    seen: set[int] = set()

    for offset in offsets:
        string_id = u32(data, offset)
        string_start = offset + 4
        string_end = data.index(b"\x00", string_start)
        text = data[string_start:string_end]
        if string_id in replacements:
            text = replacements[string_id].encode("cp1252")
            seen.add(string_id)
        records.append((string_id, text))

    for string_id, replacement in replacements.items():
        if string_id not in seen:
            records.append((string_id, replacement.encode("cp1252")))

    output = bytearray()
    output += struct.pack("<H", len(records))
    output += version
    output += b"\x00\x00\x00\x00" * len(records)

    new_offsets: list[int] = []
    for string_id, text in records:
        new_offsets.append(len(output))
        output += struct.pack("<I", string_id)
        output += text
        output += b"\x00"

    for index, offset in enumerate(new_offsets):
        struct.pack_into("<I", output, 4 + index * 4, offset)

    return bytes(output)


def referenced_tile_indices(imag: bytes, tile_count: int) -> set[int]:
    return {
        u32(imag, offset)
        for offset in range(0, len(imag) - 3, 4)
        if u32(imag, offset) < tile_count
    }


def splt_palette_colors(palette: bytes) -> list[tuple[int, int, int]]:
    if len(palette) < 8 + 256 * 4:
        raise ValueError("Expected a 256-color SPLT palette")

    colors: list[tuple[int, int, int]] = []
    for index in range(256):
        offset = 8 + index * 4
        colors.append((palette[offset], palette[offset + 1], palette[offset + 2]))
    return colors


def nearest_palette_index(red: int, green: int, blue: int, colors: list[tuple[int, int, int]]) -> int:
    best_index = 0
    best_distance = math.inf
    for index, (palette_red, palette_green, palette_blue) in enumerate(colors):
        distance = (
            (red - palette_red) * (red - palette_red)
            + (green - palette_green) * (green - palette_green)
            + (blue - palette_blue) * (blue - palette_blue)
        )
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


def tile_palette_index(tile: bytes) -> int | None:
    if len(tile) < 24:
        return None
    return struct.unpack_from("<H", tile, 22)[0]


def fourcc_id(value: str) -> int:
    raw = value.encode("ascii")
    if len(raw) != 4:
        raise ValueError(f"Expected a four-character id, got {value!r}")
    return struct.unpack("<I", raw)[0]


def pad_name(name: bytes) -> bytes:
    if len(name) > 20:
        raise ValueError(f"CAM entry name too long: {name!r}")
    return name.ljust(20, b"\x00")


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


if __name__ == "__main__":
    raise SystemExit(main())
