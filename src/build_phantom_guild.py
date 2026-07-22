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
SOURCE_HERO_IMAGE = b"AVN1Wizard"
SOURCE_BUILDING_IMAGE = b"ABY1Wizard Guild1"
SOURCE_ICE_LANCE_ICON = b"XL15PowerShock"
SOURCE_FROST_ARMOR_ICON = b"WRb2fireshield_IC"
SOURCE_BLIZZARD_ICON = b"WRg2meteor_blast"
ROGUE_HERO_IMAGE = b"AVJ1Rogue"
PHANTOM_HERO_IMAGE = b"PHM1Phantom"
PHANTOM_BUILDING_IMAGE = b"PHG1Phantom Guild"
PHANTOM_ICE_LANCE_ICON = b"WRa2Ice Lance"
PHANTOM_FROST_ARMOR_ICON = b"WRa3Frost Armor"
PHANTOM_BLIZZARD_ICON = b"WRa4Blizzard"
HERO_PORTRAIT_TILE = 6293
HERO_ICON_TILE = 6299
ROGUE_HERO_ICON_TILE = 4996
BUILDING_PROFILE_TILE = 1779
BUILDING_ICON_TILE = 1904
ICE_LANCE_ICON_TILE = 202
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
    source_maindata = args.game_path / "Data" / "maindata.cam"
    source_interfacedata = args.game_path / "Data" / "interfacedata.cam"
    source_mx_interfacedata = args.game_path / "DataMX" / "mx_interfacedata.cam"
    if not source_textdata.exists():
        raise FileNotFoundError(source_textdata)
    if not source_maindata.exists():
        raise FileNotFoundError(source_maindata)
    if not source_interfacedata.exists():
        raise FileNotFoundError(source_interfacedata)

    write_textdata_cam(source_textdata, data_dir / "phantom_textdata.cam")
    write_maindata_cam(
        source_maindata,
        data_dir / "phantom_maindata.cam",
        args.portrait_rgb,
        args.hero_icon_rgb,
        args.building_profile_rgb,
        args.building_icon_rgb,
        args.ice_lance_icon_rgb,
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
\t<Description type="Unit" subType="Character" ID="PHIC" Name="FrozenCowl" Description="Frozen Cowl">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="8"/>
\t\t\t<ImageIDBase value="AVk4"/>
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
\t\t\t\t<Attribute ID="FrozenCowl" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Character" ID="PHIR" Name="BlackIcerod" Description="Black Icerod">
\t\t<Engine version="1">
\t\t\t<Info value="Static"/>
\t\t\t<Info value="Directionless"/>
\t\t\t<Info value="BlockGround"/>
\t\t\t<CanUse value="HumanPlayer"/>
\t\t\t<Menu value="8"/>
\t\t\t<ImageIDBase value="AVk4"/>
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
\t\t\t\t<Attribute ID="BlackIcerod" Value="0"/>
\t\t\t</Attributes>
\t\t</Game>
\t</Description>
\t<Description type="Unit" subType="Building" ID="PHG1" Name="Phantoms_Guild1" Description="Phantoms Guild">
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


def phantom_actions_xml() -> str:
    return """<Majesty>
\t<Description type="Action" subType="Standard" ID="WRa2" Name="ice_lance" Description="Ice Lance">
\t\t<Engine version="1">
\t\t\t<ImageSet value="Cast"/>
\t\t\t<CompletionImageSet value="Stand"/>
\t\t\t<Sound value="Energy_Blast"/>
\t\t\t<SoundPhase begin="Begin"/>
\t\t\t<Projectile value="ice_lance_missile"/>
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
\t\t\t<ImageIDBase value="WRa2"/>
\t\t\t<Script type="0" cProc="0" GPLFunction="Ice_Lance_Hit"/>
\t\t\t<Attachment kind="Movement" type="Walk" ID="fast missile"/>
\t\t\t<DefaultSound value="0"/>
\t\t</Engine>
\t</Description>
</Majesty>
"""


def phantom_overlays_xml() -> str:
    return """<Majesty>
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
\t\t(IGdeathscript\tgravestone)
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

\t$Wizard_tree(thisagent);
end

function Phantom_birth (agent thisagent)

declare

begin
\t$PlaySound(thisagent, "Phantom", "VFX_SPECIAL1");
\t$hero_birth(thisagent);
\t$NewThread($Phantom_grant_starter_items, 500, thisagent);
\t$LearnSpell(thisagent, "ice_lance");
end

function Phantom_grant_starter_items (agent thisagent)

declare

begin
\tIf ($isdead(thisagent))
\t\treturn;

\tIf ($AgentHasInventoryItem("FrozenCowl", thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem("FrozenCowl", thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$adjustattribute(thisagent, #ATTRIB_Armor_Basic_Damage, 1);
\t\tend

\tIf ($AgentHasInventoryItem("BlackIcerod", thisagent) == False)
\t\tbegin
\t\t\t$CreateNewInventoryItem("BlackIcerod", thisagent, #Allow_Cloned_Quest_Item);
\t\t\t$adjustattribute(thisagent, #ATTRIB_Weapon_Basic_Damage, 8);
\t\tend
end

function Ice_Lance_Hit(agent thisagent, agent target)

declare

begin
\t$PlaySound(target, "Energy_Blast", "Attack");
\t$createeffector(target, "energy_blast_effector", $GetSpellAttribute("ice_lance", "effector_duration"));
\t$spell_attack(thisagent, target, 12 + $GetAttribute(thisagent, #ATTRIB_ExperienceLevel));
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
    return f"""<Majesty>
\t<Mod id="{{{MOD_ID}}}">
\t\t<Name>PhantomGuildPoc</Name>
\t\t<DisplayName lang="en_US">Phantom Guild POC</DisplayName>
\t\t<Description lang="en_US">
\t\t\t<Short>Adds a test Phantoms Guild and recruitable Phantom hero.</Short>
\t\t\t<Long/>
\t\t</Description>
\t\t<DataConfiguration>
\t\t\t<Dataset base="Any">
\t\t\t\t<Load>
\t\t\t\t\t<Descriptions>Data\\phantom_units.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_actions.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_projectiles.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_overlays.xml</Descriptions>
\t\t\t\t\t<Descriptions>Data\\phantom_sounds.xml</Descriptions>
\t\t\t\t\t<CAM>Data\\phantom_textdata.cam</CAM>
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
\t\t\t\t</Load>
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
            fourcc_id(BUILDING_ID): "Phantoms Guild",
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


def write_maindata_cam(
    source_maindata: Path,
    output_path: Path,
    portrait_rgb: Path | None,
    hero_icon_rgb: Path | None,
    building_profile_rgb: Path | None,
    building_icon_rgb: Path | None,
    ice_lance_icon_rgb: Path | None,
) -> None:
    hero_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_HERO_IMAGE).data
    rogue_hero_imag = read_cam_entry(source_maindata, b"IMAG", ROGUE_HERO_IMAGE).data
    building_imag = read_cam_entry(source_maindata, b"IMAG", SOURCE_BUILDING_IMAGE).data
    ice_lance_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_ICE_LANCE_ICON).data
    frost_armor_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_FROST_ARMOR_ICON).data
    blizzard_icon = read_cam_entry(source_maindata, b"IMAG", SOURCE_BLIZZARD_ICON).data
    tiles = read_cam_entries(source_maindata, b"TILE")
    palettes = read_cam_entries(source_maindata, b"SPLT")

    tile_indices = referenced_tile_indices(hero_imag, len(tiles))
    tile_indices.update(referenced_tile_indices(rogue_hero_imag, len(tiles)))
    tile_indices.update(referenced_tile_indices(building_imag, len(tiles)))
    tile_indices.update(referenced_tile_indices(ice_lance_icon, len(tiles)))
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
    extra_tiles: list[CamEntry] = []
    if ice_lance_icon_rgb:
        custom_tile_index = max_tile_index + len(extra_tiles) + 1
        custom_tile = tile_from_rgb(
            tiles[ICE_LANCE_ICON_TILE].data,
            palettes,
            ice_lance_icon_rgb.read_bytes(),
        )
        extra_tiles.append(CamEntry(name=pad_name(b"PHa1IceIcon"), data=custom_tile))
        ice_lance_icon = remap_imag_tile_indices(
            ice_lance_icon,
            {ICE_LANCE_ICON_TILE: custom_tile_index},
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
                    CamEntry(name=pad_name(ROGUE_HERO_IMAGE), data=rogue_hero_imag),
                    CamEntry(name=pad_name(PHANTOM_HERO_IMAGE), data=hero_imag),
                    CamEntry(name=pad_name(PHANTOM_BUILDING_IMAGE), data=building_imag),
                    CamEntry(name=pad_name(PHANTOM_ICE_LANCE_ICON), data=ice_lance_icon),
                    CamEntry(name=pad_name(PHANTOM_FROST_ARMOR_ICON), data=frost_armor_icon),
                    CamEntry(name=pad_name(PHANTOM_BLIZZARD_ICON), data=blizzard_icon),
                ),
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
                pixels.append(nearest_palette_index(red, green, blue, colors))
                x += 1

            next_x = x
            while next_x < width:
                pixel_offset = (y * width + next_x) * 3
                if not is_transparent_rgb(rgb[pixel_offset], rgb[pixel_offset + 1], rgb[pixel_offset + 2]):
                    break
                next_x += 1
            has_more_segments = next_x < width
            flags = 0 if has_more_segments else 0x80
            row += struct.pack("<HH", start, len(pixels) | (flags << 8))
            row += bytes(pixels)
            x = next_x

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

    original_palette_offset = struct.unpack_from("<I", original_tile, 22)[0]
    if 0 <= original_palette_offset < len(original_tile):
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
