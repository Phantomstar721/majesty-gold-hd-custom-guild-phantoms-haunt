from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHEET = ROOT / "assets/source/phantom-guild-sprite-sheet-smooth.png"
DAMAGED_B = ROOT / "assets/source/phantom-guild-damaged-b-sample-v1.png"
COLLAPSED = ROOT / "assets/source/phantom-guild-collapsed-intermediate-sample-v1.png"
OUTPUT = ROOT / "artifacts/reviews/phantom-guild-destruction-progression-hires-v1.png"

CARD_SIZE = (2800, 2200)
PANEL_SIZE = (1320, 835)
PANEL_BACKGROUND = (255, 0, 255)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def subject_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    pixels = image.convert("RGB")
    mask = Image.new("1", image.size)
    mask_pixels = mask.load()
    source_pixels = pixels.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = source_pixels[x, y]
            is_magenta = red > 205 and blue > 170 and green < 85 and red > green * 2.4
            mask_pixels[x, y] = not is_magenta
    return mask.getbbox() or (0, 0, image.width, image.height)


def fit_on_panel(image: Image.Image) -> Image.Image:
    cropped = image.convert("RGB").crop(subject_bounds(image))
    margin = 35
    scale = min(
        (PANEL_SIZE[0] - margin * 2) / cropped.width,
        (PANEL_SIZE[1] - margin * 2) / cropped.height,
    )
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.Resampling.LANCZOS,
    )
    panel = Image.new("RGB", PANEL_SIZE, PANEL_BACKGROUND)
    panel.paste(
        resized,
        ((PANEL_SIZE[0] - resized.width) // 2, (PANEL_SIZE[1] - resized.height) // 2),
    )
    return panel


def main() -> int:
    sheet = Image.open(SOURCE_SHEET).convert("RGB")
    half_width = sheet.width // 2
    half_height = sheet.height // 2
    damaged_a = sheet.crop((0, half_height, half_width, sheet.height))
    final_rubble = sheet.crop((half_width, half_height, sheet.width, sheet.height))

    frames = (
        ("1 — DAMAGED A", "existing source • tile 1529", damaged_a),
        ("2 — DAMAGED B", "new transitional sample • tile 1530", Image.open(DAMAGED_B)),
        (
            "3 — COLLAPSED INTERMEDIATE",
            "new transitional sample • tile 1531",
            Image.open(COLLAPSED),
        ),
        ("4 — FINAL RUBBLE", "existing source • tile 1508", final_rubble),
    )

    card = Image.new("RGB", CARD_SIZE, (20, 24, 31))
    draw = ImageDraw.Draw(card)
    draw.text((70, 35), "PHANTOM GUILD — DESTRUCTION PROGRESSION", font=font(54), fill=(235, 241, 248))
    draw.text(
        (72, 100),
        "Fervus-compatible four-stage proposal • high-resolution source review",
        font=font(28),
        fill=(146, 164, 184),
    )

    positions = ((60, 205), (1420, 205), (60, 1200), (1420, 1200))
    for (title, subtitle, image), (x, y) in zip(frames, positions):
        draw.rounded_rectangle(
            (x - 4, y - 4, x + PANEL_SIZE[0] + 4, y + PANEL_SIZE[1] + 4),
            radius=14,
            fill=(77, 88, 103),
        )
        card.paste(fit_on_panel(image), (x, y))
        draw.text((x + 8, y + PANEL_SIZE[1] + 16), title, font=font(31), fill=(235, 241, 248))
        draw.text(
            (x + 8, y + PANEL_SIZE[1] + 58),
            subtitle,
            font=font(23),
            fill=(146, 164, 184),
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUTPUT, optimize=True)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
