"""Unit tests for the pure parts of the Phantoms Haunt builder.

These cover the functions that take data in and give data back: TILE encoding,
CAM container structure, string-table patching, tile reduction and the generated
XML. Nothing here needs Majesty installed, so the suite runs anywhere.

The art generation, GPL compilation and packaging paths are deliberately not
covered; they need the game's own archives and the SDK compiler. Package-level
correctness is checked by src/validate_phantom_build.py after every build.
"""

from __future__ import annotations

import ast
import inspect
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "src" / "build_phantom_guild.py"
BUILD_SCRIPT_PATH = REPO_ROOT / "scripts" / "Build-CustomGuildPhantomsHaunt.ps1"
BUILD_OUTPUT_HELPER_PATH = REPO_ROOT / "scripts" / "HauntBuildOutput.ps1"

sys.path.insert(0, str(REPO_ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402
import validate_phantom_build as validator  # noqa: E402


def make_tile(pixels: list[list[int]], palette_index: int = 0) -> bytes:
    """Encode a pixel grid the same way the builder does.

    header_words is the whole eight-word TILE v3 header: version, height,
    width, then five words the engine keeps but this code does not interpret.
    """
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    header = (3, height, width, 0, 0, 0, 0, 0)
    return builder.encode_indexed_v3_tile(pixels, palette_index, header)


class TileEncodingTests(unittest.TestCase):
    def test_round_trip_preserves_pixels(self):
        pixels = [
            [0, 0, 5, 6, 7, 0],
            [1, 2, 0, 0, 3, 4],
            [0, 0, 0, 0, 0, 0],
            [9, 0, 9, 0, 9, 0],
        ]
        decoded = builder.decode_indexed_v3_tile(make_tile(pixels))
        self.assertIsNotNone(decoded)
        height, width, out = decoded
        self.assertEqual(height, len(pixels))
        self.assertEqual(width, len(pixels[0]))
        self.assertEqual(out, pixels)

    def test_round_trip_single_run_per_row(self):
        pixels = [[7, 7, 7], [0, 8, 0]]
        _, _, out = builder.decode_indexed_v3_tile(make_tile(pixels))
        self.assertEqual(out, pixels)

    def test_fully_transparent_tile_round_trips(self):
        pixels = [[0, 0, 0], [0, 0, 0]]
        _, _, out = builder.decode_indexed_v3_tile(make_tile(pixels))
        self.assertEqual(out, pixels)

    def test_palette_index_survives(self):
        tile = make_tile([[1, 2]], palette_index=161)
        self.assertEqual(builder.tile_palette_index(tile), 161)

    def test_decode_rejects_non_v3(self):
        self.assertIsNone(builder.decode_indexed_v3_tile(b"\x02\x00" + b"\x00" * 40))

    def test_decode_rejects_truncated(self):
        self.assertIsNone(builder.decode_indexed_v3_tile(b"\x03\x00\x02\x00"))

    def test_dimensions_match_encoded_grid(self):
        self.assertEqual(builder.tile_dimensions(make_tile([[1, 2, 3], [4, 5, 6]])), (2, 3))

    def test_visible_bbox_ignores_transparent_border(self):
        """Returns (left, top, right, bottom) with right and bottom exclusive,
        matching the exclusive-end convention TILE v3 uses throughout."""
        pixels = [
            [0, 0, 0, 0],
            [0, 4, 4, 0],
            [0, 0, 0, 0],
        ]
        self.assertEqual(builder.tile_visible_bbox(make_tile(pixels)), (1, 1, 3, 2))

    def test_visible_bbox_is_none_for_an_empty_tile(self):
        self.assertIsNone(builder.tile_visible_bbox(make_tile([[0, 0], [0, 0]])))

    def test_blank_tile_keeps_geometry_but_draws_nothing(self):
        original = make_tile([[1, 2, 3], [4, 5, 6]])
        blanked = builder.blank_indexed_v3_tile(original)
        self.assertEqual(builder.tile_dimensions(blanked), builder.tile_dimensions(original))
        _, _, out = builder.decode_indexed_v3_tile(blanked)
        self.assertTrue(all(value == 0 for row in out for value in row))


class TileReductionTests(unittest.TestCase):
    def _entries(self, count: int):
        return [
            builder.CamEntry(name=builder.pad_name(f"T{i:03d}".encode()), data=make_tile([[i % 200 + 1]]))
            for i in range(count)
        ]

    def _imag_referencing(self, indices):
        return b"".join(struct.pack("<I", i) for i in indices)

    def test_referenced_slots_survive(self):
        entries = self._entries(10)
        out = builder.reduce_unreferenced_tiles(
            entries, [self._imag_referencing([2, 5])], set(), set()
        )
        self.assertEqual(out[2].data, entries[2].data)
        self.assertEqual(out[5].data, entries[5].data)

    def test_unreferenced_slots_are_emptied(self):
        entries = self._entries(10)
        out = builder.reduce_unreferenced_tiles(
            entries, [self._imag_referencing([2])], set(), set()
        )
        self.assertEqual(out[7].data, b"")

    def test_always_keep_is_honoured(self):
        entries = self._entries(10)
        out = builder.reduce_unreferenced_tiles(
            entries, [self._imag_referencing([2])], {8}, set()
        )
        self.assertEqual(out[8].data, entries[8].data)

    def test_entry_count_and_names_are_preserved(self):
        """Majesty addresses tiles by position, so reduction must never shift
        or drop an entry."""
        entries = self._entries(12)
        out = builder.reduce_unreferenced_tiles(
            entries, [self._imag_referencing([1])], set(), set()
        )
        self.assertEqual(len(out), len(entries))
        self.assertEqual([e.name for e in out], [e.name for e in entries])

    def test_engine_addressed_slots_are_kept(self):
        """These are reached by slot number rather than through an IMAG record.
        Blanking BUILDING_ICON_TILE once made the Haunt vanish from the build
        menu."""
        engine_addressed = builder.maindata_engine_addressed_tile_indices()
        size = max(engine_addressed) + 2
        entries = self._entries(size)
        out = builder.reduce_unreferenced_tiles(
            entries, [self._imag_referencing([0])], set(), engine_addressed
        )
        for index in engine_addressed:
            self.assertNotEqual(out[index].data, b"", f"tile {index} must not be emptied")

    def test_named_constants_are_in_the_keep_set(self):
        keep = builder.maindata_engine_addressed_tile_indices()
        for name in (
            "HERO_PORTRAIT_TILE",
            "HERO_ICON_TILE",
            "BUILDING_PROFILE_TILE",
            "BUILDING_ICON_TILE",
            "HERO_INTERFACE_PANEL_TILE",
        ):
            self.assertIn(getattr(builder, name), keep, f"{name} missing from keep set")

class PackageInvariantTests(unittest.TestCase):
    def test_one_unexpected_unreferenced_tile_byte_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "phantom_interfacedata.cam"
            path.write_bytes(b"x")
            sections = {
                b"TILE": [validator.Entry(b"TILE", b"unexpected", 0, 1, 0)],
            }
            with self.assertRaises(validator.ValidationError):
                validator.validate_no_redistributed_stock_art(path, sections)

    def test_bdep_append_preserves_every_stock_byte(self):
        stock = b"# stock\r\nABP1 : ABJ2 ABJ3 NOT NOT ||\r\n"
        built = builder.append_haunt_building_dependency(stock)
        self.assertTrue(built.startswith(stock))
        self.assertEqual(built.count(builder.HAUNT_BDEP_RULE), 1)
        validator.validate_building_dependencies_against_stock(
            Path("phantom_miscdata.cam"), built, stock
        )

    def test_altered_stock_bdep_byte_is_rejected(self):
        stock = b"# stock\r\nABP1 : ABJ2 ABJ3 NOT NOT ||\r\n"
        built = bytearray(builder.append_haunt_building_dependency(stock))
        built[2] ^= 1
        with self.assertRaises(validator.ValidationError):
            validator.validate_building_dependencies_against_stock(
                Path("phantom_miscdata.cam"), bytes(built), stock
            )

    def test_bdep_append_rejects_an_existing_haunt_rule(self):
        with self.assertRaises(ValueError):
            builder.append_haunt_building_dependency(
                builder.HAUNT_BDEP_RULE + b"\r\n"
            )

    def test_bdep_whole_record_compatibility_is_documented(self):
        packaging = (REPO_ROOT / "docs" / "packaging.md").read_text(encoding="utf-8")
        self.assertIn("BDEP mod compatibility", packaging)
        self.assertIn("not concatenated or merged", packaging)
        self.assertIn(builder.HAUNT_BDEP_RULE.decode("ascii"), packaging)


class ImagReferenceTests(unittest.TestCase):
    def test_full_width_references_are_found(self):
        imag = struct.pack("<III", 4, 9, 1)
        self.assertEqual(builder.referenced_tile_indices(imag, 16), {4, 9, 1})

    def test_out_of_range_references_are_ignored(self):
        imag = struct.pack("<II", 3, 9999)
        self.assertNotIn(9999, builder.referenced_tile_indices(imag, 16))

    def test_union_covers_both_widths(self):
        imag = struct.pack("<II", 5, 6)
        combined = builder.imag_referenced_tile_indices([imag], 32)
        self.assertTrue({5, 6}.issubset(combined))


class CamContainerTests(unittest.TestCase):
    def test_write_then_read_round_trips(self):
        section = builder.CamSection(
            extension=b"TILE",
            padding=b"\x01\x00\x00\x00",
            entries=(
                builder.CamEntry(name=builder.pad_name(b"AAA1"), data=b"hello"),
                builder.CamEntry(name=builder.pad_name(b"BBB2"), data=b"world!"),
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.cam"
            builder.write_cam((section,), path)
            entries = builder.read_cam_entries(path, b"TILE")
        self.assertEqual([e.data for e in entries], [b"hello", b"world!"])
        self.assertEqual(entries[0].name.rstrip(b"\x00"), b"AAA1")

    def test_zero_length_entries_survive_a_round_trip(self):
        """The shipped package relies on these."""
        section = builder.CamSection(
            extension=b"TILE",
            padding=b"\x01\x00\x00\x00",
            entries=(
                builder.CamEntry(name=builder.pad_name(b"AAA1"), data=b"data"),
                builder.CamEntry(name=builder.pad_name(b"BBB2"), data=b""),
                builder.CamEntry(name=builder.pad_name(b"CCC3"), data=b"more"),
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.cam"
            builder.write_cam((section,), path)
            entries = builder.read_cam_entries(path, b"TILE")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[1].data, b"")
        self.assertEqual(entries[2].data, b"more")

    def test_multiple_sections_are_addressable(self):
        sections = (
            builder.CamSection(b"IMAG", b"\x00\x00\x00\x00",
                               (builder.CamEntry(builder.pad_name(b"IM01"), b"image"),)),
            builder.CamSection(b"TILE", b"\x01\x00\x00\x00",
                               (builder.CamEntry(builder.pad_name(b"TL01"), b"tile"),)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.cam"
            builder.write_cam(sections, path)
            self.assertEqual(builder.read_cam_entries(path, b"IMAG")[0].data, b"image")
            self.assertEqual(builder.read_cam_entries(path, b"TILE")[0].data, b"tile")

    def test_missing_section_raises(self):
        section = builder.CamSection(b"TILE", b"\x01\x00\x00\x00",
                                     (builder.CamEntry(builder.pad_name(b"T1"), b"x"),))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.cam"
            builder.write_cam((section,), path)
            with self.assertRaises(ValueError):
                builder.read_cam_entries(path, b"SPLT")

    def test_non_cam_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.cam"
            path.write_bytes(b"not a cam archive at all")
            with self.assertRaises(ValueError):
                builder.read_cam_entries(path, b"TILE")


class StringTableTests(unittest.TestCase):
    def _strt(self, strings: list[str]) -> bytes:
        count = len(strings)
        offsets = []
        payload = b""
        base = 4 + count * 4
        for text in strings:
            offsets.append(base + len(payload))
            payload += struct.pack("<I", len(text) + 1) + text.encode("cp1252") + b"\x00"
        return struct.pack("<H", count) + b"\x00\x00" + b"".join(
            struct.pack("<I", o) for o in offsets
        ) + payload

    def test_patch_replaces_only_the_named_index(self):
        data = self._strt(["alpha", "beta", "gamma"])
        patched = builder.patch_strt_strings(data, {1: "BETA!"})
        self.assertIn(b"BETA!", patched)
        self.assertIn(b"alpha", patched)
        self.assertIn(b"gamma", patched)

    def test_indexed_table_is_extended_to_reach_the_index(self):
        """Item ids index directly into QITM, so the table has to physically
        reach the id or the Items panel shows 'Unknown Item'."""
        data = self._strt(["a", "b"])
        patched = builder.patch_indexed_strt_strings(data, {6: "Frozen Cowl"})
        self.assertGreaterEqual(struct.unpack_from("<H", patched, 0)[0], 7)
        self.assertIn(b"Frozen Cowl", patched)


class PaletteTests(unittest.TestCase):
    def test_nearest_index_picks_the_exact_match(self):
        colors = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
        self.assertEqual(builder.nearest_palette_index(0, 255, 0, colors), 2)

    def test_nearest_index_picks_the_closest(self):
        colors = [(0, 0, 0), (250, 10, 10), (10, 10, 250)]
        self.assertEqual(builder.nearest_palette_index(240, 20, 20, colors), 1)

    def test_near_black_is_treated_as_transparent(self):
        """The RGB-to-tile path treats near-black as transparent, not just
        pure black, so source art must not rely on very dark pixels."""
        self.assertTrue(builder.is_transparent_rgb(0, 0, 0))
        self.assertTrue(builder.is_transparent_rgb(9, 9, 11))
        self.assertFalse(builder.is_transparent_rgb(10, 9, 11))
        self.assertFalse(builder.is_transparent_rgb(9, 10, 11))
        self.assertFalse(builder.is_transparent_rgb(9, 9, 12))


class GplSourceTests(unittest.TestCase):
    SOURCE = (
        "function Alpha(agent a)\n"
        "begin\n"
        "\t$DoThing();\n"
        "end\n"
        "\n"
        "function Beta()\n"
        "begin\n"
        "\t$Other();\n"
        "end\n"
    )

    def test_extracts_a_named_function(self):
        out = builder.extract_gpl_function(self.SOURCE, "Alpha")
        self.assertTrue(out.startswith("function Alpha"))
        self.assertIn("$DoThing();", out)
        self.assertNotIn("$Other();", out)

    def test_extracts_the_last_function(self):
        self.assertIn("$Other();", builder.extract_gpl_function(self.SOURCE, "Beta"))

    def test_missing_function_raises(self):
        with self.assertRaises(ValueError):
            builder.extract_gpl_function(self.SOURCE, "NotThere")

    def test_dark_forest_gate_is_spliced_into_stock_lists_directly(self):
        entry = 'function DARK_FOREST()\nBegin\n\t$disableunittype("Gnome_hovel");\nEnd'
        victory = (
            'function dark_forest_victory()\nBegin\n'
            '\t\t\t\t\t$enableunittype("Gnome_hovel");\nEnd'
        )

        entry = builder.patch_dark_forest_entry_for_haunt(entry)
        victory = builder.patch_dark_forest_unlock_for_haunt(victory)

        self.assertIn(
            '$disableunittype("Gnome_hovel");\n\t$DisableUnitType("Phantoms_Haunt");',
            entry,
        )
        self.assertIn(
            '$enableunittype("Gnome_hovel");\n'
            '\t\t\t\t\t$EnableUnitType("Phantoms_Haunt");',
            victory,
        )
        self.assertNotIn("Phantom_Lock_Haunt_For_Quest", entry)
        self.assertNotIn("Phantom_Unlock_Haunt_For_Quest", victory)

    def test_quest_lock_set_follows_temple_classification(self):
        self.assertEqual(
            builder.TEMPLE_LOCKED_EPIC_QUESTS,
            (
                "DARK_FOREST",
                "DAY_OF_RECKONING",
                "SLAY_DRAGON",
                "FORSAKEN_LANDS",
                "SAVE_PRINCE",
                "WIZARDS_CURSE",
            ),
        )
        self.assertEqual(builder.TEMPLE_LOCKED_EXPANSION_QUESTS, ("VIGIL",))
        self.assertEqual(
            builder.TEMPLE_LOCKED_DEMO_QUESTS,
            ("VAMPIRIC_REVENGE",),
        )
        haunt_available_quests = {
            "BARREN_WASTE",
            "BELL_BOOK_CANDLE",
            "LICHE_QUEEN",
            "SCIONS_CHAOS",
            "SIEGE",
        }
        self.assertTrue(
            haunt_available_quests.isdisjoint(builder.TEMPLE_LOCKED_EPIC_QUESTS)
        )


class GplTemplateTests(unittest.TestCase):
    """The static GPL body lives in src/gpl/phantom.gpl rather than inside a
    Python string. These guard the file's presence and shape; correctness of
    the GPL itself is checked by validate_phantom_build.py after a build."""

    def test_template_file_exists(self):
        self.assertTrue(builder.GPL_TEMPLATE_PATH.is_file(), builder.GPL_TEMPLATE_PATH)

    def test_template_is_read_verbatim(self):
        raw = builder.GPL_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertEqual(builder.phantom_gpl_template(), raw)

    def test_template_uses_tabs_and_unix_newlines(self):
        text = builder.phantom_gpl_template()
        self.assertIn("\t", text)
        self.assertNotIn("\r", text, "template must not carry CRLF into the compiler")

    def test_template_brackets_the_body_with_newlines(self):
        """phantom_gpl() concatenates constants + template + overrides with no
        separator of its own, so the template supplies its own padding."""
        text = builder.phantom_gpl_template()
        self.assertTrue(text.startswith("\n"))
        self.assertTrue(text.endswith("\n"))

    def test_template_contains_the_expected_entry_points(self):
        text = builder.phantom_gpl_template()
        for name in (
            "Function Phantom_Lock_Haunt_For_Quest",
            "Function Phantoms_Haunt_Birth",
            "function Priestess_tree",
            "Function Phantom_Priestess_Bazaar_Check",
            "Function Phantom_Priestess_Champs_Check",
        ):
            self.assertIn(name, text, f"missing {name}")

    def test_phantom_uses_field_oriented_decision_tree(self):
        text = builder.phantom_gpl_template()
        start = text.index("function Phantom_tree (agent thisagent)")
        end = text.index("\nfunction Phantom_Hero_Birth", start)
        tree = text[start:end]
        expected_in_order = (
            "$Phantom_Sync_Speed_Profile(thisagent)",
            "$Phantom_Try_Frost_Armor(thisagent)",
            "$check_nearby(thisagent)",
            "$Check_rewards(thisagent,FALSE)",
            "$Defend_home(thisagent)",
            "$rest(thisagent)",
            "$Purchase_equipment(thisagent)",
            "$pursue_entertainment(thisagent)",
            "$Raid_lair(thisagent,80)",
            "$raid_enemy_building(thisagent,65)",
            "$Combat_wandering(thisagent,90)",
            "$combat_wandering_heroes(thisagent,75)",
            "$Explore_Map(thisagent,75)",
            '$Visit_Building(ThisAgent, "Royal_gardens", 5)',
            '$check_library(thisagent,15, "Train_magic_resist")',
            "$Go_Home(thisagent,30)",
            "$hero_wander",
        )
        positions = [tree.index(value) for value in expected_in_order]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("$Wizard_tree(thisagent);", tree)

    def test_phantom_uses_tuned_base_movement_profile(self):
        root = ET.fromstring(builder.phantom_units_xml())
        phantom = root.find('.//Description[@ID="PHM1"]')
        self.assertIsNotNone(phantom)
        movement = phantom.find('./Engine/Attachment[@kind="Movement"]')
        speed = phantom.find("./Game/Speed")
        self.assertEqual(movement.attrib["ID"], "Class 1")
        self.assertEqual(speed.attrib["value"], "1")

    def test_phantom_speed_profile_tracks_call_to_grave_level(self):
        text = builder.phantom_gpl_template()
        start = text.index("Function Phantom_Sync_Speed_Profile(agent ThisAgent)")
        end = text.index("\nFunction Phantom_Start_Player_Perk_Watch", start)
        profile = text[start:end]
        self.assertIn("#Phantom_Base_Movement_Bonus", profile)
        self.assertIn('"call_to_grave",\n\t\t"character_level"', profile)
        self.assertIn("#ATTRIB_ExperienceLevel", profile)
        self.assertIn("$SetAttribute(ThisAgent, #ATTRIB_Speed, 5);", profile)
        self.assertIn("$SetAttribute(ThisAgent, #ATTRIB_Speed, 1);", profile)

    def test_stock_functions_replaced_by_name_are_present(self):
        """These are overridden by their stock names, which is how the mod
        hooks Majesty's own behaviour. Losing one silently reverts a feature."""
        text = builder.phantom_gpl_template()
        for name in (
            "Function Potion_Check",
            "Function Heal",
            "Function Player_Heal",
            "Function Hero_Drop_Quest_Items",
            "Function Eval_For_Healing",
            "function Priestess_tree",
        ):
            self.assertIn(name, text, f"missing stock override {name}")

    def test_template_does_not_call_expansion_only_helpers_directly(self):
        """Purchase_Bazaar and Hall_Champs_Check exist only in the Northern
        Expansion. Calling them directly breaks Priestesses in Original
        Majesty quests, so they must go through the guarded wrappers."""
        body = builder.phantom_gpl_template()
        tree_start = body.index("function Priestess_tree")
        tree_end = body.index("\nEnd", tree_start)
        priestess_tree = body[tree_start:tree_end]
        self.assertNotIn("$Purchase_Bazaar(", priestess_tree)
        self.assertNotIn("$Hall_Champs_Check(", priestess_tree)
        self.assertIn("$Phantom_Priestess_Bazaar_Check(", priestess_tree)
        self.assertIn("$Phantom_Priestess_Champs_Check(", priestess_tree)


class StockRewriteGuardTests(unittest.TestCase):
    """The quest overrides are produced by rewriting stock SDK source. A silent
    no-op there would ship a package missing its quest rules."""

    def test_substitute_once_raises_when_nothing_matches(self):
        with self.assertRaises(ValueError):
            builder.substitute_once("no marker", r"(?im)^begin\s*$", "x", "case")

    def test_substitute_once_applies_a_single_match(self):
        out = builder.substitute_once("begin\nbegin\n", r"(?im)^begin\s*$", "BEGIN", "case")
        self.assertEqual(out, "BEGIN\nbegin\n")

    def test_replace_once_raises_when_absent(self):
        with self.assertRaises(ValueError):
            builder.replace_once("aaa", "zzz", "y", "case")

    def test_replace_once_raises_when_ambiguous(self):
        with self.assertRaises(ValueError):
            builder.replace_once("aa aa", "aa", "y", "case")

    def test_replace_once_applies_a_unique_match(self):
        self.assertEqual(builder.replace_once("a b c", "b", "B", "case"), "a B c")


class EquipmentSpecTests(unittest.TestCase):
    def test_item_ids_are_unique(self):
        ids = [spec[0] for spec in builder.phantom_equipment_item_specs()]
        self.assertEqual(len(ids), len(set(ids)), "duplicate item id")

    def test_attribute_names_are_unique(self):
        names = [spec[2] for spec in builder.phantom_equipment_item_specs()]
        self.assertEqual(len(names), len(set(names)), "duplicate attribute name")

    def test_ids_stay_inside_the_reserved_ranges(self):
        """80, 81 and 82 are load-bearing for save compatibility."""
        ids = sorted(spec[0] for spec in builder.phantom_equipment_item_specs())
        self.assertIn(builder.PHANTOM_COWL_BASE_ITEM_ID, ids)
        self.assertIn(builder.PHANTOM_ICEROD_BASE_ITEM_ID, ids)
        for value in ids:
            self.assertLessEqual(value, builder.PHANTOM_ICEROD_VARIANT_LAST_ID)


class GeneratedXmlTests(unittest.TestCase):
    GENERATORS = (
        "phantom_units_xml",
        "phantom_actions_xml",
        "phantom_projectiles_xml",
        "phantom_overlays_xml",
        "phantom_particles_xml",
        "phantom_sounds_xml",
    )

    def test_every_generator_emits_well_formed_xml(self):
        for name in self.GENERATORS:
            with self.subTest(generator=name):
                ET.fromstring(getattr(builder, name)())

    def test_manifest_is_well_formed(self):
        ET.fromstring(builder.mod_xml())

    def test_phantom_loyalty_matches_priestess(self):
        hero_data = builder.phantom_hero_data()
        self.assertIn("(Loyalty 30)", hero_data)
        self.assertNotIn("(Loyalty 55)", hero_data)

    def test_manifest_declares_exactly_one_dataset(self):
        """Majesty recognises only the first sibling Dataset and silently drops
        the rest, so one 'Any' block is the only correct shape."""
        root = ET.fromstring(builder.mod_xml())
        datasets = root.findall(".//Dataset")
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].get("base"), "Any")

    def test_manifest_does_not_reference_the_removed_mx_archive(self):
        self.assertNotIn("phantom_mx_interfacedata.cam", builder.mod_xml())

    def test_unit_ids_are_unique(self):
        root = ET.fromstring(builder.phantom_units_xml())
        ids = [d.get("ID") for d in root.iter("Description") if d.get("ID")]
        self.assertEqual(len(ids), len(set(ids)), "duplicate Description ID")

    def test_haunt_levels_use_stock_krypta_repeat_build_multiplier(self):
        root = ET.fromstring(builder.phantom_units_xml())
        for description_id in ("PHG1", "PHG2", "PHG3"):
            with self.subTest(description_id=description_id):
                multiplier = root.find(
                    f'.//Description[@ID="{description_id}"]/Game/Multiplier'
                )
                self.assertIsNotNone(multiplier)
                self.assertEqual(multiplier.get("value"), "2.0")


class HelperTests(unittest.TestCase):
    def test_pad_name_is_twenty_bytes(self):
        self.assertEqual(len(builder.pad_name(b"ABC1")), 20)

    def test_pad_name_rejects_oversized_names(self):
        with self.assertRaises(ValueError):
            builder.pad_name(b"X" * 21)

    def test_u32_reads_little_endian(self):
        self.assertEqual(builder.u32(struct.pack("<I", 0x11223344), 0), 0x11223344)

    def test_fourcc_round_trips_through_u32(self):
        self.assertEqual(builder.fourcc_id("PHM1"), builder.u32(b"PHM1", 0))

    def test_remap_rewrites_only_listed_indices(self):
        imag = struct.pack("<III", 10, 20, 30)
        out = builder.remap_imag_tile_indices(imag, {20: 99})
        self.assertEqual(struct.unpack("<III", out), (10, 99, 30))


class CliContractTests(unittest.TestCase):
    """Guards against plumbing that goes nowhere.

    An argument that is declared but never read is worse than useless: the
    build script keeps passing it, so it reads as wired up when nothing
    consumes it.
    """

    @staticmethod
    def _builder_source() -> str:
        return (BUILDER_PATH).read_text(encoding="utf-8")

    def test_every_declared_argument_is_read(self):
        source = self._builder_source()
        tree = ast.parse(source)

        declared: dict[str, int] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("--")
            ):
                declared[node.args[0].value] = node.lineno

        self.assertTrue(declared, "no CLI arguments found; the parser moved")

        read = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "args"
        }

        unread = sorted(
            f"{flag} (line {line})"
            for flag, line in declared.items()
            if flag[2:].replace("-", "_") not in read
        )
        self.assertEqual(
            unread,
            [],
            "declared but never read as args.<name>: " + ", ".join(unread),
        )

    def test_build_script_passes_only_declared_arguments(self):
        script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
        # The builder invocation runs to the first line that is not a
        # backtick continuation.
        start = script.index("build_phantom_guild.py")
        invocation = script[start:]
        end = invocation.index("\nif ")
        invocation = invocation[:end]

        passed = set(re.findall(r"(--[a-z0-9-]+)", invocation))
        declared = set(re.findall(r'add_argument\("(--[a-z0-9-]+)"', self._builder_source()))

        undeclared = sorted(passed - declared)
        self.assertEqual(
            undeclared,
            [],
            "build script passes arguments the builder does not declare: "
            + ", ".join(undeclared),
        )

    def test_legacy_unused_tile_modes_are_not_exposed(self):
        validator_source = (REPO_ROOT / "src" / "validate_phantom_build.py").read_text(
            encoding="utf-8"
        )
        build_script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("--unused-tile-mode", self._builder_source())
        self.assertNotIn("--unused-tile-mode", validator_source)
        self.assertNotIn("UnusedTileMode", build_script)


class BuildOutputSafetyTests(unittest.TestCase):
    """The packaging script may replace only a validated child of dist."""

    @classmethod
    def setUpClass(cls):
        cls.powershell = shutil.which("powershell") or shutil.which("pwsh")
        if cls.powershell is None:
            raise unittest.SkipTest("PowerShell is required for build-output safety tests")

    def _run_helper(self, body: str) -> subprocess.CompletedProcess[str]:
        command = f". '{BUILD_OUTPUT_HELPER_PATH}'; {body}"
        return subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_only_package_directories_below_dist_are_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            (repo / "dist").mkdir(parents=True)
            accepted = self._run_helper(
                f"Get-SafeHauntBuildOutputPath -RepoRoot '{repo}' "
                "-OutputRoot '.\\dist\\package'"
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(
                Path(accepted.stdout.strip()),
                repo / "dist" / "package",
            )

            for unsafe in (".", "..", ".\\dist", str(Path(temp) / "outside")):
                with self.subTest(unsafe=unsafe):
                    rejected = self._run_helper(
                        f"Get-SafeHauntBuildOutputPath -RepoRoot '{repo}' "
                        f"-OutputRoot '{unsafe}'"
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn("Unsafe Haunt build output", rejected.stderr)

    def test_validated_stage_replaces_previous_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            staged = root / "staged"
            final = root / "final"
            backup = root / "backup"
            staged.mkdir()
            final.mkdir()
            (staged / "version.txt").write_text("new", encoding="ascii")
            (final / "version.txt").write_text("old", encoding="ascii")

            result = self._run_helper(
                f"Publish-ValidatedHauntBuild -StagedRoot '{staged}' "
                f"-FinalRoot '{final}' -BackupRoot '{backup}'"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((final / "version.txt").read_text(encoding="ascii"), "new")
            self.assertFalse(staged.exists())
            self.assertFalse(backup.exists())

    def test_failure_before_publication_preserves_previous_package(self):
        dist = REPO_ROOT / "dist"
        dist.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="safety-test-", dir=dist) as output:
            output_path = Path(output)
            sentinel = output_path / "known-good.txt"
            sentinel.write_text("keep", encoding="ascii")
            missing = REPO_ROOT / "does-not-exist-for-output-safety-test.png"
            result = subprocess.run(
                [
                    self.powershell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(BUILD_SCRIPT_PATH),
                    "-OutputRoot",
                    str(output_path),
                    "-PortraitImage",
                    str(missing),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="ascii"), "keep")
            leftovers = list(dist.glob(f".staging-{output_path.name}-*"))
            leftovers += list(dist.glob(f".work-{output_path.name}-*"))
            self.assertEqual(leftovers, [])


class RecruitmentVoiceTests(unittest.TestCase):
    """The recruitment bark ships through --voice-dir, not its own argument."""

    def test_recruitment_wave_is_registered(self):
        self.assertIn((b"PHS1", "recruitment"), builder.PHANTOM_VOICE_WAVES)

    def test_recruitment_voice_is_a_twenty_percent_one_shot(self):
        gpl = builder.phantom_gpl_template()
        self.assertIn('$HasAttribute("PhantomRecruitmentVoice", thisagent) == False', gpl)
        self.assertIn("$RandomNumber(100) + 1 <= 20", gpl)
        self.assertIn('$PlaySound(thisagent, "Phantom_Hired", "Begin")', gpl)

    def test_multi_event_descriptor_uses_runtime_sound_name(self):
        source = inspect.getsource(builder.write_sounddesc_cam)
        self.assertIn('b"Phantom_Voice\\x00\\x00"', source)
        self.assertNotIn('b"Phantom\\x00\\x00"', source)

    def test_multi_event_descriptor_head_matches_stock_binary_shape(self):
        self.assertEqual(builder.dsnd_head_size(b"Wizard"), 16)
        self.assertEqual(builder.dsnd_head_size(b"Rage_of_Krolm"), 23)
        self.assertEqual(builder.dsnd_head_size(b"Phantom_Voice"), 23)


class IcyTouchTests(unittest.TestCase):
    def test_basic_attack_reach_is_shared_by_validation_and_cast(self):
        gpl = builder.phantom_gpl_template()
        helper_start = gpl.index(
            "function Phantom_Icy_Touch_In_Range(agent thisagent, agent target) is boolean"
        )
        check_start = gpl.index(
            "function Icy_Touch_Check(agent thisagent) is integer", helper_start
        )
        cast_start = gpl.index("\nfunction Icy_Touch_Cast", check_start)
        gravechill_start = gpl.index(
            "\nfunction Phantom_Apply_Gravechill", cast_start
        )
        helper = gpl[helper_start:check_start]
        check = gpl[check_start:cast_start]
        cast = gpl[cast_start:gravechill_start]

        baseline = helper.index("target_range = #Phantom_Icy_Touch_Range;")
        attack_type = helper.index('target\'s "attacktype" == 1', baseline)
        basic_attack = helper.index(
            'target\'s "attack_action" == "basic_attack"', attack_type
        )
        range_compare = helper.index(
            "If ($GetAttribute(target, #ATTRIB_MaxAttackRange) > target_range)",
            basic_attack,
        )
        range_assignment = helper.index(
            "target_range = $GetAttribute(target, #ATTRIB_MaxAttackRange);",
            range_compare,
        )
        distance = helper.index("distance <= target_range", range_assignment)
        adjacent = helper.index("$IsAdjacent(thisagent, target)", distance)
        self.assertLess(baseline, attack_type)
        self.assertLess(attack_type, basic_attack)
        self.assertLess(basic_attack, range_compare)
        self.assertLess(range_compare, range_assignment)
        self.assertLess(range_assignment, distance)
        self.assertLess(distance, adjacent)
        for forbidden in (
            "Daemonwood",
            '"basic_attack_with_stand"',
            '"do_nothing"',
            '"castingrange"',
        ):
            self.assertNotIn(forbidden, helper)

        range_call = "$Phantom_Icy_Touch_In_Range(thisagent, target)"
        self.assertEqual(
            gpl[helper_start:gravechill_start].count(range_call),
            2,
        )
        check_gate = check.index(f"If ({range_call})")
        self.assertLess(check_gate, check.index("return 1;", check_gate))
        cast_gate = cast.index(f"If ({range_call} == False)")
        cast_return = cast.index("return;", cast_gate)
        weapon_attack = cast.index("$make_attack(thisagent, target);", cast_return)
        self.assertLess(cast_gate, cast_return)
        self.assertLess(cast_return, weapon_attack)

    def test_phantom_target_uses_only_close_contact_range(self):
        hero_data = builder.phantom_hero_data()
        units = builder.phantom_units_xml()

        self.assertIn("(attacktype 1)", hero_data)
        self.assertIn("(attack_action do_nothing)", hero_data)
        self.assertNotIn("(attack_action basic_attack)", hero_data)
        self.assertIn('<AttackRange min="1" max="240"/>', units)


class EndlessWinterTrackingTests(unittest.TestCase):
    def test_exceptional_travel_permanently_detaches_before_relocation(self):
        gpl = builder.phantom_gpl_template()
        tracking_start = gpl.index("function Endless_Winter_Track(agent thisagent)")
        active_start = gpl.index(
            "function Endless_Winter_Active(agent thisagent)", tracking_start
        )
        tracking = gpl[tracking_start:active_start]

        parent_read = tracking.index("tracked_target = $Parent(thisagent);")
        invalid = tracking.index(
            "If ($isvalidgamepiece(tracked_target) == False)", parent_read
        )
        invalid_kill = tracking.index(
            '$KillThread(thisagent\'s "EndlessWinterTracking");', invalid
        )
        invalid_return = tracking.index("return;", invalid_kill)
        dead = tracking.index("$IsDead(tracked_target)", invalid_return)
        entering = tracking.index("$IsEnteringBuilding(tracked_target)", dead)
        inside = tracking.index("$InsideBuilding(tracked_target)", entering)
        speed_trail = tracking.index("$HasSpeedTrail(tracked_target)", inside)
        exceptional_kill = tracking.index(
            '$KillThread(thisagent\'s "EndlessWinterTracking");', speed_trail
        )
        exceptional_return = tracking.index("return;", exceptional_kill)
        anchor_location = tracking.index(
            "anchor_location = $LocationOf(thisagent);", exceptional_return
        )
        target_location = tracking.index(
            "target_location = $LocationOf(tracked_target);", anchor_location
        )
        travel_distance = tracking.index(
            "travel_distance = $DistanceBetweenCoords(", target_location
        )
        jump_gate = tracking.index(
            "If (travel_distance > #Phantom_Endless_Winter_Radius)",
            travel_distance,
        )
        jump_kill = tracking.index(
            '$KillThread(thisagent\'s "EndlessWinterTracking");', jump_gate
        )
        jump_return = tracking.index("return;", jump_kill)
        x_guard = tracking.index(
            "$GetX(anchor_location) != $GetX(target_location)", jump_return
        )
        y_guard = tracking.index(
            "$GetY(anchor_location) != $GetY(target_location)", x_guard
        )
        relocation = tracking.index(
            "$TeleportToUnit(thisagent, 50000, tracked_target, 0);", y_guard
        )

        self.assertLess(parent_read, invalid)
        self.assertLess(invalid, invalid_kill)
        self.assertLess(invalid_kill, invalid_return)
        self.assertLess(invalid_return, dead)
        self.assertLess(dead, entering)
        self.assertLess(entering, inside)
        self.assertLess(inside, speed_trail)
        self.assertLess(speed_trail, exceptional_kill)
        self.assertLess(exceptional_kill, exceptional_return)
        self.assertLess(exceptional_return, anchor_location)
        self.assertLess(anchor_location, target_location)
        self.assertLess(target_location, travel_distance)
        self.assertLess(travel_distance, jump_gate)
        self.assertLess(jump_gate, jump_kill)
        self.assertLess(jump_kill, jump_return)
        self.assertLess(jump_return, x_guard)
        self.assertLess(x_guard, y_guard)
        self.assertLess(y_guard, relocation)

        self.assertEqual(
            tracking.count('$KillThread(thisagent\'s "EndlessWinterTracking");'),
            3,
        )
        for forbidden in (
            '$KillThread(thisagent\'s "activeScript");',
            "$DeleteGamePiece(thisagent);",
            "#ATTRIB_HasEffectWingedFeet",
            "#ATTRIB_MovementRateModifier",
            "$CheckEffector(",
            '"Speed_Tonic"',
        ):
            self.assertNotIn(forbidden, tracking)

    def test_named_radius_drives_jump_guard_and_damage_scan(self):
        gpl = builder.phantom_gpl_template()
        tracking_start = gpl.index("function Endless_Winter_Track(agent thisagent)")
        active_start = gpl.index(
            "function Endless_Winter_Active(agent thisagent)", tracking_start
        )
        next_function = gpl.index(
            "function Endless_Winter_Inner_Missile_Hit", active_start
        )
        tracking = gpl[tracking_start:active_start]
        active = gpl[active_start:next_function]

        self.assertIn(
            "If (travel_distance > #Phantom_Endless_Winter_Radius)", tracking
        )
        self.assertIn(
            "targets = $compile_enemies(thisagent, #Phantom_Endless_Winter_Radius);",
            active,
        )
        self.assertNotIn("$compile_enemies(thisagent, 175);", active)
        self.assertEqual(gpl.count("#Phantom_Endless_Winter_Radius"), 2)


class CallToGraveTests(unittest.TestCase):
    def test_safe_travel_prioritizes_recall_over_tonic_and_low_hp_branches(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index("function travel_to_safe(agent thisagent)")
        end = gpl.index("\nfunction Call_To_Grave_Check", start)
        travel = gpl[start:end]
        expected = (
            'thisagent\'s "Title" == "Phantom"',
            '$isspellavailable(thisagent,"call_to_grave",1)',
            "$Call_To_Grave_Check(thisagent) == 1",
            '$cast(thisagent,"call_to_grave",thisagent, "");',
            "$hasLowHP(thisagent) == FALSE",
            "$TryTravelSpell(thisagent);",
            "$heal_self_fleeing(thisagent);",
            '$clearlist(thisagent\'s "hostiles");',
        )
        positions = [travel.index(value) for value in expected]
        self.assertEqual(positions, sorted(positions))

    def test_validation_preserves_stock_self_target_travel_state(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index("function Call_To_Grave_Check(agent thisagent) is integer")
        end = gpl.index("\nfunction Call_To_Grave_Effect", start)
        check = gpl[start:end]
        task = check.index('thisagent\'s "taskname" != "go_home"')
        self_target = check.index('thisagent\'s "Target" == thisagent', task)
        saved_destination = check.index(
            'destination = thisagent\'s "destination";', self_target
        )
        home_target = check.index(
            'thisagent\'s "target" != thisagent\'s "home"', saved_destination
        )
        real_target = check.index(
            '$isvalidgamepiece(thisagent\'s "target")', home_target
        )
        self.assertLess(task, self_target)
        self.assertLess(self_target, saved_destination)
        self.assertLess(saved_destination, home_target)
        self.assertLess(home_target, real_target)

    def test_delayed_teleport_rejects_zero_hp_death_window(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index(
            "function Call_To_Grave_DoMove(agent thisagent, integer theRange)"
        )
        end = gpl.index("\nfunction flee_part_II", start)
        move = gpl[start:end]
        valid = move.index("$IsValidGamePiece(ThisAgent) == False")
        dead = move.index("$IsDead(ThisAgent)", valid)
        zero_hp = move.index("#ATTRIB_HP) <= 0", dead)
        teleport = move.index("$TeleportToPoint", zero_hp)
        self.assertLess(valid, dead)
        self.assertLess(dead, zero_hp)
        self.assertLess(zero_hp, teleport)

    def test_fleeing_phantom_uses_stock_travel_spell_path(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index(
            "function flee_part_II(agent thisagent, list places, integer intent)"
        )
        end = gpl.index("\nfunction Phantom_tree", start)
        flee = gpl[start:end]
        self.assertIn('thisagent\'s "Activescript" = $use_building_safe;', flee)
        self.assertNotIn("call_to_grave", flee)

    def test_behavior_watcher_does_not_cast_travel_spell(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index("function Phantom_Frost_Armor_Watch(agent thisagent)")
        end = gpl.index("\nfunction Phantom_Frost_Armor_Recharge_Check", start)
        watcher = gpl[start:end]
        self.assertNotIn("call_to_grave", watcher)
        self.assertNotIn("Phantom_Sync_Speed_Profile", watcher)
        self.assertIn("$Phantom_Grant_Frost_Armor_Bonus(thisagent);", watcher)

    def test_behavior_watcher_does_not_use_stock_questscript_field(self):
        gpl = builder.phantom_gpl_template()
        self.assertNotIn(
            'thisagent\'s "QuestScript" = $Phantom_Frost_Armor_Watch;', gpl
        )
        self.assertIn(
            '"PhantomFrostArmorWatch",\n\t\t\t"function",\n\t\t\t$Phantom_Frost_Armor_Watch',
            gpl,
        )
        self.assertIn("$Phantom_Ensure_Behavior_Watch(thisagent);", gpl)
        self.assertIn("$Phantom_Ensure_Behavior_Watch(Phantom);", gpl)


class FrostArmorAttackerRangeTests(unittest.TestCase):
    def test_spellcaster_range_can_consume_the_ward(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index("function Phantom_Frost_Armor_Watch(agent thisagent)")
        end = gpl.index("\nfunction Phantom_Frost_Armor_Recharge_Check", start)
        watcher = gpl[start:end]
        weapon_range = watcher.index(
            "attack_range = $GetAttribute(hostile, #ATTRIB_MaxAttackRange);"
        )
        caster_type = watcher.index(
            'hostile\'s "Type" == "Hero" || hostile\'s "Type" == "Monster"',
            weapon_range,
        )
        cast_range = watcher.index(
            'If (hostile\'s "castingrange" > attack_range)', caster_type
        )
        promote_range = watcher.index(
            'attack_range = hostile\'s "castingrange";', cast_range
        )
        distance = watcher.index(
            "$DistanceBetweenAgents(hostile, thisagent) <= attack_range + 24",
            promote_range,
        )
        self.assertLess(weapon_range, caster_type)
        self.assertLess(caster_type, cast_range)
        self.assertLess(cast_range, promote_range)
        self.assertLess(promote_range, distance)


class PriestessPhantomSupportTests(unittest.TestCase):
    def test_rush_range_bonus_is_paired_and_reversible(self):
        gpl = builder.phantom_gpl_template()
        begin_start = gpl.index(
            "Function Phantom_Rush_Unto_Death_Begin(agent ThisAgent)"
        )
        end_start = gpl.index(
            "Function Phantom_Rush_Unto_Death_End(agent ThisAgent)", begin_start
        )
        after_end = gpl.index(
            "Function Phantom_Sync_Speed_Profile(agent ThisAgent)", end_start
        )
        begin = gpl[begin_start:end_start]
        end = gpl[end_start:after_end]
        self.assertIn("#ATTRIB_MaxAttackRange", begin)
        self.assertIn(
            'ThisAgent\'s "castingrange" += #Phantom_Rush_Range_Bonus;', begin
        )
        self.assertIn("#ATTRIB_MaxAttackRange", end)
        self.assertIn(
            'ThisAgent\'s "castingrange" -= #Phantom_Rush_Range_Bonus;', end
        )
        self.assertNotIn("#ATTRIB_HasEffectWingedFeet", begin)
        self.assertNotIn("#ATTRIB_HasEffectWingedFeet", end)

    def test_rush_uses_private_state_and_only_repairs_legacy_native_flag(self):
        gpl = builder.phantom_gpl_template()
        watcher_start = gpl.index(
            "Function Phantom_Haunt_Player_Perk_Watch(agent Palace)"
        )
        watcher_end = gpl.index(
            "Function Phantoms_Haunt_Construction_Birth(agent ThisAgent)",
            watcher_start,
        )
        watcher = gpl[watcher_start:watcher_end]

        active_init = watcher.index(
            'If ($HasAttribute("PhantomRushUntoDeathActive", Priestess) == False)'
        )
        legacy_active = watcher.index(
            'Priestess\'s "PhantomRushUntoDeathActive" == True', active_init
        )
        legacy_flag = watcher.index("#ATTRIB_HasEffectWingedFeet", legacy_active)
        winged_icon = watcher.index(
            '$CheckEffector(Priestess, "winged_feet_icon") == False', legacy_flag
        )
        tonic_icon = watcher.index(
            '$CheckEffector(Priestess, "speed_tonic_icon") == False', winged_icon
        )
        legacy_clear = watcher.index(
            "$SetAttribute(Priestess, #ATTRIB_HasEffectWingedFeet, 0);",
            tonic_icon,
        )
        level_branch = watcher.index("If (Haunt_Level >= 3)", legacy_clear)
        private_gate = watcher.index(
            'Priestess\'s "PhantomRushUntoDeathActive" == False', level_branch
        )
        rush_begin = watcher.index(
            "$Phantom_Rush_Unto_Death_Begin(Priestess);", private_gate
        )
        active_assignment = watcher.index(
            'Priestess\'s "PhantomRushUntoDeathActive" = True;', rush_begin
        )

        self.assertLess(active_init, legacy_active)
        self.assertLess(legacy_active, legacy_flag)
        self.assertLess(legacy_flag, winged_icon)
        self.assertLess(winged_icon, tonic_icon)
        self.assertLess(tonic_icon, legacy_clear)
        self.assertLess(legacy_clear, level_branch)
        self.assertLess(level_branch, private_gate)
        self.assertLess(private_gate, rush_begin)
        self.assertLess(rush_begin, active_assignment)
        self.assertNotIn("#ATTRIB_HasEffectWingedFeet", watcher[level_branch:])
        self.assertEqual(
            watcher.count(
                "$SetAttribute(Priestess, #ATTRIB_HasEffectWingedFeet, 0);"
            ),
            1,
        )
        self.assertNotIn("PhantomRushWingedFeetMigration", watcher)

    def test_supporter_inherits_followed_phantoms_building_target(self):
        gpl = builder.phantom_gpl_template()
        start = gpl.index(
            "function Phantom_Priestess_Follow_Support(agent ThisAgent)"
        )
        end = gpl.index("\nFunction Phantom_Priestess_Assigned_To", start)
        support = gpl[start:end]
        building = support.index('New_Target\'s "Type" == "Building"')
        lair = support.index('New_Target\'s "Type" == "Lair"', building)
        active = support.index(
            'If (Target\'s "ActiveScript" == $Attack_Object)', lair
        )
        join = support.index("If (Join_Attack)", active)
        attack = support.index('$Attack_Object;', join)
        self.assertLess(building, lair)
        self.assertLess(lair, active)
        self.assertLess(active, join)
        self.assertLess(join, attack)


class StandaloneRepoTests(unittest.TestCase):
    """This repository must work with nothing else cloned beside it.

    Two review scripts used to import across repository boundaries, reaching
    into a sibling checkout and an unlicensed third-party folder. Anyone who
    cloned only this project got a bare ModuleNotFoundError. One of them was
    broken outright, because importing a 2,000-line module for a single
    function also pulled in that module's video dependency.
    """

    SEARCH_DIRS = ("src", "scripts", "tests")
    FORBIDDEN = (
        "BrandonWill",
        "sprite_extractor",
        "extract_assets",
        "art-asset-extractor",
        "majesty-cam-tool",
    )

    def _source_files(self):
        # This file names the forbidden tokens on purpose, as the thing it
        # guards against, so it is not a subject of its own scan.
        here = Path(__file__).resolve()
        for name in self.SEARCH_DIRS:
            directory = REPO_ROOT / name
            if directory.is_dir():
                for path in directory.rglob("*.py"):
                    if path.resolve() != here:
                        yield path

    def test_no_module_is_imported_from_another_repository(self):
        offenders = []
        for path in self._source_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    root = name.split(".")[0]
                    if root in ("sprite_extractor", "extract_assets"):
                        offenders.append(f"{path.name}:{node.lineno} imports {name}")
        self.assertEqual(offenders, [], "cross-repository imports: " + ", ".join(offenders))

    # A repo-root name followed by .parent walks above the repository, which is
    # exactly how the old imports reached a sibling checkout. Plain
    # Path(__file__).resolve().parent is the script's own folder and is fine.
    ESCAPING_SYS_PATH = re.compile(
        r"(ROOT\.parent|REPO_ROOT\.parent|parents\[\s*[1-9]\d*\s*\]\s*\.parent"
        r"|parents\[\s*[2-9]\s*\]|\.\.[\\/])"
    )

    def test_no_sys_path_entry_escapes_the_repository(self):
        offenders = []
        for path in self._source_files():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "sys.path" not in line:
                    continue
                if self.ESCAPING_SYS_PATH.search(line):
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
        self.assertEqual(
            offenders,
            [],
            "sys.path entries pointing outside the repo: " + "; ".join(offenders),
        )

    def test_no_source_file_names_a_sibling_repository(self):
        offenders = []
        for path in self._source_files():
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            # Only executable code counts. The provenance note in majesty_imag
            # is a docstring and is meant to stay.
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node, clean=False)
                    if doc:
                        docstrings.update(doc.splitlines())
            for number, line in enumerate(text.splitlines(), 1):
                if line in docstrings or line.strip().startswith("#"):
                    continue
                for token in self.FORBIDDEN:
                    if token in line:
                        offenders.append(f"{path.name}:{number} mentions {token}")
        self.assertEqual(offenders, [], "sibling-repo references: " + ", ".join(offenders))


class VendoredImagTests(unittest.TestCase):
    """The vendored helpers the review scripts depend on."""

    @staticmethod
    def _module():
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import majesty_imag  # noqa: PLC0415

        return majesty_imag

    def test_parse_anim_set_rejects_a_short_blob(self):
        self.assertEqual(self._module().parse_anim_set(b"\x00" * 4), [])

    def test_parse_anim_set_reads_the_entry_table(self):
        imag = self._module()
        blob = bytearray(b"\x00" * 0x14)
        blob += struct.pack("<I", 2)
        blob += struct.pack("<II", 1, 0x40)      # Walk
        blob += struct.pack("<II", 8, 0x50)      # Stand
        blob += b"\x00" * 0x40
        self.assertEqual(
            imag.parse_anim_set(bytes(blob)),
            [(1, "Walk", 0x40), (8, "Stand", 0x50)],
        )

    def test_variant_set_ids_keep_the_base_name(self):
        """High word is a variant counter: 0x10001 is the second Walk set."""
        imag = self._module()
        blob = bytearray(b"\x00" * 0x14)
        blob += struct.pack("<I", 1)
        blob += struct.pack("<II", (1 << 16) | 1, 0x30)
        blob += b"\x00" * 0x40
        self.assertEqual(imag.parse_anim_set(bytes(blob))[0][1], "Walk-1")

    def test_wholly_unknown_set_ids_fall_back_to_the_raw_id(self):
        imag = self._module()
        blob = bytearray(b"\x00" * 0x14)
        blob += struct.pack("<I", 1)
        blob += struct.pack("<II", 91735, 0x30)
        blob += b"\x00" * 0x40
        self.assertEqual(imag.parse_anim_set(bytes(blob))[0][1], "set-91735")

    def test_directional_descriptor_rejects_a_short_blob(self):
        self.assertEqual(self._module().parse_directional_frame_descriptor(b"\x00" * 8, 0), [])

    def test_tile_v1_rejects_a_non_v1_tile(self):
        self.assertIsNone(self._module().tile_v1_to_image(struct.pack("<H", 3) + b"\x00" * 40))

    def test_palette_key_colors_are_rejected(self):
        imag = self._module()
        self.assertTrue(imag.is_palette_key_color(248, 10, 10, 10))
        self.assertTrue(imag.is_palette_key_color(12, 200, 20, 200))
        self.assertFalse(imag.is_palette_key_color(12, 40, 90, 160))


if __name__ == "__main__":
    unittest.main()
