from __future__ import annotations

import argparse
from collections import deque
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
BUILDING_ID = "MBPhantomGuild"
BUILDING_TEXT_ID = "PHG1"
# Majesty keys recruit-panel behavior in the exe by AP dialog id. AP07 is the
# stock Elf recruit panel, so borrowing it keeps this mod Workshop-only.
PHANTOM_GUILD_DIALOG_ID = b"AP07"
SOURCE_RECRUIT_GUILD_DIALOG_ID = PHANTOM_GUILD_DIALOG_ID
SOURCE_HERO_IMAGE = b"AVN1Wizard"
SOURCE_PHANTOM_SPRITE_IMAGE = b"AVG1Priestess"
SOURCE_BUILDING_IMAGE = b"ABQ1Temple, Fervus1"
SOURCE_TELEPORT_EFFECT_IMAGE = b"WRd1teleport_e"
SOURCE_ICE_LANCE_ICON = b"XL15PowerShock"
SOURCE_ICE_LANCE_PROJECTILE = b"WPc2fire_blast_M"
SOURCE_FROST_ARMOR_ICON = b"WRb2fireshield_IC"
SOURCE_ICY_TOUCH_ICON = b"WRc1fire_blast_e"
SOURCE_BLIZZARD_ICON = b"WRg2meteor_blast"
SOURCE_METEOR_STORM_IMAGE = b"WRg1meteor_swarm_E1"
SOURCE_METEOR_HIT_IMAGE = b"WRg2meteor_blast"
SOURCE_METEOR_MISSILE_IMAGE = b"WPg3meteor_missile"
SOURCE_METEOR_STORM_PARTICLE_IMAGE = b"XL20MeteorStrmEffct"
SOURCE_METEOR_MISSILE_PARTICLE_IMAGE = b"XL21MeteorStrmMiss"
PHANTOM_HERO_IMAGE = b"PHM1Phantom"
PHANTOM_BUILDING_IMAGE = b"PHG1Phantom Guild"
RAW_TEXTURES_IMAGE = b"INTIraw textures"
PHANTOM_RAW_TEXTURES_IMAGE = b"PHTIraw textures"
PHANTOM_ICE_LANCE_ICON = b"WRa2Ice Lance"
PHANTOM_ICE_LANCE_PROJECTILE = b"PHp1fire_blast_M"
PHANTOM_FROST_ARMOR_ICON = b"WRa3Frost Armor"
PHANTOM_ICY_TOUCH_ICON = b"WRa4Icy Touch"
PHANTOM_BLIZZARD_ICON = b"WRa5Blizzard"
FROST_FIELD_HIT_IMAGE = b"XR30frost_fld_hit"
CHILL_ICON_TEMPLATE_IMAGE = b"XR25plague_icon"
PHANTOM_ICE_LANCE_HIT_IMAGE = b"PHo3Ice Lance Hit"
PHANTOM_CHILL_ICON_IMAGE = b"PHo4chill_icon"
PHANTOM_EMPOWERED_CHILL_ICON_IMAGE = b"PHc3emp_chill_icon"
PHANTOM_GRAVECHILL_ICON_IMAGE = b"PHg1Gravechill"
PHANTOM_GRAVECHILL_HIT_IMAGE = b"PHg2Gravechill Hit"
PHANTOM_FROST_ARMOR_CRYSTAL_IMAGE = b"PHf1Frost Crystal"
PHANTOM_FROZEN_SMALL_IMAGE = b"PHf2Frozen Small"
PHANTOM_FROZEN_MEDIUM_IMAGE = b"PHf3Frozen Medium"
PHANTOM_FROZEN_LARGE_IMAGE = b"PHf4Frozen Large"
PHANTOM_CALL_TO_GRAVE_IMAGE = b"PHc2Call to Grave"
PHANTOM_ETERNAL_SOUL_ICON_IMAGE = b"PHe1Soul Flame Icon"
PHANTOM_ETERNAL_SOUL_CAST_IMAGE = b"PHe2Soul Flame"
PHANTOM_ENDLESS_WINTER_IMAGE = b"PHw1Winter Storm"
PHANTOM_ENDLESS_WINTER_HIT_IMAGE = b"PHw2Winter Hit"
PHANTOM_ENDLESS_WINTER_MISSILE_IMAGE = b"PHw3Winter Missile"
PHANTOM_ENDLESS_WINTER_STORM_PARTICLE_IMAGE = b"PHw4Winter Flakes"
PHANTOM_ENDLESS_WINTER_MISSILE_PARTICLE_IMAGE = b"PHw5Missile Flakes"
PHANTOM_ENDLESS_WINTER_ANCHOR_IMAGE = b"PHw6Winter Anchor"
PHANTOM_APPROVED_STAND_BODY_HEIGHTS = (61, 55, 52, 50, 50, 56, 60, 61)
HERO_PORTRAIT_TILE = 6293
HERO_ICON_TILE = 6299
BUILDING_PROFILE_TILE = 1509
BUILDING_ICON_TILE = 1510
HERO_INTERFACE_PANEL_TILE = 4793
BUILDING_DIALOG_BACKING_TILE = 466
BUILDING_SPRITE_PALETTE_INDEX = 560
PHANTOM_HERO_ICON_PALETTE_INDEX = 560
PHANTOM_HERO_PORTRAIT_PALETTE_INDEX = 560
BUILDING_ACTIVE_SET_ID = 192
# The inherited Fervus destruction animation places its third fire layer well
# beyond the upper-right edge of the Phantoms Haunt's custom damaged and rubble
# frames. Keep the effect, but anchor it on the building across every collapse
# state in which that layer appears.
BUILDING_DESTRUCTION_ATTACHMENT_REMAPS = {
    0x03000063: (35, 25),  # Die-4 / damaged A, fire layer 3
    0x03000064: (35, 25),  # Die-5 / damaged B, fire layer 3
    0x03000065: (35, 25),  # Die-6 / damaged B, fire layer 3
    0x03000066: (35, 25),  # Die-7 / destroyed alternate, fire layer 3
    0x03000067: (35, 25),  # Die-8 / destroyed alternate, fire layer 3
}
ICE_LANCE_ICON_TILE = 202
ICE_LANCE_PROJECTILE_TILES = tuple(range(202, 214))
ICE_LANCE_DIRECTIONAL_PROJECTILE_TILES = tuple(range(8368, 8496))
ICE_LANCE_PROJECTILE_DIRECTIONS = 32
ICE_LANCE_PROJECTILE_FRAMES_PER_DIRECTION = 4
ICE_LANCE_PROJECTILE_PALETTE_INDEX = 161
SPELL_LIST_ICON_IMAGE = b"INTnChar spell icon"
WEAPON_ICON_IMAGE = b"INBwicons weapons"
ARMOR_ICON_IMAGE = b"INBaarmor icons"
ICE_LANCE_SPELL_ICON_TILES = (344,)
FROST_ARMOR_SPELL_ICON_TILES = (345,)
ICY_TOUCH_SPELL_ICON_TILES = (346,)
FIRE_BLAST_SPELL_ICON_TILE = 357
BLIZZARD_SPELL_ICON_TILES = (347,)
CALL_TO_GRAVE_SPELL_ICON_TILES = (348,)
ETERNAL_SOUL_SPELL_ICON_TILES = (349,)
STAFF_ICON_TILES: tuple[int, ...] = ()
STAFF_SMALL_ICON_TILES: tuple[int, ...] = ()
MX_STAFF_ICON_TILES: tuple[int, ...] = ()
LEATHER_ARMOR_ICON_TILES: tuple[int, ...] = ()

PHANTOM_COWL_BASE_ITEM_ID = 80
PHANTOM_ICEROD_BASE_ITEM_ID = 81
PHANTOM_FROST_ARMOR_ITEM_ID = 82
PHANTOM_COWL_VARIANT_FIRST_ID = 83
PHANTOM_COWL_VARIANT_LAST_ID = 97
PHANTOM_ICEROD_VARIANT_FIRST_ID = 98
PHANTOM_ICEROD_VARIANT_LAST_ID = 112

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
    parser.add_argument("--portrait-rgb", type=Path)
    parser.add_argument("--hero-icon-rgb", type=Path)
    parser.add_argument("--building-profile-rgb", type=Path)
    parser.add_argument("--building-icon-rgb", type=Path)
    parser.add_argument("--building-sprite-rgb-dir", type=Path)
    parser.add_argument("--hero-sprite-png-dir", type=Path)
    parser.add_argument("--interface-panel-rgb", type=Path)
    parser.add_argument("--building-dialog-panel-rgb", type=Path)
    parser.add_argument("--ice-lance-icon-rgb", type=Path)
    parser.add_argument("--ice-lance-projectile-source-png", type=Path)
    parser.add_argument("--icy-touch-impact-source-png", type=Path)
    parser.add_argument("--frost-armor-crystal-source-png", type=Path)
    parser.add_argument("--frost-armor-frozen-casing-source-png", type=Path)
    parser.add_argument("--call-to-grave-portal-source-png", type=Path)
    parser.add_argument("--eternal-soul-flame-source-png", type=Path)
    parser.add_argument("--endless-winter-vortex-source-png", type=Path)
    parser.add_argument("--endless-winter-hit-source-png", type=Path)
    parser.add_argument("--endless-winter-missile-source-png", type=Path)
    parser.add_argument("--ice-lance-spell-icon-rgb", type=Path)
    parser.add_argument("--frost-armor-spell-icon-rgb", type=Path)
    parser.add_argument("--blizzard-spell-icon-rgb", type=Path)
    parser.add_argument("--call-to-grave-spell-icon-rgb", type=Path)
    parser.add_argument("--phantom-cowl-icon-rgb", type=Path)
    parser.add_argument("--dark-staff-small-icon-rgb", type=Path)
    parser.add_argument("--dark-staff-mx-icon-rgb", type=Path)
    parser.add_argument("--dark-staff-icon-rgb", type=Path)
    args = parser.parse_args()

    data_dir = args.output_root / "Data"
    gpl_dir = args.output_root / "GPL"
    data_dir.mkdir(parents=True, exist_ok=True)
    gpl_dir.mkdir(parents=True, exist_ok=True)

    source_textdata = args.game_path / "Data" / "textdata.cam"
    source_gpltext = args.game_path / "Data" / "gpltext.cam"
    source_mx_gpltext = args.game_path / "DataMX" / "mx_gpltext.cam"
    source_maindata = args.game_path / "Data" / "maindata.cam"
    source_ice_effect_maindata = args.game_path / "DataMX" / "mx_maindata.cam"
    source_interfacedata = args.game_path / "Data" / "interfacedata.cam"
    source_mx_interfacedata = args.game_path / "DataMX" / "mx_interfacedata.cam"
    if not source_textdata.exists():
        raise FileNotFoundError(source_textdata)
    if not source_gpltext.exists():
        raise FileNotFoundError(source_gpltext)
    if not source_maindata.exists():
        raise FileNotFoundError(source_maindata)
    if not source_interfacedata.exists():
        raise FileNotFoundError(source_interfacedata)

    write_textdata_cam(source_textdata, data_dir / "phantom_textdata.cam")
    write_gpltext_cam(
        source_mx_gpltext if source_mx_gpltext.exists() else source_gpltext,
        data_dir / "phantom_gpltext.cam",
    )
    write_maindata_cam(
        source_maindata,
        data_dir / "phantom_maindata.cam",
        args.portrait_rgb,
        args.hero_icon_rgb,
        args.building_profile_rgb,
        args.building_icon_rgb,
        args.building_sprite_rgb_dir,
        args.hero_sprite_png_dir,
        args.interface_panel_rgb,
        args.ice_lance_icon_rgb,
        args.ice_lance_projectile_source_png,
        args.icy_touch_impact_source_png,
        args.frost_armor_crystal_source_png,
        args.frost_armor_frozen_casing_source_png,
        args.call_to_grave_portal_source_png,
        args.eternal_soul_flame_source_png,
        args.endless_winter_vortex_source_png,
        args.endless_winter_hit_source_png,
        args.endless_winter_missile_source_png,
        source_ice_effect_maindata if source_ice_effect_maindata.exists() else None,
    )
    write_interfacedata_cam(
        source_interfacedata,
        data_dir / "phantom_interfacedata.cam",
        args.ice_lance_spell_icon_rgb,
        args.frost_armor_spell_icon_rgb,
        args.blizzard_spell_icon_rgb,
        args.call_to_grave_spell_icon_rgb,
        args.phantom_cowl_icon_rgb,
        args.dark_staff_small_icon_rgb,
        args.dark_staff_icon_rgb,
        args.building_dialog_panel_rgb,
    )
    if source_mx_interfacedata.exists():
        write_mx_interfacedata_cam(
            source_mx_interfacedata,
            data_dir / "phantom_mx_interfacedata.cam",
            args.dark_staff_mx_icon_rgb,
        )
    write_voices_cam(data_dir / "phantom_voices.cam")

    (data_dir / "phantom_units.xml").write_text(phantom_units_xml(), encoding="utf-8")
    (data_dir / "phantom_actions.xml").write_text(phantom_actions_xml(), encoding="utf-8")
    (data_dir / "phantom_projectiles.xml").write_text(phantom_projectiles_xml(), encoding="utf-8")
    (data_dir / "phantom_overlays.xml").write_text(phantom_overlays_xml(), encoding="utf-8")
    (data_dir / "phantom_particles.xml").write_text(phantom_particles_xml(), encoding="utf-8")
    (data_dir / "phantom_sounds.xml").write_text(phantom_sounds_xml(), encoding="utf-8")
    (gpl_dir / "Phantom_Building_Data.dat").write_text(phantom_building_data(), encoding="utf-8")
    (gpl_dir / "Phantom_Hero_Data.dat").write_text(phantom_hero_data(), encoding="utf-8")
    (gpl_dir / "Phantom_Items_Data.dat").write_text(phantom_items_data(), encoding="utf-8")
    (gpl_dir / "Phantom.gpl").write_text(phantom_gpl(), encoding="utf-8")
    (gpl_dir / "Phantom.gplproj").write_text(phantom_gplproj(), encoding="utf-8")
    (args.output_root / "PhantomGuildPoc.mmxml").write_text(mod_xml(), encoding="utf-8")
    return 0


def phantom_equipment_item_specs() -> list[tuple[int, str, str, str, str]]:
    specs: list[tuple[int, str, str, str, str]] = []
    for family in ("cowl", "icerod"):
        for struct_level in range(4):
            for magic_level in range(4):
                combination = struct_level * 4 + magic_level
                if family == "cowl":
                    item_id = (
                        PHANTOM_COWL_BASE_ITEM_ID
                        if combination == 0
                        else PHANTOM_COWL_VARIANT_FIRST_ID + combination - 1
                    )
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
                    image_id = "PHIC"
                else:
                    item_id = (
                        PHANTOM_ICEROD_BASE_ITEM_ID
                        if combination == 0
                        else PHANTOM_ICEROD_VARIANT_FIRST_ID + combination - 1
                    )
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
                    image_id = "PHIR"
                specs.append((item_id, agent_name, attribute_name, display_name, image_id))
    return sorted(specs)


def phantom_equipment_units_xml() -> str:
    descriptions: list[str] = []
    for _, agent_name, attribute_name, display_name, image_id in phantom_equipment_item_specs():
        descriptions.append(
            f"""\t<Description type="Unit" subType="Character" ID="{agent_name}" Name="{agent_name}" Description="{display_name}">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="8"/>
\t\t\t<ImageIDBase value="{image_id}"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="APb1"/>
\t\t\t<MaxHP value="10"/>
\t\t\t<RecruitDelay value="10000"/>
\t\t\t<Flags value="NotFlaggable"/>
\t\t\t<Flags value="NotSpellTarget"/>
\t\t\t<Flags value="IsInventoryItem"/>
\t\t\t<HelpID value="h020"/>
\t\t\t<Attributes>
\t\t\t\t<Attribute ID="CanDropItem" Value="0"/>
\t\t\t\t<Attribute ID="{attribute_name}" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>"""
        )
    return "\n".join(descriptions)


def phantom_units_xml() -> str:
    return f"""<Majesty>
\t<Description type="Unit" subType="Character" ID="PHM1" Name="Phantom" Description="Phantom">
\t\t<Engine version="1">
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="6"/>
\t\t\t<ImageIDBase value="PHM1"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="Class 1"/>
\t\t\t<DefaultSound value="Phantom"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="AP20"/>
\t\t\t<Cost value="1"/>
\t\t\t<Experience value="2000"/>
\t\t\t<MaxHP value="18"/>
\t\t\t<SightRange value="240"/>
\t\t\t<Speed value="4"/>
\t\t\t<AttackRange min="1" max="240"/>
\t\t\t<Vitality value="8"/>
\t\t\t<Artifice value="8"/>
\t\t\t<WillPower value="22"/>
\t\t\t<Intelligence value="24"/>
\t\t\t<Strength value="8"/>
\t\t\t<MagicResistance value="25"/>
\t\t\t<Attack value="30"/>
\t\t\t<Parry value="20"/>
\t\t\t<Dodge value="25"/>
\t\t\t<WeaponBasicDamage value="0"/>
\t\t\t<ArmorBasicDamage value="0"/>
\t\t\t<RecruitDelay value="1000"/>
\t\t\t<PrimaryStat value="2"/>
\t\t\t<NameGenType value="NM16"/>
\t\t\t<Flags value="Heals"/>
\t\t\t<Flags value="HasHPBar"/>
\t\t\t<Flags value="CanHighlight"/>
\t\t\t<HelpID value="h020"/>
\t\t\t<AllowedWeapon value="Staff"/>
\t\t\t<AllowedArmor value="Leather"/>
\t\t\t<AllowedSpells>
\t\t\t\t<Spell ID="0" Value="ice_lance"/>
\t\t\t\t<Spell ID="1" Value="frost_armor"/>
\t\t\t\t<Spell ID="2" Value="icy_touch"/>
\t\t\t\t<Spell ID="3" Value="call_to_grave"/>
\t\t\t\t<Spell ID="4" Value="eternal_soul"/>
\t\t\t\t<Spell ID="5" Value="endless_winter"/>
\t\t\t</AllowedSpells>
\t\t</Game>
\t</Description>
{phantom_equipment_units_xml()}
\t<Description type="Unit" subType="Character" ID="FrostArmorBonus" Name="FrostArmorBonus" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="8"/>
\t\t\t<ImageIDBase value="PHIC"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="APb1"/>
\t\t\t<MaxHP value="10"/>
\t\t\t<RecruitDelay value="10000"/>
\t\t\t<Flags value="NotFlaggable"/>
\t\t\t<Flags value="NotSpellTarget"/>
\t\t\t<Flags value="IsInventoryItem"/>
\t\t\t<HelpID value="h020"/>
\t\t\t<Attributes>
\t\t\t\t<Attribute ID="CanDropItem" Value="0"/>
\t\t\t\t<Attribute ID="Phantom_Item_FrostArmorBonus" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Character" ID="PHW1" Name="endless_winter_storm" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="12"/>
\t\t\t<ImageIDBase value="PHw6"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Endless_Winter_Unit_Created"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="Class 1"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<RecruitDelay value="10000"/>
\t\t\t<Flags value="NotInMiniMap"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Building" ID="MBPhantomGuild" Name="Phantoms_Haunt" Description="Phantoms Haunt">
\t\t<Engine version="1">
\t\t\t<Info value="BlockGround"/>
\t\t\t<Info value="BlockFlying"/>
\t\t\t<Info value="ModifyTerrainTextureOnPlacement"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="1"/>
\t\t\t<ImageIDBase value="PHG1"/>
\t\t\t<DefaultSound value="Phantoms_Haunt"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="{PHANTOM_GUILD_DIALOG_ID.decode('ascii')}"/>
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
\t\t\t<HelpID value="hP34"/>
\t\t\t<Produces>
\t\t\t\t<Unit ID="Phantom"/>
\t\t\t</Produces>
\t\t</Game>
\t</Description>
</Majesty>
"""


def phantom_actions_xml() -> str:
    return """<Majesty>
\t<Description type="Action" subType="Standard" ID="WRa2" Name="ice_lance" Description="Ice Lance">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="Energy_Blast"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Ice_Lance_Cast"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="3000"/>
\t\t\t<TimeoutDuration value="2500"/>
\t\t\t<SpellType value="Attack"/>
\t\t\t<CharacterLevel value="1"/>
\t\t\t<SpellRank value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa3" Name="frost_armor" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="FireShield"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Frost_Armor_Begin"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="21000"/>
\t\t\t<TimeoutDuration value="1000"/>
\t\t\t<SpellType value="CombatUtility"/>
\t\t\t<CharacterLevel value="3"/>
\t\t\t<SpellRank value="3"/>
\t\t\t<ValidationScript value="Frost_Armor_Check"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa4" Name="icy_touch" Description="Icy Touch">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Attack"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="Fire_Blast"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Icy_Touch_Cast"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<TimeoutDuration value="5000"/>
\t\t\t<SpellType value="Attack"/>
\t\t\t<CharacterLevel value="4"/>
\t\t\t<SpellRank value="3"/>
\t\t\t<ValidationScript value="Icy_Touch_Check"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa5" Name="endless_winter" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Endless_Winter_Hit"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="21000"/>
\t\t\t<TimeoutDuration value="55000"/>
\t\t\t<SpellType value="Attack"/>
\t\t\t<CharacterLevel value="7"/>
\t\t\t<SpellRank value="7"/>
\t\t\t<ValidationScript value="Endless_Winter_Check"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa6" Name="call_to_grave" Description="Call to Grave">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Call_To_Grave_Effect"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="1200"/>
\t\t\t<TimeoutDuration value="5000"/>
\t\t\t<SpellType value="4"/>
\t\t\t<CharacterLevel value="5"/>
\t\t\t<SpellRank value="4"/>
\t\t\t<ValidationScript value="Call_To_Grave_Check"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa7" Name="eternal_soul" Description="Eternal Soul">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="Shield_of_Light"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Eternal_Soul_Begin"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="25000"/>
\t\t\t<TimeoutDuration value="30000"/>
\t\t\t<SpellType value="Attack"/>
\t\t\t<CharacterLevel value="6"/>
\t\t\t<SpellRank value="5"/>
\t\t</Game>
\t</Description>
</Majesty>
"""


def phantom_projectiles_xml() -> str:
    return """<Majesty>
\t<Description type="Unit" subType="Projectile" ID="PHp1" Name="ice_lance_missile" Description="Ice Lance">
\t\t<Engine version="1">
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHp1"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Ice_Lance_Hit"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="dragon_missile"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t</Description>
\t<Description type="Unit" subType="Projectile" ID="PHW2" Name="endless_winter_missile" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHw3"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Endless_Winter_Inner_Missile_Hit"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="fast missile"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t</Description>
\t<Description type="Unit" subType="Projectile" ID="PHW7" Name="endless_winter_missile_middle" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHw3"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Endless_Winter_Middle_Missile_Hit"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="fast missile"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t</Description>
\t<Description type="Unit" subType="Projectile" ID="PHW8" Name="endless_winter_missile_outer" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHw3"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Endless_Winter_Outer_Missile_Hit"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="fast missile"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t</Description>
</Majesty>
"""


def phantom_overlays_xml() -> str:
    return """<Majesty>
\t<Description type="Unit" subType="Overlay" ID="PHo3" Name="ice_lance_hit_effector" Description="Ice Lance Hit">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHo3"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHg1" Name="gravechill_icon" Description="Gravechill">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHg1"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHg2" Name="gravechill_hit_effector" Description="Gravechill Hit">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHg2"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo1" Name="frost_armor_effector" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHf1"/>
\t\t\t<DefaultSound value="FireShield"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo2" Name="frost_armor_icon" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Info value="NotVisibleInISOView"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHo3"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo6" Name="frost_armor_spent" Description="Frost Armor Spent">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Info value="NotVisibleInISOView"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHo3"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo7" Name="frost_armor_frozen_timer" Description="Frozen">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Info value="NotVisibleInISOView"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHo3"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Frost_Armor_Frozen_End"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo8" Name="frost_armor_frozen_small" Description="Frozen">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHf2"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo9" Name="frost_armor_frozen_medium" Description="Frozen">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHf3"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PH10" Name="frost_armor_frozen_large" Description="Frozen">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHf4"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo4" Name="ice_lance_chill_icon" Description="Chilled">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHo4"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PH11" Name="ice_lance_empowered_chill_icon" Description="Empowered Chill">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHc3"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHc2" Name="call_to_grave_effector" Description="Call to Grave">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHc2"/>
\t\t\t<AttachmentPointID value="3"/>
\t\t\t<DefaultSound value="Teleport"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHe1" Name="eternal_soul_icon" Description="Eternal Soul">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHe1"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Eternal_Soul_End"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHe2" Name="eternal_soul_effector" Description="Eternal Soul">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHe2"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHW3" Name="endless_winter_hit_effector" Description="Endless Winter Hit">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHw2"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHW6" Name="endless_winter_vortex_effector" Description="Endless Winter Vortex">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="PHw1"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
</Majesty>
"""


def phantom_particles_xml() -> str:
    return """<Majesty>
\t<Description type="Unit" subType="ParticleSystem" ID="PHW4" Name="endless_winter_storm_attachment" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Info value="NoGPLAgent"/>
\t\t\t<Menu value="13"/>
\t\t\t<ImageIDBase value="PHw4"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t\t<InitialParticles value="1"/>
\t\t\t<MaxParticles value="10"/>
\t\t\t<Bounds min="-1000.0, -1000.0, -1000.0" max="1000.0, 1000.0, 1000.0"/>
\t\t\t<Emitter>
\t\t\t\t<Type value="Area"/>
\t\t\t\t<Type value="Column"/>
\t\t\t\t<Velocity value="0.0, 0.0, 0.0"/>
\t\t\t\t<Acceleration value="0.0, 0.0, 0.0"/>
\t\t\t\t<Offset value="0.0, 0.0, 0.0"/>
\t\t\t\t<SurfaceNormal value="0.0, 0.0, 1.0"/>
\t\t\t\t<Radius value="0.05"/>
\t\t\t\t<RadiusVariance value="0.5"/>
\t\t\t\t<DirectionVariance value="90.0"/>
\t\t\t\t<Rate value="8.0"/>
\t\t\t\t<Lifespan value="4294967295"/>
\t\t\t\t<Recycle value="0"/>
\t\t\t</Emitter>
\t\t\t<Particle>
\t\t\t\t<Lifespan value="1000"/>
\t\t\t\t<LifespanVariance value="0.4"/>
\t\t\t\t<InitialSpeed value="3.0"/>
\t\t\t\t<InitialSpeedVariance value="0.4"/>
\t\t\t\t<Gravity value="0.0, 0.0, 0.0"/>
\t\t\t\t<BirthColor value="0.0, 0.0, 0.0, 0.0"/>
\t\t\t\t<MidlifeColor value="0.0, 0.0, 0.0, 1.0"/>
\t\t\t\t<DeathColor value="0.0, 0.0, 0.0, 0.0"/>
\t\t\t\t<BirthSize value="0.1"/>
\t\t\t\t<MaxSize value="7.0"/>
\t\t\t\t<DeathSize value="0.2"/>
\t\t\t\t<SizeTime in="0.5" out="0.3"/>
\t\t\t\t<FadeTime in="0.1" out="0.5"/>
\t\t\t\t<JitterOrientation value="0.0, 0.0, 0.0"/>
\t\t\t\t<JitterDisplacement value="0.0, 0.0, 0.0"/>
\t\t\t\t<BirthSpinRate value="0.0"/>
\t\t\t\t<MidlifeSpinRate value="0.0"/>
\t\t\t\t<DeathSpinRate value="0.0"/>
\t\t\t</Particle>
\t\t</Engine>
\t</Description>
\t<Description type="Unit" subType="ParticleSystem" ID="PHW5" Name="endless_winter_missile_attachment" Description="Endless Winter">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Info value="NoGPLAgent"/>
\t\t\t<Menu value="13"/>
\t\t\t<ImageIDBase value="PHw5"/>
\t\t\t<AttachmentPointID value="2"/>
\t\t\t<DefaultSound value="0"/>
\t\t\t<InitialParticles value="2"/>
\t\t\t<MaxParticles value="8"/>
\t\t\t<Bounds min="-1000.0, -1000.0, -1000.0" max="1000.0, 1000.0, 1000.0"/>
\t\t\t<Emitter>
\t\t\t\t<Type value="Area"/>
\t\t\t\t<Type value="Column"/>
\t\t\t\t<Velocity value="0.0, 0.0, 0.0"/>
\t\t\t\t<Acceleration value="0.0, 0.0, 0.0"/>
\t\t\t\t<Offset value="0.0, 0.0, 0.0"/>
\t\t\t\t<SurfaceNormal value="0.0, 0.0, 1.0"/>
\t\t\t\t<Radius value="0.04"/>
\t\t\t\t<RadiusVariance value="0.0"/>
\t\t\t\t<DirectionVariance value="360.0"/>
\t\t\t\t<Rate value="18.0"/>
\t\t\t\t<Lifespan value="4294967295"/>
\t\t\t\t<Recycle value="0"/>
\t\t\t</Emitter>
\t\t\t<Particle>
\t\t\t\t<Lifespan value="300"/>
\t\t\t\t<LifespanVariance value="0.5"/>
\t\t\t\t<InitialSpeed value="4.0"/>
\t\t\t\t<InitialSpeedVariance value="0.4"/>
\t\t\t\t<Gravity value="0.0, 0.0, 0.0"/>
\t\t\t\t<BirthColor value="0.0, 0.0, 0.0, 0.0"/>
\t\t\t\t<MidlifeColor value="0.0, 0.0, 0.0, 1.0"/>
\t\t\t\t<DeathColor value="0.0, 0.0, 0.0, 0.0"/>
\t\t\t\t<BirthSize value="0.1"/>
\t\t\t\t<MaxSize value="7.0"/>
\t\t\t\t<DeathSize value="0.2"/>
\t\t\t\t<SizeTime in="0.5" out="0.3"/>
\t\t\t\t<FadeTime in="0.1" out="0.2"/>
\t\t\t\t<JitterOrientation value="0.0, 0.0, 0.0"/>
\t\t\t\t<JitterDisplacement value="0.0, 0.0, 0.0"/>
\t\t\t\t<BirthSpinRate value="0.0"/>
\t\t\t\t<MidlifeSpinRate value="0.0"/>
\t\t\t\t<DeathSpinRate value="0.0"/>
\t\t\t</Particle>
\t\t</Engine>
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
\t\t\t<Phase ID="VFX_GAIN_LEVEL">
\t\t\t\t<Wave value="PHS1"/>
\t\t\t\t<Group value="Up-Level_Group"/>
\t\t\t</Phase>
\t\t\t<Phase ID="VFX_LEVEL_10">
\t\t\t\t<Wave value="PHS1"/>
\t\t\t\t<DistanceModifier value="10001.0"/>
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
\t<Description type="Sound" subType="Standard" ID="PH02" Name="Phantoms_Haunt">
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
\t\t(attack_action do_nothing)
\t\t(Cast_Action Basic_Cast)
\t\t(Pickup_Action Basic_Pickup)
\t\t(PrimaryStat ATTRIB_Intelligence)
\t\t(Friend\txx)
\t\t(attacktype 1)
\t\t(castingrange 190)
\t\t(PercentageHPRetreat 0)
\t\t(enemy_estimation 0.1)
\t\t(self_estimation 10.0)
\t\t(Loyalty 55)
\t\t(Greed 12)
\t\t(Luck 12)
\t\t(Upgrade_Armor_Chance\t100)
\t\t(Upgrade_Weapon_Chance\t100)
\t\t(Poison_Weapon_Chance\t0)
\t\t(evaluationScript\teval_enemies_nearby)
\t\t(activeScript\tPhantom_tree)
\t\t(basicscript\tPhantom_tree)
\t\t(StartingScript\tPhantom_tree)
\t\t(birthScript\tPhantom_birth)
\t\t(IGdeathscript\tPhantom_death)
\t}
[end]

[endless_winter_storm]
\t{Spell
\t\t(type\t\tspell)
\t\t(subtype\tspell)
\t\t(title\t\tendless_winter_storm)
\t\t(activeScript\tEndless_Winter_Active)
\t}
[end]
"""


def phantom_items_data() -> str:
    entries: list[str] = []
    for _, agent_name, _, _, _ in phantom_equipment_item_specs():
        entries.append(
            f"""[{agent_name}]
\t{{Special_Item
\t\t(type \t\tSpecial_Item)
\t\t(Title\t\t{agent_name})
\t}}
[end]
"""
        )
    entries.append(
        """[FrostArmorBonus]
\t{Special_Item
\t\t(type \t\tSpecial_Item)
\t\t(Title\t\tFrostArmorBonus)
\t}
[end]
"""
    )
    return "\n".join(entries)


def phantom_building_data() -> str:
    return """[Phantoms_Haunt]
\t{Guild
\t\t(type building)
\t\t(subtype Guild)
\t\t(title Phantoms_Haunt)
\t\t(Level 1)
\t\t(max_level 1)
\t\t(member_title Phantom)
\t\t(member_basicscript Phantom_tree)
\t\t(max_members 4)
\t\t(Lived_In_Script Phantom_Lived_In)
\t\t(Sleep_for 30000)
\t\t(birthscript basic_birth)
\t\t(birthScript2 Guild_Birth)
\t\t(IGdeathscript guild_destroyed_a)
\t\t(upgradescript basic_upgrade)
\t\t(Armor_Physical_Base 10)
\t\t(Armor_Magical_Base 10)
\t\t(IntentExt PHANTOMSGUILD)
\t}
[end]

"""


def phantom_gpl() -> str:
    item_expressions = "\n".join(
        f"expression #{attribute_name} {item_id}"
        for item_id, _, attribute_name, _, _ in phantom_equipment_item_specs()
    )
    item_expressions += (
        f"\nexpression #Phantom_Item_FrostArmorBonus {PHANTOM_FROST_ARMOR_ITEM_ID}\n"
    )
    item_expressions += "\nexpression #Phantom_Icy_Touch_Range 24\n"
    item_expressions += "\nexpression #Phantom_Call_To_Grave_Range 50000\n"
    item_expressions += "\nexpression #Phantom_Call_To_Grave_Min_Distance 500\n"
    item_expressions += "\nexpression #Phantom_Ice_Lance_Confidence 10\n"
    item_expressions += "expression #Phantom_Frost_Armor_Confidence 10\n"
    item_expressions += "expression #Phantom_Icy_Touch_Confidence 25\n"
    item_expressions += "expression #Phantom_Call_To_Grave_Confidence 10\n"
    item_expressions += "expression #Phantom_Eternal_Soul_Confidence 25\n"
    item_expressions += "expression #Phantom_Endless_Winter_Confidence 30\n"
    return item_expressions + """

function spell_extra_value(agent thisagent) is integer

declare
\tinteger value;

begin
\tif ($isspellavailable(thisagent,"energy_blast",1))
\t\tvalue += 10;

\tif ($isspellavailable(thisagent,"fire_blast",1))
\t\tvalue += 30;

\tif ($isspellavailable(thisagent,"fire_ball",1))
\t\tvalue += 30;

\tif ($isspellavailable(thisagent,"teleport",1))
\t\tvalue += 5;

\tif ($isspellavailable(thisagent,"resist_magic",1))
\t\tvalue += 5;

\tif ($isspellavailable(thisagent,"meteor_storm",1))
\t\tvalue += 30;

\tif ($isspellavailable(thisagent,"drain_life",1))
\t\tvalue += 30;

\tif ($isspellavailable(thisagent,"sun_scorch",1))
\t\tvalue += 30;

\tif (thisagent's "Title" == "Phantom")
\t\tbegin
\t\t\tif ($isspellavailable(thisagent,"ice_lance",1))
\t\t\t\tvalue += #Phantom_Ice_Lance_Confidence;

\t\t\tif ($isspellavailable(thisagent,"frost_armor",1))
\t\t\t\tvalue += #Phantom_Frost_Armor_Confidence;

\t\t\tif ($isspellavailable(thisagent,"icy_touch",1))
\t\t\t\tvalue += #Phantom_Icy_Touch_Confidence;

\t\t\tif ($isspellavailable(thisagent,"call_to_grave",1))
\t\t\t\tvalue += #Phantom_Call_To_Grave_Confidence;

\t\t\tif ($isspellavailable(thisagent,"eternal_soul",1))
\t\t\t\tvalue += #Phantom_Eternal_Soul_Confidence;

\t\t\tif ($isspellavailable(thisagent,"endless_winter",1))
\t\t\t\tvalue += #Phantom_Endless_Winter_Confidence;
\t\tend

\treturn value;
end

function DEAL_DEMON()

declare
\tagent AIRootAgent,palace,guild,lair,phantoms_haunt,elf_guild,agrela_temple;
\tlist guilds,palaces,lairs;

begin
\tAIRootAgent = $RetrieveAgent ("GplAIRoot");
\tAIRootAgent's "Quest_Number" = #QNumber_Deal_Demon;

\tpalaces = $ListPalaces();
\tpalace = $listmember(palaces,1);

\t$Setup_Quest_Music (AiRootAgent);

\t$ListObjects (Palace, "Building", -1, Guilds, #NotMyPlayer, #NoHiddenMap);
\tGuilds = $ListSubtypes (Guilds, "Guild");

\t$setup_random_treasure(30, #default_spawn_treasure_dist);

\tForeach Guild in Guilds do
\t\tbegin
\t\t\tGuild's "SpecialScript" = $Hero_Generator;
\t\t\t$NewThread( Guild's "SpecialScript", 60000 + $randomnumber(60000), Guild );
\t\tend

\tphantoms_haunt = $SpawnUnit(palace, "Phantoms_Haunt", $RandomCoord(palace, 275, 475), "MaxHP");

\telf_guild = $SpawnUnit(palace, "Elven_Bungalow", $RandomCoord(palace, 275, 475), "MaxHP");

\tagrela_temple = $SpawnUnit(palace, "Temple_Agrela1", $RandomCoord(palace, 275, 475), "MaxHP");

\t$listobjects(palace,"lair",-1,lairs,#NoHiddenMap);
\tforeach lair in lairs do
\t\tbegin
\t\t\tif (lair's "special_spawn_type" == "vampire")
\t\t\t\tlair's "special_spawn_type" = "werewolf";
\t\tend

\tAIRootAgent's "VictoryCondition" = $Demon_victory;
\t$NewThread( AIRootAgent's "VictoryCondition", #VictoryCondition_callback_frequency );
\tAIRootAgent's "VictoryCondition2" = $Demon_victory2;
\t$newThread( AIRootAgent's "VictoryCondition2", 1200000);
end

Function Potion_Check(agent thisagent, list potentials) is boolean

Declare
\tinteger intel_roll;

Begin
\tIf (thisagent's "Title" == "Phantom")
\t\treturn False;

\t$DebugOut("Should I buy some Healing Potions?");

\tIf ($GetAttribute(thisagent, #ATTRIB_NumHealingPotions) >= #Max_Heal_Potions)
\t\treturn False;

\tIf ($Total_Gold(thisagent) < #Heal_Potion_Price)
\t\treturn False;

\tpotentials = $List_Attribs(potentials, #ATTRIB_ResearchHealingPotions);

\tIf ($ListSize(potentials) == 0)
\t\treturn False;

\tintel_roll = $RandomNumber(30) + 1;
\tIf ($GetAttribute(thisagent, #ATTRIB_Intelligence) > intel_roll)
\t\tbegin
\t\t\tthisagent's "TaskName" = "visiting";
\t\t\tthisagent's "Target" = $Loyalty_Mod_Pick_Closest(thisagent, potentials);
\t\t\t$SpecifyIntent(thisagent, #Intent_purchasing_heal_potions);
\t\t\treturn True;
\t\tend

\treturn False;
End

Function Bazaar_Item_Check ( agent ThisAgent, integer item, list potentials, integer Item_cost ) is boolean

Declare
\tinteger Intel_Roll;

Begin
\t$DebugOut ( "Should I buy item#", item, "?" );

\tIf (ThisAgent's "Title" == "Phantom" && item == #Bazaar_Item_Four)
\t\treturn False;

\tIf ((thisagent's "title" == "cultist") && (item == #Bazaar_Item_Six))
\t\treturn False;

\tIf (item == #Bazaar_Item_Two)
\t\tIf ((thisagent's "title" != "ranger") && (thisagent's "title" != "rogue") && (thisagent's "title" != "elf"))
\t\t\treturn False;

\tIf ($AgentHasInventoryItem(item, thisagent))
\t\tbegin
\t\t\t$DebugOut ( "I already have item #", item, ", so I dont need one." );
\t\t\treturn False;
\t\tend

\tIf ($Total_Gold(ThisAgent) < Item_Cost)
\t\tbegin
\t\t\t$DebugOut ("I don't have enough money for item #", item, "!");
\t\t\treturn False;
\t\tend

\tIntel_Roll = $RandomNumber (30) + 1;

\tIf ($GetAttribute(ThisAgent, #ATTRIB_Intelligence) > Intel_Roll)
\t\tbegin
\t\t\tThisAgent's "TaskName" = $Get_Bazaar_Task_Name(item);
\t\t\tThisAgent's "Target" = $Loyalty_Mod_Pick_Closest(ThisAgent, Potentials);
\t\t\t$DebugOut ("Yes!");
\t\t\t$SetBuyerIntent(ThisAgent, item);
\t\t\treturn True;
\t\tend

\t$DebugOut ("No!");
\treturn False;
End

Function Heal( Agent ThisAgent, Agent Target, integer Healing_Amount )

Declare

Begin
\tIf (Target's "Title" == "Phantom")
\t\tIf (ThisAgent's "Title" != "Priestess")
\t\t\treturn;

\t$Healing_Shared(Target, Healing_Amount);
End

Function Player_Heal( Agent Target, integer Healing_Amount )

Declare

Begin
\tIf (Target's "Title" == "Phantom")
\t\treturn;

\t$Healing_Shared(Target, Healing_Amount);
End

function Regeneration_elixer_effect ( agent thisagent, agent target )

declare

begin
\tIf ($IsDead(thisagent))
\t\treturn;

\tIf (thisagent's "Title" == "Phantom")
\t\tbegin
\t\t\t$DeleteInventoryItem(#Bazaar_Item_Four, ThisAgent);
\t\t\t$ForgetSpell(ThisAgent, "Regeneration_Elixer");
\t\t\treturn;
\t\tend

\t$CreateEffector(thisagent, "Regeneration_elixer_effector", 0);
\t$CreateEffector(
\t\tthisagent,
\t\t"Regeneration_elixer_icon",
\t\t$GetSpellAttribute("Regeneration_Elixer", "effector_duration")
\t);
\t$AdjustAttribute(thisagent, #ATTRIB_HealingRateModifier, -5);
\t$SetAttribute(thisagent, #ATTRIB_HasEffectRegeneration, 1);

\t$DeleteInventoryItem(#Bazaar_Item_Four, ThisAgent);
\t$ForgetSpell(ThisAgent, "Regeneration_Elixer");
end

function Healing_Wind ()

declare
\tagent palace,hero;
\tlist heroes;

begin
\tpalace = $GetPlayerOnePalace();

\t$ListObjects(
\t\tpalace,
\t\t"hero",
\t\t-1,
\t\theroes,
\t\t#CheckSubTypes,
\t\t"hero",
\t\t#MyPlayer,
\t\t#NoHiddenMap,
\t\t#InsideOtherUnits
\t);

\tForeach hero in heroes do
\t\tbegin
\t\t\tIf (hero's "Title" != "Phantom")
\t\t\t\tIf ($IsDead(hero) == False)
\t\t\t\t\tIf ($GetAttribute(hero, #ATTRIB_HasEffectRegeneration) != 1)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t$CreateEffector(hero, "Regeneration_elixer_effector", 0);
\t\t\t\t\t\t\t$CreateEffector(hero, "Regeneration_elixer_icon", 120000);
\t\t\t\t\t\t\t$AdjustAttribute(hero, #ATTRIB_HealingRateModifier, -3);
\t\t\t\t\t\t\t$SetAttribute(hero, #ATTRIB_HasEffectRegeneration, 1);
\t\t\t\t\t\tend
\t\tend
end

Function Eval_For_Healing(agent ThisAgent, integer Distance) is Agent

Declare
\tlist Heroes,Injured_Heroes;
\tagent Hero,BestAgent;
\tinteger Percent_HP,Temp_Distance,Temp_Score,Best_Score;

Begin
\t$ListObjects(ThisAgent, "Hero", Distance, Heroes);

\tIf ($ListSize(Heroes) > 0)
\t\tbegin
\t\t\tForeach Hero in Heroes do
\t\t\t\tbegin
\t\t\t\t\tIf (Hero's "Title" != "Phantom")
\t\t\t\t\t\tIf ($GetAttribute(Hero, #ATTRIB_HP) < $GetAttribute(Hero, #ATTRIB_MaxHP))
\t\t\t\t\t\t\tIf ($GetPlayerTeamNumber(Hero) == $GetPlayerTeamNumber(ThisAgent))
\t\t\t\t\t\t\t\tInjured_Heroes << Hero;
\t\t\t\t\t\t\tElse If ($RandomNumber(100) > ThisAgent's "Loyalty")
\t\t\t\t\t\t\t\tInjured_Heroes << Hero;
\t\t\t\tend

\t\t\tIf ($ListSize(Injured_Heroes) > 0)
\t\t\t\tbegin
\t\t\t\t\tBest_Score = 5000000;
\t\t\t\t\tForeach Hero in Injured_Heroes do
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tTemp_Distance = $DistanceBetweenAgents(ThisAgent, Hero);
\t\t\t\t\t\t\tPercent_HP = ($GetAttribute(Hero, #ATTRIB_HP) * 100) /
\t\t\t\t\t\t\t\t$GetAttribute(Hero, #ATTRIB_MaxHP);
\t\t\t\t\t\t\tTemp_Score = (Temp_Distance / 10) * Percent_HP;
\t\t\t\t\t\t\tIf (Temp_Score < Best_Score)
\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\tBest_Score = Temp_Score;
\t\t\t\t\t\t\t\t\tBestAgent = Hero;
\t\t\t\t\t\t\t\tend
\t\t\t\t\t\tend

\t\t\t\t\tIf (Best_Score < ($GetAttribute(ThisAgent, #ATTRIB_Intelligence) * 150))
\t\t\t\t\t\treturn BestAgent;
\t\t\t\tend
\t\tend

\treturn $NullAgent();
End

function Healer_Heal_Effect(agent thisagent, agent target)

declare
\tagent AIRootAgent;
\tinteger Healing;

begin
\tIf ($isdead(target))
\t\treturn;

\tIf (target's "Title" == "Phantom")
\t\tbegin
\t\t\t$Reset_Tasks(thisagent);
\t\t\treturn;
\t\tend

\tIf ($isdead(thisagent) == False)
\t\tbegin
\t\t\t$CreateEffector(target, "healer_healing_effector", 0);
\t\t\tAIRootAgent = $RetrieveAgent("GplAIRoot");

\t\t\tIf ($HasAttribute("Deathmatch_Rules", AIRootAgent))
\t\t\t\tbegin
\t\t\t\t\tIf (AIRootAgent's "Deathmatch_Rules" == True)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tHealing = #Deathmatch_Agrella_Healing_Multiplier *
\t\t\t\t\t\t\t\t$GetAttribute(ThisAgent, #ATTRIB_ExperienceLevel);
\t\t\t\t\t\t\tIf (Healing > #Deathmatch_Agrella_Healing_Cap)
\t\t\t\t\t\t\t\tHealing = #Deathmatch_Agrella_Healing_Cap;
\t\t\t\t\t\tend
\t\t\t\t\tElse
\t\t\t\t\t\tHealing = #Agrella_Healing_Multiplier *
\t\t\t\t\t\t\t$GetAttribute(ThisAgent, #ATTRIB_ExperienceLevel);
\t\t\t\tend
\t\t\tElse
\t\t\t\tHealing = #Agrella_Healing_Multiplier *
\t\t\t\t\t$GetAttribute(ThisAgent, #ATTRIB_ExperienceLevel);

\t\t\t$Heal(ThisAgent, Target, Healing);
\t\t\tIf (Target's "BackScript" == $Use_Building_Safe)
\t\t\t\tIf ($haslowHP(Target) == False)
\t\t\t\t\t$Reset_Tasks(Target);
\t\tend
end

function Drain_Life_Hit(agent thisagent, agent target)

declare
\tinteger Effector_Duration,Healing_Needed,Temp_Healing_Needed,HP,MaxHP;
\tlist Phantoms,My_Skeletons;
\tagent Phantom,Best_Phantom,Skeleton,Best_Skeleton;

begin
\tIf ($isdead(target))
\t\treturn;
\tIf ($isdead(thisagent))
\t\treturn;

\tEffector_Duration = $GetSpellAttribute("Drain_Life", "effector_duration");

\tIf (Target's "Type" != "Building" && Target's "Type" != "Lair")
\t\tbegin
\t\t\tIf ($GetAttribute(ThisAgent, #ATTRIB_HP) < $GetAttribute(ThisAgent, #ATTRIB_MaxHP))
\t\t\t\tbegin
\t\t\t\t\t$CreateEffector(ThisAgent, "life_drain_effector2", Effector_Duration);
\t\t\t\t\t$Heal(ThisAgent, ThisAgent, 5);
\t\t\t\tend
\t\t\tElse
\t\t\t\tbegin
\t\t\t\t\tHealing_Needed = 0;
\t\t\t\t\t$ListObjects(
\t\t\t\t\t\tThisAgent,
\t\t\t\t\t\t"Hero",
\t\t\t\t\t\t$GetAttribute(ThisAgent, #ATTRIB_SightRange),
\t\t\t\t\t\tPhantoms
\t\t\t\t\t);
\t\t\t\t\tPhantoms = $ListTitles(Phantoms, "Phantom");

\t\t\t\t\tForeach Phantom in Phantoms do
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tIf ($GetPlayerTeamNumber(Phantom) == $GetPlayerTeamNumber(ThisAgent))
\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\tHP = $GetAttribute(Phantom, #ATTRIB_HP);
\t\t\t\t\t\t\t\t\tMaxHP = $GetAttribute(Phantom, #ATTRIB_MaxHP);
\t\t\t\t\t\t\t\t\tIf (HP < MaxHP)
\t\t\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\t\t\tTemp_Healing_Needed = MaxHP - HP;
\t\t\t\t\t\t\t\t\t\t\tIf (Temp_Healing_Needed > Healing_Needed)
\t\t\t\t\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\t\t\t\t\tHealing_Needed = Temp_Healing_Needed;
\t\t\t\t\t\t\t\t\t\t\t\t\tBest_Phantom = Phantom;
\t\t\t\t\t\t\t\t\t\t\t\tend
\t\t\t\t\t\t\t\t\t\tend
\t\t\t\t\t\t\t\tend
\t\t\t\t\t\tend

\t\t\t\t\tIf ($IsValidGamePiece(Best_Phantom))
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t$CreateEffector(Best_Phantom, "life_drain_effector2", Effector_Duration);
\t\t\t\t\t\t\t$Heal(ThisAgent, Best_Phantom, 5);
\t\t\t\t\t\tend
\t\t\t\t\tElse
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tHealing_Needed = 0;
\t\t\t\t\t\t\t$ListObjects(
\t\t\t\t\t\t\t\tThisAgent,
\t\t\t\t\t\t\t\t"Hero",
\t\t\t\t\t\t\t\t$GetAttribute(ThisAgent, #ATTRIB_SightRange),
\t\t\t\t\t\t\t\tMy_Skeletons,
\t\t\t\t\t\t\t\t#CheckSubtypes,
\t\t\t\t\t\t\t\t"Controlled"
\t\t\t\t\t\t\t);
\t\t\t\t\t\t\tMy_Skeletons = $ListTitles(My_Skeletons, "Skeleton");

\t\t\t\t\t\t\tForeach Skeleton in My_Skeletons do
\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\tHP = $GetAttribute(Skeleton, #ATTRIB_HP);
\t\t\t\t\t\t\t\t\tMaxHP = $GetAttribute(Skeleton, #ATTRIB_MaxHP);
\t\t\t\t\t\t\t\t\tIf (HP < MaxHP)
\t\t\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\t\t\tTemp_Healing_Needed = MaxHP - HP;
\t\t\t\t\t\t\t\t\t\t\tIf (Temp_Healing_Needed > Healing_Needed)
\t\t\t\t\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\t\t\t\t\tHealing_Needed = Temp_Healing_Needed;
\t\t\t\t\t\t\t\t\t\t\t\t\tBest_Skeleton = Skeleton;
\t\t\t\t\t\t\t\t\t\t\t\tend
\t\t\t\t\t\t\t\t\t\tend
\t\t\t\t\t\t\t\tend

\t\t\t\t\t\t\tIf ($IsValidGamePiece(Best_Skeleton))
\t\t\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t\t\t$CreateEffector(Best_Skeleton, "life_drain_effector2", Effector_Duration);
\t\t\t\t\t\t\t\t\t$Heal(ThisAgent, Best_Skeleton, 5);
\t\t\t\t\t\t\t\tend
\t\t\t\t\t\tend
\t\t\t\tend
\t\tend

\t$CreateEffector(Target, "life_drain_effector", Effector_Duration);
\t$Spell_Attack(ThisAgent, Target, 15);
end

Function WizGuild_Check(agent ThisAgent, string Equipment, integer Bonus, list WizGuilds) is boolean

Declare
\tagent WizGuild;
\tlist Potentials;
\tinteger Intel_Roll,Gold_Needed;

Begin
\tIf (ThisAgent's "Title" == "Phantom" && Equipment == "Armor")
\t\tBonus = $Phantom_cowl_magic_level(ThisAgent);

\tIf (Bonus >= 3)
\t\treturn False;

\tIf (Bonus == 0)
\t\tGold_Needed = #Cost_Per_Magic_Enchantment1;
\tIf (Bonus == 1)
\t\tGold_Needed = #Cost_Per_Magic_Enchantment2;
\tIf (Bonus == 2)
\t\tGold_Needed = #Cost_Per_Magic_Enchantment3;

\tIf ($Total_Gold(ThisAgent) < Gold_Needed)
\t\treturn False;

\tIf ($ListSize(WizGuilds) == 0)
\t\treturn False;

\tForeach WizGuild in WizGuilds do
\t\tbegin
\t\t\tIf (WizGuild's "Level" > Bonus)
\t\t\t\tPotentials << WizGuild;
\t\tend

\tIf ($ListSize(Potentials) == 0)
\t\treturn False;

\tIntel_Roll = $RandomNumber(30) + 1;
\tIf ($GetAttribute(ThisAgent, #ATTRIB_Intelligence) > Intel_Roll)
\t\tbegin
\t\t\tIf (Equipment == "Weapon")
\t\t\t\tThisAgent's "Task_Number" = #ATTRIB_Weapon_Magic_Bonus;
\t\t\tElse
\t\t\t\tThisAgent's "Task_Number" = #ATTRIB_Armor_Magic_Bonus;

\t\t\tThisAgent's "Target" = $Loyalty_Mod_Pick_Closest(ThisAgent, Potentials);
\t\t\tThisAgent's "TaskName" = "visiting";
\t\t\treturn True;
\t\tend

\treturn False;
End

Function Obtain_Upgrade(agent ThisAgent)

Declare
\tagent ThisBuilding;
\tinteger What_To_Upgrade,Total_Gold,Gold,Upgrade,Mult,Old_Upgrade,Parry_Increase;

Begin
\tThisBuilding = ThisAgent's "Target";
\tTotal_Gold = $Total_Gold(ThisAgent);
\tWhat_To_Upgrade = ThisAgent's "Task_Number";
\tOld_Upgrade = $GetAttribute(ThisAgent, What_To_Upgrade);
\t$SetThreadInterval(ThisAgent's "ActiveScript", #Normal_Cycle);
\tMult = #armor_multiplier;

\tIf (What_To_Upgrade == #ATTRIB_Armor_Struct_Bonus)
\t\tbegin
\t\t\tIf (Old_Upgrade == 0 && Total_Gold >= #Cost_Per_Struct_Upgrade1 * Mult &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchArmorLevel_2) != 0)
\t\t\t\tbegin
\t\t\t\t\tTotal_Gold -= #Cost_Per_Struct_Upgrade1 * Mult;
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade1 * Mult;
\t\t\t\t\tUpgrade = 1;
\t\t\t\tend

\t\t\tIf (Old_Upgrade <= 1 && Total_Gold >= #Cost_Per_Struct_Upgrade2 * Mult &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchArmorLevel_3) != 0)
\t\t\t\tbegin
\t\t\t\t\tTotal_Gold -= #Cost_Per_Struct_Upgrade2 * Mult;
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade2 * Mult;
\t\t\t\t\tUpgrade = 2;
\t\t\t\tend

\t\t\tIf (Old_Upgrade <= 2 && Total_Gold >= #Cost_Per_Struct_Upgrade3 * Mult &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchArmorLevel_4) != 0)
\t\t\t\tbegin
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade3 * Mult;
\t\t\t\t\tUpgrade = 3;
\t\t\t\tend
\t\tend
\tElse
\t\tbegin
\t\t\tIf (Old_Upgrade == 0 && Total_Gold >= #Cost_Per_Struct_Upgrade1 &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchWeaponLevel_2) != 0)
\t\t\t\tbegin
\t\t\t\t\tTotal_Gold -= #Cost_Per_Struct_Upgrade1;
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade1;
\t\t\t\t\tUpgrade = 1;
\t\t\t\tend

\t\t\tIf (Old_Upgrade <= 1 && Total_Gold >= #Cost_Per_Struct_Upgrade2 &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchWeaponLevel_3) != 0)
\t\t\t\tbegin
\t\t\t\t\tTotal_Gold -= #Cost_Per_Struct_Upgrade2;
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade2;
\t\t\t\t\tUpgrade = 2;
\t\t\t\tend

\t\t\tIf (Old_Upgrade <= 2 && Total_Gold >= #Cost_Per_Struct_Upgrade3 &&
\t\t\t\t$GetAttribute(ThisBuilding, #ATTRIB_ResearchWeaponLevel_4) != 0)
\t\t\t\tbegin
\t\t\t\t\tGold += #Cost_Per_Struct_Upgrade3;
\t\t\t\t\tUpgrade = 3;
\t\t\t\tend
\t\tend

\tIf (Upgrade > 0)
\t\tbegin
\t\t\t$Spend_Gold(ThisAgent, ThisBuilding, Gold);
\t\t\t$SetAttribute(ThisAgent, What_To_Upgrade, Upgrade);

\t\t\tIf (ThisAgent's "Title" == "Phantom")
\t\t\t\tbegin
\t\t\t\t\tIf (What_To_Upgrade == #ATTRIB_Weapon_Struct_Bonus)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tParry_Increase = (Upgrade - Old_Upgrade) * 5;
\t\t\t\t\t\t\t$MagicalAdjustAttribute(ThisAgent, #ATTRIB_Parry, Parry_Increase);
\t\t\t\t\t\t\t$Phantom_sync_icerod_item(ThisAgent);
\t\t\t\t\t\tend
\t\t\t\t\tElse
\t\t\t\t\t\t$Phantom_sync_cowl_item(ThisAgent);
\t\t\t\tend
\t\tend

\tThisAgent's "ActiveScript" = $Done_Enhancing_Equipment;
End

Function Obtain_Enchantment(agent ThisAgent)

Declare
\tagent ThisBuilding;
\tinteger What_To_Upgrade,Total_Gold,Gold,Upgrade,Bldg_Level,Current_Upgrade,Stored_Upgrade;

Begin
\tThisBuilding = ThisAgent's "Target";
\tTotal_Gold = $Total_Gold(ThisAgent);
\tWhat_To_Upgrade = ThisAgent's "Task_Number";
\tCurrent_Upgrade = $GetAttribute(ThisAgent, What_To_Upgrade);
\tIf (ThisAgent's "Title" == "Phantom" &&
\t\tWhat_To_Upgrade == #ATTRIB_Armor_Magic_Bonus)
\t\tCurrent_Upgrade = $Phantom_cowl_magic_level(ThisAgent);

\tThisAgent's "Task_Number" = 0;
\t$SetThreadInterval(ThisAgent's "ActiveScript", #Normal_Cycle);
\tBldg_Level = ThisBuilding's "Level";

\tIf (Current_Upgrade == 0 && Total_Gold >= #Cost_Per_Magic_Enchantment1)
\t\tbegin
\t\t\tTotal_Gold -= #Cost_Per_Magic_Enchantment1;
\t\t\tGold += #Cost_Per_Magic_Enchantment1;
\t\t\tUpgrade = 1;
\t\tend

\tIf (Current_Upgrade <= 1 && Total_Gold >= #Cost_Per_Magic_Enchantment2 && Bldg_Level > 1)
\t\tbegin
\t\t\tTotal_Gold -= #Cost_Per_Magic_Enchantment2;
\t\t\tGold += #Cost_Per_Magic_Enchantment2;
\t\t\tUpgrade = 2;
\t\tend

\tIf (Current_Upgrade <= 2 && Total_Gold >= #Cost_Per_Magic_Enchantment3 && Bldg_Level > 2)
\t\tbegin
\t\t\tGold += #Cost_Per_Magic_Enchantment3;
\t\t\tUpgrade = 3;
\t\tend

\tIf (Upgrade > 0)
\t\tbegin
\t\t\t$Spend_Gold(ThisAgent, ThisBuilding, Gold);
\t\t\tStored_Upgrade = Upgrade;
\t\t\tIf (ThisAgent's "Title" == "Phantom" &&
\t\t\t\tWhat_To_Upgrade == #ATTRIB_Armor_Magic_Bonus &&
\t\t\t\tThisAgent's "Reborn_Counter" == 1)
\t\t\t\tStored_Upgrade += 10000;
\t\t\t$SetAttribute(ThisAgent, What_To_Upgrade, Stored_Upgrade);

\t\t\tIf (ThisAgent's "Title" == "Phantom")
\t\t\t\tbegin
\t\t\t\t\tIf (What_To_Upgrade == #ATTRIB_Weapon_Magic_Bonus)
\t\t\t\t\t\t$Phantom_sync_icerod_item(ThisAgent);
\t\t\t\t\tElse
\t\t\t\t\t\t$Phantom_sync_cowl_item(ThisAgent);
\t\t\t\tend
\t\tend

\tThisAgent's "ActiveScript" = $Done_Enhancing_Equipment;
End

function attack_object(agent thisagent)

declare
\tinteger targetrange,attackrange;
\tagent target;
\tstring spell_name;
\tboolean casting;

begin
\ttarget = thisagent's "target";

\tIf ($notvalid(target))
\t\t$reset_tasks(thisagent);
\tElse If ($haslowHP(thisagent))
\t\t$heal_self(thisagent);
\tElse
\t\tbegin
\t\t\tspell_name = $getbestspell(thisagent, #list_attack);
\t\t\tIf (spell_name == "nothing")
\t\t\t\tbegin
\t\t\t\t\tattackrange = $getattribute(thisagent, #ATTRIB_maxattackrange);
\t\t\t\t\tcasting = False;
\t\t\t\tend
\t\t\tElse
\t\t\t\tbegin
\t\t\t\t\tIf (thisagent's "Title" == "Phantom")
\t\t\t\t\t\tattackrange = $Phantom_effective_casting_range(thisagent);
\t\t\t\t\tElse
\t\t\t\t\t\tattackrange = thisagent's "castingrange";
\t\t\t\t\tcasting = True;
\t\t\t\tend

\t\t\ttargetrange = $distanceBetweenAgents(thisagent, target);
\t\t\tIf (targetrange > attackrange)
\t\t\t\tbegin
\t\t\t\t\tthisagent's "destination" = $locationof(target);
\t\t\t\t\tthisagent's "activeScript" = $travel_to;
\t\t\t\t\tthisagent's "backScript" = $attack_object;
\t\t\t\t\t$move(thisagent, target);
\t\t\t\tend
\t\t\tElse If (($listsize(thisagent's "hostiles") > 0) &&
\t\t\t\t((target's "type" == "building") || (target's "type" == "lair")))
\t\t\t\t(thisagent's "evaluationscript")(thisagent);
\t\t\tElse If ($Hero_Peasant_check(thisagent) == False)
\t\t\t\tbegin
\t\t\t\t\tIf (casting)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\t$PlaySound(ThisAgent, "VFX_CAST_SPELL1");
\t\t\t\t\t\t\t$castspell(thisagent, spell_name, target, "");
\t\t\t\t\t\tend
\t\t\t\t\tElse
\t\t\t\t\t\t$performAction(thisagent, thisagent's "attack_action", target);
\t\t\t\tend
\t\tend
end

function getattackrange(agent thisagent) is integer

declare
\tinteger arrivedist;

begin
\tIf ($getbestspell(thisagent, #List_attack) == "nothing")
\t\tarrivedist = $getattribute(thisagent, #ATTRIB_MaxAttackRange);
\tElse If (thisagent's "Title" == "Phantom")
\t\tarrivedist = $Phantom_effective_casting_range(thisagent);
\tElse
\t\tarrivedist = thisagent's "castingrange";

\treturn arrivedist;
end

function Call_To_Grave_Check(agent thisagent) is integer

declare
\tcoordinate destination;

begin
\tif (thisagent's "taskname" != "go_home")
\t\treturn 0;

\tif (thisagent's "target" != thisagent's "home")
\t\treturn 0;

\tif (thisagent's "Target" == thisagent)
\t\tdestination = thisagent's "destination";
\telse
\t\tif ($isvalidgamepiece(thisagent's "target"))
\t\t\tdestination = $locationof(thisagent's "target");
\t\telse
\t\t\treturn 0;

\tif ($distancebetweencoords(destination,$locationof(thisagent)) > #Phantom_Call_To_Grave_Min_Distance)
\t\treturn 1;

\treturn 0;
end

function Call_To_Grave_Effect(agent thisagent, agent target)

declare
\tinteger theTimePeriod;

begin
\ttheTimePeriod = $GetSpellAttribute("call_to_grave","effector_duration");
\t$createeffector(thisagent,"call_to_grave_effector",theTimePeriod);
\tthisagent's "teleportScript" = $Call_To_Grave_DoMove;
\t$RunThread(thisagent's "teleportScript",theTimePeriod/2,thisagent,#Phantom_Call_To_Grave_Range);
end

function Call_To_Grave_DoMove(agent thisagent, integer theRange)

declare

begin
\tIf ($IsDead(ThisAgent))
\t\treturn;

\tif (thisagent's "Target" == thisagent)
\t\t$TeleportToPoint(thisagent,theRange,thisagent's "destination");
\telse
\t\tif ($isvalidgamepiece(thisagent's "target"))
\t\t\t$TeleportToUnit(thisagent,theRange,thisagent's "Target",thisagent's "castingrange");
end

function flee_part_II(agent thisagent, list places, integer intent)

declare
\tagent go_here;

begin
\tif (thisagent's "Title" == "Phantom" && $isvalidgamepiece(thisagent's "home"))
\t\tgo_here = thisagent's "home";
\telse if ($listsize(places) > 0)
\t\tgo_here = $pick_closest(thisagent,places);
\telse
\t\tbegin
\t\t\t$go_berserk(thisagent);
\t\t\treturn;
\t\tend

\tif (go_here == thisagent's "home")
\t\tthisagent's "taskname" = "go_home";
\telse
\t\tthisagent's "taskname" = "visiting";

\t$SpecifyIntent(ThisAgent,intent);
\tthisagent's "Activescript" = $use_building_safe;
\tthisagent's "backscript" = $use_building_safe;
\tthisagent's "target" = go_here;
\tthisagent's "destination" = $locationof(thisagent's "target");

\t$createeffector(thisagent,"thought_bubble_danger",#danger_bubble_time);
\t$say(thisagent,"VFX_FLEE_COMBAT");
end

function Phantom_tree (agent thisagent)

declare

begin
\t$DebugOut("Phantom deciding");

\tIf ($Phantom_Try_Frost_Armor(thisagent) == False)
\t\t$Wizard_tree(thisagent);
end

function Phantom_birth (agent thisagent)

declare

begin
\t$PlaySound(thisagent, "Phantom", "VFX_SPECIAL1");
\t$hero_birth(thisagent);
\t$Phantom_grant_starter_items(thisagent);
\t$LearnSpell(thisagent, "ice_lance");
\tthisagent's "Reborn_Counter" = 0;
\tthisagent's "QuestScript" = $Phantom_Frost_Armor_Watch;
\t$NewThread(thisagent's "QuestScript", 100, thisagent);
end

function Phantom_has_cowl_item(agent thisagent) is boolean

declare
\tinteger item_id;

begin
\tIf ($AgentHasInventoryItem(#Phantom_Item_FrozenCowl, thisagent))
\t\treturn True;

\titem_id = 83;
\tWhile (item_id <= 97) do
\t\tbegin
\t\t\tIf ($AgentHasInventoryItem(item_id, thisagent))
\t\t\t\treturn True;
\t\t\titem_id += 1;
\t\tend

\treturn False;
end

function Phantom_has_icerod_item(agent thisagent) is boolean

declare
\tinteger item_id;

begin
\tIf ($AgentHasInventoryItem(#Phantom_Item_BlackIcerod, thisagent))
\t\treturn True;

\titem_id = 98;
\tWhile (item_id <= 112) do
\t\tbegin
\t\t\tIf ($AgentHasInventoryItem(item_id, thisagent))
\t\t\t\treturn True;
\t\t\titem_id += 1;
\t\tend

\treturn False;
end

function Phantom_remove_cowl_items(agent thisagent)

declare
\tinteger item_id;

begin
\tWhile ($AgentHasInventoryItem(#Phantom_Item_FrozenCowl, thisagent)) do
\t\t$DeleteInventoryItem(#Phantom_Item_FrozenCowl, thisagent);

\titem_id = 83;
\tWhile (item_id <= 97) do
\t\tbegin
\t\t\tWhile ($AgentHasInventoryItem(item_id, thisagent)) do
\t\t\t\t$DeleteInventoryItem(item_id, thisagent);
\t\t\titem_id += 1;
\t\tend
end

function Phantom_remove_icerod_items(agent thisagent)

declare
\tinteger item_id;

begin
\tWhile ($AgentHasInventoryItem(#Phantom_Item_BlackIcerod, thisagent)) do
\t\t$DeleteInventoryItem(#Phantom_Item_BlackIcerod, thisagent);

\titem_id = 98;
\tWhile (item_id <= 112) do
\t\tbegin
\t\t\tWhile ($AgentHasInventoryItem(item_id, thisagent)) do
\t\t\t\t$DeleteInventoryItem(item_id, thisagent);
\t\t\titem_id += 1;
\t\tend
end

function Phantom_cowl_magic_level(agent thisagent) is integer

declare
\tinteger magic_level;

begin
\tmagic_level = $GetAttribute(thisagent, #ATTRIB_Armor_Magic_Bonus);
\tIf (thisagent's "Reborn_Counter" == 1)
\t\tmagic_level -= 10000;

\tIf (magic_level < 0)
\t\tmagic_level = 0;
\tIf (magic_level > 3)
\t\tmagic_level = 3;

\treturn magic_level;
end

function Phantom_effective_casting_range(agent thisagent) is integer

declare
\tinteger magic_level;

begin
\tmagic_level = $GetAttribute(thisagent, #ATTRIB_Weapon_Magic_Bonus);
\tIf (magic_level < 0)
\t\tmagic_level = 0;
\tIf (magic_level > 3)
\t\tmagic_level = 3;

\treturn 190 + (magic_level * 10);
end

function Phantom_sync_cowl_item(agent thisagent)

declare
\tinteger struct_level,magic_level,combination,item_id;

begin
\tstruct_level = $GetAttribute(thisagent, #ATTRIB_Armor_Struct_Bonus);
\tIf (struct_level < 0)
\t\tstruct_level = 0;
\tIf (struct_level > 3)
\t\tstruct_level = 3;
\tmagic_level = $Phantom_cowl_magic_level(thisagent);
\tcombination = (struct_level * 4) + magic_level;

\tIf (combination == 0)
\t\titem_id = 80;
\tElse
\t\titem_id = 82 + combination;

\t$Phantom_remove_cowl_items(thisagent);
\t$CreateNewInventoryItem(item_id, thisagent, #Allow_Cloned_Quest_Item);
end

function Phantom_sync_icerod_item(agent thisagent)

declare
\tinteger struct_level,magic_level,combination,item_id;

begin
\tstruct_level = $GetAttribute(thisagent, #ATTRIB_Weapon_Struct_Bonus);
\tIf (struct_level < 0)
\t\tstruct_level = 0;
\tIf (struct_level > 3)
\t\tstruct_level = 3;
\tmagic_level = $GetAttribute(thisagent, #ATTRIB_Weapon_Magic_Bonus);
\tIf (magic_level < 0)
\t\tmagic_level = 0;
\tIf (magic_level > 3)
\t\tmagic_level = 3;
\tcombination = (struct_level * 4) + magic_level;

\tIf (combination == 0)
\t\titem_id = 81;
\tElse
\t\titem_id = 97 + combination;

\t$Phantom_remove_icerod_items(thisagent);
\t$CreateNewInventoryItem(item_id, thisagent, #Allow_Cloned_Quest_Item);
end

function Phantom_sync_equipment_items(agent thisagent)

declare

begin
\t$Phantom_sync_cowl_item(thisagent);
\t$Phantom_sync_icerod_item(thisagent);
end

function Phantom_grant_starter_items (agent thisagent)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf ($Phantom_has_cowl_item(thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem(#Phantom_Item_FrozenCowl, thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$AdjustAttribute (thisagent, #ATTRIB_Armor_Basic_Damage, 2);
\t\tend

\tIf ($Phantom_has_icerod_item(thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem(#Phantom_Item_BlackIcerod, thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$AdjustAttribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);
\t\t\t$MagicalAdjustAttribute (thisagent, #ATTRIB_Parry, 5);
\t\tend
end

function Ice_Lance_Cast(agent thisagent, agent target)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf ($isdead(target))
\t\treturn;

\t$createmissile("ice_lance_missile", thisagent, target);
end

function Phantom_Eternal_Soul_Active(agent thisagent) is boolean

declare

begin
\tIf ($NotValid(thisagent))
\t\treturn False;

\tIf ($IsValidGamePiece(thisagent) == False)
\t\treturn False;

\tIf ($HasAttribute("PhantomEternalSoulActive", thisagent) == False)
\t\treturn False;

\tIf (thisagent's "PhantomEternalSoulActive" == False)
\t\treturn False;

\treturn True;
end

function Eternal_Soul_Begin(agent thisagent, agent target)

declare
\tinteger base_max_hp, current_hp, bonus_max_hp, boosted_max_hp, boosted_hp;

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf ($HasAttribute("PhantomEternalSoulActive", thisagent) == False)
\t\tbegin
\t\t\t$AddAttribute(thisagent, "PhantomEternalSoulActive", "boolean", False);
\t\t\t$AddAttribute(thisagent, "PhantomEternalSoulMaxHPBonus", "integer", 0);
\t\tend

\tIf (thisagent's "PhantomEternalSoulActive")
\t\treturn;

\tbase_max_hp = $GetAttribute(thisagent, #ATTRIB_MaxHP);
\tcurrent_hp = $GetAttribute(thisagent, #ATTRIB_HP);
\tbonus_max_hp = (base_max_hp * 30) / 100;
\tIf (bonus_max_hp < 1)
\t\tbonus_max_hp = 1;

\tboosted_max_hp = base_max_hp + bonus_max_hp;
\tboosted_hp = ((current_hp * boosted_max_hp) + (base_max_hp / 2)) / base_max_hp;

\tthisagent's "PhantomEternalSoulActive" = True;
\tthisagent's "PhantomEternalSoulMaxHPBonus" = bonus_max_hp;
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, 15);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, 15);
\t$AdjustAttribute(thisagent, #ATTRIB_MaxHP, bonus_max_hp);
\t$SetAttribute(thisagent, #ATTRIB_HP, boosted_hp);
\t$CreateEffector(thisagent, "eternal_soul_icon", $GetSpellAttribute("eternal_soul", "effector_duration"));
\t$CreateEffector(thisagent, "eternal_soul_effector", 0);
end

function Eternal_Soul_End(agent thisagent)

declare
\tinteger boosted_max_hp, current_hp, bonus_max_hp, base_max_hp, restored_hp;

begin
\tIf ($HasAttribute("PhantomEternalSoulActive", thisagent) == False)
\t\treturn;

\tIf (thisagent's "PhantomEternalSoulActive" == False)
\t\treturn;

\tthisagent's "PhantomEternalSoulActive" = False;
\tbonus_max_hp = thisagent's "PhantomEternalSoulMaxHPBonus";
\tthisagent's "PhantomEternalSoulMaxHPBonus" = 0;

\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, -15);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, -15);

\tboosted_max_hp = $GetAttribute(thisagent, #ATTRIB_MaxHP);
\tbase_max_hp = boosted_max_hp - bonus_max_hp;
\tIf (base_max_hp < 1)
\t\tbase_max_hp = 1;

\tcurrent_hp = $GetAttribute(thisagent, #ATTRIB_HP);
\t$AdjustAttribute(thisagent, #ATTRIB_MaxHP, -bonus_max_hp);

\tIf ($IsDead(thisagent))
\t\treturn;

\trestored_hp = ((current_hp * base_max_hp) + (boosted_max_hp / 2)) / boosted_max_hp;
\tIf (restored_hp > base_max_hp)
\t\trestored_hp = base_max_hp;
\t$SetAttribute(thisagent, #ATTRIB_HP, restored_hp);
end

function Ice_Lance_Hit(agent thisagent, agent target)

declare

begin
\t$PlaySound(target, "Energy_Blast", "Attack");
\t$spell_attack(thisagent, target, 8);

\tIf ($isdead(target))
\t\treturn;

\t$createeffector(target, "ice_lance_hit_effector", 0);

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn;

\t$Phantom_Apply_Chill(thisagent, target, $GetSpellAttribute("ice_lance", "effector_duration"));
end

function Phantom_Apply_Chill(agent source, agent target, integer duration)

declare
\tinteger desired_tier;

begin
\tdesired_tier = 1;
\tIf ($Phantom_Eternal_Soul_Active(source))
\t\tdesired_tier = 2;

\t$Phantom_Apply_Chill_Tier(target, duration, desired_tier);
end

function Phantom_Apply_Chill_Tier(agent target, integer duration, integer desired_tier)

declare

begin
\tIf ($isdead(target))
\t\treturn;

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn;

\tIf ($HasAttribute("PhantomChillRemaining", target) == False)
\t\tbegin
\t\t\t$AddAttribute(target, "PhantomChillRemaining", "integer", duration);
\t\t\t$AddAttribute(target, "PhantomChillActive", "boolean", False);
\t\t\t$AddAttribute(target, "PhantomChillTier", "integer", 0);
\t\t\t$AddAttribute(target, "PhantomChillWatch", "function", $Phantom_Chill_Watch);
\t\tend
\tIf ($HasAttribute("PhantomChillIconDelay", target) == False)
\t\t$AddAttribute(target, "PhantomChillIconDelay", "integer", 0);

\tIf (target's "PhantomChillActive" == False)
\t\tbegin
\t\t\ttarget's "PhantomChillActive" = True;
\t\t\ttarget's "PhantomChillTier" = desired_tier;
\t\t\ttarget's "PhantomChillRemaining" = duration;
\t\t\tIf (desired_tier == 2)
\t\t\t\tbegin
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_MovementRateModifier, 100);
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_ActionRateModifier, 1000);
\t\t\t\tend
\t\t\tElse
\t\t\t\tbegin
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_MovementRateModifier, 50);
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_ActionRateModifier, 500);
\t\t\t\tend
\t\tend
\tElse If (desired_tier == 2)
\t\tbegin
\t\t\tIf (target's "PhantomChillTier" == 1)
\t\t\t\tbegin
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_MovementRateModifier, 50);
\t\t\t\t\t$AdjustAttribute(target, #ATTRIB_ActionRateModifier, 500);
\t\t\t\tend
\t\t\ttarget's "PhantomChillTier" = 2;
\t\t\ttarget's "PhantomChillRemaining" = duration;
\t\tend
\tElse
\t\tbegin
\t\t\tIf (target's "PhantomChillTier" != 2)
\t\t\t\tbegin
\t\t\t\t\ttarget's "PhantomChillTier" = 1;
\t\t\t\t\ttarget's "PhantomChillRemaining" = duration;
\t\t\t\tend
\t\tend

\t$Phantom_Chill_Sync_Icon(target);

\tIf ($IsRunning(target's "PhantomChillWatch") == False)
\t\t$NewThread(target's "PhantomChillWatch", 100, target);
end

function Phantom_Chill_Sync_Icon(agent target)

declare

begin
\tIf (target's "PhantomChillIconDelay" > 0)
\t\treturn;

\tIf (target's "PhantomChillTier" == 2)
\t\tbegin
\t\t\tIf ($CheckEffector(target, "ice_lance_chill_icon"))
\t\t\t\tbegin
\t\t\t\t\t$DeleteEffector(target, "ice_lance_chill_icon");
\t\t\t\t\ttarget's "PhantomChillIconDelay" = 200;
\t\t\t\t\treturn;
\t\t\t\tend
\t\t\tIf ($CheckEffector(target, "ice_lance_empowered_chill_icon") == False)
\t\t\t\t$CreateEffector(target, "ice_lance_empowered_chill_icon", 1, "infinite");
\t\tend
\tElse
\t\tbegin
\t\t\tIf ($CheckEffector(target, "ice_lance_empowered_chill_icon"))
\t\t\t\tbegin
\t\t\t\t\t$DeleteEffector(target, "ice_lance_empowered_chill_icon");
\t\t\t\t\ttarget's "PhantomChillIconDelay" = 200;
\t\t\t\t\treturn;
\t\t\t\tend
\t\t\tIf ($CheckEffector(target, "ice_lance_chill_icon") == False)
\t\t\t\t$CreateEffector(target, "ice_lance_chill_icon", 1, "infinite");
\t\tend
end

function Phantom_Chill_Watch(agent thisagent)

declare

begin
\tIf ($IsValidGamePiece(thisagent) == False)
\t\treturn;

\tIf (thisagent's "PhantomChillActive" == False)
\t\tbegin
\t\t\t$KillThread(thisagent's "PhantomChillWatch");
\t\t\treturn;
\t\tend

\tIf (thisagent's "PhantomChillIconDelay" > 0)
\t\tthisagent's "PhantomChillIconDelay" -= 100;
\t$Phantom_Chill_Sync_Icon(thisagent);

\tthisagent's "PhantomChillRemaining" -= 100;
\tIf (thisagent's "PhantomChillRemaining" > 0)
\t\treturn;

\t$KillThread(thisagent's "PhantomChillWatch");
\tthisagent's "PhantomChillActive" = False;
\tIf (thisagent's "PhantomChillTier" == 2)
\t\tbegin
\t\t\t$AdjustAttribute(thisagent, #ATTRIB_MovementRateModifier, -100);
\t\t\t$AdjustAttribute(thisagent, #ATTRIB_ActionRateModifier, -1000);
\t\tend
\tElse
\t\tbegin
\t\t\t$AdjustAttribute(thisagent, #ATTRIB_MovementRateModifier, -50);
\t\t\t$AdjustAttribute(thisagent, #ATTRIB_ActionRateModifier, -500);
\t\tend
\tthisagent's "PhantomChillTier" = 0;
\tthisagent's "PhantomChillIconDelay" = 0;
\tIf ($CheckEffector(thisagent, "ice_lance_chill_icon"))
\t\t$DeleteEffector(thisagent, "ice_lance_chill_icon");
\tIf ($CheckEffector(thisagent, "ice_lance_empowered_chill_icon"))
\t\t$DeleteEffector(thisagent, "ice_lance_empowered_chill_icon");
end

function Phantom_death(agent thisagent)

declare

begin
\tIf (thisagent's "Reborn_Counter" == 1)
\t\tbegin
\t\t\t$DeleteEffector(thisagent, "frost_armor_effector");
\t\t\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, -10000);
\t\t\t$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, -10000);
\t\tend
\tthisagent's "Reborn_Counter" = 0;
\t$Phantom_remove_starter_items(thisagent);
\t$gravestone(thisagent);
end

function Phantom_remove_starter_items(agent thisagent)

declare

begin
\t$Phantom_remove_cowl_items(thisagent);
\t$Phantom_remove_icerod_items(thisagent);

\tWhile ($AgentHasInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent)) do
\t\tbegin
\t\t\t$DeleteInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent);
\t\tend
end

Function Hero_Drop_Quest_Items (agent ThisAgent)

Declare
\tinteger WhatItem;
\tstring agentType;

Begin
\tIf (ThisAgent's "Title" == "Phantom")
\t\tbegin
\t\t\tIf ($isdead(ThisAgent) == False)
\t\t\t\t$KillThread(ThisAgent's "QuestScript");
\t\t\t$Phantom_remove_starter_items(ThisAgent);
\t\tend

\tWhatItem = -1;

\tWhile ($AgentHasInventoryItem(WhatItem, ThisAgent)) do
\t\tbegin
\t\t\t$DeleteInventoryItem(WhatItem, ThisAgent);

\t\t\tIf (WhatItem != #QItem_Magic_Sword &&
\t\t\t\tWhatItem != #MarketItem_Ring_Protection &&
\t\t\t\tWhatItem != #MarketItem_Market3_Item)
\t\t\t\tbegin
\t\t\t\t\tIf ($CanDropInventoryItem(WhatItem) == True)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tagentType = $GetInventoryItemAgentType(WhatItem);
\t\t\t\t\t\t\t$SpawnUnit(ThisAgent, agentType, "Override", $Concatenate($MakeInventoryAttribute(WhatItem), 0));
\t\t\t\t\t\tend
\t\t\t\tend

\t\t\tWhatItem = -1;
\t\tend
End

function Phantom_Grant_Frost_Armor_Bonus(agent thisagent)

declare

begin
\tIf ($GetAttribute(thisagent, #ATTRIB_ExperienceLevel) < 3)
\t\treturn;

\tIf ($AgentHasInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent))
\t\treturn;

\t$CreateNewInventoryItem(#Phantom_Item_FrostArmorBonus, thisagent, #Allow_Cloned_Quest_Item);
\t$AdjustAttribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10);
end

function Frost_Armor_Begin(agent thisagent, agent target)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf (thisagent's "Reborn_Counter" != 0)
\t\treturn;

\tthisagent's "Reborn_Counter" = 1;
\t$createeffector(thisagent, "frost_armor_effector", 180000);
\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 10000);
\t$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, 10000);
\t$clearlist(thisagent's "Hostiles");
end

function Frost_Armor_Check(agent thisagent) is integer

declare

begin
\tIf ($isdead(thisagent))
\t\treturn 0;

\tIf (thisagent's "Reborn_Counter" != 0)
\t\treturn 0;

\treturn 1;
end

function Phantom_Try_Frost_Armor(agent thisagent) is boolean

declare
\tlist targets;

begin
\tIf ($GetAttribute(thisagent, #ATTRIB_ExperienceLevel) < 3)
\t\treturn False;

\tIf ($Frost_Armor_Check(thisagent) == 0)
\t\treturn False;

\ttargets = $compile_enemies(thisagent, 240);
\tIf ($ListSize(targets) == 0)
\t\treturn False;

\t$Frost_Armor_Begin(thisagent, thisagent);
\t$PerformAction(thisagent, "Basic_Cast", thisagent);
\treturn True;
end

function Phantom_Arm_Frost_Armor_In_Combat(agent thisagent) is boolean

declare

begin
\tIf ($GetAttribute(thisagent, #ATTRIB_ExperienceLevel) < 3)
\t\treturn False;

\tIf ($Frost_Armor_Check(thisagent) == 0)
\t\treturn False;

\tIf (thisagent's "ActiveScript" != $Attack_object &&
\t\tthisagent's "BackScript" != $Attack_object)
\t\treturn False;

\t$Frost_Armor_Begin(thisagent, thisagent);
\t$PerformAction(thisagent, "Basic_Cast", thisagent);
\treturn True;
end

function Phantom_Frost_Armor_Watch(agent thisagent)

declare
\tagent attacker;
\tagent hostile;
\tinteger attack_range;

begin
\tIf ($isdead(thisagent))
\t\tbegin
\t\t\t$KillThread(thisagent's "QuestScript");
\t\t\treturn;
\t\tend

\t$Phantom_Grant_Frost_Armor_Bonus(thisagent);
\t$Phantom_Frost_Armor_Recharge_Check(thisagent);

\tIf ($Phantom_Arm_Frost_Armor_In_Combat(thisagent))
\t\treturn;

\tIf (thisagent's "Reborn_Counter" != 1)
\t\treturn;

\tIf ($CheckEffector(thisagent, "frost_armor_effector") == False)
\t\t$CreateEffector(thisagent, "frost_armor_effector", 180000);

\tIf ($ListSize(thisagent's "Hostiles") == 0)
\t\treturn;

\tattacker = $NullAgent();
\tForeach hostile in thisagent's "Hostiles" do
\t\tbegin
\t\t\tIf ($notvalid(attacker))
\t\t\t\tIf ($isvalidgamepiece(hostile))
\t\t\t\t\tIf (hostile's "Target" == thisagent)
\t\t\t\t\t\tbegin
\t\t\t\t\t\t\tattack_range = $GetAttribute(hostile, #ATTRIB_MaxAttackRange);
\t\t\t\t\t\t\tIf ($DistanceBetweenAgents(hostile, thisagent) <= attack_range + 24)
\t\t\t\t\t\t\t\tattacker = hostile;
\t\t\t\t\t\tend
\t\tend

\t$ClearList(thisagent's "Hostiles");

\tIf ($notvalid(attacker))
\t\treturn;

\tthisagent's "Reborn_Counter" = 2;
\t$DeleteEffector(thisagent, "frost_armor_effector");
\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, -10000);
\t$adjustattribute(thisagent, #ATTRIB_Armor_Magic_Bonus, -10000);
\t$CreateEffector(thisagent, "ice_lance_hit_effector", 0);

\tIf (attacker's "Type" == "Building" || attacker's "Type" == "Lair")
\t\treturn;

\t$Frost_Armor_Freeze(attacker);
end

function Phantom_Frost_Armor_Recharge_Check(agent thisagent)

declare

begin
\tIf (thisagent's "Reborn_Counter" != 2)
\t\treturn;

\tIf ($InsideBuilding(thisagent) == False)
\t\treturn;

\tIf (thisagent's "ActiveScript" == $rest_at_inn ||
\t\tthisagent's "ActiveScript" == $Done_resting_inn ||
\t\tthisagent's "ActiveScript" == $Rest_at_guild ||
\t\tthisagent's "ActiveScript" == $Phantom_Rest_At_Guild ||
\t\tthisagent's "ActiveScript" == $Done_resting_guild)
\t\tthisagent's "Reborn_Counter" = 0;
end

function Frost_Armor_Freeze(agent target)

declare
\tinteger max_hp;

begin
\tIf ($isdead(target))
\t\treturn;

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn;

\tIf ($CheckEffector(target, "frost_armor_frozen_timer"))
\t\t$DeleteEffector(target, "frost_armor_frozen_timer");
\tElse If ($GetAttribute(target, #ATTRIB_HasEffectPetrify) == 1)
\t\treturn;

\t$SetAttribute(target, #ATTRIB_HasEffectPetrify, 1);
\t$GetProperUnitArt(target);
\t$Freeze_Unit(target);

\tmax_hp = $GetAttribute(target, #ATTRIB_MaxHP);
\tIf (max_hp < 50)
\t\t$CreateEffector(target, "frost_armor_frozen_small", 2700);
\tElse If (max_hp < 150)
\t\t$CreateEffector(target, "frost_armor_frozen_medium", 2700);
\tElse
\t\t$CreateEffector(target, "frost_armor_frozen_large", 2700);

\t$CreateEffector(target, "frost_armor_frozen_timer", 3000);
end

function Frost_Armor_Frozen_End(agent thisagent)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\t$DeleteEffector(thisagent, "frost_armor_frozen_small");
\t$DeleteEffector(thisagent, "frost_armor_frozen_medium");
\t$DeleteEffector(thisagent, "frost_armor_frozen_large");
\t$SetAttribute(thisagent, #ATTRIB_HasEffectPetrify, 0);
\t$GetProperUnitArt(thisagent);
\t$UnFreeze_Unit(thisagent);
end

function Phantom_Lived_In(agent thisagent)

declare

begin
\t$Lived_In(thisagent);
\tthisagent's "ActiveScript" = $Phantom_Rest_At_Guild;
end

function Phantom_Rest_At_Guild(agent thisagent)

declare

begin
\t$Rest_At_Guild(thisagent);

\tIf (thisagent's "Reborn_Counter" == 2)
\t\tthisagent's "Reborn_Counter" = 0;
end

function Icy_Touch_Check(agent thisagent) is integer

declare
\tagent target;
\tinteger distance;

begin
\ttarget = thisagent's "Target";

\tIf ($NotValid(target))
\t\treturn 0;

\tIf ($IsDead(target))
\t\treturn 0;

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn 0;

\tdistance = $DistanceBetweenAgents(thisagent, target);

\tIf (distance <= #Phantom_Icy_Touch_Range)
\t\treturn 1;

\treturn 0;
end

function Icy_Touch_Cast(agent thisagent, agent action_target)

declare
\tagent target;

begin
\ttarget = thisagent's "Target";

\tIf ($NotValid(target))
\t\treturn;

\tIf ($IsDead(target))
\t\treturn;

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn;

\t$make_attack(thisagent, target);

\tIf ($IsDead(target))
\t\treturn;

\t$spell_attack(thisagent, target, 30);

\tIf ($IsDead(target))
\t\treturn;

\t$Phantom_Apply_Chill(thisagent, target, $GetSpellAttribute("ice_lance", "effector_duration"));
\t$CreateEffector(target, "gravechill_hit_effector", 0);
\t$Phantom_Apply_Gravechill(target, 8000);
end

function Phantom_Apply_Gravechill(agent target, integer duration)

declare

begin
\tIf ($isdead(target))
\t\treturn;

\tIf (target's "Type" == "Building" || target's "Type" == "Lair")
\t\treturn;

\tIf ($HasAttribute("PhantomGravechillRemaining", target) == False)
\t\tbegin
\t\t\t$AddAttribute(target, "PhantomGravechillRemaining", "integer", duration);
\t\t\t$AddAttribute(target, "PhantomGravechillActive", "boolean", False);
\t\t\t$AddAttribute(target, "PhantomGravechillWatch", "function", $Phantom_Gravechill_Watch);
\t\tend
\ttarget's "PhantomGravechillRemaining" = duration;

\tIf (target's "PhantomGravechillActive" == False)
\t\tbegin
\t\t\ttarget's "PhantomGravechillActive" = True;
\t\t\t$MagicalAdjustAttribute(target, #ATTRIB_Strength, -5);
\t\t\t$MagicalAdjustAttribute(target, #ATTRIB_Parry, -2);
\t\t\t$MagicalAdjustAttribute(target, #ATTRIB_MagicResistance, -2);
\t\tend

\tIf ($CheckEffector(target, "gravechill_icon") == False)
\t\t$CreateEffector(target, "gravechill_icon", 1, "infinite");

\tIf ($IsRunning(target's "PhantomGravechillWatch") == False)
\t\t$NewThread(target's "PhantomGravechillWatch", 100, target);
end

function Phantom_Gravechill_Watch(agent thisagent)

declare

begin
\tIf ($IsValidGamePiece(thisagent) == False)
\t\treturn;

\tIf (thisagent's "PhantomGravechillActive" == False)
\t\tbegin
\t\t\t$KillThread(thisagent's "PhantomGravechillWatch");
\t\t\treturn;
\t\tend

\tthisagent's "PhantomGravechillRemaining" -= 100;
\tIf (thisagent's "PhantomGravechillRemaining" > 0)
\t\treturn;

\t$KillThread(thisagent's "PhantomGravechillWatch");
\tthisagent's "PhantomGravechillActive" = False;
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Strength, 5);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Parry, 2);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_MagicResistance, 2);
\tIf ($CheckEffector(thisagent, "gravechill_icon"))
\t\t$DeleteEffector(thisagent, "gravechill_icon");
end

function Endless_Winter_Hit(agent thisagent, agent target)

declare
\tinteger cast_range;
\tlist targets;
\tagent closest_enemy;
\tinteger closest_distance;
\tinteger target_distance;

begin
\tcast_range = $Phantom_effective_casting_range(thisagent);
\ttargets = $compile_enemies(thisagent, cast_range);
\tIf ($ListSize(targets) == 0)
\t\treturn;

\tclosest_enemy = $Pick_Closest(thisagent, targets);
\tIf ($notvalid(closest_enemy))
\t\treturn;

\tIf ($isvalidgamepiece(target))
\t\tIf ($IsDead(target) == False)
\t\t\tIf ($AgentInList(target, targets))
\t\t\t\tbegin
\t\t\t\t\tclosest_distance = $DistanceBetweenAgents(thisagent, closest_enemy);
\t\t\t\t\ttarget_distance = $DistanceBetweenAgents(thisagent, target);
\t\t\t\t\tIf (target_distance == closest_distance)
\t\t\t\t\t\tclosest_enemy = target;
\t\t\t\tend

\t$CreateSpellUnit(thisagent, "endless_winter_storm", closest_enemy);
end

function Endless_Winter_Check(agent thisagent) is integer

declare
\tinteger cast_range;
\tlist targets;

begin
\tIf ($isdead(thisagent))
\t\treturn 0;

\tcast_range = $Phantom_effective_casting_range(thisagent);
\ttargets = $compile_enemies(thisagent, cast_range);
\tIf ($ListSize(targets) > 0)
\t\treturn 1;

\treturn 0;
end

function Endless_Winter_Unit_Created(agent thisagent, agent target)

declare
\tinteger duration;

begin
\tduration = $GetSpellAttribute("endless_winter", "effector_duration");
\t$SetParent(thisagent, target);
\t$SetSpellUnitTimeout(
\t\tthisagent,
\t\tduration + 500
\t);
\t$CreateEffector(
\t\tthisagent,
\t\t"endless_winter_vortex_effector",
\t\tduration
\t);
\t$AddAttribute(
\t\tthisagent,
\t\t"EndlessWinterTracking",
\t\t"function",
\t\t$Endless_Winter_Track
\t);
\t$AddAttribute(
\t\tthisagent,
\t\t"EndlessWinterCleanup",
\t\t"function",
\t\t$Endless_Winter_Cleanup
\t);
\t$RunThread(
\t\tthisagent's "EndlessWinterCleanup",
\t\tduration + 100,
\t\tthisagent
\t);
\t$NewThread(thisagent's "EndlessWinterTracking", 25, thisagent);
\t$NewThread(thisagent's "activeScript", 1600, thisagent);
\t$Endless_Winter_Track(thisagent);
\t$Endless_Winter_Active(thisagent);
end

function Endless_Winter_Cleanup(agent thisagent)

declare

begin
\tIf ($isvalidgamepiece(thisagent) == False)
\t\treturn;

\t$KillThread(thisagent's "EndlessWinterTracking");
\t$KillThread(thisagent's "activeScript");
\t$DeleteGamePiece(thisagent);
end

function Endless_Winter_Track(agent thisagent)

declare
\tagent tracked_target;
\tcoordinate anchor_location;
\tcoordinate target_location;

begin
\tIf ($isvalidgamepiece(thisagent) == False)
\t\treturn;

\ttracked_target = $Parent(thisagent);
\tIf ($isvalidgamepiece(tracked_target))
\t\tIf ($IsDead(tracked_target) == False)
\t\t\tbegin
\t\t\t\tanchor_location = $LocationOf(thisagent);
\t\t\t\ttarget_location = $LocationOf(tracked_target);
\t\t\t\tIf (($GetX(anchor_location) != $GetX(target_location)) || ($GetY(anchor_location) != $GetY(target_location)))
\t\t\t\t\t$TeleportToUnit(thisagent, 50000, tracked_target, 0);
\t\t\tend
end

function Endless_Winter_Active(agent thisagent)

declare
\tlist targets;
\tagent target;
\tinteger distance;

begin
\tIf ($isvalidgamepiece(thisagent) == False)
\t\treturn;

\ttargets = $compile_enemies(thisagent, 175);

\tforeach target in targets do
\t\tbegin
\t\t\tdistance = $DistanceBetweenCoords(
\t\t\t\t$LocationOf(thisagent),
\t\t\t\t$LocationOf(target)
\t\t\t);
\t\t\tIf (distance <= #Phantom_Icy_Touch_Range)
\t\t\t\t$CreateMissile("endless_winter_missile", thisagent, target);
\t\t\tElse If (distance <= 80)
\t\t\t\t$CreateMissile("endless_winter_missile_middle", thisagent, target);
\t\t\tElse
\t\t\t\t$CreateMissile("endless_winter_missile_outer", thisagent, target);
\t\tend
end

function Endless_Winter_Inner_Missile_Hit(agent thisagent, agent target)

declare

begin
\t$Endless_Winter_Missile_Hit(target, 8, 2);
end

function Endless_Winter_Middle_Missile_Hit(agent thisagent, agent target)

declare

begin
\t$Endless_Winter_Missile_Hit(target, 6, 1);
end

function Endless_Winter_Outer_Missile_Hit(agent thisagent, agent target)

declare

begin
\t$Endless_Winter_Missile_Hit(target, 4, 1);
end

function Endless_Winter_Missile_Hit(agent target, integer damage, integer chill_tier)

declare

begin
\t$CreateEffector(target, "endless_winter_hit_effector", 0);
\t$player_spell_attack(target, damage, damage);
\t$Phantom_Apply_Chill_Tier(
\t\ttarget,
\t\t$GetSpellAttribute("ice_lance", "effector_duration"),
\t\tchill_tier
\t);
end

function Blizzard_Check(agent thisagent) is integer

declare
\tlist targets;

begin
\ttargets = $compile_enemies(thisagent, 175);
\tif ($listsize(targets) > 0)
\t\treturn 1;
\telse
\t\treturn 0;
end

function Blizzard_Hit(agent thisagent, agent target)

declare
\tlist targets;
\tagent dude;

begin
\t$createeffector(thisagent, "meteor_storm_effector2", 0);
\ttargets = $compile_enemies(thisagent, 175);

\tforeach dude in targets do
\t\tbegin
\t\t\t$createeffector(dude, "meteor_storm_effector2", 0);
\t\t\t$spell_attack(thisagent, dude, 18 + $GetAttribute(thisagent, #ATTRIB_ExperienceLevel));
\t\tend
end

"""


def phantom_gplproj() -> str:
    return """data="Phantom_Building_Data.dat"
data="Phantom_Hero_Data.dat"
data="Phantom_Items_Data.dat"

source="Phantom.gpl"
"""


def mod_xml() -> str:
    load_block = """\t\t\t\t<Load>
\t\t\t\t\t<CAM>Data\\phantom_textdata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_gpltext.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_maindata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_interfacedata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_mx_interfacedata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_voices.cam</CAM>
\t\t\t\t\t<Descriptions>Data\\phantom_units.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_actions.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_projectiles.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_overlays.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_particles.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_sounds.xml</Descriptions>
\t\t\t\t\t<GPL>
\t\t\t\t\t\t<Target>Data\\Phantom.bcd</Target>
\t\t\t\t\t\t<Source>GPL\\Phantom_Building_Data.dat</Source>
\t\t\t\t\t\t<Source>GPL\\Phantom_Hero_Data.dat</Source>
\t\t\t\t\t\t<Source>GPL\\Phantom_Items_Data.dat</Source>
\t\t\t\t\t\t<Source>GPL\\Phantom.gpl</Source>
\t\t\t\t\t</GPL>
\t\t\t\t</Load>"""
    return f"""<Majesty>
\t<Mod id="{{{MOD_ID}}}">
\t\t<Name>PhantomGuildPoc</Name>
\t\t<DisplayName lang="en_US">Phantoms Haunt POC</DisplayName>
\t\t<Description lang="en_US">
\t\t\t<Short>Adds the Phantoms Haunt and its recruitable Phantom heroes.</Short>
\t\t\t<Long/>
\t\t</Description>
\t\t<DataConfiguration>
\t\t\t<Dataset base="Majesty">
\t{load_block}
\t\t\t</Dataset>
\t\t\t<Dataset base="MajestyExpansion">
\t{load_block}
\t\t\t</Dataset>
\t\t</DataConfiguration>
\t</Mod>
</Majesty>
"""


def write_textdata_cam(source_textdata: Path, output_path: Path) -> None:
    unit_names = read_cam_entry(source_textdata, b"STRT", b"UNTN")
    action_names = read_cam_entry(source_textdata, b"STRT", b"ACTN")
    source_guild_menu = read_cam_entry(source_textdata, b"SMNU", SOURCE_RECRUIT_GUILD_DIALOG_ID)
    source_guild_strings = read_cam_entry(source_textdata, b"STRT", SOURCE_RECRUIT_GUILD_DIALOG_ID)
    patched_unit_names = patch_strt_strings(
        unit_names.data,
        {
            fourcc_id(HERO_ID): "Phantom",
            fourcc_id(BUILDING_TEXT_ID): "Phantoms Haunt",
            fourcc_id("PHIC"): "Frozen Cowl",
            fourcc_id("PHIR"): "Black Icerod",
        },
    )
    patched_action_names = patch_strt_strings(
        action_names.data,
        {
            fourcc_id("WRa2"): "Ice Lance",
            fourcc_id("WRa3"): "Frost Armor",
            fourcc_id("WRa4"): "Icy Touch",
            fourcc_id("WRa5"): "Endless Winter",
            fourcc_id("WRa6"): "Call to Grave",
            fourcc_id("WRa7"): "Eternal Soul",
        },
    )
    cloned_guild_menu = (
        source_guild_menu.data
        # AP07 uses AVd1 for the Elf guild member/count icon. The INTI token is
        # the broad panel texture source; INBg is mostly frame/control pieces.
        .replace(b"AVd1", b"PHM1")
        .replace(b"AVE1", b"PHM1")
        .replace(b"AVG1", b"PHM1")
        .replace(b"INTI", b"PHTI")
    )
    cloned_guild_strings = patch_indexed_strt_strings(
        source_guild_strings.data,
        {
            0: "PHANTOMS HAUNT",
            1: "RECRUIT Phantom         ",
            2: "Recruit a Phantom ",
            3: "Destroy this Phantoms Haunt.",
        },
    )

    write_cam(
        (
            CamSection(
                extension=b"SMNU",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(PHANTOM_GUILD_DIALOG_ID), data=cloned_guild_menu),
                ),
            ),
            CamSection(
                extension=b"STRT",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(b"UNTN"), data=patched_unit_names),
                    CamEntry(name=pad_name(b"ACTN"), data=patched_action_names),
                    CamEntry(name=pad_name(PHANTOM_GUILD_DIALOG_ID), data=cloned_guild_strings),
                ),
            ),
        ),
        output_path,
    )


def write_gpltext_cam(source_gpltext: Path, output_path: Path) -> None:
    quest_item_names = read_cam_entry(source_gpltext, b"STRT", b"QITM")
    help_text = read_cam_entry(source_gpltext, b"STRT", b"HPTX")
    equipment_item_text: dict[int, str] = {}
    for item_id, _, _, display_name, _ in phantom_equipment_item_specs():
        if "Cowl" in display_name:
            if item_id == PHANTOM_COWL_BASE_ITEM_ID:
                combination = 0
            else:
                combination = item_id - PHANTOM_COWL_VARIANT_FIRST_ID + 1
            struct_level, magic_level = divmod(combination, 4)
            bonus_text = (
                f"(+{2 + struct_level} armor, +{magic_level} magic armor)"
            )
        else:
            if item_id == PHANTOM_ICEROD_BASE_ITEM_ID:
                combination = 0
            else:
                combination = item_id - PHANTOM_ICEROD_VARIANT_FIRST_ID + 1
            struct_level, magic_level = divmod(combination, 4)
            bonus_text = (
                f"(+{8 + struct_level} damage, +{magic_level} magic, "
                f"+{5 + struct_level * 5} parry, +{10 + magic_level * 10} cast range)"
            )
        equipment_item_text[item_id] = f"{display_name}\n\x01FFDDAA{bonus_text}"

    patched_quest_item_names = patch_indexed_strt_strings(
        quest_item_names.data,
        {
            **equipment_item_text,
            82: "Frost Armor\n\x01FFDDAA(+10 armor)",
        },
    )
    patched_help_text = patch_strt_strings(
        help_text.data,
        {
            fourcc_id("hP34"): (
                "- Recruits Phantoms\n\n"
                "- Phantoms are ghostly ice casters with custom class gear\n\n"
                "\x01BCBCFFThe Phantoms Haunt gathers cold, restless spirits into service as arcane heroes. "
                "Its members fight like fragile spellcasters, striking from range with Ice Lance and other frost magic."
            ),
        },
    )
    write_cam(
        (
            CamSection(
                extension=b"STRT",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(b"QITM"), data=patched_quest_item_names),
                    CamEntry(name=pad_name(b"HPTX"), data=patched_help_text),
                ),
            ),
        ),
        output_path,
    )


def patch_indexed_strt_strings(data: bytes, replacements: dict[int, str]) -> bytes:
    count = struct.unpack_from("<H", data, 0)[0]
    version = data[2:4]
    offsets = list(struct.unpack_from(f"<{count}I", data, 4))
    records: list[tuple[int, bytes]] = []

    for index, offset in enumerate(offsets):
        string_id = u32(data, offset)
        string_start = offset + 4
        string_end = data.index(b"\x00", string_start)
        text = data[string_start:string_end]
        if index in replacements:
            text = replacements[index].encode("cp1252")
        records.append((string_id, text))

    target_count = max(max(replacements) + 1, len(records)) if replacements else len(records)
    while len(records) < target_count:
        index = len(records)
        text = replacements.get(index, "Unknown Item").encode("cp1252")
        records.append((index, text))

    for index, replacement in replacements.items():
        records[index] = (index, replacement.encode("cp1252"))

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


def write_maindata_cam(
    source_maindata: Path,
    output_path: Path,
    portrait_rgb: Path | None,
    hero_icon_rgb: Path | None,
    building_profile_rgb: Path | None,
    building_icon_rgb: Path | None,
    building_sprite_rgb_dir: Path | None,
    hero_sprite_png_dir: Path | None,
    interface_panel_rgb: Path | None,
    ice_lance_icon_rgb: Path | None,
    ice_lance_projectile_source_png: Path | None,
    icy_touch_impact_source_png: Path | None,
    frost_armor_crystal_source_png: Path | None,
    frost_armor_frozen_casing_source_png: Path | None,
    call_to_grave_portal_source_png: Path | None,
    eternal_soul_flame_source_png: Path | None,
    endless_winter_vortex_source_png: Path | None,
    endless_winter_hit_source_png: Path | None,
    endless_winter_missile_source_png: Path | None,
    ice_effect_maindata: Path | None,
) -> None:
    hero_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_PHANTOM_SPRITE_IMAGE).data
    hero_imag = replace_priestess_die_holds_with_directional_third_frames(hero_imag)
    building_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_BUILDING_IMAGE).data
    teleport_effect_imag = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_TELEPORT_EFFECT_IMAGE,
    ).data
    ice_lance_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICE_LANCE_ICON).data
    ice_lance_projectile = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICE_LANCE_PROJECTILE).data
    frost_armor_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_FROST_ARMOR_ICON).data
    icy_touch_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICY_TOUCH_ICON).data
    blizzard_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_BLIZZARD_ICON).data
    endless_winter_image = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_METEOR_STORM_IMAGE,
    ).data
    endless_winter_hit_image = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_METEOR_HIT_IMAGE,
    ).data
    endless_winter_missile_image = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_METEOR_MISSILE_IMAGE,
    ).data
    endless_winter_storm_particle_image = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_METEOR_STORM_PARTICLE_IMAGE,
    ).data
    endless_winter_missile_particle_image = read_cam_entry(
        source_maindata,
        b"IMAG",
        SOURCE_METEOR_MISSILE_PARTICLE_IMAGE,
    ).data
    endless_winter_image = replace_embedded_attachment_id(
        endless_winter_image,
        b"XL20",
        b"PHW4",
    )
    endless_winter_missile_image = replace_embedded_attachment_id(
        endless_winter_missile_image,
        b"XL21",
        b"PHW5",
    )
    tiles = read_cam_entries(source_maindata, b"TILE")
    palettes = read_cam_entries(source_maindata, b"SPLT")
    endless_winter_tile_indices = sorted(
        index
        for index in referenced_tile_indices(endless_winter_image, len(tiles))
        if index >= 8000
    )
    endless_winter_hit_tile_indices = sorted(
        index
        for index in referenced_tile_indices(endless_winter_hit_image, len(tiles))
        if index >= 8000
    )
    endless_winter_missile_tile_indices = sorted(
        index
        for index in referenced_tile_indices(endless_winter_missile_image, len(tiles))
        if index >= 8000
    )
    endless_winter_storm_particle_tile_indices = [
        tile_index
        for _set_id, frames in single_direction_imag_animation_sets(
            endless_winter_storm_particle_image
        )
        for _record_offset, tile_index in frames
        if tile_index
    ]
    endless_winter_missile_particle_tile_indices = [
        tile_index
        for _set_id, frames in single_direction_imag_animation_sets(
            endless_winter_missile_particle_image
        )
        for _record_offset, tile_index in frames
        if tile_index
    ]
    ice_lance_hit_effect: bytes | None = None
    ice_effect_tiles: list[bytes] = []
    source_ice_tile_indices: list[int] = []
    chill_icon_image: bytes | None = None
    empowered_chill_icon_image: bytes | None = None
    gravechill_icon_image: bytes | None = None
    gravechill_hit_image: bytes | None = None
    gravechill_hit_template_tiles: list[bytes] = []
    eternal_soul_icon_image: bytes | None = None
    eternal_soul_cast_image: bytes | None = None
    eternal_soul_cast_template_tiles: list[bytes] = []
    chill_icon_template_tiles: list[bytes] = []
    source_chill_icon_tile_indices: list[int] = []
    frost_armor_crystal_image: bytes | None = None
    frozen_small_image: bytes | None = None
    frozen_medium_image: bytes | None = None
    frozen_large_image: bytes | None = None
    call_to_grave_image: bytes | None = None
    if ice_effect_maindata:
        source_ice_lance_hit_effect = read_cam_entry(
            ice_effect_maindata,
            b"IMAG",
            FROST_FIELD_HIT_IMAGE,
        ).data
        source_ice_effect_tiles = read_cam_entries(ice_effect_maindata, b"TILE")
        source_ice_effect_palettes = read_cam_entries(ice_effect_maindata, b"SPLT")
        source_ice_tile_indices = sorted(
            animation_tile_indices(source_ice_lance_hit_effect, len(source_ice_effect_tiles))
        )
        ice_lance_hit_effect = source_ice_lance_hit_effect
        if source_ice_effect_palettes and source_ice_tile_indices:
            source_palette_index = tile_palette_index(source_ice_effect_tiles[source_ice_tile_indices[0]].data)
            if source_palette_index is not None and source_palette_index < len(source_ice_effect_palettes):
                source_palette_colors = splt_palette_colors(source_ice_effect_palettes[source_palette_index].data)
                target_palette_colors = splt_palette_colors(palettes[32].data)
                ice_effect_tiles = [
                    remap_indexed_v3_tile_to_palette(
                        source_ice_effect_tiles[index].data,
                        source_palette_colors,
                        32,
                        target_palette_colors,
                    )
                    for index in source_ice_tile_indices
                ]
        gravechill_hit_image = source_ice_lance_hit_effect
        gravechill_hit_template_tiles = ice_effect_tiles
        eternal_soul_cast_image = source_ice_lance_hit_effect
        eternal_soul_cast_template_tiles = ice_effect_tiles
        chill_icon_image = read_cam_entry(
            ice_effect_maindata,
            b"IMAG",
            CHILL_ICON_TEMPLATE_IMAGE,
        ).data
        source_chill_icon_tile_indices = sorted(
            animation_tile_indices(chill_icon_image, len(source_ice_effect_tiles))
        )
        chill_icon_template_tiles = [
            source_ice_effect_tiles[source_tile_index].data
            for source_tile_index in source_chill_icon_tile_indices
        ]
        empowered_chill_icon_image = chill_icon_image
        gravechill_icon_image = chill_icon_image
        eternal_soul_icon_image = chill_icon_image
        frost_armor_crystal_image = chill_icon_image
        frozen_small_image = chill_icon_image
        frozen_medium_image = chill_icon_image
        frozen_large_image = chill_icon_image
        call_to_grave_image = teleport_effect_imag

    phantom_sprite_tile_indices = sorted(
        index
        for index in referenced_tile_indices(hero_imag, len(tiles))
        if 4586 <= index <= 4793
    )
    building_sprite_rgb_paths = building_sprite_replacement_paths(building_sprite_rgb_dir)
    building_active_frame_paths = building_active_replacement_paths(building_sprite_rgb_dir)
    hero_sprite_png_paths = hero_sprite_replacement_paths(hero_sprite_png_dir)
    hero_cast_glow_paths = cast_glow_replacement_paths(hero_sprite_png_dir)
    if len(hero_cast_glow_paths) == 4:
        # Every Cast direction is replaced with a staff-local glow below, so
        # the four shared Priestess ground-swirl TILEs must not be copied into
        # the Phantom archive as immediately orphaned custom assets.
        phantom_sprite_tile_indices = [
            index for index in phantom_sprite_tile_indices if not 4788 <= index <= 4791
        ]
    building_sprite_tile_indices = sorted(
        referenced_low16_tile_indices(building_imag, len(tiles)) & set(building_sprite_rgb_paths)
    )
    if building_active_frame_paths:
        # The full eight-frame Active animation below replaces the stock
        # single-frame Active tile. Do not append an immediately orphaned copy.
        building_sprite_tile_indices = [
            tile_index for tile_index in building_sprite_tile_indices if tile_index != 1506
        ]

    tile_indices: set[int] = set()
    tile_indices.update(referenced_tile_indices(building_imag, len(tiles)))
    tile_indices.update(building_sprite_tile_indices)
    tile_indices.update(referenced_tile_indices(ice_lance_icon, len(tiles)))
    tile_indices.update(referenced_tile_indices(ice_lance_projectile, len(tiles)))
    tile_indices.update(referenced_tile_indices(frost_armor_icon, len(tiles)))
    tile_indices.update(referenced_tile_indices(icy_touch_icon, len(tiles)))
    tile_indices.update(referenced_tile_indices(blizzard_icon, len(tiles)))
    tile_indices.update(endless_winter_tile_indices)
    tile_indices.update(endless_winter_hit_tile_indices)
    tile_indices.update(endless_winter_missile_tile_indices)
    tile_indices.update(endless_winter_storm_particle_tile_indices)
    tile_indices.update(endless_winter_missile_particle_tile_indices)
    tile_indices.update((HERO_PORTRAIT_TILE, HERO_ICON_TILE, BUILDING_PROFILE_TILE, BUILDING_ICON_TILE, ICE_LANCE_ICON_TILE))
    max_tile_index = max(tile_indices)

    replacement_tiles = {
        HERO_PORTRAIT_TILE: tile_from_rgb(
            remap_tile_palette_index(tiles[HERO_PORTRAIT_TILE].data, PHANTOM_HERO_PORTRAIT_PALETTE_INDEX),
            palettes,
            portrait_rgb.read_bytes() if portrait_rgb else None,
        ),
        HERO_ICON_TILE: tile_from_rgb(
            remap_tile_palette_index(tiles[HERO_ICON_TILE].data, PHANTOM_HERO_ICON_PALETTE_INDEX),
            palettes,
            hero_icon_rgb.read_bytes() if hero_icon_rgb else None,
        ),
    }
    for frame_index, tile_index in enumerate(ICE_LANCE_PROJECTILE_TILES):
        replacement_tiles[tile_index] = generated_ice_lance_projectile_tile(
            tiles[tile_index].data,
            palettes,
            frame_index,
            len(ICE_LANCE_PROJECTILE_TILES),
        )
    ice_lance_icon = remap_imag_animation_sequence(ice_lance_icon, [204, 205, 206, 207, 208])
    extra_tiles: list[CamEntry] = []
    _ = ice_lance_icon_rgb

    directional_projectile_tile_indices = sorted(
        index
        for index in referenced_tile_indices(ice_lance_projectile, len(tiles))
        if index in ICE_LANCE_DIRECTIONAL_PROJECTILE_TILES
    )
    building_art_tile_replacements: dict[int, int] = {}
    if building_profile_rgb:
        custom_tile_index = max_tile_index + len(extra_tiles) + 1
        building_art_tile_replacements[BUILDING_PROFILE_TILE] = custom_tile_index
        extra_tiles.append(
            CamEntry(
                name=pad_name(b"PHG1Profile"),
                data=tile_from_rgb(
                    tiles[BUILDING_PROFILE_TILE].data,
                    palettes,
                    building_profile_rgb.read_bytes(),
                ),
            )
        )
    if building_icon_rgb:
        custom_tile_index = max_tile_index + len(extra_tiles) + 1
        building_art_tile_replacements[BUILDING_ICON_TILE] = custom_tile_index
        extra_tiles.append(
            CamEntry(
                name=pad_name(b"PHG1BuildIcon"),
                data=tile_from_rgb(
                    remap_tile_palette_index(tiles[BUILDING_ICON_TILE].data, BUILDING_SPRITE_PALETTE_INDEX),
                    palettes,
                    building_icon_rgb.read_bytes(),
                ),
            )
        )
    if building_art_tile_replacements:
        building_imag = remap_imag_low16_tile_indices(building_imag, building_art_tile_replacements)

    if building_sprite_tile_indices:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        building_tile_replacements: dict[int, int] = {}
        for offset, source_tile_index in enumerate(building_sprite_tile_indices):
            custom_tile_index = first_custom_tile_index + offset
            building_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHG1Bld{offset:04d}".encode("ascii")),
                    data=tile_from_png_native_size(
                        remap_tile_palette_index(tiles[source_tile_index].data, BUILDING_SPRITE_PALETTE_INDEX),
                        palettes,
                        building_sprite_rgb_paths[source_tile_index],
                    ),
                )
            )
        building_imag = remap_imag_low16_tile_indices(building_imag, building_tile_replacements)

    if building_active_frame_paths:
        active_frame_indices: list[int] = []
        for frame_index, path in enumerate(building_active_frame_paths):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            active_frame_indices.append(custom_tile_index)
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHG1Act{frame_index:02d}".encode("ascii")),
                    data=tile_from_png_native_size(
                        remap_tile_palette_index(tiles[1506].data, BUILDING_SPRITE_PALETTE_INDEX),
                        palettes,
                        path,
                    ),
                )
            )
        building_imag = replace_building_state_animation_tiles(
            building_imag,
            BUILDING_ACTIVE_SET_ID,
            active_frame_indices,
        )

    building_imag = remap_building_attachment_points(
        building_imag,
        BUILDING_DESTRUCTION_ATTACHMENT_REMAPS,
    )

    if directional_projectile_tile_indices:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        projectile_tile_replacements: dict[int, int] = {}
        for offset, source_tile_index in enumerate(directional_projectile_tile_indices):
            custom_tile_index = first_custom_tile_index + offset
            projectile_tile_replacements[source_tile_index] = custom_tile_index
            direction_index, frame_index = projectile_direction_frame_for_source_tile(source_tile_index)
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHp1IceTile{offset}".encode("ascii")),
                    data=generated_ice_lance_projectile_tile(
                        tiles[source_tile_index].data,
                        palettes,
                        frame_index,
                        ICE_LANCE_PROJECTILE_FRAMES_PER_DIRECTION,
                        projectile_angle_for_direction(direction_index),
                        ice_lance_projectile_source_png,
                    ),
                )
            )
        ice_lance_projectile = remap_imag_tile_indices(ice_lance_projectile, projectile_tile_replacements)

    if endless_winter_missile_tile_indices:
        winter_missile_replacements: dict[int, int] = {}
        fixed_missile_template = tiles[
            max(
                endless_winter_missile_tile_indices,
                key=lambda tile_index: (
                    struct.unpack_from("<H", tiles[tile_index].data, 2)[0]
                    * struct.unpack_from("<H", tiles[tile_index].data, 4)[0]
                ),
            )
        ].data
        for frame_index, source_tile_index in enumerate(
            endless_winter_missile_tile_indices
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            winter_missile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(
                        f"PHw3Snow{frame_index:02d}".encode("ascii")
                    ),
                    data=(
                        generated_endless_winter_missile_tile(
                            fixed_missile_template,
                            palettes,
                            endless_winter_missile_source_png,
                            len(endless_winter_missile_tile_indices)
                            - frame_index
                            - 1,
                        )
                        if endless_winter_missile_source_png
                        else blank_indexed_v3_tile(fixed_missile_template)
                    ),
                )
            )
        endless_winter_missile_image = remap_imag_tile_indices(
            endless_winter_missile_image,
            winter_missile_replacements,
        )

    for (
        particle_image,
        source_particle_tile_indices,
        tile_prefix,
    ) in (
        (
            endless_winter_storm_particle_image,
            endless_winter_storm_particle_tile_indices,
            b"PHw4Flake",
        ),
        (
            endless_winter_missile_particle_image,
            endless_winter_missile_particle_tile_indices,
            b"PHw5Flake",
        ),
    ):
        particle_replacements: dict[int, int] = {}
        fixed_particle_template = tiles[
            max(
                source_particle_tile_indices,
                key=lambda tile_index: (
                    struct.unpack_from("<H", tiles[tile_index].data, 2)[0]
                    * struct.unpack_from("<H", tiles[tile_index].data, 4)[0]
                ),
            )
        ].data
        for frame_index, source_tile_index in enumerate(
            source_particle_tile_indices
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            particle_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(
                        tile_prefix
                        + f"{frame_index:02d}".encode("ascii")
                    ),
                    data=(
                        generated_endless_winter_particle_tile(
                            fixed_particle_template,
                            palettes,
                            endless_winter_missile_source_png,
                            frame_index,
                            len(source_particle_tile_indices),
                        )
                        if endless_winter_missile_source_png
                        else blank_indexed_v3_tile(fixed_particle_template)
                    ),
                )
            )
        remapped_particle_image = remap_imag_tile_indices(
            particle_image,
            particle_replacements,
        )
        if tile_prefix == b"PHw4Flake":
            endless_winter_storm_particle_image = remapped_particle_image
        else:
            endless_winter_missile_particle_image = remapped_particle_image

    if phantom_sprite_tile_indices:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        phantom_sprite_tile_replacements: dict[int, int] = {}
        phantom_sprite_tiles_by_source: dict[int, bytes] = {}
        for offset, source_tile_index in enumerate(phantom_sprite_tile_indices):
            custom_tile_index = first_custom_tile_index + offset
            phantom_sprite_tile_replacements[source_tile_index] = custom_tile_index
            source_tile = tiles[source_tile_index].data
            if source_tile_index == 4786 and portrait_rgb:
                tile = tile_from_rgb(
                    remap_tile_palette_index(source_tile, PHANTOM_HERO_PORTRAIT_PALETTE_INDEX),
                    palettes,
                    portrait_rgb.read_bytes(),
                )
            elif source_tile_index == 4792 and hero_icon_rgb:
                tile = tile_from_rgb(
                    remap_tile_palette_index(source_tile, PHANTOM_HERO_ICON_PALETTE_INDEX),
                    palettes,
                    hero_icon_rgb.read_bytes(),
                )
            elif source_tile_index == HERO_INTERFACE_PANEL_TILE and interface_panel_rgb:
                tile = tile_from_rgb(
                    remap_tile_palette_index(source_tile, 32),
                    palettes,
                    interface_panel_rgb.read_bytes(),
                )
            elif source_tile_index in hero_sprite_png_paths:
                hero_direction = hero_sprite_direction_index(source_tile_index)
                shadow_source_path = (
                    None
                    if source_tile_index == 4787
                    else (
                        hero_sprite_png_paths[source_tile_index]
                        if 4779 <= source_tile_index <= 4785
                        else hero_sprite_png_paths.get(4586 + hero_direction * 8)
                    )
                )
                death_art = is_phantom_death_art_tile(source_tile_index)
                cast_body = is_phantom_cast_body_tile(source_tile_index)
                render_template_tile = source_tile
                if cast_body:
                    # Stock Priestess cast phases use differently sized TILE
                    # canvases. Reusing the first canvas for all four phases of
                    # a direction keeps the Phantom's dimensions, hotspot, and
                    # feet perfectly stable throughout the cast.
                    cast_direction = (source_tile_index - 4746) // 4
                    render_template_tile = tiles[4746 + cast_direction * 4].data
                tile = tile_from_png_source(
                    remap_tile_palette_index(render_template_tile, 32),
                    palettes,
                    hero_sprite_png_paths[source_tile_index],
                    scale_multiplier=hero_sprite_scale_multiplier(source_tile_index),
                    max_anchor_height=hero_sprite_max_anchor_height(source_tile_index),
                    target_art_height=hero_sprite_target_art_height(source_tile_index),
                    vertical_offset=hero_sprite_vertical_offset(source_tile_index),
                    shadow_strength=hero_sprite_shadow_strength(source_tile_index),
                    horizontal_alignment=hero_sprite_horizontal_alignment(source_tile_index),
                    shadow_png_path=shadow_source_path,
                    edge_margin=(
                        2
                        if death_art or cast_body or 4586 <= source_tile_index <= 4649
                        else 0
                    ),
                    body_base_offset=hero_sprite_body_base_offset(source_tile_index),
                )
            else:
                tile = recolored_priestess_phantom_sprite_tile(source_tile, palettes, source_tile_index)
            extra_tiles.append(
                CamEntry(
                    name=pad_name(
                        f"PHM1PhantomTile{source_tile_index - 4586}".encode("ascii")
                    ),
                    data=tile,
                )
            )
            phantom_sprite_tiles_by_source[source_tile_index] = tile
        hero_imag = remap_imag_low16_tile_indices(hero_imag, phantom_sprite_tile_replacements)
        if len(hero_cast_glow_paths) == 4:
            cast_glow_indices: dict[tuple[int, int], int] = {}
            for direction in range(8):
                # Detect the staff crystal once from the brightest cast phase.
                # Re-detecting it from every brightness-ramped body frame made
                # the glow's calculated anchor bounce vertically.
                anchor_body_tile = phantom_sprite_tiles_by_source.get(
                    4746 + direction * 4 + 3
                )
                if anchor_body_tile is None:
                    raise ValueError(
                        f"Missing generated cast anchor TILE for direction {direction}"
                    )
                for stage, glow_path in enumerate(hero_cast_glow_paths):
                    body_source_tile = 4746 + direction * 4 + stage
                    body_tile = phantom_sprite_tiles_by_source.get(body_source_tile)
                    if body_tile is None:
                        raise ValueError(
                            f"Missing generated cast body TILE {body_source_tile} "
                            f"for direction {direction}, stage {stage}"
                        )
                    custom_tile_index = max_tile_index + len(extra_tiles) + 1
                    cast_glow_indices[(direction, stage)] = custom_tile_index
                    extra_tiles.append(
                        CamEntry(
                            name=pad_name(
                                f"PHM1CastGlowD{direction}F{stage}".encode("ascii")
                            ),
                            data=cast_staff_glow_overlay_tile(
                                body_tile,
                                palettes,
                                glow_path,
                                direction,
                                stage,
                                anchor_body_tile=anchor_body_tile,
                            ),
                        )
                    )
            hero_imag = replace_cast_effect_frames_with_directional_glows(
                hero_imag,
                cast_glow_indices,
                {
                    direction: phantom_sprite_tile_replacements[4586 + direction * 8]
                    for direction in range(8)
                },
            )

    if ice_lance_hit_effect and ice_effect_tiles:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        ice_tile_replacements: dict[int, int] = {}
        for offset, (source_tile_index, tile_entry) in enumerate(zip(source_ice_tile_indices, ice_effect_tiles)):
            custom_tile_index = first_custom_tile_index + offset
            ice_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHo3IceTile{offset}".encode("ascii")),
                    data=tile_entry,
                )
            )
        ice_lance_hit_effect = remap_imag_animation_tiles(ice_lance_hit_effect, ice_tile_replacements)

    if chill_icon_image and chill_icon_template_tiles and source_chill_icon_tile_indices:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        chill_tile_replacements: dict[int, int] = {}
        frame_count = len(source_chill_icon_tile_indices)
        for frame_index, (source_tile_index, template_tile) in enumerate(
            zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
        ):
            custom_tile_index = first_custom_tile_index + frame_index
            chill_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHc1ChillTile{frame_index}".encode("ascii")),
                    data=generated_chill_snowflake_tile(
                        template_tile,
                        palettes,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        chill_icon_image = remap_imag_animation_tiles(
            chill_icon_image,
            chill_tile_replacements,
        )

    if (
        empowered_chill_icon_image
        and chill_icon_template_tiles
        and source_chill_icon_tile_indices
    ):
        empowered_chill_tile_replacements: dict[int, int] = {}
        frame_count = len(source_chill_icon_tile_indices)
        for frame_index, (source_tile_index, template_tile) in enumerate(
            zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            empowered_chill_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(
                        f"PHc3EmpChillTile{frame_index}".encode("ascii")
                    ),
                    data=generated_chill_snowflake_tile(
                        template_tile,
                        palettes,
                        frame_index,
                        frame_count,
                        empowered=True,
                    ),
                )
            )
        empowered_chill_icon_image = remap_imag_animation_tiles(
            empowered_chill_icon_image,
            empowered_chill_tile_replacements,
        )

    if (
        gravechill_icon_image
        and chill_icon_template_tiles
        and source_chill_icon_tile_indices
        and icy_touch_impact_source_png
    ):
        gravechill_tile_replacements: dict[int, int] = {}
        frame_count = len(source_chill_icon_tile_indices)
        for frame_index, (source_tile_index, template_tile) in enumerate(
            zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            gravechill_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHg1Skull{frame_index:02d}".encode("ascii")),
                    data=generated_gravechill_skull_tile(
                        template_tile,
                        palettes,
                        icy_touch_impact_source_png,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        gravechill_icon_image = remap_imag_animation_tiles(
            gravechill_icon_image,
            gravechill_tile_replacements,
        )

    if (
        gravechill_hit_image
        and gravechill_hit_template_tiles
        and source_ice_tile_indices
        and icy_touch_impact_source_png
    ):
        gravechill_hit_replacements: dict[int, int] = {}
        frame_count = len(source_ice_tile_indices)
        for frame_index, source_tile_index in enumerate(source_ice_tile_indices):
            # Frost Field's first two impact canvases are only 10x10 and
            # 22x22. That is useful for its growing ground burst, but it
            # crushes the skull's spectral formation stages into specks. Keep
            # the same six-frame one-shot record while flooring those two
            # canvases at the readable third-frame size.
            template_tile = gravechill_hit_template_tiles[max(2, frame_index)]
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            gravechill_hit_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHg2SkullHit{frame_index:02d}".encode("ascii")),
                    data=generated_gravechill_hit_tile(
                        template_tile,
                        palettes,
                        icy_touch_impact_source_png,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        gravechill_hit_image = remap_imag_animation_tiles(
            gravechill_hit_image,
            gravechill_hit_replacements,
        )

    if (
        eternal_soul_icon_image
        and chill_icon_template_tiles
        and source_chill_icon_tile_indices
        and eternal_soul_flame_source_png
    ):
        eternal_soul_icon_replacements: dict[int, int] = {}
        frame_count = len(source_chill_icon_tile_indices)
        for frame_index, (source_tile_index, template_tile) in enumerate(
            zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            eternal_soul_icon_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHe1FlameIcon{frame_index:02d}".encode("ascii")),
                    data=generated_eternal_soul_icon_tile(
                        template_tile,
                        palettes,
                        eternal_soul_flame_source_png,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        eternal_soul_icon_image = remap_imag_animation_tiles(
            eternal_soul_icon_image,
            eternal_soul_icon_replacements,
        )

    if (
        eternal_soul_cast_image
        and eternal_soul_cast_template_tiles
        and source_ice_tile_indices
        and eternal_soul_flame_source_png
    ):
        eternal_soul_cast_replacements: dict[int, int] = {}
        frame_count = len(source_ice_tile_indices)
        for frame_index, source_tile_index in enumerate(source_ice_tile_indices):
            # Frost Field changes canvas size as its burst expands. Use one
            # fixed final-frame canvas so the flame itself supplies all growth
            # and remains locked to the same attachment anchor.
            template_tile = eternal_soul_cast_template_tiles[-1]
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            eternal_soul_cast_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHe2FlameCast{frame_index:02d}".encode("ascii")),
                    data=generated_eternal_soul_cast_tile(
                        template_tile,
                        palettes,
                        eternal_soul_flame_source_png,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        eternal_soul_cast_image = remap_imag_animation_tiles(
            eternal_soul_cast_image,
            eternal_soul_cast_replacements,
        )

    if (
        frost_armor_crystal_image
        and chill_icon_template_tiles
        and source_chill_icon_tile_indices
        and frost_armor_crystal_source_png
    ):
        crystal_tile_replacements: dict[int, int] = {}
        frame_count = len(source_chill_icon_tile_indices)
        for frame_index, (source_tile_index, template_tile) in enumerate(
            zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            crystal_tile_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHf1Crystal{frame_index:02d}".encode("ascii")),
                    data=generated_frost_armor_crystal_tile(
                        template_tile,
                        palettes,
                        frost_armor_crystal_source_png,
                        frame_index,
                        frame_count,
                    ),
                )
            )
        frost_armor_crystal_image = remap_imag_animation_tiles(
            frost_armor_crystal_image,
            crystal_tile_replacements,
        )

    frozen_variants = (
        ("PHf2Frozen", frozen_small_image, (58, 72)),
        ("PHf3Frozen", frozen_medium_image, (82, 104)),
        ("PHf4Frozen", frozen_large_image, (116, 144)),
    )
    remapped_frozen_images: list[bytes | None] = []
    for tile_prefix, frozen_image, canvas_size in frozen_variants:
        if (
            frozen_image
            and chill_icon_template_tiles
            and source_chill_icon_tile_indices
            and frost_armor_frozen_casing_source_png
        ):
            frozen_tile_replacements: dict[int, int] = {}
            frame_count = len(source_chill_icon_tile_indices)
            for frame_index, (source_tile_index, template_tile) in enumerate(
                zip(source_chill_icon_tile_indices, chill_icon_template_tiles)
            ):
                custom_tile_index = max_tile_index + len(extra_tiles) + 1
                frozen_tile_replacements[source_tile_index] = custom_tile_index
                extra_tiles.append(
                    CamEntry(
                        name=pad_name(f"{tile_prefix}{frame_index:02d}".encode("ascii")),
                        data=generated_frost_armor_casing_tile(
                            template_tile,
                            palettes,
                            frost_armor_frozen_casing_source_png,
                            frame_index,
                            frame_count,
                            canvas_size,
                        ),
                    )
                )
            frozen_image = remap_imag_animation_tiles(
                frozen_image,
                frozen_tile_replacements,
            )
        remapped_frozen_images.append(frozen_image)
    frozen_small_image, frozen_medium_image, frozen_large_image = remapped_frozen_images

    if (
        call_to_grave_image
        and call_to_grave_portal_source_png
    ):
        portal_sets = single_direction_imag_animation_sets(call_to_grave_image)
        portal_phase_by_set = {80: "open", 64: "hold", 96: "close"}
        if {set_id for set_id, _frames in portal_sets} != set(portal_phase_by_set):
            raise ValueError(
                "Wizard Teleport IMAG no longer has the expected "
                "open/hold/close animation sets"
            )
        call_to_grave_replacements: dict[int, int] = {}
        portal_tile_number = 0
        for set_id, frames in portal_sets:
            phase = portal_phase_by_set[set_id]
            for frame_index, (_record_offset, source_tile_index) in enumerate(frames):
                if source_tile_index in call_to_grave_replacements:
                    continue
                progress = frame_index / max(1, len(frames) - 1)
                if phase == "open":
                    openness = 0.10 + 0.90 * progress
                    visible_alpha = 0.24 + 0.76 * progress
                elif phase == "close":
                    openness = 1.0 - 0.90 * progress
                    visible_alpha = 1.0 - 0.76 * progress
                else:
                    openness = 1.0
                    visible_alpha = 1.0
                custom_tile_index = max_tile_index + len(extra_tiles) + 1
                call_to_grave_replacements[source_tile_index] = custom_tile_index
                extra_tiles.append(
                    CamEntry(
                        name=pad_name(
                            f"PHc2Portal{portal_tile_number:02d}".encode("ascii")
                        ),
                        data=generated_call_to_grave_portal_tile(
                            tiles[source_tile_index].data,
                            palettes,
                            call_to_grave_portal_source_png,
                            openness,
                            visible_alpha,
                        ),
                    )
                )
                portal_tile_number += 1
        call_to_grave_image = remap_imag_tile_indices(
            call_to_grave_image,
            call_to_grave_replacements,
        )

    if endless_winter_vortex_source_png and endless_winter_tile_indices:
        winter_replacements: dict[int, int] = {}
        fixed_winter_template = tiles[
            max(
                endless_winter_tile_indices,
                key=lambda tile_index: (
                    struct.unpack_from("<H", tiles[tile_index].data, 2)[0]
                    * struct.unpack_from("<H", tiles[tile_index].data, 4)[0]
                ),
            )
        ].data
        for frame_index, source_tile_index in enumerate(endless_winter_tile_indices):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            winter_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHw1Storm{frame_index:02d}".encode("ascii")),
                    data=generated_endless_winter_vortex_tile(
                        fixed_winter_template,
                        palettes,
                        endless_winter_vortex_source_png,
                        frame_index,
                        len(endless_winter_tile_indices),
                    ),
                )
            )
        endless_winter_image = remap_imag_tile_indices(
            endless_winter_image,
            winter_replacements,
        )

    if endless_winter_hit_source_png and endless_winter_hit_tile_indices:
        winter_hit_replacements: dict[int, int] = {}
        fixed_hit_template = tiles[endless_winter_hit_tile_indices[-2]].data
        for frame_index, source_tile_index in enumerate(
            endless_winter_hit_tile_indices
        ):
            custom_tile_index = max_tile_index + len(extra_tiles) + 1
            winter_hit_replacements[source_tile_index] = custom_tile_index
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHw2Hit{frame_index:02d}".encode("ascii")),
                    data=generated_endless_winter_hit_tile(
                        fixed_hit_template,
                        palettes,
                        endless_winter_hit_source_png,
                        frame_index,
                        len(endless_winter_hit_tile_indices),
                        (
                            struct.unpack_from(
                                "<H",
                                tiles[source_tile_index].data,
                                2,
                            )[0]
                            * struct.unpack_from(
                                "<H",
                                tiles[source_tile_index].data,
                                4,
                            )[0]
                        )
                        / max(
                            struct.unpack_from("<H", tiles[index].data, 2)[0]
                            * struct.unpack_from("<H", tiles[index].data, 4)[0]
                            for index in endless_winter_hit_tile_indices
                        ),
                    ),
                )
            )
        endless_winter_hit_image = remap_imag_tile_indices(
            endless_winter_hit_image,
            winter_hit_replacements,
        )

    # Teleporting a Character resets its Walk animation state. Keep the
    # periodically relocated GPL spell unit as a fully transparent anchor and
    # render the vortex once as an attached overlay; the overlay follows the
    # anchor without restarting its own animation on every pulse.
    endless_winter_anchor_image = replace_embedded_attachment_id(
        endless_winter_image,
        b"PHW4",
        b"\x00\x00\x00\x00",
    )
    anchor_blank_tile_index = max_tile_index + len(extra_tiles) + 1
    anchor_template_index = max(
        endless_winter_tile_indices,
        key=lambda tile_index: (
            struct.unpack_from("<H", tiles[tile_index].data, 2)[0]
            * struct.unpack_from("<H", tiles[tile_index].data, 4)[0]
        ),
    )
    extra_tiles.append(
        CamEntry(
            name=pad_name(b"PHw6Anchor00"),
            data=blank_indexed_v3_tile(tiles[anchor_template_index].data),
        )
    )
    anchor_tile_replacements = {
        tile_index: anchor_blank_tile_index
        for _set_id, frames in single_direction_imag_animation_sets(
            endless_winter_anchor_image
        )
        for _record_offset, tile_index in frames
        if tile_index
    }
    endless_winter_anchor_image = remap_imag_tile_indices(
        endless_winter_anchor_image,
        anchor_tile_replacements,
    )

    palette_indices: set[int] = set()
    tile_entries: list[CamEntry] = []
    for tile_index in range(max_tile_index + 1):
        tile = replacement_tiles.get(tile_index, tiles[tile_index].data)

        palette_index = tile_palette_index(tile)
        if palette_index is not None and palette_index < len(palettes):
            palette_indices.add(palette_index)
        tile_entries.append(CamEntry(name=tiles[tile_index].name, data=tile))

    tile_entries.extend(extra_tiles)
    for tile_entry in extra_tiles:
        palette_index = tile_palette_index(tile_entry.data)
        if palette_index is not None:
            palette_indices.add(palette_index)

    max_palette_index = max(palette_indices)
    palette_entries = tuple(
        CamEntry(
            name=palettes[index].name,
            data=(
                splt_with_color_replacements(
                    palettes[index].data,
                    {
                        247: (156, 33, 24),
                        248: (178, 0, 178),
                        249: (204, 0, 204),
                        250: (229, 0, 229),
                    },
                )
                if index == BUILDING_SPRITE_PALETTE_INDEX
                else palettes[index].data
            ),
        )
        for index in range(max_palette_index + 1)
    )
    image_entries = [
        CamEntry(name=pad_name(PHANTOM_HERO_IMAGE), data=hero_imag),
        CamEntry(name=pad_name(PHANTOM_BUILDING_IMAGE), data=building_imag),
        CamEntry(name=pad_name(PHANTOM_ICE_LANCE_ICON), data=ice_lance_icon),
        CamEntry(name=pad_name(PHANTOM_ICE_LANCE_PROJECTILE), data=ice_lance_projectile),
        CamEntry(name=pad_name(PHANTOM_FROST_ARMOR_ICON), data=frost_armor_icon),
        CamEntry(name=pad_name(PHANTOM_ICY_TOUCH_ICON), data=icy_touch_icon),
        CamEntry(name=pad_name(PHANTOM_BLIZZARD_ICON), data=blizzard_icon),
    ]
    if ice_lance_hit_effect:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_ICE_LANCE_HIT_IMAGE), data=ice_lance_hit_effect))
    if chill_icon_image:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_CHILL_ICON_IMAGE), data=chill_icon_image))
    if empowered_chill_icon_image:
        image_entries.append(
            CamEntry(
                name=pad_name(PHANTOM_EMPOWERED_CHILL_ICON_IMAGE),
                data=empowered_chill_icon_image,
            )
        )
    if gravechill_icon_image:
        image_entries.append(
            CamEntry(name=pad_name(PHANTOM_GRAVECHILL_ICON_IMAGE), data=gravechill_icon_image)
        )
    if gravechill_hit_image:
        image_entries.append(
            CamEntry(name=pad_name(PHANTOM_GRAVECHILL_HIT_IMAGE), data=gravechill_hit_image)
        )
    if frost_armor_crystal_image:
        image_entries.append(
            CamEntry(name=pad_name(PHANTOM_FROST_ARMOR_CRYSTAL_IMAGE), data=frost_armor_crystal_image)
        )
    if frozen_small_image:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_FROZEN_SMALL_IMAGE), data=frozen_small_image))
    if frozen_medium_image:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_FROZEN_MEDIUM_IMAGE), data=frozen_medium_image))
    if frozen_large_image:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_FROZEN_LARGE_IMAGE), data=frozen_large_image))
    if call_to_grave_image:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_CALL_TO_GRAVE_IMAGE), data=call_to_grave_image))
    if eternal_soul_icon_image:
        image_entries.append(
            CamEntry(
                name=pad_name(PHANTOM_ETERNAL_SOUL_ICON_IMAGE),
                data=eternal_soul_icon_image,
            )
        )
    if eternal_soul_cast_image:
        image_entries.append(
            CamEntry(
                name=pad_name(PHANTOM_ETERNAL_SOUL_CAST_IMAGE),
                data=eternal_soul_cast_image,
            )
        )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_IMAGE),
            data=endless_winter_image,
        )
    )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_HIT_IMAGE),
            data=endless_winter_hit_image,
        )
    )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_MISSILE_IMAGE),
            data=endless_winter_missile_image,
        )
    )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_STORM_PARTICLE_IMAGE),
            data=endless_winter_storm_particle_image,
        )
    )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_MISSILE_PARTICLE_IMAGE),
            data=endless_winter_missile_particle_image,
        )
    )
    image_entries.append(
        CamEntry(
            name=pad_name(PHANTOM_ENDLESS_WINTER_ANCHOR_IMAGE),
            data=endless_winter_anchor_image,
        )
    )
    write_cam(
        (
            CamSection(
                extension=b"IMAG",
                padding=b"\x00\x00\x00\x00",
                entries=tuple(image_entries),
            ),
            CamSection(extension=b"TILE", padding=b"\x01\x00\x00\x00", entries=tuple(tile_entries)),
            CamSection(extension=b"SPLT", padding=b"\x00\x00\x00\x00", entries=palette_entries),
        ),
        output_path,
    )


def write_mx_interfacedata_cam(
    source_interfacedata: Path,
    output_path: Path,
    dark_staff_mx_icon_rgb: Path | None,
) -> None:
    weapon_image = read_cam_entry(source_interfacedata, b"IMAG", WEAPON_ICON_IMAGE).data
    tiles = read_cam_entries(source_interfacedata, b"TILE")

    replacement_tiles: dict[int, bytes] = {}
    for tile_index in MX_STAFF_ICON_TILES:
        if dark_staff_mx_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], dark_staff_mx_icon_rgb.read_bytes())

    tile_indices = referenced_tile_indices(weapon_image, len(tiles))
    tile_indices.update(replacement_tiles)
    max_tile_index = max(tile_indices)
    tile_entries = tuple(
        CamEntry(name=tiles[tile_index].name, data=replacement_tiles.get(tile_index, tiles[tile_index].data))
        for tile_index in range(max_tile_index + 1)
    )

    write_cam(
        (
            CamSection(
                extension=b"IMAG",
                padding=b"\x00\x00\x00\x00",
                entries=(CamEntry(name=pad_name(WEAPON_ICON_IMAGE), data=weapon_image),),
            ),
            CamSection(extension=b"TILE", padding=b"\x01\x00\x00\x00", entries=tile_entries),
        ),
        output_path,
    )


def write_interfacedata_cam(
    source_interfacedata: Path,
    output_path: Path,
    ice_lance_spell_icon_rgb: Path | None,
    frost_armor_spell_icon_rgb: Path | None,
    blizzard_spell_icon_rgb: Path | None,
    call_to_grave_spell_icon_rgb: Path | None,
    phantom_cowl_icon_rgb: Path | None,
    dark_staff_small_icon_rgb: Path | None,
    dark_staff_icon_rgb: Path | None,
    control_panel_rgb: Path | None,
) -> None:
    icon_images = {
        SPELL_LIST_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", SPELL_LIST_ICON_IMAGE).data,
        WEAPON_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", WEAPON_ICON_IMAGE).data,
        ARMOR_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", ARMOR_ICON_IMAGE).data,
    }
    raw_texture_image = read_cam_entry(source_interfacedata, b"IMAG", RAW_TEXTURES_IMAGE).data
    phantom_raw_texture_image = raw_texture_image
    tiles = read_cam_entries(source_interfacedata, b"TILE")

    replacement_tiles: dict[int, bytes] = {}
    for tile_index in ICE_LANCE_SPELL_ICON_TILES:
        if ice_lance_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], ice_lance_spell_icon_rgb.read_bytes())
    for tile_index in FROST_ARMOR_SPELL_ICON_TILES:
        if frost_armor_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], frost_armor_spell_icon_rgb.read_bytes())
    for tile_index in ICY_TOUCH_SPELL_ICON_TILES:
        replacement_tiles[tile_index] = tiles[FIRE_BLAST_SPELL_ICON_TILE].data
    for tile_index in BLIZZARD_SPELL_ICON_TILES:
        if blizzard_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], blizzard_spell_icon_rgb.read_bytes())
    for tile_index in CALL_TO_GRAVE_SPELL_ICON_TILES:
        if call_to_grave_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], call_to_grave_spell_icon_rgb.read_bytes())
    for tile_index in ETERNAL_SOUL_SPELL_ICON_TILES:
        replacement_tiles[tile_index] = replacement_tiles.get(
            FROST_ARMOR_SPELL_ICON_TILES[0],
            tiles[FROST_ARMOR_SPELL_ICON_TILES[0]].data,
        )
    for tile_index in LEATHER_ARMOR_ICON_TILES:
        if phantom_cowl_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], phantom_cowl_icon_rgb.read_bytes())
    for tile_index in STAFF_ICON_TILES:
        if dark_staff_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], dark_staff_icon_rgb.read_bytes())
    for tile_index in STAFF_SMALL_ICON_TILES:
        if dark_staff_small_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], dark_staff_small_icon_rgb.read_bytes())
    base_tile_indices: set[int] = set(replacement_tiles)
    for image in icon_images.values():
        base_tile_indices.update(referenced_tile_indices(image, len(tiles)))
    base_tile_indices.update(referenced_tile_indices(raw_texture_image, len(tiles)))
    base_max_tile_index = max(base_tile_indices)

    extra_tiles: list[CamEntry] = []
    if control_panel_rgb:
        custom_tile_index = base_max_tile_index + len(extra_tiles) + 1
        # The recruit panel backing is an INTI raw-textures tile, not the
        # tempting INBgbuilding dialog image record.
        phantom_raw_texture_image = remap_imag_tile_indices(
            raw_texture_image,
            {BUILDING_DIALOG_BACKING_TILE: custom_tile_index},
        )
        extra_tiles.append(
            CamEntry(
                name=pad_name(b"PHTIPanel0001"),
                data=tile_v1_embedded_from_rgb(
                    tiles[BUILDING_DIALOG_BACKING_TILE].data,
                    control_panel_rgb.read_bytes(),
                ),
            )
        )

    tile_entries = list(
        CamEntry(name=tiles[tile_index].name, data=replacement_tiles.get(tile_index, tiles[tile_index].data))
        for tile_index in range(base_max_tile_index + 1)
    )
    tile_entries.extend(extra_tiles)

    write_cam(
        (
            CamSection(
                extension=b"IMAG",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    *tuple(CamEntry(name=pad_name(name), data=data) for name, data in icon_images.items()),
                    CamEntry(name=pad_name(PHANTOM_RAW_TEXTURES_IMAGE), data=phantom_raw_texture_image),
                ),
            ),
            CamSection(extension=b"TILE", padding=b"\x01\x00\x00\x00", entries=tuple(tile_entries)),
        ),
        output_path,
    )


def tile_from_rgb(original_tile: bytes, palettes: list[CamEntry], rgb: bytes | None) -> bytes:
    if rgb is None:
        return original_tile
    if len(original_tile) < 26:
        return original_tile

    version = struct.unpack_from("<H", original_tile, 0)[0]
    if version == 3:
        return tile_v3_from_rgb(original_tile, palettes, rgb)
    if version != 1:
        return original_tile

    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    row_stride = struct.unpack_from("<H", original_tile, 6)[0]
    expected_rgb_size = width * height * 3
    if len(rgb) != expected_rgb_size:
        raise ValueError(
            f"Expected {expected_rgb_size} RGB bytes for {width}x{height} tile, got {len(rgb)}"
        )

    if row_stride == width * 2:
        output = bytearray(original_tile[:26])
        for offset in range(0, len(rgb), 3):
            red = rgb[offset]
            green = rgb[offset + 1]
            blue = rgb[offset + 2]
            rgb565 = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
            output += struct.pack("<H", rgb565)

        image_plane_size = row_stride * height
        if len(original_tile) > 26 + image_plane_size:
            output += original_tile[26 + image_plane_size :]
        return bytes(output)

    colors = tile_palette_colors(original_tile, palettes)
    if colors is None:
        return original_tile

    output = bytearray(original_tile[:26])
    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            output.append(nearest_palette_index(rgb[offset], rgb[offset + 1], rgb[offset + 2], colors))
        for _ in range(max(0, row_stride - width)):
            output.append(0)

    image_plane_size = row_stride * height
    if len(original_tile) > 26 + image_plane_size:
        output += original_tile[26 + image_plane_size :]

    return bytes(output)


def tile_v1_embedded_from_rgb(original_tile: bytes, rgb: bytes) -> bytes:
    if len(original_tile) < 26 or struct.unpack_from("<H", original_tile, 0)[0] != 1:
        return original_tile

    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    row_stride = struct.unpack_from("<H", original_tile, 6)[0]
    if len(rgb) != width * height * 3 or row_stride < width or row_stride == width * 2:
        return original_tile

    from PIL import Image

    source = Image.frombytes("RGB", (width, height), rgb)
    quantized = source.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    raw_palette = quantized.getpalette() or []

    output = bytearray(original_tile[:26])
    for y in range(height):
        for x in range(width):
            output.append(min(255, int(quantized.getpixel((x, y))) + 1))
        for _ in range(max(0, row_stride - width)):
            output.append(0)

    original_palette_offset = struct.unpack_from("<I", original_tile, 22)[0]
    original_palette_tail = (
        original_tile[original_palette_offset:]
        if 0 <= original_palette_offset < len(original_tile)
        else b""
    )
    palette_prefix = original_palette_tail[:8]
    palette_suffix = original_palette_tail[8 + 256 * 4 :]
    new_palette_offset = len(output)
    struct.pack_into("<H", output, 20, 1)
    struct.pack_into("<I", output, 22, new_palette_offset)
    output += palette_prefix or b"\x00\x00\x00\x01\x00\x00\x00\x00"
    output += b"\x00\x00\x00\x00"
    for index in range(255):
        offset = index * 3
        if offset + 2 < len(raw_palette):
            red, green, blue = raw_palette[offset], raw_palette[offset + 1], raw_palette[offset + 2]
        else:
            red, green, blue = (0, 0, 0)
        output += bytes((red, green, blue, 0))
    output += palette_suffix
    return bytes(output)


def fit_rgb_to_size(
    rgb: bytes,
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> bytes:
    if len(rgb) == target_width * target_height * 3:
        return rgb
    if len(rgb) != source_width * source_height * 3:
        raise ValueError(
            f"Expected {source_width * source_height * 3} RGB bytes for source image, got {len(rgb)}"
        )

    from PIL import Image

    source = Image.frombytes("RGB", (source_width, source_height), rgb)
    target = Image.new("RGB", (target_width, target_height), (0, 0, 0))
    x = (target_width - source_width) // 2
    y = (target_height - source_height) // 2
    target.paste(source, (x, y))
    return target.tobytes()


def phantom_building_dialog_frame_tile(original_tile: bytes, panel_rgb: bytes) -> bytes:
    decoded = decode_indexed_v3_tile(original_tile)
    if decoded is None:
        return original_tile

    height, width, pixels = decoded
    if len(panel_rgb) != width * height * 3:
        return original_tile

    remapped, palette = quantize_phantom_building_dialog_pixels(
        original_tile,
        panel_rgb,
        width,
        height,
        pixels,
    )
    return encode_indexed_v3_tile_with_embedded_palette(original_tile, remapped, palette)


def quantize_phantom_building_dialog_pixels(
    original_tile: bytes,
    rgb: bytes,
    width: int,
    height: int,
    source_pixels: list[list[int]],
) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    from PIL import Image

    source_colors = tile_palette_colors(original_tile, [])
    if source_colors is None:
        source_colors = [(index, index, index) for index in range(256)]

    source = Image.frombytes("RGB", (width, height), rgb)
    fill_mask = [[False for _ in range(width)] for _ in range(height)]
    used_indices = {0}
    for y in range(height):
        for x in range(width):
            value = source_pixels[y][x]
            if value != 0 and is_building_dialog_key_index(value, source_colors):
                fill_mask[y][x] = False
                continue
            if value != 0 and is_building_dialog_repaintable_background_pixel(x, y, value, source_colors):
                fill_mask[y][x] = True
            elif value != 0:
                used_indices.add(value)
            else:
                fill_mask[y][x] = is_phantom_building_dialog_fill_pixel(x, y)

    custom_indices = [
        index
        for index in range(1, 247)
        if index not in used_indices and not is_building_dialog_key_index(index, source_colors)
    ]
    if not custom_indices:
        return source_pixels, source_colors

    fill_points: list[tuple[int, int]] = []
    fill_colors: list[tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if fill_mask[y][x]:
                fill_points.append((x, y))
                fill_colors.append(source.getpixel((x, y)))

    if not fill_colors:
        return source_pixels, source_colors

    fill_source = Image.new("RGB", (len(fill_colors), 1), (0, 0, 0))
    fill_source.putdata(fill_colors)
    quantized = fill_source.quantize(colors=min(255, len(custom_indices)), method=Image.Quantize.MEDIANCUT)
    raw_palette = quantized.getpalette() or []
    palette = list(source_colors)
    for index, palette_index in enumerate(custom_indices):
        offset = index * 3
        if offset + 2 < len(raw_palette):
            red = raw_palette[offset]
            green = raw_palette[offset + 1]
            blue = raw_palette[offset + 2]
            if red > 100 and blue > 90 and green < 100:
                red = min(red, 70)
                green = max(green, 55)
                blue = max(blue, 125)
            palette[palette_index] = (
                red,
                green,
                blue,
            )

    remapped = [
        [
            0 if is_building_dialog_key_index(value, source_colors) else value
            for value in row
        ]
        for row in source_pixels
    ]
    for source_index, (x, y) in enumerate(fill_points):
        quantized_index = min(int(quantized.getpixel((source_index, 0))), len(custom_indices) - 1)
        remapped[y][x] = custom_indices[quantized_index]

    return remapped, palette


def is_phantom_building_dialog_fill_pixel(x: int, y: int) -> bool:
    # The stock frame tile has transparent holes where other UI pieces are
    # drawn. Fill the general backing area, but keep the building portrait
    # window and outer transparent gutters clear.
    if x < 3 or x >= 199 or y < 3 or y >= 242:
        return False
    if 48 <= x < 154 and 25 <= y < 131:
        return False
    return True


def is_building_dialog_repaintable_background_pixel(
    x: int,
    y: int,
    index: int,
    colors: list[tuple[int, int, int]],
) -> bool:
    if not is_phantom_building_dialog_fill_pixel(x, y):
        return False
    if index <= 0 or index >= len(colors):
        return False

    red, green, blue = colors[index]
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    parchment = red > 135 and green > 110 and blue > 70
    gold_or_bronze_trim = red > 90 and green > 55 and red >= blue * 1.45 and green >= blue * 1.10
    bright_trim = luminance > 150
    if parchment or gold_or_bronze_trim or bright_trim:
        return False

    return True


def is_building_dialog_key_index(index: int, colors: list[tuple[int, int, int]]) -> bool:
    if index == 0 or index >= len(colors):
        return index == 0
    red, green, blue = colors[index]
    return index >= 247 or (red > 100 and blue > 90 and green < 100)


def hero_sprite_scale_multiplier(source_tile_index: int) -> float:
    if 4722 <= source_tile_index <= 4745 or 4779 <= source_tile_index <= 4787:
        return 1.0
    if 4746 <= source_tile_index <= 4777:
        # Cast bodies previously bypassed the 1.12 multiplier used by Stand,
        # Hover, Attack, and Special, making the Phantom visibly contract when
        # a spell began.
        return 1.12
    return 1.12


def hero_sprite_max_anchor_height(source_tile_index: int) -> int | None:
    # The stock shared dissolve records use progressively enormous canvases for
    # effects. Scaling replacement character art to those per-frame bounds
    # makes the Phantom balloon several times before becoming a gravestone.
    if 4778 <= source_tile_index <= 4785:
        return 45
    return None


def hero_sprite_target_art_height(source_tile_index: int) -> int | None:
    """Normalize motion and casting to the approved Stand size by direction."""
    if 4586 <= source_tile_index <= 4649 or 4746 <= source_tile_index <= 4777:
        direction = hero_sprite_direction_index(source_tile_index)
        return PHANTOM_APPROVED_STAND_BODY_HEIGHTS[direction]
    return None


def hero_sprite_vertical_offset(source_tile_index: int) -> int:
    return 0


def hero_sprite_body_base_offset(source_tile_index: int) -> int | None:
    if 4746 <= source_tile_index <= 4777:
        direction = (source_tile_index - 4746) // 4
        # Match each direction's approved Stand robe base. The extra source
        # canvas space is added above the hotspot, never below the feet.
        return (10, 9, 10, 10, 9, 10, 10, 9)[direction]
    if 4722 <= source_tile_index <= 4745:
        return 12
    if 4779 <= source_tile_index <= 4785:
        return 8
    if source_tile_index == 4787:
        return 22
    return None


def hero_sprite_shadow_strength(source_tile_index: int) -> float:
    if 4778 <= source_tile_index <= 4785:
        return max(0.12, 1.0 - (source_tile_index - 4778) / 7.0)
    return 1.0


def hero_sprite_horizontal_alignment(source_tile_index: int) -> str:
    return "right" if hero_sprite_direction_index(source_tile_index) >= 4 else "left"


def hero_sprite_direction_index(source_tile_index: int) -> int:
    direction = 0
    if 4586 <= source_tile_index <= 4649:
        direction = min(7, (source_tile_index - 4586) // 8)
    elif 4650 <= source_tile_index <= 4657:
        direction = min(7, source_tile_index - 4650)
    elif 4658 <= source_tile_index <= 4689:
        direction = min(7, (source_tile_index - 4658) // 4)
    elif 4690 <= source_tile_index <= 4721:
        direction = min(7, (source_tile_index - 4690) // 4)
    elif 4722 <= source_tile_index <= 4745:
        direction = min(7, (source_tile_index - 4722) // 3)
    elif 4746 <= source_tile_index <= 4777:
        direction = min(7, (source_tile_index - 4746) // 4)
    return direction


def is_phantom_death_art_tile(source_tile_index: int) -> bool:
    return (
        4722 <= source_tile_index <= 4745
        or 4779 <= source_tile_index <= 4785
        or source_tile_index == 4787
    )


def is_phantom_cast_body_tile(source_tile_index: int) -> bool:
    return 4746 <= source_tile_index <= 4777


def tile_from_png_source(
    original_tile: bytes,
    palettes: list[CamEntry],
    png_path: Path,
    *,
    scale_multiplier: float = 1.0,
    max_anchor_height: int | None = None,
    target_art_height: int | None = None,
    vertical_offset: int = 0,
    shadow_strength: float = 1.0,
    horizontal_alignment: str = "left",
    shadow_png_path: Path | None = None,
    edge_margin: int = 0,
    body_base_offset: int | None = None,
) -> bytes:
    decoded = decode_indexed_v3_tile(original_tile)
    colors = tile_palette_colors(original_tile, palettes)
    if decoded is None or colors is None:
        return original_tile

    height, width, original_pixels = decoded

    from PIL import Image, ImageEnhance, ImageFilter

    source = Image.open(png_path).convert("RGBA")
    source = remove_small_detached_alpha_components(source)
    bbox = (
        source.getchannel("A").getbbox()
        if target_art_height is not None
        else source.getbbox()
    )
    if bbox is None:
        return original_tile

    source = source.crop(bbox)
    art_points = [
        (x, y)
        for y, row in enumerate(original_pixels)
        for x, value in enumerate(row)
        if value != 0 and not 247 <= value <= 250
    ]
    if art_points:
        anchor_left = min(point[0] for point in art_points)
        anchor_top = min(point[1] for point in art_points)
        anchor_right = max(point[0] for point in art_points) + 1
        anchor_bottom = max(point[1] for point in art_points) + 1
    else:
        anchor_left, anchor_top, anchor_right, anchor_bottom = 0, 0, width, height

    anchor_height = max(1, anchor_bottom - anchor_top)
    if max_anchor_height is not None:
        anchor_height = max_anchor_height
    # Size the Phantom body by the stock character height, while allowing
    # action effects to use the rest of the native TILE canvas. Constraining
    # the whole attack/cast image to the narrow Priestess body bbox would make
    # the character tiny merely because an ice lance or vortex extends aside.
    if target_art_height is not None:
        # Walk and Cast inherit several Priestess TILE canvases which are much
        # shorter than the approved Phantom Stand art in the same direction.
        # Scaling inside those native bounds only clips the enlarged sprite.
        # Give the art an explicit visible height, grow the canvas upward, and
        # translate the hotspot with the added pixels so its world position and
        # robe base remain unchanged.
        scale = target_art_height / source.height
        required_width = math.ceil(source.width * scale) + edge_margin * 2
        required_height = math.ceil(source.height * scale) + edge_margin * 2
        expanded_width = max(width, required_width)
        base_expanded_height = max(height, required_height)
        if body_base_offset is not None:
            # Cast placement needs genuine room above and below the native
            # canvas. Shift the hotspot only for the upper addition so world
            # position is preserved while neither edge can clamp the robe.
            top_padding = base_expanded_height - height + 4
            expanded_height = base_expanded_height + 8
        else:
            top_padding = base_expanded_height - height
            expanded_height = base_expanded_height
        left_padding = (expanded_width - width) // 2
        if left_padding or top_padding or expanded_width != width:
            anchor_left += left_padding
            anchor_right += left_padding
            anchor_top += top_padding
            anchor_bottom += top_padding
            hotspot_x, hotspot_y = struct.unpack_from("<HH", original_tile, 10)
            patched_template = bytearray(original_tile)
            struct.pack_into(
                "<HH",
                patched_template,
                10,
                hotspot_x + left_padding,
                hotspot_y + top_padding,
            )
            original_tile = bytes(patched_template)
            width = expanded_width
            height = expanded_height
        anchor_height = target_art_height
    else:
        available_width = max(1, width - edge_margin * 2)
        available_height = max(1, height - edge_margin * 2)
        scale = min(
            available_width / source.width,
            available_height / source.height,
            anchor_height / source.height,
        ) * scale_multiplier
    scaled_size = (
        max(1, int(source.width * scale)),
        max(1, int(source.height * scale)),
    )
    source = source.resize(scaled_size, Image.Resampling.LANCZOS)
    source = ImageEnhance.Contrast(source).enhance(1.08).filter(ImageFilter.SHARPEN)

    target = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    anchor_x = (anchor_left + anchor_right) // 2
    x = anchor_x - source.width // 2
    if body_base_offset is None:
        y = anchor_bottom - source.height + vertical_offset
    else:
        hotspot_y = struct.unpack_from("<H", original_tile, 12)[0]
        y = hotspot_y + body_base_offset - source.height
    if source.width > width:
        x = width - source.width if horizontal_alignment == "right" else 0
    else:
        x = max(edge_margin, min(width - edge_margin - source.width, x))
    y = max(edge_margin, min(height - edge_margin - source.height, y))
    target.alpha_composite(source, (x, y))

    # Project the Phantom's own dark silhouette toward the upper-left Majesty
    # light direction. A small displacement at the robe base keeps the shadow
    # detached so the character still reads as hovering.
    shadow_target = target
    if shadow_png_path is not None:
        shadow_source = Image.open(shadow_png_path).convert("RGBA")
        shadow_source = remove_small_detached_alpha_components(shadow_source)
        shadow_bbox = shadow_source.getbbox()
        if shadow_bbox is not None:
            shadow_source = shadow_source.crop(shadow_bbox)
            # The visible Phantom is intentionally 112% of the stock body.
            # Its flattened ground projection must remain within the original
            # Priestess TILE's much narrower shadow margin, so use a compact
            # caster rather than shrinking the visible hero again.
            shadow_scale = min(
                width / shadow_source.width,
                anchor_height / shadow_source.height,
            ) * 0.90
            shadow_source = shadow_source.resize(
                (
                    max(1, int(shadow_source.width * shadow_scale)),
                    max(1, int(shadow_source.height * shadow_scale)),
                ),
                Image.Resampling.LANCZOS,
            )
            shadow_target = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shadow_x = anchor_x - shadow_source.width // 2
            if body_base_offset is None:
                shadow_y = anchor_bottom - shadow_source.height + vertical_offset
            else:
                hotspot_y = struct.unpack_from("<H", original_tile, 12)[0]
                shadow_y = hotspot_y + body_base_offset - shadow_source.height
            if shadow_source.width > width:
                shadow_x = width - shadow_source.width if horizontal_alignment == "right" else 0
            else:
                shadow_x = max(edge_margin, min(width - edge_margin - shadow_source.width, shadow_x))
            shadow_y = max(edge_margin, min(height - edge_margin - shadow_source.height, shadow_y))
            shadow_target.alpha_composite(shadow_source, (shadow_x, shadow_y))

    output_pixels = projected_floating_hero_shadow(shadow_target, shadow_strength)
    for target_y in range(height):
        for target_x in range(width):
            red, green, blue, alpha = target.getpixel((target_x, target_y))
            if alpha < 18:
                continue
            output_pixels[target_y][target_x] = nearest_visible_palette_index(
                max(12, red),
                max(13, green),
                max(18, blue),
                colors,
            )

    return encode_indexed_v3_tile_like_original(
        original_tile,
        output_pixels,
        split_shadow_controls=True,
    )


def projected_floating_hero_shadow(
    target: "Image.Image",
    strength: float,
) -> list[list[int]]:
    width, height = target.size
    pixels = [[0 for _ in range(width)] for _ in range(height)]
    if strength <= 0:
        return pixels

    body_mask = [[False for _ in range(width)] for _ in range(height)]
    body_points: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = target.getpixel((x, y))
            if alpha < 32:
                continue
            luminance = 0.299 * red + 0.587 * green + 0.114 * blue
            bright_cyan_effect = (
                blue > red + 34
                and green > red + 28
                and luminance > 105
            )
            near_white_effect = luminance > 205
            if bright_cyan_effect or near_white_effect:
                continue
            body_mask[y][x] = True
            body_points.append((x, y))

    if not body_points:
        return pixels

    # Keep the central hood/torso/robe mass as the shadow caster. Long dark
    # weapons and outstretched arms remain valid body occluders, but must not
    # turn the projected shadow into a horizontal bar.
    points_by_row: dict[int, list[int]] = {}
    for x, y in body_points:
        points_by_row.setdefault(y, []).append(x)
    caster_points: list[tuple[int, int]] = []
    for y, row_xs in points_by_row.items():
        row_xs.sort()
        row_center = row_xs[len(row_xs) // 2]
        row_span = row_xs[-1] - row_xs[0] + 1
        half_width = max(3, min(12, round(row_span * 0.38)))
        caster_points.extend(
            (x, y)
            for x in row_xs
            if abs(x - row_center) <= half_width
        )

    base_y = max(y for _x, y in caster_points)
    raw_projection: list[tuple[float, float]] = []
    for x, y in caster_points:
        vertical_height = base_y - y
        raw_projection.append(
            (
                x - 3.0 - vertical_height * 0.44,
                base_y - 3.0 - vertical_height * 0.36,
            )
        )

    hits: dict[tuple[int, int], int] = {}
    for raw_x, raw_y in raw_projection:
        shadow_x = round(raw_x)
        shadow_y = round(raw_y)
        if 0 <= shadow_x < width and 0 <= shadow_y < height:
            point = (shadow_x, shadow_y)
            hits[point] = hits.get(point, 0) + 1

    core = set(hits)
    feather: dict[tuple[int, int], int] = {}
    for x, y in core:
        for dx, dy in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
        ):
            point = (x + dx, y + dy)
            if (
                0 <= point[0] < width
                and 0 <= point[1] < height
                and point not in core
            ):
                feather[point] = min(
                    feather.get(point, 250),
                    249 if dx == 0 or dy == 0 else 250,
                )

    if strength >= 0.72:
        core_dark = 247
    elif strength >= 0.38:
        core_dark = 248
    else:
        core_dark = 249

    for (x, y), hit_count in hits.items():
        pixels[y][x] = core_dark if hit_count >= 2 else min(250, core_dark + 1)
    for (x, y), value in feather.items():
        pixels[y][x] = value

    # Shadow control pixels must remain visibly detached from the floating art.
    # Remove any projected or feather pixel that touches the body mask.
    for y in range(height):
        for x in range(width):
            if pixels[y][x] == 0:
                continue
            touches_body = False
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    if body_mask[neighbor_y][neighbor_x]:
                        touches_body = True
                        break
                if touches_body:
                    break
            if touches_body:
                pixels[y][x] = 0

    # Quantization and detached-body clearance can strand the projected hood
    # as an isolated upper-left island. Retain only the connected primary
    # ground silhouette instead of emitting a visibly floating fragment.
    shadow_points = {
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value != 0
    }
    components: list[set[tuple[int, int]]] = []
    while shadow_points:
        component: set[tuple[int, int]] = set()
        pending = [shadow_points.pop()]
        while pending:
            point_x, point_y = pending.pop()
            component.add((point_x, point_y))
            for neighbor_y in range(max(0, point_y - 1), min(height, point_y + 2)):
                for neighbor_x in range(max(0, point_x - 1), min(width, point_x + 2)):
                    neighbor = (neighbor_x, neighbor_y)
                    if neighbor in shadow_points:
                        shadow_points.remove(neighbor)
                        pending.append(neighbor)
        components.append(component)

    if components:
        primary = max(components, key=len)
        for component in components:
            if component is primary:
                continue
            for x, y in component:
                pixels[y][x] = 0

    return pixels


def cast_staff_glow_overlay_tile(
    body_tile: bytes,
    palettes: list[CamEntry],
    glow_png_path: Path,
    direction: int,
    stage: int,
    *,
    anchor_body_tile: bytes | None = None,
) -> bytes:
    from PIL import Image

    decoded = decode_indexed_v3_tile(body_tile)
    colors = tile_palette_colors(body_tile, palettes)
    if decoded is None or colors is None:
        raise ValueError("Expected a readable indexed cast body TILE")
    height, width, body_pixels = decoded
    anchor_pixels = body_pixels
    if anchor_body_tile is not None:
        anchor_decoded = decode_indexed_v3_tile(anchor_body_tile)
        if anchor_decoded is None:
            raise ValueError("Expected a readable indexed cast anchor TILE")
        anchor_height, anchor_width, anchor_pixels = anchor_decoded
        if (anchor_width, anchor_height) != (width, height):
            raise ValueError(
                "Cast anchor TILE geometry does not match the glow output TILE"
            )

    candidates: list[tuple[int, int]] = []
    for y, row in enumerate(anchor_pixels):
        if y > int(height * 0.62):
            continue
        for x, palette_index in enumerate(row):
            if palette_index == 0 or 247 <= palette_index <= 250:
                continue
            red, green, blue = colors[palette_index]
            if blue >= 115 and green >= 80 and blue > red + 24 and green > red + 12:
                candidates.append((x, y))
    if not candidates:
        raise ValueError(f"Could not locate staff crystal for cast direction {direction}")

    staff_on_right = direction in (0, 1, 4)
    extreme_x = (
        max(x for x, _y in candidates)
        if staff_on_right
        else min(x for x, _y in candidates)
    )
    crystal_points = [(x, y) for x, y in candidates if abs(x - extreme_x) <= 4]
    center_x = round(sum(x for x, _y in crystal_points) / len(crystal_points))
    center_y = round(sum(y for _x, y in crystal_points) / len(crystal_points))

    glow = Image.open(glow_png_path).convert("RGBA")
    glow = remove_small_detached_alpha_components(glow)
    bbox = glow.getbbox()
    if bbox is None:
        raise ValueError(f"Cast glow source is empty: {glow_png_path}")
    glow = glow.crop(bbox)
    diameter = (11, 14, 18, 11)[stage]
    glow.thumbnail((diameter, diameter), Image.Resampling.LANCZOS)

    visible_alpha = glow.getchannel("A").point(
        lambda alpha: 255 if alpha >= 18 else 0
    )
    visible_bbox = visible_alpha.getbbox()
    if visible_bbox is None:
        raise ValueError(f"Cast glow stage {stage} has no visible alpha")
    visible_left, visible_top, visible_right, visible_bottom = visible_bbox
    # Align the center of the pixels that survive TILE alpha thresholding,
    # rather than the outer PNG rectangle. Differently shaped/pulsed sources
    # otherwise appear to bounce despite sharing the same staff coordinate.
    left = round(
        (
            2 * center_x
            - (visible_left + visible_right - 1)
        )
        / 2
    )
    top = round(
        (
            2 * center_y
            - (visible_top + visible_bottom - 1)
        )
        / 2
    )
    left = max(1, min(width - glow.width - 1, left))
    top = max(1, min(height - glow.height - 1, top))
    pixels = [[0 for _x in range(width)] for _y in range(height)]
    for glow_y in range(glow.height):
        for glow_x in range(glow.width):
            red, green, blue, alpha = glow.getpixel((glow_x, glow_y))
            if alpha < 18:
                continue
            pixels[top + glow_y][left + glow_x] = nearest_visible_palette_index(
                max(12, red),
                max(13, green),
                max(18, blue),
                colors,
            )

    return encode_indexed_v3_tile_like_original(body_tile, pixels)


def tile_from_png_native_size(original_tile: bytes, palettes: list[CamEntry], png_path: Path) -> bytes:
    from PIL import Image

    colors = tile_palette_colors(original_tile, palettes)
    if colors is None:
        return original_tile

    shadow_marker_indices = {
        (156, 33, 24): 247,
        (178, 0, 178): 248,
        (204, 0, 204): 249,
        (229, 0, 229): 250,
    }
    image = Image.open(png_path).convert("RGBA")
    pixels: list[list[int]] = []
    for y in range(image.height):
        row: list[int] = []
        for x in range(image.width):
            red, green, blue, alpha = image.getpixel((x, y))
            if alpha < 16 or is_transparent_rgb(red, green, blue):
                row.append(0)
            elif (red, green, blue) in shadow_marker_indices:
                row.append(shadow_marker_indices[(red, green, blue)])
            else:
                row.append(nearest_visible_palette_index(red, green, blue, colors))
        pixels.append(row)

    return encode_indexed_v3_tile_like_original(
        original_tile,
        pixels,
        split_shadow_controls=True,
    )


def remove_small_detached_alpha_components(image: "Image.Image") -> "Image.Image":
    from PIL import Image

    cleaned = image.copy()
    alpha = cleaned.getchannel("A")
    pixels = cleaned.load()
    mask = alpha.load()
    width, height = cleaned.size
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int, int, int], list[tuple[int, int]]]] = []

    for y in range(height):
        for x in range(width):
            if mask[x, y] == 0 or (x, y) in seen:
                continue

            queue = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in seen
                        or mask[nx, ny] == 0
                    ):
                        continue
                    seen.add((nx, ny))
                    queue.append((nx, ny))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            components.append((len(points), (min(xs), min(ys), max(xs) + 1, max(ys) + 1), points))

    if not components:
        return cleaned

    largest_size, largest_bbox, _largest_points = max(components, key=lambda component: component[0])
    largest_left, largest_top, largest_right, largest_bottom = largest_bbox
    keep: set[tuple[int, int]] = set()
    for size, bbox, points in components:
        left, top, right, bottom = bbox
        close_to_body = (
            left <= largest_right + 18
            and right >= largest_left - 18
            and top <= largest_bottom + 18
            and bottom >= largest_top - 18
        )
        meaningful_detail = size >= max(16, int(largest_size * 0.015))
        if bbox == largest_bbox or close_to_body or meaningful_detail:
            keep.update(points)

    for y in range(height):
        for x in range(width):
            if mask[x, y] and (x, y) not in keep:
                pixels[x, y] = (0, 0, 0, 0)

    return cleaned


def tile_visible_bbox(tile: bytes) -> tuple[int, int, int, int] | None:
    version = struct.unpack_from("<H", tile, 0)[0] if len(tile) >= 2 else 0
    if version == 3:
        decoded = decode_indexed_v3_tile(tile)
        if decoded is None:
            return None
        height, width, pixels = decoded
        xs: list[int] = []
        ys: list[int] = []
        for y in range(height):
            for x in range(width):
                if pixels[y][x] != 0:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return None
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    if version == 1 and len(tile) >= 26:
        height = struct.unpack_from("<H", tile, 2)[0]
        width = struct.unpack_from("<H", tile, 4)[0]
        row_stride = struct.unpack_from("<H", tile, 6)[0]
        if row_stride == width * 2:
            return 0, 0, width, height
        plane = tile[26 : 26 + row_stride * height]
        xs: list[int] = []
        ys: list[int] = []
        for y in range(height):
            for x in range(min(width, row_stride)):
                if plane[y * row_stride + x] != 0:
                    xs.append(x)
                    ys.append(y)
        if xs:
            return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    return None


def tile_dimensions(tile: bytes) -> tuple[int, int] | None:
    if len(tile) < 26:
        return None

    version = struct.unpack_from("<H", tile, 0)[0]
    if version == 1:
        height = struct.unpack_from("<H", tile, 2)[0]
        width = struct.unpack_from("<H", tile, 4)[0]
        return height, width
    if version == 3:
        height = struct.unpack_from("<H", tile, 2)[0]
        width = struct.unpack_from("<H", tile, 4)[0]
        return height, width
    return None


def tile_v3_from_rgb(
    original_tile: bytes,
    palettes: list[CamEntry],
    rgb: bytes,
    palette_override: tuple[int, list[tuple[int, int, int]]] | None = None,
) -> bytes:
    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    expected_rgb_size = width * height * 3
    if len(rgb) != expected_rgb_size:
        raise ValueError(
            f"Expected {expected_rgb_size} RGB bytes for {width}x{height} tile, got {len(rgb)}"
        )

    if palette_override:
        target_palette_index, colors = palette_override
    else:
        target_palette_index = None
        colors = tile_palette_colors(original_tile, palettes)
    if colors is None:
        return original_tile

    header = bytearray(original_tile[:26])
    if target_palette_index is not None:
        struct.pack_into("<H", header, 20, 0)
        struct.pack_into("<I", header, 22, target_palette_index)
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray()
        x = 0
        while x < width:
            pixel_offset = (y * width + x) * 3
            if is_transparent_rgb(rgb[pixel_offset], rgb[pixel_offset + 1], rgb[pixel_offset + 2]):
                x += 1
                continue

            start = x
            pixels: list[int] = []
            while x < width and len(pixels) < 80:
                pixel_offset = (y * width + x) * 3
                red = rgb[pixel_offset]
                green = rgb[pixel_offset + 1]
                blue = rgb[pixel_offset + 2]
                if is_transparent_rgb(red, green, blue):
                    break
                pixels.append(nearest_visible_palette_index(red, green, blue, colors))
                x += 1

            next_x = x
            while next_x < width:
                pixel_offset = (y * width + next_x) * 3
                if not is_transparent_rgb(rgb[pixel_offset], rgb[pixel_offset + 1], rgb[pixel_offset + 2]):
                    break
                next_x += 1
            has_more_segments = next_x < width
            flags = 0 if has_more_segments else 0x80
            row += struct.pack("<HBB", start + len(pixels), len(pixels), flags)
            row += bytes(pixels)
            x = next_x

        if not row:
            row += struct.pack("<HBB", 0, 0, 0x80)
        rows.append(bytes(row))

    offset_base = 26
    row_offsets_size = height * 4
    cursor = row_offsets_size
    output = bytearray(header)
    for row in rows:
        output += struct.pack("<I", cursor)
        cursor += len(row)
    for row in rows:
        output += row

    palette_mode = struct.unpack_from("<H", original_tile, 20)[0]
    original_palette_offset = struct.unpack_from("<I", original_tile, 22)[0]
    if target_palette_index is None and palette_mode == 1 and 0 <= original_palette_offset < len(original_tile):
        new_palette_offset = len(output)
        struct.pack_into("<I", output, 22, new_palette_offset)
        output += original_tile[original_palette_offset:]

    return bytes(output)


def is_transparent_rgb(red: int, green: int, blue: int) -> bool:
    return red < 10 and green < 10 and blue < 12


def remap_imag_tile_indices(imag: bytes, replacements: dict[int, int]) -> bytes:
    patched = bytearray(imag)
    for offset in range(0, len(patched) - 3, 4):
        value = u32(patched, offset)
        if value in replacements:
            struct.pack_into("<I", patched, offset, replacements[value])
    return bytes(patched)


def replace_embedded_attachment_id(
    imag: bytes,
    source_id: bytes,
    target_id: bytes,
) -> bytes:
    """Redirect one stock IMAG particle attachment without touching its art."""
    if len(source_id) != 4 or len(target_id) != 4:
        raise ValueError("Embedded attachment IDs must contain exactly four bytes")
    if imag.count(source_id) != 1:
        raise ValueError(
            f"Expected exactly one embedded {source_id!r} attachment ID"
        )
    return imag.replace(source_id, target_id, 1)


def remap_imag_low16_tile_indices(imag: bytes, replacements: dict[int, int]) -> bytes:
    patched = bytearray(imag)
    for offset in range(0, len(patched) - 3, 4):
        value = u32(patched, offset)
        low_tile_index = value & 0xFFFF
        if low_tile_index in replacements:
            struct.pack_into(
                "<I",
                patched,
                offset,
                (value & 0xFFFF0000) | replacements[low_tile_index],
            )
    return bytes(patched)


def single_direction_imag_animation_sets(
    imag: bytes,
) -> list[tuple[int, list[tuple[int, int]]]]:
    """Read the one-direction animation sets used by stock overlay IMAGs."""
    if len(imag) < 24:
        raise ValueError("Overlay IMAG is too short for an animation-set table")

    entry_count = u32(imag, 20)
    table_end = 24 + entry_count * 8
    if entry_count <= 0 or table_end > len(imag):
        raise ValueError("Overlay IMAG has an invalid animation-set table")

    result: list[tuple[int, list[tuple[int, int]]]] = []
    for index in range(entry_count):
        entry_offset = 24 + index * 8
        set_id = u32(imag, entry_offset)
        set_offset = u32(imag, entry_offset + 4)
        if set_offset + 68 > len(imag):
            raise ValueError(f"Overlay IMAG set {set_id} is truncated")
        direction_offset = set_offset + u32(imag, set_offset + 64)
        if direction_offset + 20 > len(imag):
            raise ValueError(f"Overlay IMAG set {set_id} has an invalid direction")
        frame_count = u32(imag, direction_offset + 4) >> 16
        frame_start = direction_offset + 20
        last_tile_end = frame_start + (frame_count - 1) * 8 + 4
        if frame_count <= 0 or last_tile_end > len(imag):
            raise ValueError(f"Overlay IMAG set {set_id} has an invalid frame table")
        result.append(
            (
                set_id,
                [
                    (
                        frame_start + frame_index * 8,
                        u32(imag, frame_start + frame_index * 8),
                    )
                    for frame_index in range(frame_count)
                ],
            )
        )
    return result


def replace_priestess_die_holds_with_directional_third_frames(imag: bytes) -> bytes:
    """Keep the recognizable shatter pose directional before shared effects."""
    if len(imag) < 24:
        raise ValueError("Hero IMAG is too short for an animation-set table")

    entry_count = u32(imag, 20)
    table_start = 24
    table_end = table_start + entry_count * 8
    if entry_count <= 0 or table_end > len(imag):
        raise ValueError("Hero IMAG has an invalid animation-set table")

    die_set_offset: int | None = None
    for index in range(entry_count):
        entry_offset = table_start + index * 8
        if u32(imag, entry_offset) == 96:
            die_set_offset = u32(imag, entry_offset + 4)
            break
    if die_set_offset is None or die_set_offset + 0x58 > len(imag):
        raise ValueError("Hero IMAG has no readable Die animation set")

    direction_offsets = [
        struct.unpack_from("<i", imag, die_set_offset + 0x40 + slot * 4)[0]
        for slot in range(8)
    ]
    populated = [offset for offset in direction_offsets if offset > 0]
    if len(populated) != 8:
        raise ValueError(f"Expected eight populated Die directions, found {len(populated)}")

    patched = bytearray(imag)
    for direction_index, relative_offset in enumerate(populated):
        direction_offset = die_set_offset + relative_offset
        frame_table = direction_offset + 0x28
        if frame_table + 13 * 8 > len(imag):
            raise ValueError(f"Die direction {direction_index} has a truncated frame table")

        first_tile = u32(imag, frame_table + 4) & 0xFFFF
        expected_first = 4722 + direction_index * 3
        if first_tile != expected_first:
            raise ValueError(
                f"Die direction {direction_index} begins with TILE {first_tile}; "
                f"expected {expected_first}"
            )
        third_directional_tile = first_tile + 2
        for frame_index in range(2, 6):
            tile_offset = frame_table + frame_index * 8 + 4
            value = u32(patched, tile_offset)
            struct.pack_into(
                "<I",
                patched,
                tile_offset,
                (value & 0xFFFF0000) | third_directional_tile,
            )

    return bytes(patched)


def replace_cast_effect_frames_with_directional_glows(
    imag: bytes,
    glow_indices: dict[tuple[int, int], int],
    recovery_indices: dict[int, int],
) -> bytes:
    if len(glow_indices) != 32:
        raise ValueError(f"Expected 32 directional cast glows, got {len(glow_indices)}")
    if len(recovery_indices) != 8:
        raise ValueError(f"Expected eight directional cast recovery TILEs, got {len(recovery_indices)}")
    if len(imag) < 24:
        raise ValueError("Hero IMAG is too short for an animation-set table")

    entry_count = u32(imag, 20)
    table_end = 24 + entry_count * 8
    if entry_count <= 0 or table_end > len(imag):
        raise ValueError("Hero IMAG has an invalid animation-set table")

    cast_set_offset: int | None = None
    for index in range(entry_count):
        entry_offset = 24 + index * 8
        if u32(imag, entry_offset) == 128:
            cast_set_offset = u32(imag, entry_offset + 4)
            break
    if cast_set_offset is None or cast_set_offset + 0x58 > len(imag):
        raise ValueError("Hero IMAG has no readable Cast animation set")

    populated = [
        struct.unpack_from("<i", imag, cast_set_offset + 0x40 + slot * 4)[0]
        for slot in range(8)
    ]
    populated = [offset for offset in populated if offset > 0]
    if len(populated) != 8:
        raise ValueError(f"Expected eight populated Cast directions, found {len(populated)}")

    patched = bytearray(imag)
    effect_stages = (0, 1, 2, 1, 3)
    for direction, relative_offset in enumerate(populated):
        frame_table = cast_set_offset + relative_offset + 0x30
        if frame_table + 16 * 8 > len(imag):
            raise ValueError(f"Cast direction {direction} has a truncated frame table")
        for frame_index, stage in zip(range(8, 13), effect_stages):
            frame_offset = frame_table + frame_index * 8
            tile_offset = frame_offset + 4
            # The stock Priestess swirl is authored around the ground and its
            # IMAG frames carry large per-direction offsets (often 40–75 px
            # upward). Our glow is already positioned on the staff crystal in
            # the body TILE's coordinate system, so those inherited offsets
            # would displace it far above the Phantom. A tiny upward nudge
            # centers the glow on the in-game staff crystal.
            struct.pack_into("<hh", patched, frame_offset, 2, -5)
            value = u32(patched, tile_offset)
            custom_index = glow_indices[(direction, stage)]
            if custom_index > 0xFFFF:
                raise ValueError(f"Custom cast glow TILE index {custom_index} exceeds low16")
            struct.pack_into(
                "<I",
                patched,
                tile_offset,
                (value & 0xFFFF0000) | custom_index,
            )
        recovery_index = recovery_indices[direction]
        if recovery_index > 0xFFFF:
            raise ValueError(f"Cast recovery TILE index {recovery_index} exceeds low16")
        for frame_index in range(13, 16):
            tile_offset = frame_table + frame_index * 8 + 4
            value = u32(patched, tile_offset)
            struct.pack_into(
                "<I",
                patched,
                tile_offset,
                (value & 0xFFFF0000) | recovery_index,
            )

    return bytes(patched)


def replace_building_state_animation_tiles(imag: bytes, set_id: int, tile_indices: list[int]) -> bytes:
    if len(imag) < 28 or not tile_indices:
        return imag

    entry_count = u32(imag, 20)
    table_start = 24
    table_end = table_start + entry_count * 8
    if entry_count <= 0 or table_end > len(imag):
        return imag

    entries: list[tuple[int, int]] = []
    target_position: int | None = None
    for index in range(entry_count):
        entry_offset = table_start + index * 8
        current_set_id = u32(imag, entry_offset)
        rel_offset = u32(imag, entry_offset + 4)
        entries.append((current_set_id, rel_offset))
        if current_set_id == set_id:
            target_position = index

    if target_position is None:
        return imag

    target_rel = entries[target_position][1]
    next_rel = entries[target_position + 1][1] if target_position + 1 < len(entries) else len(imag)
    if target_rel < table_end or next_rel <= target_rel or next_rel > len(imag):
        return imag

    old_chunk = imag[target_rel:next_rel]
    if len(old_chunk) < 116:
        return imag

    new_chunk = bytearray(old_chunk[:112])
    struct.pack_into("<H", new_chunk, 74, len(tile_indices))
    for frame_index, tile_index in enumerate(tile_indices):
        if frame_index > 0:
            new_chunk += b"\x00\x00\x00\x00"
        new_chunk += struct.pack("<I", tile_index)

    delta = len(new_chunk) - len(old_chunk)
    patched = bytearray()
    patched += imag[:target_rel]
    patched += new_chunk
    patched += imag[next_rel:]

    for index, (_current_set_id, rel_offset) in enumerate(entries):
        if rel_offset > target_rel:
            struct.pack_into("<I", patched, table_start + index * 8 + 4, rel_offset + delta)

    return bytes(patched)


def remap_building_attachment_points(
    imag: bytes,
    replacements: dict[int, tuple[int, int]],
) -> bytes:
    if len(imag) < 24 or not replacements:
        return imag

    entry_count = u32(imag, 20)
    table_start = 24
    table_end = table_start + entry_count * 8
    if entry_count <= 0 or table_end > len(imag):
        raise ValueError("Building IMAG has an invalid animation-set table")

    patched = bytearray(imag)
    remaining = set(replacements)
    for index in range(entry_count):
        entry_offset = table_start + index * 8
        set_id = u32(imag, entry_offset)
        if set_id not in replacements:
            continue

        set_offset = u32(imag, entry_offset + 4)
        if set_offset < table_end or set_offset + 68 > len(imag):
            raise ValueError(f"Building IMAG set {set_id:#010x} has an invalid offset")
        direction_offset = set_offset + u32(imag, set_offset + 64)
        coordinate_offset = direction_offset
        if coordinate_offset + 4 > len(imag):
            raise ValueError(f"Building IMAG set {set_id:#010x} has invalid attachment data")

        x, y = replacements[set_id]
        struct.pack_into("<hh", patched, coordinate_offset, x, y)
        remaining.remove(set_id)

    if remaining:
        missing = ", ".join(f"{set_id:#010x}" for set_id in sorted(remaining))
        raise ValueError(f"Building IMAG is missing attachment sets: {missing}")
    return bytes(patched)


def animation_tile_indices(imag: bytes, tile_count: int) -> list[int]:
    if len(imag) < 128:
        return []

    frame_count = u32(imag, 104) >> 16
    frame_start = 128
    frame_stride = 8
    indices: list[int] = []
    for frame_index in range(frame_count):
        offset = frame_start + frame_index * frame_stride
        if offset + 4 > len(imag):
            break
        tile_index = u32(imag, offset)
        if tile_index < tile_count:
            indices.append(tile_index)
    return indices


def remap_imag_animation_tiles(imag: bytes, replacements: dict[int, int]) -> bytes:
    patched = bytearray(imag)
    frame_count = u32(imag, 104) >> 16 if len(imag) >= 108 else 0
    frame_start = 128
    frame_stride = 8
    for frame_index in range(frame_count):
        offset = frame_start + frame_index * frame_stride
        if offset + 4 > len(patched):
            break
        tile_index = u32(patched, offset)
        if tile_index in replacements:
            struct.pack_into("<I", patched, offset, replacements[tile_index])
    return bytes(patched)


def remap_imag_frame_count(imag: bytes, frame_count: int) -> bytes:
    patched = bytearray(imag)
    if len(patched) >= 108:
        value = u32(patched, 104)
        value = (value & 0x0000FFFF) | (frame_count << 16)
        struct.pack_into("<I", patched, 104, value)
    return bytes(patched)


def remap_imag_animation_sequence(imag: bytes, tile_indices: list[int]) -> bytes:
    patched = bytearray(remap_imag_frame_count(imag, len(tile_indices)))
    frame_start = 128
    frame_stride = 8
    for frame_index, tile_index in enumerate(tile_indices):
        offset = frame_start + frame_index * frame_stride
        if offset + 4 > len(patched):
            break
        struct.pack_into("<I", patched, offset, tile_index)
    return bytes(patched)


def remap_tile_palette_index(tile: bytes, palette_index: int) -> bytes:
    if len(tile) < 26:
        return tile

    patched = bytearray(tile)
    struct.pack_into("<I", patched, 22, palette_index)
    return bytes(patched)


def generated_ice_lance_projectile_tile(
    original_tile: bytes,
    palettes: list[CamEntry],
    frame_index: int,
    frame_count: int,
    angle: float | None = None,
    source_png: Path | None = None,
) -> bytes:
    if len(original_tile) < 26:
        return original_tile

    version = struct.unpack_from("<H", original_tile, 0)[0]
    if version not in (1, 3):
        return original_tile

    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    if width <= 0 or height <= 0:
        return original_tile

    if source_png and source_png.is_file():
        return generated_source_ice_lance_projectile_tile(
            original_tile,
            palettes,
            source_png,
            frame_index,
            frame_count,
            angle if angle is not None else -0.68,
        )

    phase = frame_index / max(1, frame_count - 1)
    rgb = bytearray(b"\x00" * (width * height * 3))

    center_x = width * 0.50
    center_y = height * 0.50
    draw_angle = angle if angle is not None else -0.68
    ux_angle = math.cos(draw_angle)
    uy_angle = math.sin(draw_angle)
    horizontal_extent = (width * 0.46) / max(0.12, abs(ux_angle))
    vertical_extent = (height * 0.46) / max(0.12, abs(uy_angle))
    half_length = min(horizontal_extent, vertical_extent)
    lance_length = half_length * (1.58 + 0.12 * phase)
    start = (center_x - ux_angle * lance_length * 0.50, center_y - uy_angle * lance_length * 0.50)
    end = (center_x + ux_angle * lance_length * 0.50, center_y + uy_angle * lance_length * 0.50)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy) or 1.0
    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux

    for y in range(height):
        for x in range(width):
            px = x + 0.5
            py = y + 0.5
            vx = px - start[0]
            vy = py - start[1]
            along = (vx * ux + vy * uy) / length
            perpendicular = abs(vx * nx + vy * ny)
            intensity = 0.0

            base_width = max(1.4, min(width, height) * (0.052 + 0.008 * phase))
            shaft_width = base_width * max(0.34, 1.05 - along * 0.76)
            glow_width = shaft_width * 2.0
            if 0.06 <= along <= 0.72 and perpendicular <= glow_width:
                intensity = max(intensity, 0.16 * (1.0 - perpendicular / glow_width))
            if 0.10 <= along <= 0.76 and perpendicular <= shaft_width:
                intensity = max(intensity, 0.58 + 0.34 * (1.0 - perpendicular / shaft_width))

            head_profile = max(0.0, 1.0 - abs(along - 0.82) / 0.18)
            head_width = max(0.0, min(width, height) * 0.19 * head_profile)
            if 0.66 <= along <= 1.0 and perpendicular <= head_width:
                intensity = max(intensity, 0.72 + 0.24 * (1.0 - perpendicular / max(1.0, head_width)))

            trail_gate = 0.00 <= along <= 0.34
            trail_wave = abs(math.sin((along * 34.0) + frame_index * 0.85))
            if trail_gate and trail_wave > 0.60:
                trail_width = max(0.9, base_width * (1.8 - along * 2.0))
                if perpendicular <= trail_width:
                    intensity = max(intensity, 0.42 * (1.0 - along) + 0.18)

            for shard_along, shard_side, shard_len in (
                (0.22, -1.0, 0.18),
                (0.32, 1.0, 0.15),
                (0.48, -1.0, 0.13),
                (0.58, 1.0, 0.10),
            ):
                sx = start[0] + ux * length * shard_along + nx * base_width * 2.6 * shard_side
                sy = start[1] + uy * length * shard_along + ny * base_width * 2.6 * shard_side
                shard_end = (
                    sx + ux * length * shard_len - nx * base_width * 1.7 * shard_side,
                    sy + uy * length * shard_len - ny * base_width * 1.7 * shard_side,
                )
                shard_intensity = line_intensity((px, py), (sx, sy), shard_end, base_width * 0.52)
                intensity = max(intensity, shard_intensity * 0.78)

            if intensity <= 0.0:
                continue

            offset = (y * width + x) * 3
            rgb[offset] = min(255, int(18 + 70 * intensity))
            rgb[offset + 1] = min(255, int(120 + 135 * intensity))
            rgb[offset + 2] = 255
            if intensity > 0.88:
                rgb[offset] = 236
                rgb[offset + 1] = 255
                rgb[offset + 2] = 255

    palette_tile = remap_tile_palette_index(original_tile, ICE_LANCE_PROJECTILE_PALETTE_INDEX)
    return tile_from_rgb(palette_tile, palettes, bytes(rgb))


def generated_source_ice_lance_projectile_tile(
    original_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
    angle: float,
) -> bytes:
    """Rotate and downscale the approved high-resolution lance source.

    The projectile origin remains at the center of the inherited Fire Blast
    TILE, but the visible shard is nudged forward along its travel direction.
    That makes its first rendered frame read as leaving the Phantom's raised
    casting hand instead of sitting directly over the hero's body.
    """
    from PIL import Image, ImageEnhance, ImageFilter

    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")

    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        return original_tile
    source = source.crop(alpha_bbox)

    # Pillow's positive image rotation is counter-clockwise. Screen-space
    # projectile angles use y-down coordinates, so invert the stored angle.
    rotated = source.rotate(
        -math.degrees(angle),
        resample=Image.Resampling.BICUBIC,
        expand=True,
    )
    rotated_bbox = rotated.getchannel("A").getbbox()
    if rotated_bbox is not None:
        rotated = rotated.crop(rotated_bbox)

    phase = frame_index / max(1, frame_count - 1)
    pulse = (0.86, 0.94, 1.0, 0.92)[frame_index % 4]
    max_width = max(1, int(width * 0.78 * pulse))
    max_height = max(1, int(height * 0.78 * pulse))
    rotated.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    rotated = ImageEnhance.Contrast(rotated).enhance(1.08 + phase * 0.05)
    rotated = ImageEnhance.Color(rotated).enhance(1.08)
    rotated = rotated.filter(ImageFilter.UnsharpMask(radius=0.7, percent=120, threshold=2))

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ux = math.cos(angle)
    uy = math.sin(angle)
    forward = min(width, height) * 0.07
    x = round((width - rotated.width) * 0.5 + ux * forward)
    y = round((height - rotated.height) * 0.5 + uy * forward)
    canvas.alpha_composite(rotated, (x, y))

    rgb = Image.new("RGB", (width, height), (0, 0, 0))
    rgb.paste(canvas.convert("RGB"), mask=canvas.getchannel("A"))
    palette_tile = remap_tile_palette_index(
        original_tile,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
    )
    return tile_from_rgb(palette_tile, palettes, rgb.tobytes())


def projectile_direction_frame_for_source_tile(tile_index: int) -> tuple[int, int]:
    first_tile = ICE_LANCE_DIRECTIONAL_PROJECTILE_TILES[0]
    position = max(0, tile_index - first_tile)
    return (
        position // ICE_LANCE_PROJECTILE_FRAMES_PER_DIRECTION,
        position % ICE_LANCE_PROJECTILE_FRAMES_PER_DIRECTION,
    )


def projectile_angle_for_direction(direction_index: int) -> float:
    direction = direction_index % ICE_LANCE_PROJECTILE_DIRECTIONS
    return -math.pi / 2.0 + (2.0 * math.pi * direction / ICE_LANCE_PROJECTILE_DIRECTIONS)


def blank_indexed_v3_tile(template_tile: bytes) -> bytes:
    """Preserve a projectile frame's native geometry while drawing nothing."""
    decoded = decode_indexed_v3_tile(template_tile)
    if decoded is None:
        return template_tile
    height, width, _pixels = decoded
    return encode_indexed_v3_tile_like_original(
        template_tile,
        [[0 for _ in range(width)] for _ in range(height)],
    )


def generated_gravechill_hit_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Render the six source skull stages as a one-shot target impact."""
    from PIL import Image

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        sheet = loaded.convert("RGBA")

    source_frame_count = 6
    stage = min(
        source_frame_count - 1,
        round(frame_index * (source_frame_count - 1) / max(1, frame_count - 1)),
    )
    left = round(sheet.width * stage / source_frame_count)
    right = round(sheet.width * (stage + 1) / source_frame_count)
    source = sheet.crop((left, 0, right, sheet.height))
    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(alpha_bbox)

    scale = min(
        width * 0.92 / max(1, source.width),
        height * 0.92 / max(1, source.height),
    )
    target_width = max(1, round(source.width * scale))
    target_height = max(1, round(source.height * scale))
    source = source.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    x = (width - source.width) // 2
    y = (height - source.height) // 2
    canvas.paste(source.convert("RGB"), (x, y), source.getchannel("A"))

    palette_tile = remap_tile_palette_index(
        template_tile,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
    )
    return tile_from_rgb(palette_tile, palettes, canvas.tobytes())


def generated_gravechill_skull_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Render the formed icy skull as a pulsing floating debuff symbol."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        sheet = loaded.convert("RGBA")

    source_frame_count = 6
    formed_frame_index = 2
    left = round(sheet.width * formed_frame_index / source_frame_count)
    right = round(sheet.width * (formed_frame_index + 1) / source_frame_count)
    source = sheet.crop((left, 0, right, sheet.height))
    source = remove_small_detached_alpha_components(source)
    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(alpha_bbox)

    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    pulse = 0.98 + 0.035 * math.sin(turn * 2.0)
    target_height = max(10, round(min(width, height) * 0.72 * pulse))
    target_width = max(
        7,
        round(source.width * target_height / max(1, source.height)),
    )
    source = source.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # A restrained horizontal compression suggests a hovering crystal turning
    # about its vertical axis without ever making the small icon disappear.
    yaw_width = max(6, round(target_width * (0.78 + 0.22 * abs(math.cos(turn)))))
    source = source.resize((yaw_width, target_height), Image.Resampling.LANCZOS)
    source = ImageEnhance.Brightness(source).enhance(
        0.96 + 0.06 * math.sin(turn * 2.0)
    )

    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    bob = round(math.sin(turn) * 0.8)
    x = (width - source.width) // 2
    y = (height - source.height) // 2 + bob
    canvas.paste(source.convert("RGB"), (x, y), source.getchannel("A"))

    palette_tile = remap_tile_palette_index(
        template_tile,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
    )
    return tile_from_rgb(palette_tile, palettes, canvas.tobytes())


def generated_ice_lance_impact_tile(
    template_tile: bytes,
    palette_index: int,
    frame_index: int,
    frame_count: int,
) -> bytes:
    height = 64
    width = 64
    phase = frame_index / max(1, frame_count - 1)
    pixels = [[0 for _ in range(width)] for _ in range(height)]

    cx = width * 0.50
    cy = height * 0.52
    grow = min(1.0, phase * 1.7 + 0.18)
    fade = 1.0 - max(0.0, phase - 0.45) * 1.15
    shard_angles = (
        -math.pi / 2.0,
        -math.pi * 0.30,
        -math.pi * 0.10,
        math.pi * 0.08,
        math.pi * 0.28,
        math.pi * 0.52,
        math.pi * 0.78,
        math.pi,
        -math.pi * 0.78,
        -math.pi * 0.54,
    )
    shard_lengths = (27.0, 22.0, 28.0, 21.0, 25.0, 19.0, 24.0, 20.0, 26.0, 18.0)

    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            distance = math.sqrt(dx * dx + dy * dy)
            color = 0

            if distance < 5.0 + 3.0 * (1.0 - phase):
                color = 1
            elif distance < 9.0 + 2.0 * grow:
                color = 39

            for index, angle in enumerate(shard_angles):
                ray_x = math.cos(angle)
                ray_y = math.sin(angle)
                along = dx * ray_x + dy * ray_y
                max_length = shard_lengths[index] * grow
                if along < 0.0 or along > max_length:
                    continue

                perp = abs(dx * -ray_y + dy * ray_x)
                base_width = 5.5 if index % 2 == 0 else 4.0
                shard_width = max(0.7, base_width * (1.0 - along / max(1.0, max_length)))
                if perp > shard_width:
                    continue

                core = perp < shard_width * 0.34
                if along > max_length * 0.72 and core:
                    color = max_palette_color(color, 1)
                elif core:
                    color = max_palette_color(color, 39)
                else:
                    color = max_palette_color(color, 73)

            if frame_index >= frame_count - 2 and color not in (0, 1):
                color = 73 if fade > 0.25 else 0

            if color == 0:
                continue

            pixels[y][x] = color

    tile = encode_indexed_v3_tile(
        pixels,
        palette_index,
        header_words=(
            3,
            height,
            width,
            0,
            32,
            0,
            0,
            1,
        ),
    )
    _ = template_tile
    return tile


def generated_chill_snowflake_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    frame_index: int,
    frame_count: int,
    empowered: bool = False,
) -> bytes:
    """Create one rotating frame for normal or empowered Chill."""
    from PIL import Image, ImageDraw

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    scale = 4
    canvas = Image.new("RGB", (width * scale, height * scale), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    center_x = width * scale * 0.5
    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    center_y = height * scale * 0.5 + math.sin(turn) * scale * 0.6
    pulse = 0.98 + 0.03 * math.sin(turn * 2.0)
    radius = min(width, height) * scale * 0.34 * pulse
    yaw = math.cos(turn)
    yaw_scale = math.copysign(0.18 + 0.82 * abs(yaw), yaw)
    if empowered:
        dark = (8, 28, 82)
        cyan = (28, 112, 190)
        pale = (88, 178, 220)
    else:
        dark = (24, 92, 146)
        cyan = (70, 205, 236)
        pale = (190, 240, 246)

    def project(angle: float, distance: float) -> tuple[float, float]:
        return (
            center_x + math.cos(angle) * distance * yaw_scale,
            center_y + math.sin(angle) * distance,
        )

    for arm_index in range(6):
        angle = -math.pi / 2.0 + arm_index * math.pi / 3.0
        end_x, end_y = project(angle, radius)
        draw.line(
            (center_x, center_y, end_x, end_y),
            fill=dark,
            width=3 * scale,
        )
        draw.line(
            (center_x, center_y, end_x, end_y),
            fill=cyan,
            width=2 * scale,
        )
        draw.line(
            (center_x, center_y, end_x, end_y),
            fill=pale,
            width=max(1, scale // 2),
        )

        branch_x, branch_y = project(angle, radius * 0.62)
        for branch_angle in (angle - math.pi * 0.72, angle + math.pi * 0.72):
            branch_end_x = branch_x + math.cos(branch_angle) * radius * 0.28 * yaw_scale
            branch_end_y = branch_y + math.sin(branch_angle) * radius * 0.28
            draw.line(
                (branch_x, branch_y, branch_end_x, branch_end_y),
                fill=dark,
                width=2 * scale,
            )
            draw.line(
                (branch_x, branch_y, branch_end_x, branch_end_y),
                fill=cyan,
                width=scale,
            )

    spark_radius = max(2, scale)
    spark_x = center_x + math.sin(turn) * radius * 0.92
    spark_y = center_y - radius * 0.22
    draw.ellipse(
        (
            spark_x - spark_radius,
            spark_y - spark_radius,
            spark_x + spark_radius,
            spark_y + spark_radius,
        ),
        fill=cyan,
    )

    core_radius = max(2, 3 * scale // 2)
    draw.ellipse(
        (
            center_x - core_radius,
            center_y - core_radius,
            center_x + core_radius,
            center_y + core_radius,
        ),
        fill=pale,
    )
    canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)
    palette_tile = remap_tile_palette_index(
        template_tile,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
    )
    return tile_from_rgb(palette_tile, palettes, canvas.tobytes())


def generated_eternal_soul_icon_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Render a compact ghost flame that gently pulses above the Phantom."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(bbox)

    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    pulse = 0.90 + 0.12 * (0.5 + 0.5 * math.sin(turn * 2.0))
    target_height = max(10, round(height * 0.82 * pulse))
    target_width = max(6, round(source.width * target_height / max(1, source.height)))
    if target_width > round(width * 0.76):
        target_width = max(6, round(width * 0.76))
        target_height = max(10, round(source.height * target_width / max(1, source.width)))
    source = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
    source = ImageEnhance.Brightness(source).enhance(
        0.86 + 0.10 * (0.5 + 0.5 * math.sin(turn * 2.0))
    )

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - source.width) // 2
    top = height - source.height - 1 + round(math.sin(turn) * 0.8)
    canvas.alpha_composite(source, (left, top))
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            struct.unpack_from("<H", template_tile, 10)[0],
            struct.unpack_from("<H", template_tile, 12)[0],
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_eternal_soul_cast_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Grow, pulse, and fade the ghost flame as a six-frame self-buff cast."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(bbox)

    progress = frame_index / max(1, frame_count - 1)
    if progress <= 0.60:
        growth = progress / 0.60
        smooth_growth = growth * growth * (3.0 - 2.0 * growth)
        scale = 0.18 + 0.82 * smooth_growth
        visible_alpha = 0.32 + 0.68 * growth
    elif progress <= 0.82:
        pulse = (progress - 0.60) / 0.22
        scale = 1.0 + 0.08 * math.sin(math.pi * pulse)
        visible_alpha = 1.0
    else:
        fade = (progress - 0.82) / 0.18
        scale = 1.03 - 0.15 * fade
        # Leave a dim, partially-eroded final drawing; the one-shot overlay
        # then removes it, completing the fade instead of snapping from the
        # brightest pulse directly to nothing.
        visible_alpha = max(0.22, 1.0 - 0.78 * fade)

    target_height = max(4, round(height * 0.74 * scale))
    target_width = max(3, round(source.width * target_height / max(1, source.height)))
    if target_width > round(width * 0.94):
        target_width = max(3, round(width * 0.94))
        target_height = max(4, round(source.height * target_width / max(1, source.width)))
    source = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
    source = ImageEnhance.Brightness(source).enhance(
        0.48 + 0.50 * visible_alpha
    )
    alpha = source.getchannel("A").point(lambda value: round(value * visible_alpha))
    source.putalpha(alpha)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - source.width) // 2
    top = height - source.height - 1
    canvas.alpha_composite(source, (left, top))
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            min(width - 1, struct.unpack_from("<H", template_tile, 10)[0] + 6),
            min(height - 1, struct.unpack_from("<H", template_tile, 12)[0] + 12),
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_frost_armor_crystal_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Render a hovering octahedral ward turning around its vertical axis."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox:
        source = source.crop(bbox)

    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    pulse = 0.98 + 0.035 * math.sin(turn * 2.0)
    target_height = max(8, round(height * 0.82 * pulse))
    target_width = max(5, round(source.width * target_height / max(1, source.height)))
    source = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
    yaw = math.cos(turn)
    yaw_width = max(3, round(target_width * (0.20 + 0.80 * abs(yaw))))
    source = source.resize((yaw_width, target_height), Image.Resampling.LANCZOS)
    if yaw < 0:
        source = source.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    source = ImageEnhance.Brightness(source).enhance(0.96 + 0.08 * abs(yaw))

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - source.width) // 2
    top = (height - source.height) // 2 + round(math.sin(turn) * 1.2)
    canvas.alpha_composite(source, (left, top))
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            struct.unpack_from("<H", template_tile, 10)[0],
            struct.unpack_from("<H", template_tile, 12)[0],
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_endless_winter_vortex_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Advance the internal ice arms while preserving the vortex ground plane."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")

    # The generated source is a 4x2 phase sheet. Normalize every cell onto the
    # same game-size canvas so minor source padding differences cannot cause
    # sprite bounce. A single-image source remains supported for diagnostics.
    source_frames: list[Image.Image] = []
    if 1.8 <= source.width / max(1, source.height) <= 2.2:
        for row in range(2):
            for column in range(4):
                left = round(source.width * column / 4)
                right = round(source.width * (column + 1) / 4)
                top = round(source.height * row / 2)
                bottom = round(source.height * (row + 1) / 2)
                source_frames.append(source.crop((left, top, right, bottom)))
    else:
        source_frames.append(source)

    normalized_frames: list[Image.Image] = []
    for source_frame in source_frames:
        bbox = source_frame.getchannel("A").getbbox()
        if bbox is None:
            continue
        source_frame = source_frame.crop(bbox)
        fit = min(
            width * 0.86 / max(1, source_frame.width),
            height * 0.86 / max(1, source_frame.height),
        )
        source_frame = source_frame.resize(
            (
                max(2, round(source_frame.width * fit)),
                max(2, round(source_frame.height * fit)),
            ),
            Image.Resampling.LANCZOS,
        )
        normalized = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        normalized.alpha_composite(
            source_frame,
            (
                (width - source_frame.width) // 2,
                (height - source_frame.height) // 2,
            ),
        )
        normalized_frames.append(normalized)
    if not normalized_frames:
        return blank_indexed_v3_tile(template_tile)

    phase = frame_index / max(1, frame_count)
    source_position = phase * len(normalized_frames)
    source_index = math.floor(source_position) % len(normalized_frames)
    next_source_index = (source_index + 1) % len(normalized_frames)
    blend = source_position - math.floor(source_position)
    moving_interior = Image.blend(
        normalized_frames[source_index],
        normalized_frames[next_source_index],
        blend,
    )

    # Deproject the receding ellipse to a circle, rotate the internal flow,
    # then project it back. This advances the arms in their ground plane
    # instead of clock-spinning the whole flattened sprite.
    deprojected = moving_interior.resize(
        (width, width),
        Image.Resampling.BICUBIC,
    )
    deprojected = deprojected.rotate(
        -360.0 * phase,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        center=(width / 2.0, width / 2.0),
    )
    rotated_interior = deprojected.resize(
        (width, height),
        Image.Resampling.BICUBIC,
    )

    # Keep the outer rim and elliptical silhouette from the first phase fixed.
    # The broad soft blend lets the arm spokes flow almost to the edge without
    # allowing the entire asset or its plane to turn.
    interior_mask = Image.new("L", (width, height), 0)
    mask_pixels = interior_mask.load()
    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0
    radius_x = max(1.0, width * 0.47)
    radius_y = max(1.0, height * 0.47)
    for y in range(height):
        for x in range(width):
            radius = math.sqrt(
                ((x - center_x) / radius_x) ** 2
                + ((y - center_y) / radius_y) ** 2
            )
            if radius <= 0.78:
                alpha = 255
            elif radius >= 0.98:
                alpha = 0
            else:
                transition = (radius - 0.78) / 0.20
                smooth = transition * transition * (3.0 - 2.0 * transition)
                alpha = round(255 * (1.0 - smooth))
            mask_pixels[x, y] = alpha
    canvas = Image.composite(
        rotated_interior,
        normalized_frames[0],
        interior_mask,
    )
    canvas = ImageEnhance.Brightness(canvas).enhance(0.78)
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            struct.unpack_from("<H", template_tile, 10)[0],
            struct.unpack_from("<H", template_tile, 12)[0],
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_endless_winter_missile_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    source_phase: int,
) -> bytes:
    """Render one generated snowflake-flick phase on a fixed projectile canvas."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")

    phase_count = 4
    source_phase = max(0, min(phase_count - 1, source_phase))
    left = round(source.width * source_phase / phase_count)
    right = round(source.width * (source_phase + 1) / phase_count)
    cell_width = right - left
    square_size = min(cell_width, source.height)
    top = (source.height - square_size) // 2
    frame = source.crop((left, top, right, top + square_size))
    frame = frame.resize((width, height), Image.Resampling.LANCZOS)
    frame = ImageEnhance.Brightness(frame).enhance(0.80)

    return rgba_to_indexed_tile(
        frame,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            width // 2,
            height // 2,
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_endless_winter_particle_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
) -> bytes:
    """Render a small rotating cyan snowflake for the two particle emitters."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        sheet = loaded.convert("RGBA")

    first_cell = sheet.crop((0, 0, sheet.width // 4, sheet.height))
    bounds = first_cell.getchannel("A").getbbox()
    if bounds is None:
        return blank_indexed_v3_tile(template_tile)
    flake = first_cell.crop(bounds)

    phase = frame_index / max(1, frame_count)
    pulse = 0.72 + 0.10 * math.sin(phase * math.tau)
    target_side = max(5, round(min(width, height) * pulse))
    flake.thumbnail(
        (target_side, target_side),
        Image.Resampling.LANCZOS,
    )
    flake = flake.rotate(
        phase * 120.0,
        resample=Image.Resampling.BICUBIC,
        expand=True,
    )
    flake = ImageEnhance.Brightness(flake).enhance(0.72)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(
        flake,
        (
            (width - flake.width) // 2,
            (height - flake.height) // 2,
        ),
    )
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            width // 2,
            height // 2,
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_endless_winter_hit_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
    stock_frame_area_ratio: float,
) -> bytes:
    """Grow and vertically rotate the hit tornado on a fixed ground anchor."""
    from PIL import Image, ImageEnhance

    height = struct.unpack_from("<H", template_tile, 2)[0]
    width = struct.unpack_from("<H", template_tile, 4)[0]
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(bbox)

    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    growth = max(0.30, min(1.0, math.sqrt(stock_frame_area_ratio)))
    target_height = max(5, round(height * 0.94 * growth))
    target_width = max(3, round(source.width * target_height / max(1, source.height)))
    if target_width > round(width * 0.92):
        target_width = round(width * 0.92)
        target_height = max(
            5,
            round(source.height * target_width / max(1, source.width)),
        )
    source = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
    yaw = math.cos(turn)
    yaw_width = max(3, round(target_width * (0.78 + 0.22 * abs(yaw))))
    source = source.resize((yaw_width, target_height), Image.Resampling.LANCZOS)
    if yaw < 0:
        source = source.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    source = ImageEnhance.Brightness(source).enhance(
        0.76 + 0.07 * abs(yaw)
    )

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(
        source,
        ((width - source.width) // 2, height - source.height - 1),
    )
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            struct.unpack_from("<H", template_tile, 10)[0],
            struct.unpack_from("<H", template_tile, 12)[0],
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_call_to_grave_portal_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    openness: float,
    visible_alpha: float,
) -> bytes:
    """Render one fixed-anchor phase of the spectral ice portal."""
    from PIL import Image, ImageEnhance

    width = 84
    height = 116
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return blank_indexed_v3_tile(template_tile)
    source = source.crop(bbox)

    openness = max(0.10, min(1.0, openness))
    visible_alpha = max(0.24, min(1.0, visible_alpha))
    target_height = round(height * (0.78 + 0.18 * openness))
    full_width = round(source.width * target_height / max(1, source.height))
    target_width = max(5, round(full_width * (0.16 + 0.84 * openness)))
    source = source.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )
    source = ImageEnhance.Brightness(source).enhance(0.76 + 0.16 * openness)

    alpha = source.getchannel("A").point(
        lambda value: round(value * visible_alpha)
    )
    source.putalpha(alpha)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - source.width) // 2
    top = height - source.height - 2
    canvas.alpha_composite(source, (left, top))
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (
            3,
            height,
            width,
            struct.unpack_from("<H", template_tile, 6)[0],
            32,
            width // 2,
            31,
            struct.unpack_from("<H", template_tile, 14)[0],
        ),
    )


def generated_frost_armor_casing_tile(
    template_tile: bytes,
    palettes: list[CamEntry],
    source_png: Path,
    frame_index: int,
    frame_count: int,
    canvas_size: tuple[int, int],
) -> bytes:
    """Render one size-aware ice casing frame around a frozen unit."""
    from PIL import Image, ImageEnhance

    width, height = canvas_size
    with Image.open(source_png) as loaded:
        source = loaded.convert("RGBA")
    bbox = source.getchannel("A").getbbox()
    if bbox:
        source = source.crop(bbox)

    phase = frame_index / max(1, frame_count)
    turn = phase * math.tau
    pulse = 0.965 + 0.035 * (0.5 + 0.5 * math.sin(turn * 2.0))
    target_width = max(8, round(width * 0.96 * pulse))
    target_height = max(8, round(height * 0.96 * pulse))
    source.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
    source = ImageEnhance.Brightness(source).enhance(0.94 + 0.08 * (0.5 + 0.5 * math.sin(turn)))

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - source.width) // 2
    top = height - source.height - 1
    canvas.alpha_composite(source, (left, top))
    _ = template_tile
    return rgba_to_indexed_tile(
        canvas,
        palettes,
        ICE_LANCE_PROJECTILE_PALETTE_INDEX,
        (3, height, width, 0, 32, width // 2, height // 2, 1),
    )


def rgba_to_indexed_tile(
    image: object,
    palettes: list[CamEntry],
    palette_index: int,
    header_words: tuple[int, int, int, int, int, int, int, int],
) -> bytes:
    """Quantize visible RGBA pixels while preserving index zero as transparency."""
    width, height = image.size
    colors = splt_palette_colors(palettes[palette_index].data)
    pixels = [[0 for _ in range(width)] for _ in range(height)]
    color_cache: dict[tuple[int, int, int], int] = {}
    source_pixels = image.load()
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha < 48:
                continue
            key = (red, green, blue)
            if key not in color_cache:
                color_cache[key] = nearest_visible_palette_index(red, green, blue, colors)
            pixels[y][x] = color_cache[key]
    return encode_indexed_v3_tile(pixels, palette_index, header_words=header_words)


def remap_indexed_v3_tile_to_palette(
    source_tile: bytes,
    source_colors: list[tuple[int, int, int]],
    target_palette_index: int,
    target_colors: list[tuple[int, int, int]],
) -> bytes:
    decoded = decode_indexed_v3_tile(source_tile)
    if decoded is None:
        return source_tile

    height, width, pixels = decoded
    remapped_pixels = [[0 for _ in range(width)] for _ in range(height)]
    color_cache: dict[int, int] = {}

    for y in range(height):
        for x in range(width):
            source_index = pixels[y][x]
            if source_index == 0:
                continue
            if source_index not in color_cache:
                red, green, blue = source_colors[source_index]
                color_cache[source_index] = nearest_palette_index(red, green, blue, target_colors)
            remapped_pixels[y][x] = color_cache[source_index]

    return encode_indexed_v3_tile(
        remapped_pixels,
        target_palette_index,
        header_words=(
            3,
            height,
            width,
            struct.unpack_from("<H", source_tile, 6)[0],
            32,
            struct.unpack_from("<H", source_tile, 10)[0],
            struct.unpack_from("<H", source_tile, 12)[0],
            struct.unpack_from("<H", source_tile, 14)[0],
        ),
    )


def decode_indexed_v3_tile(tile: bytes) -> tuple[int, int, list[list[int]]] | None:
    if len(tile) < 26 or struct.unpack_from("<H", tile, 0)[0] != 3:
        return None

    height = struct.unpack_from("<H", tile, 2)[0]
    width_hint = struct.unpack_from("<H", tile, 4)[0]
    offset_base = 26
    if offset_base + height * 4 > len(tile):
        return None

    offsets = [u32(tile, offset_base + row * 4) for row in range(height)]
    rows: list[list[tuple[int, list[int]]]] = []
    max_width = width_hint
    for row_index, row_offset in enumerate(offsets):
        start = offset_base + row_offset
        end = offset_base + offsets[row_index + 1] if row_index + 1 < height else len(tile)
        if start > len(tile) or end > len(tile) or start > end:
            return None

        row_data = tile[start:end]
        position = 0
        segments: list[tuple[int, list[int]]] = []
        while position + 4 <= len(row_data):
            x_end = struct.unpack_from("<H", row_data, position)[0]
            count = row_data[position + 2]
            flags = row_data[position + 3]
            position += 4
            values = list(row_data[position : position + count])
            position += count
            if count:
                x_start = x_end - count
                segments.append((x_start, values))
                max_width = max(max_width, x_end)
            if flags & 0x80:
                break
        rows.append(segments)

    pixels = [[0 for _ in range(max_width)] for _ in range(height)]
    for y, segments in enumerate(rows):
        for x_start, values in segments:
            for offset, value in enumerate(values):
                x = x_start + offset
                if 0 <= x < max_width:
                    pixels[y][x] = value

    return height, max_width, pixels


def max_palette_color(current: int, candidate: int) -> int:
    priority = {0: 0, 73: 1, 39: 2, 1: 3}
    return candidate if priority.get(candidate, 0) > priority.get(current, 0) else current


def encode_indexed_v3_tile(
    pixels: list[list[int]],
    palette_index: int,
    header_words: tuple[int, int, int, int, int, int, int, int],
) -> bytes:
    rows: list[bytes] = []
    for row_pixels in pixels:
        row = bytearray()
        x = 0
        width = len(row_pixels)
        while x < width:
            if row_pixels[x] == 0:
                x += 1
                continue

            start = x
            values: list[int] = []
            while x < width and row_pixels[x] != 0 and len(values) < 80:
                values.append(row_pixels[x])
                x += 1

            next_x = x
            while next_x < width and row_pixels[next_x] == 0:
                next_x += 1
            flags = 0 if next_x < width else 0x80
            row += struct.pack("<HBB", start + len(values), len(values), flags)
            row += bytes(values)

        if not row:
            row += struct.pack("<HBB", 0, 0, 0x80)
        rows.append(bytes(row))

    header = struct.pack("<HHHHHHHH", *header_words)
    offsets: list[int] = []
    cursor = len(rows) * 4
    for row in rows:
        offsets.append(cursor)
        cursor += len(row)

    output = bytearray(header)
    output += b"\x00" * 6
    output += struct.pack("<I", palette_index)
    for offset in offsets:
        output += struct.pack("<I", offset)
    for row in rows:
        output += row
    return bytes(output)


def encode_indexed_v3_tile_like_original(
    original_tile: bytes,
    pixels: list[list[int]],
    *,
    split_shadow_controls: bool = False,
) -> bytes:
    if len(original_tile) < 26 or struct.unpack_from("<H", original_tile, 0)[0] != 3:
        return original_tile

    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    header = bytearray(original_tile[:26])
    struct.pack_into("<H", header, 2, height)
    struct.pack_into("<H", header, 4, width)

    rows: list[bytes] = []
    for row_pixels in pixels:
        row = bytearray()
        x = 0
        row_width = len(row_pixels)
        while x < row_width:
            if row_pixels[x] == 0:
                x += 1
                continue

            start = x
            values: list[int] = []
            segment_is_shadow = 247 <= row_pixels[x] <= 250
            while x < row_width and row_pixels[x] != 0 and len(values) < 80:
                value_is_shadow = 247 <= row_pixels[x] <= 250
                if split_shadow_controls and values and value_is_shadow != segment_is_shadow:
                    break
                values.append(row_pixels[x])
                x += 1

            next_x = x
            while next_x < row_width and row_pixels[next_x] == 0:
                next_x += 1
            flags = 0 if next_x < row_width else 0x80
            row += struct.pack("<HBB", start + len(values), len(values), flags)
            row += bytes(values)

        if not row:
            row += struct.pack("<HBB", 0, 0, 0x80)
        rows.append(bytes(row))

    output = bytearray(header)
    cursor = height * 4
    for row in rows:
        output += struct.pack("<I", cursor)
        cursor += len(row)
    for row in rows:
        output += row

    palette_mode = struct.unpack_from("<H", original_tile, 20)[0]
    original_palette_offset = struct.unpack_from("<I", original_tile, 22)[0]
    if palette_mode == 1 and 0 <= original_palette_offset < len(original_tile):
        new_palette_offset = len(output)
        struct.pack_into("<I", output, 22, new_palette_offset)
        output += original_tile[original_palette_offset:]

    return bytes(output)


def encode_indexed_v3_tile_with_embedded_palette(
    original_tile: bytes,
    pixels: list[list[int]],
    palette: list[tuple[int, int, int]],
) -> bytes:
    output = bytearray(encode_indexed_v3_tile_like_original(original_tile, pixels))
    palette_mode = struct.unpack_from("<H", output, 20)[0]
    palette_offset = struct.unpack_from("<I", output, 22)[0]
    if palette_mode != 1 or palette_offset > len(output):
        return bytes(output)

    original_palette_offset = struct.unpack_from("<I", original_tile, 22)[0]
    original_palette_tail = (
        original_tile[original_palette_offset:]
        if 0 <= original_palette_offset < len(original_tile)
        else b""
    )
    palette_prefix = original_palette_tail[:8]
    palette_suffix = original_palette_tail[8 + 256 * 4 :]

    output = output[:palette_offset]
    output += palette_prefix
    for index in range(256):
        if index < len(palette):
            red, green, blue = palette[index]
        else:
            red, green, blue = (0, 0, 0)
        output += bytes((red, green, blue, 0))
    output += palette_suffix

    return bytes(output)


def line_intensity(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
) -> float:
    sx, sy = start
    ex, ey = end
    px, py = point
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        return 0.0

    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    cx = sx + dx * t
    cy = sy + dy * t
    distance = math.sqrt((px - cx) * (px - cx) + (py - cy) * (py - cy))
    if distance > width:
        return 0.0
    return 1.0 - (distance / max(0.1, width))


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

    image_plane_size = width * height
    if len(original_tile) > 26 + image_plane_size:
        output += original_tile[26 + image_plane_size :]

    return bytes(output)


def recolored_priestess_phantom_sprite_tile(
    original_tile: bytes,
    palettes: list[CamEntry],
    source_tile_index: int | None = None,
) -> bytes:
    decoded = decode_indexed_v3_tile(original_tile)
    if decoded is None:
        return original_tile

    palette_index = tile_palette_index(original_tile)
    if palette_index is None or palette_index >= len(palettes) or len(palettes) <= 32:
        return original_tile

    source_colors = splt_palette_colors(palettes[palette_index].data)
    target_colors = splt_palette_colors(palettes[32].data)
    height, width, pixels = decoded
    remapped_pixels = [[0 for _ in range(width)] for _ in range(height)]
    color_cache: dict[int, int] = {}

    for y in range(height):
        for x in range(width):
            source_index = pixels[y][x]
            if source_index == 0:
                continue

            if source_index not in color_cache:
                color_cache[source_index] = nearest_palette_index(
                    *phantom_priestess_recolor(source_colors[source_index]),
                    target_colors,
                )
            remapped_pixels[y][x] = color_cache[source_index]

    if source_tile_index is not None and is_priestess_walk_tile(source_tile_index):
        apply_phantom_float_walk_adjustment(remapped_pixels, pixels, source_tile_index)

    return encode_indexed_v3_tile(
        remapped_pixels,
        32,
        header_words=struct.unpack_from("<HHHHHHHH", original_tile, 0),
    )


def phantom_priestess_recolor(color: tuple[int, int, int]) -> tuple[int, int, int]:
    red, green, blue = color
    if red < 8 and green < 8 and blue < 10:
        return (0, 0, 0)

    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    max_channel = max(red, green, blue)
    min_channel = min(red, green, blue)
    saturation = 0 if max_channel == 0 else (max_channel - min_channel) / max_channel
    red_cloak = (
        (red > 35 and red > green * 1.16 and red > blue * 0.86 and saturation > 0.20)
        or (red > 64 and green < 74 and blue < 96 and red > green + 16)
        or (red > 50 and blue > 34 and green < 62 and red >= blue * 0.90)
    )
    skin = red > 105 and green > 58 and blue > 35 and red > blue * 1.08 and green > blue * 0.68
    gold_or_staff = (
        (red > 112 and green > 78 and blue < 84)
        or (luminance > 128 and (max_channel - min_channel) < 82)
    )

    if red_cloak:
        if luminance > 153:
            return (60, 205, 230)
        if luminance > 87:
            return (30, 95, 125)
        if luminance > 38:
            return (18, 52, 78)
        return (5, 14, 32)

    if skin:
        return (
            min(255, int(42 + luminance * 0.30)),
            min(255, int(80 + luminance * 0.37)),
            min(255, int(95 + luminance * 0.44)),
        )

    if gold_or_staff:
        if luminance > 190:
            return (184, 188, 198)
        if luminance > 122:
            return (108, 118, 132)
        return (35, 48, 62)

    if red > green + 14 and red > blue + 6:
        return (
            min(255, int(red * 0.32 + 6)),
            min(255, int(green * 0.56 + 18)),
            min(255, int(blue * 0.82 + 38)),
        )

    if luminance < 45:
        return (4, 9, 16)
    if luminance < 95:
        return (24, 38, 52)
    if luminance < 150:
        return (68, 92, 112)
    if luminance < 205:
        return (122, 158, 174)
    return (204, 235, 240)


PRIESTESS_WALK_TILE_RANGES = (
    range(4587, 4594),
    range(4595, 4602),
    range(4603, 4610),
    range(4611, 4618),
    range(4619, 4626),
    range(4627, 4634),
)


def is_priestess_walk_tile(tile_index: int) -> bool:
    return any(tile_index in tile_range for tile_range in PRIESTESS_WALK_TILE_RANGES)


def priestess_walk_frame_number(tile_index: int) -> int:
    for tile_range in PRIESTESS_WALK_TILE_RANGES:
        if tile_index in tile_range:
            return tile_index - tile_range.start
    return 0


def apply_phantom_float_walk_adjustment(
    remapped_pixels: list[list[int]],
    source_pixels: list[list[int]],
    source_tile_index: int,
) -> None:
    height = len(remapped_pixels)
    if height == 0:
        return

    width = len(remapped_pixels[0])
    frame = priestess_walk_frame_number(source_tile_index)
    start_y = int(height * 0.72)

    for y in range(start_y, height):
        row_factor = (y - start_y) / max(1, height - start_y)
        for x in range(width):
            if source_pixels[y][x] == 0:
                continue

            # The lower body is where the Priestess reads most like walking legs.
            # Poke a few stable transparent gaps near the hem so the same source
            # frames feel like a drifting robe instead of planted feet.
            hem_gap = y > int(height * 0.88) and ((x * 3 + y + frame * 5) % 11 == 0)
            deep_hem_gap = y > int(height * 0.94) and ((x + frame) % 4 == 0)
            if hem_gap or deep_hem_gap:
                remapped_pixels[y][x] = 0

        if row_factor > 0.55 and frame in (1, 2, 5, 6):
            # Dampen side-to-side stride flicker by trimming a little of the outer
            # lower silhouette on the most leg-forward frames.
            visible = [x for x in range(width) if remapped_pixels[y][x] != 0]
            if len(visible) > 7:
                remapped_pixels[y][visible[0]] = 0
                remapped_pixels[y][visible[-1]] = 0


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


def referenced_low16_tile_indices(imag: bytes, tile_count: int) -> set[int]:
    result: set[int] = set()
    for offset in range(0, len(imag) - 3, 4):
        low_tile_index = u32(imag, offset) & 0xFFFF
        if low_tile_index < tile_count:
            result.add(low_tile_index)
    return result


def building_sprite_replacement_paths(building_sprite_rgb_dir: Path | None) -> dict[int, Path]:
    if building_sprite_rgb_dir is None or not building_sprite_rgb_dir.exists():
        return {}

    prefix = "building_tile_"
    paths: dict[int, Path] = {}
    for path in sorted(building_sprite_rgb_dir.glob(f"{prefix}*.png")):
        try:
            tile_index = int(path.stem[len(prefix) :])
        except ValueError:
            continue
        paths[tile_index] = path
    return paths


def building_active_replacement_paths(building_sprite_rgb_dir: Path | None) -> list[Path]:
    if building_sprite_rgb_dir is None or not building_sprite_rgb_dir.exists():
        return []

    prefix = "building_active_frame_"
    paths: dict[int, Path] = {}
    for path in sorted(building_sprite_rgb_dir.glob(f"{prefix}*.png")):
        try:
            frame_index = int(path.stem[len(prefix) :])
        except ValueError:
            continue
        paths[frame_index] = path
    return [paths[index] for index in sorted(paths)]


def hero_sprite_replacement_paths(hero_sprite_png_dir: Path | None) -> dict[int, Path]:
    if hero_sprite_png_dir is None or not hero_sprite_png_dir.exists():
        return {}

    prefix = "hero_tile_"
    paths: dict[int, Path] = {}
    for path in sorted(hero_sprite_png_dir.glob(f"{prefix}*.png")):
        try:
            tile_index = int(path.stem[len(prefix) :])
        except ValueError:
            continue
        paths[tile_index] = path
    return paths


def cast_glow_replacement_paths(hero_sprite_png_dir: Path | None) -> list[Path]:
    if hero_sprite_png_dir is None or not hero_sprite_png_dir.exists():
        return []

    prefix = "cast_glow_"
    paths: dict[int, Path] = {}
    for path in sorted(hero_sprite_png_dir.glob(f"{prefix}*.png")):
        try:
            stage = int(path.stem[len(prefix) :])
        except ValueError:
            continue
        paths[stage] = path
    return [paths[index] for index in sorted(paths)]


def splt_palette_colors(palette: bytes) -> list[tuple[int, int, int]]:
    if len(palette) < 8 + 256 * 4:
        raise ValueError("Expected a 256-color SPLT palette")

    colors: list[tuple[int, int, int]] = []
    for index in range(256):
        offset = 8 + index * 4
        colors.append((palette[offset], palette[offset + 1], palette[offset + 2]))
    return colors


def splt_with_color_replacements(
    palette: bytes,
    replacements: dict[int, tuple[int, int, int]],
) -> bytes:
    if len(palette) < 8 + 256 * 4:
        raise ValueError("Expected a 256-color SPLT palette")
    patched = bytearray(palette)
    for index, (red, green, blue) in replacements.items():
        offset = 8 + index * 4
        patched[offset : offset + 3] = bytes((red, green, blue))
    return bytes(patched)


def embedded_palette_colors(tile: bytes, palette_offset: int) -> list[tuple[int, int, int]] | None:
    if palette_offset < 0:
        return None
    if (
        len(tile) >= palette_offset + 8 + 256 * 4
        and tile[palette_offset : palette_offset + 8] == b"\x00\x00\x00\x01\x00\x00\x00\x00"
    ):
        palette_offset += 8
    if len(tile) < palette_offset + 256 * 4:
        return None

    colors: list[tuple[int, int, int]] = []
    for index in range(256):
        offset = palette_offset + index * 4
        colors.append((tile[offset], tile[offset + 1], tile[offset + 2]))
    return colors


def tile_palette_colors(tile: bytes, palettes: list[CamEntry]) -> list[tuple[int, int, int]] | None:
    if len(tile) < 26:
        return None

    palette_mode = struct.unpack_from("<H", tile, 20)[0]
    palette_value = struct.unpack_from("<I", tile, 22)[0]
    if palette_mode == 1:
        return embedded_palette_colors(tile, palette_value)

    if palette_value < len(palettes):
        return splt_palette_colors(palettes[palette_value].data)
    return None


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


def nearest_visible_palette_index(red: int, green: int, blue: int, colors: list[tuple[int, int, int]]) -> int:
    best_index = 1
    best_distance = math.inf
    for index, (palette_red, palette_green, palette_blue) in enumerate(colors):
        if index in (0, 255):
            continue
        if palette_red > 115 and palette_green < 80 and palette_blue > 115:
            continue
        if index >= 247 and palette_green < 80 and palette_red > 80 and palette_blue > 80:
            continue
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
