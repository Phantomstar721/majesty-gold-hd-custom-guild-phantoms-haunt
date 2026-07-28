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
        default=REPO_ROOT
        / "artifacts/reviews/stock-meteor-missile-progression.png",
    )
    parser.add_argument(
        "--image-name",
        default="WPg3meteor_missile",
    )
    parser.add_argument(
        "--title",
        default="Stock Wizard Meteor Storm missile — exact animation order",
    )
    args = parser.parse_args()

    images = builder.read_cam_entries(args.cam, b"IMAG")
    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    image = next(
        entry.data
        for entry in images
        if entry.name.rstrip(b"\x00") == args.image_name.encode("ascii")
    )
    animation_sets = builder.single_direction_imag_animation_sets(image)
    frame_indices = [
        tile_index
        for _set_id, frames in animation_sets
        for _record_offset, tile_index in frames
        if tile_index
    ]

    scale = 6
    cell_width = 230
    sheet = Image.new("RGB", (cell_width * len(frame_indices), 270), (18, 24, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (14, 12),
        args.title,
        fill=(225, 238, 248),
    )
    for column, tile_index in enumerate(frame_indices):
        frame = render_tile(tiles[tile_index].data, palettes)
        enlarged = frame.resize(
            (frame.width * scale, frame.height * scale),
            Image.Resampling.NEAREST,
        )
        x = column * cell_width + (cell_width - enlarged.width) // 2
        y = 48 + (190 - enlarged.height) // 2
        sheet.paste(enlarged, (x, y), enlarged)
        draw.text(
            (column * cell_width + 12, 242),
            f"frame {column + 1}: TILE {tile_index}",
            fill=(170, 198, 220),
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
