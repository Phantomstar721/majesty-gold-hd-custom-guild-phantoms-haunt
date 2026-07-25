from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


SEQUENCES = (
    ("Active armor crystal", b"PHf1Crystal"),
    ("Frozen — small", b"PHf2Frozen"),
    ("Frozen — medium", b"PHf3Frozen"),
    ("Frozen — large", b"PHf4Frozen"),
)


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
        default=REPO_ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/frost-armor-packaged-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    selected_frames = (0, 4, 8, 12, 16, 20, 24, 28)
    cell_width = 150
    cell_height = 178
    label_width = 190
    sheet = Image.new(
        "RGB",
        (label_width + len(selected_frames) * cell_width, len(SEQUENCES) * cell_height),
        (21, 25, 34),
    )
    draw = ImageDraw.Draw(sheet)

    for row, (label, prefix) in enumerate(SEQUENCES):
        sequence = sorted(
            (
                entry
                for entry in tiles
                if entry.name.rstrip(b"\x00").startswith(prefix)
            ),
            key=lambda entry: int(entry.name.rstrip(b"\x00")[len(prefix) :]),
        )
        if len(sequence) != 29:
            raise ValueError(f"Expected 29 {prefix!r} tiles, found {len(sequence)}")
        draw.text((12, row * cell_height + 18), label, fill=(220, 235, 245))
        draw.text((12, row * cell_height + 42), "29 packaged frames", fill=(115, 165, 195))
        for column, frame_index in enumerate(selected_frames):
            frame = render_tile(sequence[frame_index].data, palettes)
            scale = min(3, max(1, 132 // max(frame.size)))
            frame = frame.resize(
                (frame.width * scale, frame.height * scale),
                Image.Resampling.NEAREST,
            )
            x = label_width + column * cell_width + (cell_width - frame.width) // 2
            y = row * cell_height + 8 + (138 - frame.height) // 2
            sheet.paste(frame, (x, y), frame)
            draw.text(
                (label_width + column * cell_width + 8, row * cell_height + 150),
                f"frame {frame_index}",
                fill=(150, 175, 200),
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
