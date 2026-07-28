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


def numbered_frames(
    tiles: list[builder.CamEntry],
    palettes: list[builder.CamEntry],
    prefix: bytes,
    expected: int,
) -> list[Image.Image]:
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
    return [render_tile(entry.data, palettes) for entry in sequence]


def save_animation(frames: list[Image.Image], path: Path, duration: int) -> None:
    background = (18, 24, 34, 255)
    preview_frames: list[Image.Image] = []
    for frame in frames:
        preview = Image.new("RGBA", frame.size, background)
        preview.alpha_composite(frame)
        preview_frames.append(preview.convert("P", palette=Image.Palette.ADAPTIVE))
    preview_frames[0].save(
        path,
        save_all=True,
        append_images=preview_frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
    )


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
        / "artifacts/reviews/endless-winter-packaged-animation-review.png",
    )
    args = parser.parse_args()

    tiles = builder.read_cam_entries(args.cam, b"TILE")
    palettes = builder.read_cam_entries(args.cam, b"SPLT")
    vortex = numbered_frames(tiles, palettes, b"PHw1Storm", 15)
    hit = numbered_frames(tiles, palettes, b"PHw2Hit", 8)
    storm_flakes = numbered_frames(tiles, palettes, b"PHw4Flake", 13)
    missile_flakes = numbered_frames(tiles, palettes, b"PHw5Flake", 7)

    sheet = Image.new("RGB", (1120, 1040), (18, 24, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 14),
        "Endless Winter — decoded packaged animation phases",
        fill=(225, 238, 248),
    )
    draw.text(
        (18, 36),
        "Vortex: fixed-plane internal flow. Impact: fixed-base growth and vertical turn.",
        fill=(125, 170, 200),
    )

    for index, frame in enumerate(vortex):
        column = index % 5
        row = index // 5
        cell_left = column * 224
        cell_top = 70 + row * 205
        sheet.paste(frame, (cell_left + (224 - frame.width) // 2, cell_top), frame)
        draw.text(
            (cell_left + 8, cell_top + 168),
            f"vortex {index + 1:02d}",
            fill=(170, 198, 220),
        )

    for index, frame in enumerate(hit):
        column = index % 8
        cell_left = column * 140
        cell_top = 695
        enlarged = frame.resize(
            (frame.width * 1, frame.height * 1),
            Image.Resampling.NEAREST,
        )
        sheet.paste(
            enlarged,
            (
                cell_left + (140 - enlarged.width) // 2,
                cell_top + 105 - enlarged.height,
            ),
            enlarged,
        )
        draw.text(
            (cell_left + 8, 810),
            f"hit {index + 1:02d}",
            fill=(170, 198, 220),
        )

    draw.text(
        (18, 850),
        "Phantom-only replacement particles (stock XL20/XL21 removed)",
        fill=(225, 238, 248),
    )
    particle_frames = storm_flakes + missile_flakes
    for index, frame in enumerate(particle_frames):
        cell_left = index * 56
        enlarged = frame.resize(
            (frame.width * 2, frame.height * 2),
            Image.Resampling.NEAREST,
        )
        sheet.paste(
            enlarged,
            (
                cell_left + (56 - enlarged.width) // 2,
                878 + (110 - enlarged.height) // 2,
            ),
            enlarged,
        )
        label = (
            f"S{index + 1:02d}"
            if index < len(storm_flakes)
            else f"M{index - len(storm_flakes) + 1:02d}"
        )
        draw.text((cell_left + 10, 1004), label, fill=(170, 198, 220))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    save_animation(
        vortex,
        args.out.with_name("endless-winter-vortex-packaged.gif"),
        90,
    )
    save_animation(
        hit,
        args.out.with_name("endless-winter-hit-packaged.gif"),
        90,
    )
    save_animation(
        storm_flakes,
        args.out.with_name("endless-winter-storm-flakes-packaged.gif"),
        75,
    )
    save_animation(
        missile_flakes,
        args.out.with_name("endless-winter-missile-flakes-packaged.gif"),
        45,
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
