from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/hero/sprite-actions.png"
OUTPUT = ROOT / "artifacts/reviews/phantom-hero-actions-review.png"

LABELS = (
    ("1 — IDLE / STAND", "spectral hover"),
    ("2 — MOVEMENT", "forward floating glide"),
    ("3 — STAFF ATTACK", "narrow ice lance"),
    ("4 — SPELL CAST", "swirling hand vortex"),
    ("5 — SPECIAL / CHANNEL", "ground frost eruption"),
    ("6 — DEATH / DISSOLVE", "mist and shard dissolve"),
)

CARD_SIZE = (1700, 1450)
PANEL_SIZE = (560, 555)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def key_magenta(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            if red > 185 and blue > 165 and green < 105 and red > green * 2:
                pixels[x, y] = (0, 0, 0, 0)
    return image


def remove_magenta(image: Image.Image) -> Image.Image:
    image = key_magenta(image)
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else Image.new("RGBA", (1, 1))


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = min(size[0] / image.width, size[1] / image.height)
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def stock_scale_preview(image: Image.Image) -> Image.Image:
    tiny = fit(image, (34, 42))
    tiny = tiny.resize((tiny.width * 4, tiny.height * 4), Image.Resampling.NEAREST)
    preview = Image.new("RGBA", (160, 190), (12, 15, 20, 255))
    preview.alpha_composite(
        tiny,
        ((preview.width - tiny.width) // 2, 8 + (160 - tiny.height) // 2),
    )
    draw = ImageDraw.Draw(preview)
    draw.text((10, 168), "≈34×42 px • 4×", font=font(16), fill=(151, 171, 193))
    return preview


def main() -> int:
    source = key_magenta(Image.open(SOURCE))
    cell_width = source.width // 3
    cell_height = source.height // 2
    card = Image.new("RGB", CARD_SIZE, (20, 24, 31))
    draw = ImageDraw.Draw(card)
    draw.text((55, 25), "PHANTOM HERO — MAJOR ACTION PREVIEW V3", font=font(48), fill=(235, 241, 248))
    draw.text(
        (57, 82),
        "Ice-phantom redesign • concept and effect approval before directional frame rendering",
        font=font(24),
        fill=(146, 164, 184),
    )

    image_x = (CARD_SIZE[0] - source.width) // 2
    row_positions = (125, 745)
    for row, row_y in enumerate(row_positions):
        if row == 0:
            row_image = source.crop((0, 0, source.width, cell_height))
            row_draw = ImageDraw.Draw(row_image)
            row_draw.rectangle((660, 448, 758, cell_height), fill=(0, 0, 0, 0))
        else:
            overlap = 72
            row_image = source.crop((0, cell_height - overlap, source.width, source.height))
            staff_overlap = source.crop((660, cell_height - overlap, 758, cell_height))
            row_draw = ImageDraw.Draw(row_image)
            row_draw.rectangle((0, 0, source.width, overlap), fill=(0, 0, 0, 0))
            row_image.alpha_composite(staff_overlap, (660, 0))
        card.paste(row_image, (image_x, row_y), row_image)

        label_y = row_y + row_image.height + 8
        draw.rectangle((image_x, label_y, image_x + source.width, label_y + 78), fill=(20, 24, 31))
        for column in range(3):
            label, note = LABELS[row * 3 + column]
            label_x = image_x + column * cell_width + 12
            draw.text((label_x, label_y + 4), label, font=font(24), fill=(235, 241, 248))
            draw.text((label_x, label_y + 38), note, font=font(18), fill=(146, 164, 184))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT, optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
