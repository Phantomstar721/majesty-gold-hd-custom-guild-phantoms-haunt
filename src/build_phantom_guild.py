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
BUILDING_ID = "MBPhantomGuild"
BUILDING_TEXT_ID = "PHG1"
SOURCE_HERO_IMAGE = b"AVN1Wizard"
SOURCE_PHANTOM_SPRITE_IMAGE = b"AVG1Priestess"
SOURCE_BUILDING_IMAGE = b"ABY1Wizard Guild1"
SOURCE_ICE_LANCE_ICON = b"XL15PowerShock"
SOURCE_ICE_LANCE_PROJECTILE = b"WPc2fire_blast_M"
SOURCE_FROST_ARMOR_ICON = b"WRb2fireshield_IC"
SOURCE_BLIZZARD_ICON = b"WRg2meteor_blast"
ROGUE_HERO_IMAGE = b"AVJ1Rogue"
PHANTOM_HERO_IMAGE = b"PHM1Phantom"
PHANTOM_BUILDING_IMAGE = b"PHG1Phantom Guild"
PHANTOM_ICE_LANCE_ICON = b"WRa2Ice Lance"
PHANTOM_ICE_LANCE_PROJECTILE = b"PHp1fire_blast_M"
PHANTOM_FROST_ARMOR_ICON = b"WRa3Frost Armor"
PHANTOM_BLIZZARD_ICON = b"WRa4Blizzard"
FROST_FIELD_HIT_IMAGE = b"XR30frost_fld_hit"
PHANTOM_ICE_LANCE_HIT_IMAGE = b"PHo3Ice Lance Hit"
HERO_PORTRAIT_TILE = 6293
HERO_ICON_TILE = 6299
ROGUE_HERO_ICON_TILE = 4996
BUILDING_PROFILE_TILE = 1779
BUILDING_ICON_TILE = 1904
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
BLIZZARD_SPELL_ICON_TILES = (346,)
STAFF_ICON_TILES: tuple[int, ...] = ()
STAFF_SMALL_ICON_TILES: tuple[int, ...] = ()
MX_STAFF_ICON_TILES: tuple[int, ...] = ()
LEATHER_ARMOR_ICON_TILES: tuple[int, ...] = ()


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
    parser.add_argument("--ice-lance-icon-rgb", type=Path)
    parser.add_argument("--ice-lance-spell-icon-rgb", type=Path)
    parser.add_argument("--frost-armor-spell-icon-rgb", type=Path)
    parser.add_argument("--blizzard-spell-icon-rgb", type=Path)
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
        args.ice_lance_icon_rgb,
        source_ice_effect_maindata if source_ice_effect_maindata.exists() else None,
    )
    write_interfacedata_cam(
        source_interfacedata,
        data_dir / "phantom_interfacedata.cam",
        args.ice_lance_spell_icon_rgb,
        args.frost_armor_spell_icon_rgb,
        args.blizzard_spell_icon_rgb,
        args.phantom_cowl_icon_rgb,
        args.dark_staff_small_icon_rgb,
        args.dark_staff_icon_rgb,
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
    (data_dir / "phantom_sounds.xml").write_text(phantom_sounds_xml(), encoding="utf-8")
    (gpl_dir / "Phantom_Building_Data.dat").write_text(phantom_building_data(), encoding="utf-8")
    (gpl_dir / "Phantom_Hero_Data.dat").write_text(phantom_hero_data(), encoding="utf-8")
    (gpl_dir / "Phantom_Items_Data.dat").write_text(phantom_items_data(), encoding="utf-8")
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
\t\t\t<Attachment kind="Movement" type="Walk" ID="Class 1"/>
\t\t\t<DefaultSound value="Phantom"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="AP20"/>
\t\t\t<Cost value="1"/>
\t\t\t<Experience value="2000"/>
\t\t\t<MaxHP value="18"/>
\t\t\t<SightRange value="240"/>
\t\t\t<Speed value="2"/>
\t\t\t<AttackRange min="1" max="240"/>
\t\t\t<Vitality value="6"/>
\t\t\t<Artifice value="8"/>
\t\t\t<WillPower value="22"/>
\t\t\t<Intelligence value="24"/>
\t\t\t<Strength value="2"/>
\t\t\t<MagicResistance value="45"/>
\t\t\t<Attack value="30"/>
\t\t\t<Parry value="20"/>
\t\t\t<Dodge value="35"/>
\t\t\t<WeaponBasicDamage value="0"/>
\t\t\t<ArmorBasicDamage value="0"/>
\t\t\t<RecruitDelay value="1000"/>
\t\t\t<PrimaryStat value="2"/>
\t\t\t<NameGenType value="NM16"/>
\t\t\t<Flags value="Heals"/>
\t\t\t<Flags value="HasHPBar"/>
\t\t\t<Flags value="CanHighlight"/>
\t\t\t<HelpID value="h020"/>
\t\t\t<AllowedSpells>
\t\t\t\t<Spell ID="0" Value="ice_lance"/>
\t\t\t</AllowedSpells>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Character" ID="FrozenCowl" Name="FrozenCowl" Description="Frozen Cowl">
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
\t\t\t\t<Attribute ID="CanDropItem" Value="1"/>
\t\t\t\t<Attribute ID="Phantom_Item_FrozenCowl" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Character" ID="BlackIcerod" Name="BlackIcerod" Description="Black Icerod">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="8"/>
\t\t\t<ImageIDBase value="PHIR"/>
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
\t\t\t\t<Attribute ID="CanDropItem" Value="1"/>
\t\t\t\t<Attribute ID="Phantom_Item_BlackIcerod" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Building" ID="MBPhantomGuild" Name="Phantoms_Guild" Description="Phantoms Guild">
\t\t<Engine version="1">
\t\t\t<Info value="BlockGround"/>
\t\t\t<Info value="BlockFlying"/>
\t\t\t<Info value="ModifyTerrainTextureOnPlacement"/>
\t\t\t<Info value="ModifyTerrainHeightOnPlacement"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="1"/>
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
\t\t\t<EffectorDuration value="20000"/>
\t\t\t<TimeoutDuration value="30000"/>
\t\t\t<SpellType value="CombatUtility"/>
\t\t\t<CharacterLevel value="3"/>
\t\t\t<SpellRank value="3"/>
\t\t</Game>
\t</Description>
\t<Description type="Action" subType="Standard" ID="WRa4" Name="blizzard" Description="Blizzard">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="Meteor_Storm"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Blizzard_Hit"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<Flags value="IsSpell"/>
\t\t\t<EffectorDuration value="21000"/>
\t\t\t<TimeoutDuration value="55000"/>
\t\t\t<SpellType value="Attack"/>
\t\t\t<CharacterLevel value="7"/>
\t\t\t<SpellRank value="7"/>
\t\t\t<ValidationScript value="Blizzard_Check"/>
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
\t<Description type="Unit" subType="Overlay" ID="PHo1" Name="frost_armor_effector" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="WRb1"/>
\t\t\t<DefaultSound value="FireShield"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="0"/>
\t\t\t<Flags value="TransparentToMouse"/>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Overlay" ID="PHo2" Name="frost_armor_icon" Description="Frost Armor">
\t\t<Engine version="1">
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="DontBlock"/>
\t\t\t<Menu value="11"/>
\t\t\t<ImageIDBase value="WRb2"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Frost_Armor_End"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t\t<Game version="1">
\t\t\t<DialogID value="0"/>
\t\t\t<StackPriority value="1"/>
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
\t\t(attack_action do_nothing)
\t\t(Cast_Action Basic_Cast)
\t\t(Pickup_Action Basic_Pickup)
\t\t(PrimaryStat ATTRIB_Intelligence)
\t\t(Friend\txx)
\t\t(attacktype 1)
\t\t(castingrange 240)
\t\t(PercentageHPRetreat 50)
\t\t(enemy_estimation 1.1)
\t\t(self_estimation 1.0)
\t\t(Loyalty 55)
\t\t(Greed 8)
\t\t(Luck 12)
\t\t(Upgrade_Armor_Chance\t0)
\t\t(Upgrade_Weapon_Chance\t0)
\t\t(Poison_Weapon_Chance\t0)
\t\t(evaluationScript\twizard_eval_nearby)
\t\t(activeScript\tPhantom_tree)
\t\t(basicscript\tPhantom_tree)
\t\t(StartingScript\tPhantom_tree)
\t\t(birthScript\tPhantom_birth)
\t\t(IGdeathscript\tPhantom_death)
\t}
[end]
"""


def phantom_items_data() -> str:
    return """[FrozenCowl]
\t{Special_Item
\t\t(type \t\tSpecial_Item)
\t\t(Title\t\tFrozenCowl)
\t}
[end]

[BlackIcerod]
\t{Special_Item
\t\t(type \t\tSpecial_Item)
\t\t(Title\t\tBlackIcerod)
\t}
[end]
"""


def phantom_building_data() -> str:
    return """[Phantoms_Guild]
\t{Guild
\t\t(type building)
\t\t(subtype Guild)
\t\t(title Phantoms_Guild)
\t\t(Level 1)
\t\t(max_level 1)
\t\t(member_title Phantom)
\t\t(member_basicscript Phantom_tree)
\t\t(max_members 4)
\t\t(Lived_In_Script Lived_In)
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
    return """expression #Phantom_Item_FrozenCowl 80
expression #Phantom_Item_BlackIcerod 81

function Phantom_tree (agent thisagent)

declare

begin
\t$DebugOut("Phantom deciding");

\t$Wizard_tree(thisagent);
end

function Phantom_birth (agent thisagent)

declare

begin
\t$PlaySound(thisagent, "Phantom", "VFX_SPECIAL1");
\t$hero_birth(thisagent);
\t$Phantom_grant_starter_items(thisagent);
\t$LearnSpell(thisagent, "ice_lance");
end

function Phantom_grant_starter_items (agent thisagent)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf ($AgentHasInventoryItem(#Phantom_Item_FrozenCowl, thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem(#Phantom_Item_FrozenCowl, thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 1);
\t\tend

\tIf ($AgentHasInventoryItem(#Phantom_Item_BlackIcerod, thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem(#Phantom_Item_BlackIcerod, thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$adjustattribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);
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

function Ice_Lance_Hit(agent thisagent, agent target)

declare

begin
\t$PlaySound(target, "Energy_Blast", "Attack");
\t$createeffector(target, "ice_lance_hit_effector", 0);
\t$spell_attack(thisagent, target, 18);
end

function Phantom_death(agent thisagent)

declare

begin
\t$Phantom_remove_starter_items(thisagent);
\t$gravestone(thisagent);
end

function Phantom_remove_starter_items(agent thisagent)

declare

begin
\tWhile ($AgentHasInventoryItem(#Phantom_Item_FrozenCowl, thisagent)) do
\t\tbegin
\t\t\t$DeleteInventoryItem(#Phantom_Item_FrozenCowl, thisagent);
\t\tend

\tWhile ($AgentHasInventoryItem(#Phantom_Item_BlackIcerod, thisagent)) do
\t\tbegin
\t\t\t$DeleteInventoryItem(#Phantom_Item_BlackIcerod, thisagent);
\t\tend
end

function Frost_Armor_Begin(agent thisagent, agent target)

declare

begin
\t$createeffector(thisagent, "frost_armor_effector", 0);
\t$createeffector(thisagent, "frost_armor_icon", $GetSpellAttribute("frost_armor", "effector_duration"));
\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 4);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Magicresistance, 20);
end

function Frost_Armor_End(agent thisagent)

declare

begin
\t$DeleteEffector(thisagent, "frost_armor_effector");
\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, -4);
\t$MagicalAdjustAttribute(thisagent, #ATTRIB_Magicresistance, -20);
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
\t\t\t\t\t<Descriptions>Data\\phantom_units.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_actions.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_projectiles.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_overlays.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_sounds.xml</Descriptions>
\t\t\t\t\t<CAM>Data\\phantom_textdata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_gpltext.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_maindata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_interfacedata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_mx_interfacedata.cam</CAM>
\t\t\t\t\t<CAM>Data\\phantom_voices.cam</CAM>
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
\t\t<DisplayName lang="en_US">Phantom Guild POC</DisplayName>
\t\t<Description lang="en_US">
\t\t\t<Short>Adds a test Phantoms Guild and recruitable Phantom hero.</Short>
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
    patched_unit_names = patch_strt_strings(
        unit_names.data,
        {
            fourcc_id(HERO_ID): "Phantom",
            fourcc_id(BUILDING_TEXT_ID): "Phantoms Guild",
            fourcc_id("PHIC"): "Frozen Cowl",
            fourcc_id("PHIR"): "Black Icerod",
        },
    )
    patched_action_names = patch_strt_strings(
        action_names.data,
        {
            fourcc_id("WRa2"): "Ice Lance",
        },
    )
    write_cam(
        (
            CamSection(
                extension=b"STRT",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(b"UNTN"), data=patched_unit_names),
                    CamEntry(name=pad_name(b"ACTN"), data=patched_action_names),
                ),
            ),
        ),
        output_path,
    )


def write_gpltext_cam(source_gpltext: Path, output_path: Path) -> None:
    quest_item_names = read_cam_entry(source_gpltext, b"STRT", b"QITM")
    patched_quest_item_names = patch_indexed_strt_strings(
        quest_item_names.data,
        {
            80: "Frozen Cowl\n\x01FFDDAA(+1 armor)",
            81: "Black Icerod\n\x01FFDDAA(+8 damage)",
        },
    )
    write_cam(
        (
            CamSection(
                extension=b"STRT",
                padding=b"\x00\x00\x00\x00",
                entries=(
                    CamEntry(name=pad_name(b"QITM"), data=patched_quest_item_names),
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
    ice_lance_icon_rgb: Path | None,
    ice_effect_maindata: Path | None,
) -> None:
    hero_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_PHANTOM_SPRITE_IMAGE).data
    rogue_hero_imag = read_cam_entry(source_maindata, b"IMAG", ROGUE_HERO_IMAGE).data
    building_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_BUILDING_IMAGE).data
    ice_lance_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICE_LANCE_ICON).data
    ice_lance_projectile = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICE_LANCE_PROJECTILE).data
    frost_armor_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_FROST_ARMOR_ICON).data
    blizzard_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_BLIZZARD_ICON).data
    tiles = read_cam_entries(source_maindata, b"TILE")
    palettes = read_cam_entries(source_maindata, b"SPLT")
    ice_lance_hit_effect: bytes | None = None
    ice_effect_tiles: list[bytes] = []
    source_ice_tile_indices: list[int] = []
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

    phantom_sprite_tile_indices = sorted(
        index
        for index in referenced_tile_indices(hero_imag, len(tiles))
        if 4586 <= index <= 4793
    )

    tile_indices: set[int] = set()
    tile_indices.update(referenced_tile_indices(rogue_hero_imag, len(tiles)))
    tile_indices.update(referenced_tile_indices(building_imag, len(tiles)))
    tile_indices.update(referenced_tile_indices(ice_lance_icon, len(tiles)))
    tile_indices.update(referenced_tile_indices(ice_lance_projectile, len(tiles)))
    tile_indices.update(referenced_tile_indices(frost_armor_icon, len(tiles)))
    tile_indices.update(referenced_tile_indices(blizzard_icon, len(tiles)))
    tile_indices.update((HERO_PORTRAIT_TILE, HERO_ICON_TILE, BUILDING_PROFILE_TILE, BUILDING_ICON_TILE, ICE_LANCE_ICON_TILE))
    max_tile_index = max(tile_indices)

    replacement_tiles = {
        ROGUE_HERO_ICON_TILE: tile_from_rgb(
            tiles[ROGUE_HERO_ICON_TILE].data,
            palettes,
            hero_icon_rgb.read_bytes() if hero_icon_rgb else None,
        ),
        HERO_PORTRAIT_TILE: tile_from_rgb(
            tiles[HERO_PORTRAIT_TILE].data,
            palettes,
            portrait_rgb.read_bytes() if portrait_rgb else None,
        ),
        HERO_ICON_TILE: tile_from_rgb(
            tiles[HERO_ICON_TILE].data,
            palettes,
            hero_icon_rgb.read_bytes() if hero_icon_rgb else None,
        ),
        BUILDING_PROFILE_TILE: tile_from_rgb(
            tiles[BUILDING_PROFILE_TILE].data,
            palettes,
            building_profile_rgb.read_bytes() if building_profile_rgb else None,
        ),
        BUILDING_ICON_TILE: tile_from_rgb(
            tiles[BUILDING_ICON_TILE].data,
            palettes,
            building_icon_rgb.read_bytes() if building_icon_rgb else None,
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
    extra_palette_entries: list[CamEntry] = []
    _ = ice_lance_icon_rgb

    directional_projectile_tile_indices = sorted(
        index
        for index in referenced_tile_indices(ice_lance_projectile, len(tiles))
        if index in ICE_LANCE_DIRECTIONAL_PROJECTILE_TILES
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
                    ),
                )
            )
        ice_lance_projectile = remap_imag_tile_indices(ice_lance_projectile, projectile_tile_replacements)

    if phantom_sprite_tile_indices:
        first_custom_tile_index = max_tile_index + len(extra_tiles) + 1
        phantom_sprite_tile_replacements: dict[int, int] = {}
        for offset, source_tile_index in enumerate(phantom_sprite_tile_indices):
            custom_tile_index = first_custom_tile_index + offset
            phantom_sprite_tile_replacements[source_tile_index] = custom_tile_index
            source_tile = tiles[source_tile_index].data
            if source_tile_index == 4786 and portrait_rgb:
                tile = tile_from_rgb(source_tile, palettes, portrait_rgb.read_bytes())
            elif source_tile_index == 4792 and hero_icon_rgb:
                tile = tile_from_rgb(source_tile, palettes, hero_icon_rgb.read_bytes())
            else:
                tile = recolored_priestess_phantom_sprite_tile(source_tile, palettes)
            extra_tiles.append(
                CamEntry(
                    name=pad_name(f"PHM1PhantomTile{offset}".encode("ascii")),
                    data=tile,
                )
            )
        hero_imag = remap_imag_low16_tile_indices(hero_imag, phantom_sprite_tile_replacements)

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
        if palette_index is not None and palette_index < len(palettes):
            palette_indices.add(palette_index)

    max_palette_index = max(palette_indices)
    palette_entries = tuple(
        CamEntry(name=palettes[index].name, data=palettes[index].data)
        for index in range(max_palette_index + 1)
    ) + tuple(extra_palette_entries)
    image_entries = [
        CamEntry(name=pad_name(ROGUE_HERO_IMAGE), data=rogue_hero_imag),
        CamEntry(name=pad_name(PHANTOM_HERO_IMAGE), data=hero_imag),
        CamEntry(name=pad_name(PHANTOM_BUILDING_IMAGE), data=building_imag),
        CamEntry(name=pad_name(PHANTOM_ICE_LANCE_ICON), data=ice_lance_icon),
        CamEntry(name=pad_name(PHANTOM_ICE_LANCE_PROJECTILE), data=ice_lance_projectile),
        CamEntry(name=pad_name(PHANTOM_FROST_ARMOR_ICON), data=frost_armor_icon),
        CamEntry(name=pad_name(PHANTOM_BLIZZARD_ICON), data=blizzard_icon),
    ]
    if ice_lance_hit_effect:
        image_entries.append(CamEntry(name=pad_name(PHANTOM_ICE_LANCE_HIT_IMAGE), data=ice_lance_hit_effect))
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
    phantom_cowl_icon_rgb: Path | None,
    dark_staff_small_icon_rgb: Path | None,
    dark_staff_icon_rgb: Path | None,
) -> None:
    icon_images = {
        SPELL_LIST_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", SPELL_LIST_ICON_IMAGE).data,
        WEAPON_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", WEAPON_ICON_IMAGE).data,
        ARMOR_ICON_IMAGE: read_cam_entry(source_interfacedata, b"IMAG", ARMOR_ICON_IMAGE).data,
    }
    tiles = read_cam_entries(source_interfacedata, b"TILE")

    replacement_tiles: dict[int, bytes] = {}
    for tile_index in ICE_LANCE_SPELL_ICON_TILES:
        if ice_lance_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], ice_lance_spell_icon_rgb.read_bytes())
    for tile_index in FROST_ARMOR_SPELL_ICON_TILES:
        if frost_armor_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], frost_armor_spell_icon_rgb.read_bytes())
    for tile_index in BLIZZARD_SPELL_ICON_TILES:
        if blizzard_spell_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], blizzard_spell_icon_rgb.read_bytes())
    for tile_index in LEATHER_ARMOR_ICON_TILES:
        if phantom_cowl_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], phantom_cowl_icon_rgb.read_bytes())
    for tile_index in STAFF_ICON_TILES:
        if dark_staff_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], dark_staff_icon_rgb.read_bytes())
    for tile_index in STAFF_SMALL_ICON_TILES:
        if dark_staff_small_icon_rgb:
            replacement_tiles[tile_index] = tile_from_rgb(tiles[tile_index].data, [], dark_staff_small_icon_rgb.read_bytes())

    tile_indices: set[int] = set(replacement_tiles)
    for image in icon_images.values():
        tile_indices.update(referenced_tile_indices(image, len(tiles)))

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
                entries=tuple(CamEntry(name=pad_name(name), data=data) for name, data in icon_images.items()),
            ),
            CamSection(extension=b"TILE", padding=b"\x01\x00\x00\x00", entries=tile_entries),
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


def tile_v3_from_rgb(original_tile: bytes, palettes: list[CamEntry], rgb: bytes) -> bytes:
    height = struct.unpack_from("<H", original_tile, 2)[0]
    width = struct.unpack_from("<H", original_tile, 4)[0]
    expected_rgb_size = width * height * 3
    if len(rgb) != expected_rgb_size:
        raise ValueError(
            f"Expected {expected_rgb_size} RGB bytes for {width}x{height} tile, got {len(rgb)}"
        )

    colors = tile_palette_colors(original_tile, palettes)
    if colors is None:
        return original_tile

    header = bytearray(original_tile[:26])
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
            while x < width and len(pixels) < 255:
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
    if palette_mode == 1 and 0 <= original_palette_offset < len(original_tile):
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


def recolored_priestess_phantom_sprite_tile(original_tile: bytes, palettes: list[CamEntry]) -> bytes:
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
    saturation = max(red, green, blue) - min(red, green, blue)
    red_cloak = red > 55 and red > green * 1.22 and red > blue * 1.12
    bright_staff = luminance > 145 and saturation < 58

    if red_cloak:
        if luminance < 55:
            return (4, 22, 30)
        if luminance < 95:
            return (14, 74, 96)
        if luminance < 150:
            return (30, 145, 180)
        return (150, 245, 255)

    if bright_staff:
        if luminance > 215:
            return (7, 9, 11)
        return (18, 22, 25)

    if luminance < 45:
        return (4, 9, 12)
    if luminance < 95:
        return (28, 38, 44)
    if luminance < 150:
        return (74, 96, 105)
    if luminance < 205:
        return (134, 168, 176)
    return (210, 238, 240)


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


def embedded_palette_colors(tile: bytes, palette_offset: int) -> list[tuple[int, int, int]] | None:
    if palette_offset < 0 or len(tile) < palette_offset + 256 * 4:
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
        if palette_red > 235 and palette_green < 30 and palette_blue > 235:
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
