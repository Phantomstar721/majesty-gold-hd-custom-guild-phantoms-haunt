from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


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
    shadow_colors = ((128, 0, 128), (153, 0, 153), (178, 0, 178), (204, 0, 204))
    for y, row in enumerate(pixels):
        for x, index in enumerate(row):
            if index:
                rgb = shadow_colors[index - 247] if 247 <= index <= 250 else colors[index]
                output[x, y] = (*rgb, 255)
    return image


def tile_hotspot(tile: bytes) -> tuple[int, int]:
    if len(tile) < 14:
        raise ValueError("TILE is too short to contain its hotspot")
    return struct.unpack_from("<HH", tile, 10)


def body_bottom(tile: bytes) -> int | None:
    decoded = builder.decode_indexed_v3_tile(tile)
    if decoded is None:
        return None
    _height, _width, pixels = decoded
    body_rows = [
        y
        for y, row in enumerate(pixels)
        if any(value != 0 and not 247 <= value <= 250 for value in row)
    ]
    return max(body_rows) + 1 if body_rows else None


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
        default=ROOT / "artifacts/reviews/phantom-hero-death-engine-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    by_name = {entry.name.rstrip(b"\x00"): entry for entry in tiles}

    source_tiles = (4722, 4723, 4724, 4779, 4780, 4781, 4782, 4783, 4784, 4785, 4787)
    scale = 3
    cell_width = 500
    cell_height = 480
    origin_x = cell_width // 2
    origin_y = 325
    card = Image.new("RGB", (cell_width * 6, cell_height * 2), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    for position, source_tile in enumerate(source_tiles):
        name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        tile = by_name[name].data
        frame = render_tile(tile, palettes)
        hotspot_x, hotspot_y = tile_hotspot(tile)
        base_y = body_bottom(tile)
        native_width, native_height = frame.size
        frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        column = position % 6
        row = position // 6
        cell_left = column * cell_width
        cell_top = row * cell_height
        world_x = cell_left + origin_x
        world_y = cell_top + origin_y
        draw.line(
            (cell_left + 20, world_y, cell_left + cell_width - 20, world_y),
            fill=(55, 68, 82),
            width=1,
        )
        draw.line(
            (world_x, cell_top + 20, world_x, cell_top + cell_height - 75),
            fill=(55, 68, 82),
            width=1,
        )
        x = world_x - hotspot_x * scale
        y = world_y - hotspot_y * scale
        card.paste(frame, (x, y), frame)
        draw.ellipse(
            (world_x - 4, world_y - 4, world_x + 4, world_y + 4),
            outline=(255, 194, 74),
            width=2,
        )
        draw.text(
            (cell_left + 14, cell_top + 390),
            f"TILE {source_tile}  {native_width}x{native_height}",
            font=font(20),
            fill=(220, 230, 240),
        )
        draw.text(
            (cell_left + 14, cell_top + 420),
            f"hotspot ({hotspot_x}, {hotspot_y})  body base {base_y - hotspot_y:+d}"
            if base_y is not None
            else f"hotspot ({hotspot_x}, {hotspot_y})  no body",
            font=font(17),
            fill=(145, 164, 183),
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    card.save(args.output, optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
