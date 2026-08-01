from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "external" / "BrandonWill-Majesty"))

import build_phantom_guild as builder  # noqa: E402
import sprite_extractor as extractor  # noqa: E402
from create_phantom_hero_engine_review import font, render_tile  # noqa: E402


CAM = ROOT / "dist/CustomGuildPhantomsHaunt/Data/phantom_maindata.cam"
OUTPUT = ROOT / "artifacts/reviews/phantom-hero-walk-engine-review.png"


def main() -> int:
    tiles = builder.read_cam_entries(CAM, b"TILE")
    palettes = builder.read_cam_entries(CAM, b"SPLT")
    image = builder.read_cam_entry(CAM, b"IMAG", b"PHM1Phantom").data
    image_sets = extractor.parse_anim_set(image)[1]
    walk = next(entry for entry in image_sets if entry["setName"] == "Walk")
    directions = extractor.parse_directional_frame_descriptor(image, walk["relOff"])["directions"]

    scale = 4
    cell_width = 250
    cell_height = 330
    card = Image.new("RGB", (cell_width * 8, cell_height * 6), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    for row, direction in enumerate(directions):
        tile_indices = [direction["tile_indices"][0] - 1, *direction["tile_indices"]]
        for column, tile_index in enumerate(tile_indices):
            frame = render_tile(tiles[tile_index].data, palettes)
            frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
            x = column * cell_width + (cell_width - frame.width) // 2
            y = row * cell_height + 5 + (270 - frame.height) // 2
            card.paste(frame, (x, y), frame)
            draw.text(
                (column * cell_width + 10, row * cell_height + 292),
                f"D{direction['slot']} {'H' if column == 0 else f'F{column - 1}'} T{tile_index}",
                font=font(17),
                fill=(220, 230, 240),
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT, optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
