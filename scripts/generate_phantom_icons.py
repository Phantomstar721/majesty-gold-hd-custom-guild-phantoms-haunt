from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_icon(args.out_dir / "phantom_hero_icon_25", (25, 25), draw_hero)
    write_icon(args.out_dir / "phantom_guild_icon_25", (25, 25), draw_guild)
    write_icon(args.out_dir / "ice_lance_icon_29", (29, 29), draw_ice_lance)
    write_icon(args.out_dir / "ice_lance_spell_icon_24", (24, 24), draw_ice_lance)
    write_icon(args.out_dir / "frost_armor_spell_icon_24", (24, 24), draw_frost_armor)
    write_icon(args.out_dir / "blizzard_spell_icon_24", (24, 24), draw_blizzard)
    write_icon(args.out_dir / "phantom_cowl_icon_23", (23, 23), draw_cowl)
    write_icon(args.out_dir / "dark_staff_icon_16", (16, 16), draw_dark_staff)
    write_icon(args.out_dir / "dark_staff_icon_23", (23, 23), draw_dark_staff)
    write_icon(args.out_dir / "dark_staff_icon_50x19", (50, 19), draw_dark_staff)
    return 0


def write_icon(path_base: Path, size: tuple[int, int], drawer) -> None:
    image = Image.new("RGB", size, (3, 4, 8))
    draw_border(ImageDraw.Draw(image), size)
    drawer(ImageDraw.Draw(image), size)
    image.save(path_base.with_suffix(".png"))
    path_base.with_suffix(".rgb").write_bytes(image.tobytes())


def draw_border(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.rectangle((0, 0, w - 1, h - 1), outline=(235, 190, 74))
    draw.rectangle((1, 1, w - 2, h - 2), outline=(90, 59, 22))
    draw.point((1, 1), fill=(255, 235, 128))
    draw.point((w - 2, 1), fill=(255, 235, 128))
    draw.point((1, h - 2), fill=(255, 235, 128))
    draw.point((w - 2, h - 2), fill=(255, 235, 128))


def draw_hero(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    cx = w // 2
    draw.polygon(
        [(cx, 3), (w - 6, 9), (w - 7, h - 4), (cx, h - 2), (6, h - 4), (5, 9)],
        fill=(26, 24, 56),
        outline=(83, 172, 230),
    )
    draw.polygon([(cx, 5), (w - 9, 10), (cx + 3, h - 7), (cx, h - 4), (cx - 3, h - 7), (8, 10)],
                 fill=(8, 12, 28), outline=(160, 225, 255))
    draw.line((cx, 7, cx, h - 6), fill=(108, 238, 255))
    draw.line((cx - 4, 13, cx + 4, 13), fill=(197, 247, 255))
    draw.point((cx - 3, 12), fill=(255, 255, 255))
    draw.point((cx + 3, 12), fill=(255, 255, 255))
    draw.arc((5, 4, w - 6, h - 3), 205, 335, fill=(42, 222, 255), width=1)


def draw_guild(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.polygon([(4, h - 4), (8, 9), (12, 4), (17, 9), (21, h - 4)], fill=(23, 35, 48), outline=(88, 220, 255))
    draw.line((12, 4, 12, h - 5), fill=(226, 243, 255))
    draw.rectangle((8, 14, 16, h - 4), fill=(8, 11, 20), outline=(214, 177, 78))
    draw.arc((6, 8, 19, h - 1), 205, 335, fill=(54, 231, 255), width=1)
    draw.line((5, h - 5, w - 6, h - 5), fill=(236, 199, 86))
    draw.point((6, 8), fill=(255, 255, 255))
    draw.point((18, 8), fill=(255, 255, 255))


def draw_ice_lance(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.line((5, h - 6, w - 5, 5), fill=(55, 118, 162), width=5)
    draw.line((5, h - 6, w - 5, 5), fill=(95, 230, 255), width=3)
    draw.line((6, h - 7, w - 6, 6), fill=(245, 255, 255), width=1)
    draw.polygon([(w - 4, 3), (w - 8, 11), (w - 12, 7)], fill=(232, 255, 255), outline=(98, 227, 255))
    draw.line((6, h - 5, 12, h - 11), fill=(235, 190, 74))
    draw.point((8, 6), fill=(255, 255, 255))
    draw.point((14, 4), fill=(98, 227, 255))
    draw.point((20, 16), fill=(98, 227, 255))


def draw_frost_armor(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.polygon(
        [(w // 2, 3), (w - 5, 8), (w - 7, h - 6), (w // 2, h - 3), (6, h - 6), (5, 8)],
        fill=(13, 26, 44),
        outline=(95, 232, 255),
    )
    draw.line((w // 2, 5, w // 2, h - 6), fill=(236, 255, 255))
    draw.line((8, 10, w - 8, 10), fill=(87, 196, 255))
    draw.point((7, 5), fill=(255, 255, 255))
    draw.point((w - 6, 5), fill=(124, 231, 255))


def draw_blizzard(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    cx = w // 2
    cy = h // 2
    for angle in (0, 45, 90, 135):
        if angle == 0:
            draw.line((4, cy, w - 5, cy), fill=(112, 232, 255), width=2)
        elif angle == 45:
            draw.line((6, h - 6, w - 7, 5), fill=(86, 182, 244), width=2)
        elif angle == 90:
            draw.line((cx, 4, cx, h - 5), fill=(232, 255, 255), width=2)
        else:
            draw.line((6, 5, w - 7, h - 6), fill=(86, 182, 244), width=2)
    draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(236, 255, 255), outline=(52, 189, 255))
    draw.point((5, 6), fill=(255, 255, 255))
    draw.point((w - 6, h - 7), fill=(255, 255, 255))


def draw_cowl(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    cx = w // 2
    draw.polygon(
        [(cx, 3), (w - 5, 9), (w - 7, h - 4), (cx, h - 2), (5, h - 4), (4, 9)],
        fill=(17, 18, 44),
        outline=(95, 223, 255),
    )
    draw.polygon([(cx, 6), (w - 8, 11), (cx + 3, h - 7), (cx - 3, h - 7), (7, 11)],
                 fill=(3, 5, 13), outline=(149, 237, 255))
    draw.arc((4, 3, w - 5, h - 2), 205, 335, fill=(232, 197, 86), width=1)


def draw_dark_staff(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.line((5, h - 4, w - 12, 4), fill=(65, 41, 82), width=5)
    draw.line((6, h - 5, w - 13, 5), fill=(132, 232, 255), width=2)
    draw.ellipse((w - 15, 1, w - 5, 11), outline=(235, 197, 86), fill=(8, 13, 29))
    draw.line((w - 13, 6, w - 7, 6), fill=(145, 238, 255))
    draw.line((w - 10, 3, w - 10, 9), fill=(235, 255, 255))
    draw.point((13, 6), fill=(255, 255, 255))


if __name__ == "__main__":
    raise SystemExit(main())
