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
        default=REPO_ROOT / "dist/CustomGuildPhantomsHaunt/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/gravechill-icon-packaged-review.png",
    )
    parser.add_argument(
        "--impact-out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/gravechill-impact-packaged-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    prefix = b"PHg1Skull"
    sequence = sorted(
        (
            entry
            for entry in tiles
            if entry.name.rstrip(b"\x00").startswith(prefix)
        ),
        key=lambda entry: int(entry.name.rstrip(b"\x00")[len(prefix) :]),
    )
    if len(sequence) != 29:
        raise ValueError(f"Expected 29 Gravechill icon tiles, found {len(sequence)}")

    selected = (0, 4, 8, 12, 16, 20, 24, 28)
    scale = 6
    cell_width = 190
    cell_height = 235
    header_height = 62
    sheet = Image.new(
        "RGB",
        (cell_width * len(selected), header_height + cell_height),
        (20, 24, 32),
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (14, 12),
        "Gravechill — decoded packaged 29-frame debuff icon",
        fill=(225, 238, 248),
    )
    draw.text(
        (14, 34),
        "Eight sampled frames at 6x native size; black is transparent in game.",
        fill=(125, 170, 200),
    )

    for column, frame_index in enumerate(selected):
        frame = render_tile(sequence[frame_index].data, palettes)
        native_size = frame.size
        frame = frame.resize(
            (frame.width * scale, frame.height * scale),
            Image.Resampling.NEAREST,
        )
        x = column * cell_width + (cell_width - frame.width) // 2
        y = header_height + 4 + (190 - frame.height) // 2
        sheet.paste(frame, (x, y), frame)
        draw.text(
            (column * cell_width + 10, header_height + 202),
            f"frame {frame_index} — {native_size[0]}x{native_size[1]}",
            fill=(170, 198, 220),
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)

    impact_prefix = b"PHg2SkullHit"
    impact_sequence = sorted(
        (
            entry
            for entry in tiles
            if entry.name.rstrip(b"\x00").startswith(impact_prefix)
        ),
        key=lambda entry: int(entry.name.rstrip(b"\x00")[len(impact_prefix) :]),
    )
    if len(impact_sequence) != 6:
        raise ValueError(
            f"Expected 6 Gravechill impact tiles, found {len(impact_sequence)}"
        )

    impact_scale = 4
    impact_cell_width = 430
    impact_cell_height = 470
    impact_header_height = 62
    impact_sheet = Image.new(
        "RGB",
        (
            impact_cell_width * len(impact_sequence),
            impact_header_height + impact_cell_height,
        ),
        (20, 24, 32),
    )
    impact_draw = ImageDraw.Draw(impact_sheet)
    impact_draw.text(
        (14, 12),
        "Gravechill — decoded packaged six-frame one-shot hit animation",
        fill=(225, 238, 248),
    )
    impact_draw.text(
        (14, 34),
        "All frames at 4x native size; black is transparent in game.",
        fill=(125, 170, 200),
    )

    for column, entry in enumerate(impact_sequence):
        frame = render_tile(entry.data, palettes)
        native_size = frame.size
        frame = frame.resize(
            (frame.width * impact_scale, frame.height * impact_scale),
            Image.Resampling.NEAREST,
        )
        x = column * impact_cell_width + (impact_cell_width - frame.width) // 2
        y = impact_header_height + 4 + (410 - frame.height) // 2
        impact_sheet.paste(frame, (x, y), frame)
        impact_draw.text(
            (column * impact_cell_width + 10, impact_header_height + 425),
            f"frame {column} — {native_size[0]}x{native_size[1]}",
            fill=(170, 198, 220),
        )

    args.impact_out.parent.mkdir(parents=True, exist_ok=True)
    impact_sheet.save(args.impact_out)
    print(args.impact_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
