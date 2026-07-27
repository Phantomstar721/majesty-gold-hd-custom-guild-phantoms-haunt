from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


def sprite_metrics(tile: bytes) -> tuple[int, ...]:
    decoded = builder.decode_indexed_v3_tile(tile)
    if decoded is None:
        raise ValueError("Expected an indexed TILE v3")
    height, width, pixels = decoded
    hotspot_x, hotspot_y = struct.unpack_from("<HH", tile, 10)
    points = [
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value != 0 and not 247 <= value <= 250
    ]
    if not points:
        raise ValueError("Sprite TILE has no visible body pixels")
    left = min(x for x, _y in points)
    right = max(x for x, _y in points)
    top = min(y for _x, y in points)
    bottom = max(y for _x, y in points)
    return (
        right - left + 1,
        bottom - top + 1,
        left - hotspot_x,
        right - hotspot_x,
        top - hotspot_y,
        bottom - hotspot_y,
        hotspot_x,
        hotspot_y,
        width,
        height,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--stock-cam",
        type=Path,
        default=Path(
            "C:/Program Files (x86)/Steam/steamapps/common/"
            "Majesty HD/Data/maindata.cam"
        ),
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    by_name = {entry.name.rstrip(b"\x00"): entry.data for entry in tiles}
    stock_tiles = (
        builder.read_cam_entries(args.stock_cam, b"TILE")
        if args.stock_cam.is_file()
        else []
    )

    def metrics(source_tile: int) -> tuple[int, ...]:
        name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        return sprite_metrics(by_name[name])

    for direction in range(8):
        stand = metrics(4650 + direction)
        walk = [metrics(4586 + direction * 8 + frame) for frame in range(8)]
        attack = [metrics(4690 + direction * 4 + frame) for frame in range(4)]
        cast = [metrics(4746 + direction * 4 + frame) for frame in range(4)]
        print(f"D{direction} STAND {stand}")
        if stock_tiles:
            stock_stand = sprite_metrics(stock_tiles[4650 + direction].data)
            stock_walk = [
                sprite_metrics(stock_tiles[4586 + direction * 8 + frame].data)
                for frame in range(8)
            ]
            stock_cast = [
                sprite_metrics(stock_tiles[4746 + direction * 4 + frame].data)
                for frame in range(4)
            ]
            print(
                f"  STOCK  stand={stock_stand[0]}x{stock_stand[1]} "
                f"walk_heights={[value[1] for value in stock_walk]} "
                f"cast_heights={[value[1] for value in stock_cast]}"
            )
        print(
            "  WALK   "
            + " ".join(
                f"{value[0]}x{value[1]}@({value[2]},{value[4]})"
                f"..({value[3]},{value[5]})/{value[8]}x{value[9]}"
                for value in walk
            )
        )
        print(
            "  ATTACK "
            + " ".join(
                f"{value[0]}x{value[1]}@({value[2]},{value[4]})"
                f"..({value[3]},{value[5]})/{value[8]}x{value[9]}"
                for value in attack
            )
        )
        print(
            "  CAST   "
            + " ".join(
                f"{value[0]}x{value[1]}@({value[2]},{value[4]})"
                f"..({value[3]},{value[5]})/{value[8]}x{value[9]}"
                for value in cast
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
