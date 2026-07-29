#!/usr/bin/env python3
"""Print stock Majesty dialog strings and embedded SMNU tokens for comparison."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_phantom_guild import read_cam_entries, read_cam_entry  # noqa: E402


def strt_records(data: bytes) -> list[tuple[int, str]]:
    count = struct.unpack_from("<H", data, 0)[0]
    offsets = struct.unpack_from(f"<{count}I", data, 4)
    records: list[tuple[int, str]] = []
    for offset in offsets:
        string_id = struct.unpack_from("<I", data, offset)[0]
        start = offset + 4
        end = data.index(b"\x00", start)
        records.append((string_id, data[start:end].decode("cp1252")))
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("textdata_cam", type=Path)
    parser.add_argument("dialog_ids", nargs="*")
    parser.add_argument(
        "--upgradable-candidates",
        action="store_true",
        help="List dialogs containing LVL and HEROES, with their SPELLS status.",
    )
    parser.add_argument(
        "--string-refs",
        action="store_true",
        help="Show aligned SMNU offsets whose 32-bit value matches an STRT id.",
    )
    parser.add_argument(
        "--control-context",
        action="store_true",
        help="Hex-dump the final 2048 SMNU bytes, where status and bottom-row controls live.",
    )
    args = parser.parse_args()

    if args.upgradable_candidates:
        menu_sizes = {
            entry.name.rstrip(b"\x00"): len(entry.data)
            for entry in read_cam_entries(args.textdata_cam, b"SMNU")
        }
        for entry in read_cam_entries(args.textdata_cam, b"STRT"):
            name = entry.name.rstrip(b"\x00")
            records = strt_records(entry.data)
            values = {text.strip().upper() for _, text in records}
            if "LVL" in values and "HEROES" in values:
                print(
                    name.decode("ascii", errors="replace"),
                    f"SMNU={menu_sizes.get(name, 0)}",
                    f"SPELLS={'SPELLS' in values}",
                    repr(records[0][1].strip() if records else ""),
                )

    for dialog_id_text in args.dialog_ids:
        dialog_id = dialog_id_text.encode("ascii")
        strings = read_cam_entry(args.textdata_cam, b"STRT", dialog_id).data
        menu = read_cam_entry(args.textdata_cam, b"SMNU", dialog_id).data
        print(f"{dialog_id_text}: STRT={len(strings)} SMNU={len(menu)}")
        for string_id, text in strt_records(strings):
            print(f"  STRT[{string_id:>2}] {text!r}")
            if args.string_refs:
                needle = struct.pack("<I", string_id)
                offsets = [
                    offset
                    for offset in range(0, len(menu) - 3, 4)
                    if menu[offset : offset + 4] == needle
                ]
                print("    refs", " ".join(f"0x{offset:04x}" for offset in offsets))
        for match in re.finditer(rb"[\x20-\x7e]{3,}", menu):
            print(f"  SMNU+0x{match.start():04x} {match.group().decode('ascii')!r}")
        if args.control_context:
            start = max(0, len(menu) - 2048)
            for offset in range(start, len(menu), 16):
                chunk = menu[offset : offset + 16]
                hex_text = " ".join(f"{value:02x}" for value in chunk)
                ascii_text = "".join(chr(value) if 32 <= value <= 126 else "." for value in chunk)
                print(f"  {offset:04x}  {hex_text:<47}  {ascii_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
