from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402
from create_phantom_hero_death_review import font, render_tile, tile_hotspot  # noqa: E402


def main() -> int:
    cam = ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam"
    output_path = ROOT / "artifacts/reviews/phantom-directional-death-engine-review.png"
    tiles = builder.read_cam_entries(cam, b"TILE")
    palettes = builder.read_cam_entries(cam, b"SPLT")
    by_name = {entry.name.rstrip(b"\x00"): entry for entry in tiles}

    scale = 3
    cell_width = 330
    cell_height = 290
    card = Image.new("RGB", (cell_width * 3, cell_height * 8), (18, 22, 28))
    draw = ImageDraw.Draw(card)

    for direction in range(8):
        for stage in range(3):
            source_tile = 4722 + direction * 3 + stage
            name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
            tile = by_name[name].data
            frame = render_tile(tile, palettes)
            hotspot_x, hotspot_y = tile_hotspot(tile)
            frame = frame.resize(
                (frame.width * scale, frame.height * scale),
                Image.Resampling.NEAREST,
            )

            cell_left = stage * cell_width
            cell_top = direction * cell_height
            world_x = cell_left + cell_width // 2
            world_y = cell_top + 205
            draw.line(
                (cell_left + 15, world_y, cell_left + cell_width - 15, world_y),
                fill=(55, 68, 82),
            )
            draw.line(
                (world_x, cell_top + 10, world_x, cell_top + 230),
                fill=(55, 68, 82),
            )
            card.paste(
                frame,
                (world_x - hotspot_x * scale, world_y - hotspot_y * scale),
                frame,
            )
            draw.text(
                (cell_left + 12, cell_top + 245),
                f"D{direction}  PHASE {stage + 1}  TILE {source_tile}",
                font=font(16),
                fill=(220, 230, 240),
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(output_path, optimize=True)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
