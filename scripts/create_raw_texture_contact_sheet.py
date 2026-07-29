#!/usr/bin/env python3
"""Render the stock INTI raw-texture tiles for dialog-background diagnosis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(
    0,
    str(REPO_ROOT.parent / "majesty-gold-hd-art-asset-extractor" / "scripts"),
)

from build_phantom_guild import (  # noqa: E402
    RAW_TEXTURES_IMAGE,
    read_cam_entries,
    read_cam_entry,
    referenced_tile_indices,
)
from extract_assets import tile_v1_to_image  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interface_cam", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()

    image_record = read_cam_entry(args.interface_cam, b"IMAG", RAW_TEXTURES_IMAGE).data
    tiles = read_cam_entries(args.interface_cam, b"TILE")
    indices = sorted(referenced_tile_indices(image_record, len(tiles)))

    previews: list[tuple[int, Image.Image]] = []
    for index in indices:
        preview = tile_v1_to_image(tiles[index].data, None)
        if preview is not None:
            previews.append((index, preview.convert("RGB")))

    cell_width = 230
    cell_height = 285
    columns = 4
    rows = (len(previews) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for position, (index, preview) in enumerate(previews):
        column = position % columns
        row = position // columns
        x = column * cell_width
        y = row * cell_height
        fitted = preview.copy()
        fitted.thumbnail((cell_width - 12, cell_height - 34), Image.Resampling.LANCZOS)
        sheet.paste(fitted, (x + (cell_width - fitted.width) // 2, y + 24))
        draw.text((x + 6, y + 5), f"TILE {index}  {preview.width}x{preview.height}", fill=(235, 235, 240))

    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output_png)
    print(f"Wrote {args.output_png} with {len(previews)} raw-texture tiles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
