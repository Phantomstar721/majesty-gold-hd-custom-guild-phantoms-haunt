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
