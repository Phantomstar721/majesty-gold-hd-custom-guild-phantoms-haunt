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


def numbered_tiles(
    tiles: list[builder.CamEntry],
    prefix: bytes,
    expected: int,
) -> list[builder.CamEntry]:
    sequence = sorted(
        (
            entry
            for entry in tiles
            if entry.name.rstrip(b"\x00").startswith(prefix)
        ),
        key=lambda entry: int(entry.name.rstrip(b"\x00")[len(prefix) :]),
    )
    if len(sequence) != expected:
        raise ValueError(
            f"Expected {expected} tiles with prefix {prefix!r}, found {len(sequence)}"
        )
    return sequence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cam",
        type=Path,
        default=REPO_ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT
        / "artifacts/reviews/eternal-soul-packaged-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    cast = numbered_tiles(tiles, b"PHe2FlameCast", 6)
    icon = numbered_tiles(tiles, b"PHe1FlameIcon", 29)

    sheet = Image.new("RGB", (1320, 790), (18, 24, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 14),
        "Eternal Soul — decoded packaged ghost-flame art",
        fill=(225, 238, 248),
    )
    draw.text(
        (18, 36),
        "Top: six-frame grow / pulse / fade cast. Bottom: sampled looping buff icon.",
        fill=(125, 170, 200),
    )

    cast_scale = 4
    cast_cell_width = sheet.width // len(cast)
    for column, entry in enumerate(cast):
        frame = render_tile(entry.data, palettes)
        native_size = frame.size
        enlarged = frame.resize(
            (frame.width * cast_scale, frame.height * cast_scale),
            Image.Resampling.NEAREST,
        )
        x = column * cast_cell_width + (cast_cell_width - enlarged.width) // 2
        y = 76 + max(0, (390 - enlarged.height) // 2)
        sheet.paste(enlarged, (x, y), enlarged)
        draw.text(
            (column * cast_cell_width + 10, 475),
            f"cast {column} — {native_size[0]}x{native_size[1]}",
            fill=(170, 198, 220),
        )

    selected = (0, 4, 8, 12, 16, 20, 24, 28)
    icon_scale = 6
    icon_cell_width = sheet.width // len(selected)
    for column, frame_index in enumerate(selected):
        frame = render_tile(icon[frame_index].data, palettes)
        native_size = frame.size
        enlarged = frame.resize(
            (frame.width * icon_scale, frame.height * icon_scale),
            Image.Resampling.NEAREST,
        )
        x = column * icon_cell_width + (icon_cell_width - enlarged.width) // 2
        y = 535 + max(0, (170 - enlarged.height) // 2)
        sheet.paste(enlarged, (x, y), enlarged)
        draw.text(
            (column * icon_cell_width + 8, 742),
            f"icon {frame_index} — {native_size[0]}x{native_size[1]}",
            fill=(170, 198, 220),
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
