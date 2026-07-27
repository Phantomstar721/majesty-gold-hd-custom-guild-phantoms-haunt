from __future__ import annotations

import argparse
from pathlib import Path
import struct
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
        default=REPO_ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT
        / "artifacts/reviews/call-to-grave-portal-packaged-review.png",
    )
    args = parser.parse_args()

    images = builder.read_cam_entries(args.cam, b"IMAG")
    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    image = next(
        entry.data
        for entry in images
        if entry.name.rstrip(b"\x00") == b"PHc2Call to Grave"
    )
    animation_sets = builder.single_direction_imag_animation_sets(image)
    expected_counts = {80: 8, 64: 8, 96: 7}
    actual_counts = {set_id: len(frames) for set_id, frames in animation_sets}
    if actual_counts != expected_counts:
        raise ValueError(
            f"Expected Wizard Teleport open/hold/close sets {expected_counts}, "
            f"found {actual_counts}"
        )

    phase_names = {80: "OPEN", 64: "HOLD", 96: "CLOSE"}
    scale = 2
    columns = 8
    cell_width = 205
    cell_height = 290
    header_height = 66
    sheet = Image.new(
        "RGB",
        (cell_width * columns, header_height + cell_height * 3),
        (18, 23, 32),
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (14, 12),
        "Call to Grave — packaged Wizard Teleport open / hold / close sets",
        fill=(225, 238, 248),
    )
    draw.text(
        (14, 35),
        "All frames are 2x native size; yellow crosshairs mark the fixed TILE hotspot.",
        fill=(125, 170, 200),
    )

    for row, (set_id, frames) in enumerate(animation_sets):
        phase = phase_names[set_id]
        for column, (_record_offset, tile_index) in enumerate(frames):
            tile = tiles[tile_index].data
            frame = render_tile(tile, palettes)
            hotspot_x, hotspot_y = struct.unpack_from("<HH", tile, 10)
            native_width, native_height = frame.size
            frame = frame.resize(
                (frame.width * scale, frame.height * scale),
                Image.Resampling.NEAREST,
            )
            cell_left = column * cell_width
            cell_top = header_height + row * cell_height
            x = cell_left + (cell_width - frame.width) // 2
            y = cell_top + 8
            sheet.paste(frame, (x, y), frame)
            marker_x = x + hotspot_x * scale
            marker_y = y + hotspot_y * scale
            draw.line(
                (marker_x - 6, marker_y, marker_x + 6, marker_y),
                fill=(255, 205, 76),
            )
            draw.line(
                (marker_x, marker_y - 6, marker_x, marker_y + 6),
                fill=(255, 205, 76),
            )
            draw.text(
                (cell_left + 8, cell_top + 246),
                f"{phase} {column + 1}  TILE {tile_index}",
                fill=(170, 198, 220),
            )
            draw.text(
                (cell_left + 8, cell_top + 266),
                f"{native_width}x{native_height}  hotspot {hotspot_x},{hotspot_y}",
                fill=(125, 160, 185),
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
