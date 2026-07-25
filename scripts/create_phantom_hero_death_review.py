from __future__ import annotations

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


def main() -> int:
    cam = ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam"
    output_path = ROOT / "artifacts/reviews/phantom-hero-death-engine-review.png"
    tiles = builder.read_cam_entries(cam, b"TILE")
    palettes = builder.read_cam_entries(cam, b"SPLT")
    by_name = {entry.name.rstrip(b"\x00"): entry for entry in tiles}

    source_tiles = (4723, 4724, 4778, 4779, 4780, 4781, 4782, 4783, 4784, 4785, 4787)
    scale = 4
    cell_width = 360
    cell_height = 390
    card = Image.new("RGB", (cell_width * 6, cell_height * 2), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    for position, source_tile in enumerate(source_tiles):
        name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
        frame = render_tile(by_name[name].data, palettes)
        visible_bbox = frame.getbbox()
        if visible_bbox is not None:
            frame = frame.crop(visible_bbox)
        frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        column = position % 6
        row = position // 6
        x = column * cell_width + (cell_width - frame.width) // 2
        y = row * cell_height + 12 + (315 - frame.height) // 2
        card.paste(frame, (x, y), frame)
        draw.text(
            (column * cell_width + 14, row * cell_height + 340),
            f"TILE {source_tile}",
            font=font(20),
            fill=(220, 230, 240),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(output_path, optimize=True)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
