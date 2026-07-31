from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from build_phantom_guild import (  # noqa: E402
    decode_indexed_v3_tile,
    read_cam_entries,
    splt_palette_colors,
    tile_palette_index,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=REPO_ROOT / "dist/CustomGuildPhantomsHaunt/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/ice-lance-directional-packaged-review.png",
    )
    args = parser.parse_args()

    tiles = read_cam_entries(args.cam, b"TILE")
    palettes = read_cam_entries(args.cam, b"SPLT")
    projectile_tiles = [
        tile
        for tile in tiles
        if tile.name.rstrip(b"\x00").startswith(b"PHp1IceTile")
    ]
    if len(projectile_tiles) != 128:
        raise ValueError(f"Expected 128 Ice Lance tiles, found {len(projectile_tiles)}")

    frames: list[Image.Image] = []
    for tile in projectile_tiles:
        decoded = decode_indexed_v3_tile(tile.data)
        if decoded is None:
            raise ValueError(f"Could not decode {tile.name!r}")
        height, width, pixels = decoded
        palette_index = tile_palette_index(tile.data)
        if palette_index is None:
            raise ValueError(f"{tile.name!r} has no palette")
        palette = splt_palette_colors(palettes[palette_index].data)
        frame = Image.new("RGBA", (width, height))
        frame.putdata(
            [
                (0, 0, 0, 0) if value == 0 else (*palette[value], 255)
                for row in pixels
                for value in row
            ]
        )
        frames.append(frame)

    cell = 96
    sheet = Image.new("RGBA", (8 * cell, 4 * cell), (28, 30, 38, 255))
    draw = ImageDraw.Draw(sheet)
    for direction in range(32):
        frame = frames[direction * 4 + 2].copy()
        frame.thumbnail((78, 78), Image.Resampling.NEAREST)
        column = direction % 8
        row = direction // 8
        x = column * cell + (cell - frame.width) // 2
        y = row * cell + (cell - frame.height) // 2
        sheet.alpha_composite(frame, (x, y))
        draw.text((column * cell + 3, row * cell + 3), str(direction), fill="white")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
