from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402


REFERENCES = (
    ("base", b"DRA2Winged_Feet_IC"),
    ("base", b"PRB2wither_IC"),
    ("mx", b"XR21meds_slow_icon"),
    ("mx", b"XR25plague_icon"),
    ("mx", b"XR29frost_fld_icon"),
    ("custom", b"PHo4chill_icon"),
    ("custom", b"PHc3emp_chill_icon"),
)


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
                output[x, y] = (*colors[index], 255)
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--game-path",
        type=Path,
        default=Path(r"C:\Program Files (x86)\Steam\steamapps\common\Majesty HD"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts/reviews/status-overlay-reference-review.png",
    )
    args = parser.parse_args()

    archives = {
        "base": args.game_path / "Data/maindata.cam",
        "mx": args.game_path / "DataMx/mx_maindata.cam",
        "custom": REPO_ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam",
    }
    loaded = {}
    for key, path in archives.items():
        loaded[key] = (
            builder.read_cam_entries(path, b"IMAG"),
            builder.read_cam_entries(path, b"TILE"),
            builder.read_cam_entries(path, b"SPLT"),
        )

    card_width = 230
    card_height = 220
    sheet = Image.new("RGB", (card_width * len(REFERENCES), card_height), (22, 25, 32))
    draw = ImageDraw.Draw(sheet)
    for column, (archive_key, image_name) in enumerate(REFERENCES):
        images, tiles, palettes = loaded[archive_key]
        image_entry = next(entry for entry in images if entry.name.rstrip(b"\x00") == image_name)
        tile_indices = sorted(
            {
                struct.unpack_from("<I", image_entry.data, offset)[0]
                for offset in range(0, len(image_entry.data) - 7, 4)
                if (
                    1000
                    <= struct.unpack_from("<I", image_entry.data, offset)[0]
                    < len(tiles)
                    and struct.unpack_from("<I", image_entry.data, offset + 4)[0] == 0
                )
            }
        )
        if not tile_indices:
            raise ValueError(f"{image_name!r} references no animation tiles")
        frame = render_tile(tiles[tile_indices[0]].data, palettes)
        scale = min(6, max(1, 150 // max(frame.size)))
        frame = frame.resize(
            (frame.width * scale, frame.height * scale),
            Image.Resampling.NEAREST,
        )
        x = column * card_width + (card_width - frame.width) // 2
        y = 20 + (150 - frame.height) // 2
        sheet.paste(frame, (x, y), frame)
        label = image_name.decode("ascii", errors="replace")
        draw.text((column * card_width + 8, 180), label, fill=(225, 235, 245))
        draw.text(
            (column * card_width + 8, 198),
            f"{len(tile_indices)} frame(s), first {tiles[tile_indices[0]].data[4:6].hex()}",
            fill=(145, 165, 185),
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(args.out)

    _, custom_tiles, custom_palettes = loaded["custom"]
    animation_specs = (
        (b"PHc1ChillTile", "chill-snowflake-animation-review.png"),
        (
            b"PHc3EmpChillTile",
            "empowered-chill-snowflake-animation-review.png",
        ),
    )
    for chill_prefix, output_name in animation_specs:
        chill_tiles = sorted(
            (
                entry
                for entry in custom_tiles
                if entry.name.rstrip(b"\x00").startswith(chill_prefix)
            ),
            key=lambda entry: int(
                entry.name.rstrip(b"\x00")[len(chill_prefix) :]
            ),
        )
        if not chill_tiles:
            continue
        frames = [render_tile(entry.data, custom_palettes) for entry in chill_tiles]
        scale = 4
        columns = 8
        cell_width = max(frame.width for frame in frames) * scale + 12
        cell_height = max(frame.height for frame in frames) * scale + 26
        rows = (len(frames) + columns - 1) // columns
        animation_sheet = Image.new(
            "RGB",
            (cell_width * columns, cell_height * rows),
            (22, 25, 32),
        )
        animation_draw = ImageDraw.Draw(animation_sheet)
        for frame_index, frame in enumerate(frames):
            frame = frame.resize(
                (frame.width * scale, frame.height * scale),
                Image.Resampling.NEAREST,
            )
            column = frame_index % columns
            row = frame_index // columns
            x = column * cell_width + (cell_width - frame.width) // 2
            y = row * cell_height + 4
            animation_sheet.paste(frame, (x, y), frame)
            animation_draw.text(
                (column * cell_width + 6, row * cell_height + cell_height - 18),
                f"frame {frame_index}",
                fill=(170, 190, 210),
            )
        animation_out = args.out.with_name(output_name)
        animation_sheet.save(animation_out)
        print(animation_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
