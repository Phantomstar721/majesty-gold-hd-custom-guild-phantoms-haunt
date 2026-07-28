from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


def render_tile(tile: bytes, palettes: list[builder.CamEntry]) -> Image.Image:
    decoded = builder.decode_indexed_v3_tile(tile)
    colors = builder.tile_palette_colors(tile, palettes)
    if decoded is None or colors is None:
        raise ValueError("Expected an indexed TILE v3 with a readable palette")
    height, width, pixels = decoded
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    output = frame.load()
    for y, row in enumerate(pixels):
        for x, index in enumerate(row):
            if index:
                output[x, y] = (*colors[index], 255)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=Path(
            r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\Majesty HD\Data\maindata.cam"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/meteor-auxiliary-tiles.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    tile_indices = list(range(242, 264))
    columns = 6
    cell_width = 180
    cell_height = 190
    header_height = 54
    rows = (len(tile_indices) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (cell_width * columns, header_height + cell_height * rows),
        (18, 24, 34),
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (14, 12),
        "Stock low-index MeteorStrmMiss / MeteorStrmEffct TILEs",
        fill=(225, 238, 248),
    )

    for position, tile_index in enumerate(tile_indices):
        frame = render_tile(tiles[tile_index].data, palettes)
        scale = min(5, max(1, 135 // max(frame.size)))
        enlarged = frame.resize(
            (frame.width * scale, frame.height * scale),
            Image.Resampling.NEAREST,
        )
        column = position % columns
        row = position // columns
        left = column * cell_width
        top = header_height + row * cell_height
        sheet.paste(
            enlarged,
            (
                left + (cell_width - enlarged.width) // 2,
                top + 8 + (140 - enlarged.height) // 2,
            ),
            enlarged,
        )
        draw.text(
            (left + 8, top + 154),
            f"TILE {tile_index}",
            fill=(170, 198, 220),
        )
        draw.text(
            (left + 8, top + 170),
            tiles[tile_index].name.rstrip(b"\x00")[4:].decode(
                "ascii",
                errors="replace",
            ),
            fill=(125, 160, 185),
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
