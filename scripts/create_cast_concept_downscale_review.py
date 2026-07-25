import argparse
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "assets/source/phantom-cast-ice-thread-concepts-v1.png"
DEFAULT_OUTPUT = ROOT / "artifacts/reviews/phantom-cast-ice-thread-game-size-review.png"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGBA")
    cell_width = source.width // 2
    cell_height = source.height // 2
    cards: list[Image.Image] = []

    for index in range(4):
        left = (index % 2) * cell_width
        top = (index // 2) * cell_height
        cell = source.crop((left, top, left + cell_width, top + cell_height))

        # The generated concept uses magenta behind cyan/white effects. Retain
        # only cold bright pixels for a useful sprite-scale readability test.
        alpha = Image.new("L", cell.size, 0)
        alpha_pixels = alpha.load()
        for y in range(cell.height):
            for x in range(cell.width):
                red, green, blue, _old_alpha = cell.getpixel((x, y))
                if green > 70 and blue > 150 and blue >= red * 0.65:
                    alpha_pixels[x, y] = min(255, max(0, (green - 55) * 2))
        cell.putalpha(alpha)

        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"Concept {index} has no readable cyan subject")
        effect = cell.crop(bbox)
        side = max(effect.width, effect.height)
        padded = Image.new("RGBA", (side + 24, side + 24), (0, 0, 0, 0))
        padded.alpha_composite(
            effect,
            ((padded.width - effect.width) // 2, (padded.height - effect.height) // 2),
        )
        tiny = padded.resize((18, 18), Image.Resampling.LANCZOS)
        enlarged = tiny.resize((288, 288), Image.Resampling.NEAREST)

        card = Image.new("RGBA", (320, 350), (14, 20, 29, 255))
        card.alpha_composite(enlarged, (16, 16))
        ImageDraw.Draw(card).text(
            (16, 318),
            f"{chr(ord('A') + index)} — 18 px simulation",
            fill=(220, 232, 244, 255),
        )
        cards.append(card)

    review = Image.new("RGBA", (640, 700), (14, 20, 29, 255))
    for index, card in enumerate(cards):
        review.alpha_composite(card, ((index % 2) * 320, (index // 2) * 350))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    review.convert("RGB").save(args.output, optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
