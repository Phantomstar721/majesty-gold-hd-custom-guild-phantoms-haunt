from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "dist/temp/building_sprites"
OUTPUT = ROOT / "artifacts/reviews/phantom-construction-current-frames.png"
FRAMES = (
    (1502, "CONSTRUCTION 1"),
    (1503, "CONSTRUCTION 2"),
    (1504, "CONSTRUCTION 3"),
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/consola.ttf"), Path("C:/Windows/Fonts/segoeui.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def main() -> int:
    scale = 2
    cell_width = 650
    cell_height = 560
    card = Image.new("RGB", (cell_width * len(FRAMES), cell_height), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    for column, (tile_index, label) in enumerate(FRAMES):
        frame = Image.open(SOURCE_DIR / f"building_tile_{tile_index:05d}.png").convert("RGBA")
        frame = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        x = column * cell_width + (cell_width - frame.width) // 2
        y = 16
        card.paste(frame, (x, y), frame)
        draw.text(
            (column * cell_width + 18, 490),
            f"{label} — TILE {tile_index}",
            font=font(23),
            fill=(220, 230, 240),
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT, optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
