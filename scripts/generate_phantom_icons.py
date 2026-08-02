from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    write_image_icon(
        args.out_dir / "phantom_hero_icon_25",
        render_hero_icon(repo_root / "assets" / "source" / "hero" / "portrait.png"),
    )
    write_image_icon(args.out_dir / "phantom_guild_icon_25", render_guild_icon())
    return 0


def write_image_icon(path_base: Path, image: Image.Image) -> None:
    image = image.convert("RGB")
    image.save(path_base.with_suffix(".png"))
    path_base.with_suffix(".rgb").write_bytes(image.tobytes())


def render_hero_icon(portrait_path: Path) -> Image.Image:
    source = Image.open(portrait_path).convert("RGB")
    width, height = source.size
    # Tight face-and-hood crop, matching retail hero icons more than a symbolic glyph.
    crop = source.crop(
        (
            int(width * 0.14),
            int(height * 0.06),
            int(width * 0.86),
            int(height * 0.81),
        )
    )
    crop = crop.resize((34, 34), Image.Resampling.LANCZOS)
    crop = crop.filter(ImageFilter.SMOOTH_MORE)
    crop = crop.resize((25, 25), Image.Resampling.LANCZOS)
    crop = ImageEnhance.Contrast(crop).enhance(1.30)
    crop = ImageEnhance.Color(crop).enhance(1.08)
    crop = ImageEnhance.Sharpness(crop).enhance(1.55)
    crop = posterize_to_majesty_icon(crop, levels=34)

    overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, 24, 24), outline=(8, 10, 14, 255))
    draw.polygon([(0, 0), (6, 0), (3, 23), (0, 24)], fill=(0, 3, 12, 80))
    draw.polygon([(24, 0), (18, 0), (22, 24), (24, 24)], fill=(0, 3, 12, 80))
    return Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")


def render_guild_icon() -> Image.Image:
    canvas = Image.new("RGBA", (25, 25), (7, 18, 46, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(25):
        red = int(7 + y * 0.35)
        green = int(18 + y * 0.75)
        blue = int(46 + y * 1.65)
        draw.line((0, y, 24, y), fill=(red, green, blue, 255))

    draw.rectangle((0, 0, 24, 24), outline=(56, 238, 255, 255))
    draw.rectangle((1, 1, 23, 23), outline=(7, 72, 105, 255))
    draw.point((1, 1), fill=(225, 255, 255, 255))
    draw.point((23, 1), fill=(96, 235, 255, 255))
    draw.point((1, 23), fill=(96, 235, 255, 255))
    draw.point((23, 23), fill=(225, 255, 255, 255))

    # Retail-style emblem: bold skull silhouette with icy cyan highlights.
    draw.ellipse((5, 3, 19, 17), fill=(22, 166, 198, 255), outline=(130, 236, 250, 255))
    draw.rectangle((8, 14, 16, 21), fill=(18, 144, 178, 255), outline=(86, 218, 238, 255))

    draw.ellipse((7, 8, 11, 12), fill=(1, 7, 20, 255))
    draw.ellipse((14, 8, 18, 12), fill=(1, 7, 20, 255))
    draw.polygon([(12, 11), (10, 15), (14, 15)], fill=(3, 13, 30, 255))
    draw.line((9, 18, 15, 18), fill=(2, 17, 33, 255))
    for x in (10, 12, 14):
        draw.line((x, 17, x, 21), fill=(148, 238, 248, 255))

    draw.arc((4, 2, 20, 20), 205, 335, fill=(74, 210, 234, 255), width=1)
    draw.point((7, 5), fill=(205, 255, 255, 255))
    draw.point((17, 5), fill=(205, 255, 255, 255))
    draw.point((12, 3), fill=(230, 255, 255, 255))
    return posterize_to_majesty_icon(canvas.convert("RGB"), levels=44)


def posterize_to_majesty_icon(image: Image.Image, levels: int) -> Image.Image:
    image = image.convert("RGB")
    pixels = image.load()
    step = max(1, 256 // levels)
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue = pixels[x, y]
            pixels[x, y] = (
                min(255, (red // step) * step),
                min(255, (green // step) * step),
                min(255, (blue // step) * step),
            )
    return image


if __name__ == "__main__":
    raise SystemExit(main())
