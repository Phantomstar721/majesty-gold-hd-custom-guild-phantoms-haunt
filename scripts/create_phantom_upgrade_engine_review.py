from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


STATE_TILES = (
    ("UPGRADE EARLY", "Bld0010"),
    ("UPGRADE LATE", "Bld0011"),
    ("INACTIVE", "Bld0012"),
    ("ACTIVE", "Act00"),
    ("DAMAGED A", "Bld0007"),
    ("DAMAGED B", "Bld0008"),
    ("COLLAPSE", "Bld0009"),
    ("DESTROYED", "Bld0000"),
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def render_packaged_tile(
    tile: bytes,
    palettes: list[builder.CamEntry],
) -> Image.Image:
    decoded = builder.decode_indexed_v3_tile(tile)
    colors = builder.tile_palette_colors(tile, palettes)
    if decoded is None or colors is None:
        raise ValueError("Expected an indexed TILE v3 with a readable palette")
    height, width, pixels = decoded
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    output = frame.load()
    for y, row in enumerate(pixels):
        for x, index in enumerate(row):
            if 1 <= index <= 246:
                output[x, y] = (*colors[index], 255)
            elif 247 <= index <= 250:
                # Approximate Majesty's terrain-darkening controls without
                # displaying their raw red/magenta palette-key colors.
                output[x, y] = (0, 0, 0, 72)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT
        / "artifacts/reviews/phantom-haunt-upgrade-packaged-v1.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    tile_by_name = {entry.name.rstrip(b"\x00"): entry.data for entry in tiles}

    scale = 2
    cell_width = 600
    cell_height = 620
    header_height = 110
    card = Image.new(
        "RGB",
        (cell_width * len(STATE_TILES), header_height + cell_height * 2),
        (18, 23, 32),
    )
    draw = ImageDraw.Draw(card)
    draw.text(
        (24, 18),
        "PHANTOMS HAUNT — PACKAGED LEVEL 2 / LEVEL 3 WORLD FRAMES",
        font=font(34),
        fill=(230, 239, 248),
    )
    draw.text(
        (26, 65),
        "Nearest-neighbor 2x • decoded from phantom_maindata.cam • shadow controls approximated as translucent black",
        font=font(19),
        fill=(142, 169, 196),
    )

    for row, level in enumerate((2, 3)):
        for column, (label, suffix) in enumerate(STATE_TILES):
            tile_name = f"PHG{level}{suffix}".encode("ascii")
            tile = tile_by_name.get(tile_name)
            if tile is None:
                raise ValueError(f"Packaged TILE {tile_name!r} was not found")
            frame = render_packaged_tile(tile, palettes)
            frame = frame.resize(
                (frame.width * scale, frame.height * scale),
                Image.Resampling.NEAREST,
            )
            x0 = column * cell_width
            y0 = header_height + row * cell_height
            checker = Image.new("RGB", (cell_width - 12, cell_height - 58), (43, 49, 58))
            checker_draw = ImageDraw.Draw(checker)
            block = 24
            for y in range(0, checker.height, block):
                for x in range(0, checker.width, block):
                    if (x // block + y // block) % 2:
                        checker_draw.rectangle(
                            (x, y, x + block - 1, y + block - 1),
                            fill=(48, 56, 65),
                        )
            card.paste(checker, (x0 + 6, y0 + 6))
            frame_x = x0 + (cell_width - frame.width) // 2
            frame_y = y0 + 8 + (checker.height - frame.height) // 2
            card.paste(frame, (frame_x, frame_y), frame)
            draw.text(
                (x0 + 16, y0 + cell_height - 43),
                f"L{level}  {label}",
                font=font(21),
                fill=(226, 235, 244),
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    card.save(args.out, optimize=True)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
