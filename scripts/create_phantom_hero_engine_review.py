from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


FRAME_LABELS = ("STAND", "WALK", "ATTACK", "CAST", "SPECIAL", "DIE")
FIRST_PRIESTESS_TILE = 4586


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/consola.ttf"), Path("C:/Windows/Fonts/segoeui.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_tile(tile: bytes, palettes: list[builder.CamEntry]) -> Image.Image:
    decoded = builder.decode_indexed_v3_tile(tile)
    colors = builder.tile_palette_colors(tile, palettes)
    if decoded is None or colors is None:
        raise ValueError("Expected an indexed TILE v3 with a readable palette")
    height, width, pixels = decoded
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    output = image.load()
    for y, row in enumerate(pixels):
        for x, index in enumerate(row):
            if index:
                if 247 <= index <= 250:
                    red, green, blue = (
                        (128, 0, 128),
                        (153, 0, 153),
                        (178, 0, 178),
                        (204, 0, 204),
                    )[index - 247]
                else:
                    red, green, blue = colors[index]
                output[x, y] = (red, green, blue, 255)
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/reviews/phantom-hero-primary-engine-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    by_name = {entry.name.rstrip(b"\x00"): entry for entry in tiles}

    scale = 4
    cell_width = 300
    cell_height = 390
    card = Image.new("RGB", (cell_width * len(FRAME_LABELS), cell_height * 6), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    for direction in range(6):
        source_tiles = (
            4650 + direction,
            4590 + direction * 8,
            4693 + direction * 4,
            4749 + direction * 4,
            4661 + direction * 4,
            4724 + direction * 3,
        )
        for column, (label, source_tile) in enumerate(zip(FRAME_LABELS, source_tiles)):
            offset = source_tile - FIRST_PRIESTESS_TILE
            name = f"PHM1PhantomTile{offset}".encode("ascii")
            frame = render_tile(by_name[name].data, palettes)
            frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
            x = column * cell_width + (cell_width - frame.width) // 2
            y = direction * cell_height + 8 + (330 - frame.height) // 2
            card.paste(frame, (x, y), frame)
            draw.text(
                (column * cell_width + 16, direction * cell_height + 350),
                f"D{direction + 2} {label}",
                font=font(20),
                fill=(220, 230, 240),
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    card.save(args.output, optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
