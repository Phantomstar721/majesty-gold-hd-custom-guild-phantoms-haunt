from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


MAGENTA = (255, 0, 255)
ACTIVE_FRAME_COUNT = 8

TILE_SPECS: dict[int, tuple[str, int, int]] = {
    1502: ("build_0", 301, 229),
    1503: ("build_1", 301, 229),
    1504: ("build_2", 301, 229),
    1505: ("inactive", 301, 229),
    1506: ("active_0", 301, 229),
    1508: ("destroyed", 283, 158),
    1529: ("damaged", 301, 229),
    1530: ("damaged", 301, 225),
    1531: ("destroyed", 301, 207),
}

BUILD_FRAME_DIMS: list[tuple[int, int, int]] = []

EMPTY_TILE_DIMS: dict[int, tuple[int, int]] = {
    **{tile_index: (115, 106) for tile_index in range(1511, 1517)},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--construction-sheet", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(args.sheet).convert("RGBA")
    variants = split_variants(sheet)
    construction_variants = (
        split_construction_variants(Image.open(args.construction_sheet).convert("RGBA"))
        if args.construction_sheet
        else {}
    )

    specs = dict(TILE_SPECS)
    for position, (tile_index, width, height) in enumerate(BUILD_FRAME_DIMS):
        progress = position / max(1, len(BUILD_FRAME_DIMS) - 1)
        if progress < 0.25:
            variant = "build_0"
        elif progress < 0.65:
            variant = "build_1"
        else:
            variant = "build_2"
        specs[tile_index] = (variant, width, height)

    for tile_index, (variant_name, width, height) in specs.items():
        image = render_variant(variants, variant_name, width, height, construction_variants)
        path_base = args.out_dir / f"building_tile_{tile_index:05d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.convert("RGB").tobytes())

    active_width = TILE_SPECS[1506][1]
    active_height = TILE_SPECS[1506][2]
    for frame_index in range(ACTIVE_FRAME_COUNT):
        image = render_variant(
            variants,
            f"active_{frame_index}",
            active_width,
            active_height,
            construction_variants,
        )
        path_base = args.out_dir / f"building_active_frame_{frame_index:02d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.convert("RGB").tobytes())

    for tile_index, (width, height) in EMPTY_TILE_DIMS.items():
        image = Image.new("RGB", (width, height), (0, 0, 0))
        path_base = args.out_dir / f"building_tile_{tile_index:05d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.tobytes())

    return 0


def split_variants(sheet: Image.Image) -> dict[str, Image.Image]:
    w, h = sheet.size
    cells = {
        "inactive": (0, 0, w // 2, h // 2),
        "active": (w // 2, 0, w, h // 2),
        "damaged": (0, h // 2, w // 2, h),
        "destroyed": (w // 2, h // 2, w, h),
    }
    return {name: crop_magenta(sheet.crop(box)) for name, box in cells.items()}


def split_construction_variants(sheet: Image.Image) -> dict[int, Image.Image]:
    w, h = sheet.size
    cell_w = w // 3
    variants: dict[int, Image.Image] = {}
    for stage in range(3):
        left = stage * cell_w
        right = w if stage == 2 else (stage + 1) * cell_w
        variants[stage] = crop_generated_magenta(sheet.crop((left, 0, right, h)))
    return variants


def crop_generated_magenta(image: Image.Image) -> Image.Image:
    """Remove the soft magenta background used by generated proof sheets."""
    pixels = image.load()
    bbox: tuple[int, int, int, int] | None = None
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0 or is_generated_magenta(red, green, blue):
                pixels[x, y] = (0, 0, 0, 0)
                continue
            if bbox is None:
                bbox = (x, y, x + 1, y + 1)
            else:
                left, top, right, bottom = bbox
                bbox = (min(left, x), min(top, y), max(right, x + 1), max(bottom, y + 1))
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return image.crop(bbox)


def crop_magenta(image: Image.Image) -> Image.Image:
    pixels = image.load()
    bbox: tuple[int, int, int, int] | None = None
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0 or is_magenta(red, green, blue):
                pixels[x, y] = (0, 0, 0, 0)
                continue
            if bbox is None:
                bbox = (x, y, x + 1, y + 1)
            else:
                left, top, right, bottom = bbox
                bbox = (min(left, x), min(top, y), max(right, x + 1), max(bottom, y + 1))
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    return image.crop(bbox)


def render_variant(
    variants: dict[str, Image.Image],
    variant_name: str,
    width: int,
    height: int,
    construction_variants: dict[int, Image.Image],
) -> Image.Image:
    if variant_name.startswith("build_"):
        stage = int(variant_name.rsplit("_", 1)[1])
        if stage in construction_variants:
            return render_construction_variant(construction_variants[stage], width, height)
        return render_build_stage(variants, stage, width, height)

    base_name = variant_name.split("_", 1)[0]
    source = prepare_building_source(variants[base_name])
    if variant_name.startswith("active_"):
        frame = int(variant_name.rsplit("_", 1)[1])
        pulse = 1.0 + 0.10 * math.sin((frame / 8.0) * math.tau)
        source = pulse_cyan(source, pulse)
    source = grade_for_ice_palette(source)

    target = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    margin_x = 3
    margin_y = 2
    scale = min((width - margin_x * 2) / source.width, (height - margin_y * 2) / source.height)
    scaled_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(scaled_size, Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    source = lift_dark_visible_pixels(source)
    x = (width - source.width) // 2
    x += state_x_offset(variant_name)
    y = height - source.height - margin_y
    target.alpha_composite(source, (x, y))
    scrub_purple_fringe(target)
    return target.convert("RGB")


def render_construction_variant(source: Image.Image, width: int, height: int) -> Image.Image:
    source = grade_for_ice_palette(source)
    target = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    margin_x = 2
    margin_y = 1
    scale = min((width - margin_x * 2) / source.width, (height - margin_y * 2) / source.height)
    scaled_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(scaled_size, Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    source = lift_dark_visible_pixels(source)
    x = (width - source.width) // 2
    y = height - source.height - margin_y
    target.alpha_composite(source, (x, y))
    scrub_purple_fringe(target)
    return target.convert("RGB")


def state_x_offset(variant_name: str) -> int:
    if variant_name == "inactive":
        return -18
    if variant_name.startswith("active_"):
        return 29
    return 0


def render_build_stage(variants: dict[str, Image.Image], stage: int, width: int, height: int) -> Image.Image:
    target = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    foundation = prepare_building_source(variants["destroyed"], widen=1.18)
    foundation = grade_for_ice_palette(foundation)
    foundation = ImageEnhance.Brightness(foundation).enhance(0.82)
    foundation = ImageEnhance.Contrast(foundation).enhance(0.82)
    composite_scaled(target, foundation, width, height, vertical_fill=0.76, y_offset=0)

    if stage > 0:
        partial = prepare_building_source(variants["damaged"], widen=1.18)
        partial = grade_for_ice_palette(partial)
        partial = reveal_bottom(partial, 0.34 if stage == 1 else 0.58, feather=18 if stage == 1 else 26)
        partial = ImageEnhance.Brightness(partial).enhance(0.80 if stage == 1 else 0.90)
        partial = ImageEnhance.Contrast(partial).enhance(0.92)
        composite_scaled(target, partial, width, height, vertical_fill=0.82 if stage == 1 else 0.90, y_offset=0)

    add_construction_beams(target, stage)
    scrub_purple_fringe(target)
    return target.convert("RGB")


def prepare_building_source(image: Image.Image, widen: float = 1.20) -> Image.Image:
    image = image.copy()
    if widen != 1.0:
        image = image.resize((max(1, int(image.width * widen)), image.height), Image.Resampling.LANCZOS)
    return image


def grade_for_ice_palette(image: Image.Image) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue

            luminance = 0.299 * red + 0.587 * green + 0.114 * blue
            saturation = max(red, green, blue) - min(red, green, blue)
            icy_light = blue > 145 and green > 125 and blue > red * 1.2 and luminance > 150
            magic_flame = red > 145 and blue > 130 and green < 85 and luminance > 120
            roof = blue > red * 1.08 and blue > green * 1.06 and luminance < 120 and saturation > 18

            if icy_light:
                pixels[x, y] = (
                    min(255, int(22 + luminance * 0.18)),
                    min(255, int(150 + luminance * 0.46)),
                    min(255, int(205 + luminance * 0.32)),
                    alpha,
                )
            elif magic_flame:
                pixels[x, y] = (
                    min(150, int(18 + luminance * 0.18)),
                    min(230, int(118 + luminance * 0.44)),
                    min(255, int(196 + luminance * 0.30)),
                    alpha,
                )
            elif roof:
                pixels[x, y] = (
                    max(3, int(luminance * 0.16)),
                    max(12, int(luminance * 0.35)),
                    max(34, int(luminance * 0.82)),
                    alpha,
                )
            elif luminance < 72:
                pixels[x, y] = (
                    max(8, int(red * 0.70 + luminance * 0.10)),
                    max(10, int(green * 0.70 + luminance * 0.12)),
                    max(14, int(blue * 0.70 + luminance * 0.16)),
                    alpha,
                )
            elif luminance < 145:
                pixels[x, y] = (
                    min(150, int(red * 0.72 + luminance * 0.20)),
                    min(160, int(green * 0.72 + luminance * 0.20)),
                    min(175, int(blue * 0.72 + luminance * 0.24)),
                    alpha,
                )
            else:
                pixels[x, y] = (
                    min(210, int(red * 0.72 + luminance * 0.22)),
                    min(220, int(green * 0.72 + luminance * 0.22)),
                    min(235, int(blue * 0.72 + luminance * 0.24)),
                    alpha,
                )
    return ImageEnhance.Contrast(image).enhance(1.03)


def composite_scaled(
    target: Image.Image,
    source: Image.Image,
    width: int,
    height: int,
    *,
    vertical_fill: float,
    y_offset: int,
) -> None:
    margin_x = 1
    margin_y = 2
    scale = min((width - margin_x * 2) / source.width, ((height - margin_y * 2) * vertical_fill) / source.height)
    scaled_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(scaled_size, Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    source = lift_dark_visible_pixels(source)
    x = (width - source.width) // 2
    y = height - source.height - margin_y + y_offset
    target.alpha_composite(source, (x, y))


def reveal_bottom(image: Image.Image, fraction: float, feather: int) -> Image.Image:
    image = image.copy()
    cutoff = int(image.height * (1.0 - fraction))
    alpha = image.getchannel("A")
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    alpha_pixels = alpha.load()
    for y in range(cutoff - feather, image.height):
        if y < 0:
            continue
        if y < cutoff:
            fade = (y - (cutoff - feather)) / max(1, feather)
        else:
            fade = 1.0
        for x in range(image.width):
            mask_pixels[x, y] = int(alpha_pixels[x, y] * fade)
    image.putalpha(mask)
    return image


def add_construction_beams(image: Image.Image, stage: int) -> None:
    pixels = image.load()
    width, height = image.size
    beam = (142, 86, 48, 255)
    highlight = (196, 132, 78, 255)
    y_base = height - (46 if stage == 0 else 42)
    x_left = 42
    x_right = width - 44
    for x in range(x_left, x_right):
        for dy in range(3):
            pixels[x, y_base + dy] = beam
    for x in range(x_left + 18, x_right - 16):
        y = y_base - int((x - x_left) * 0.22)
        for dy in range(3):
            if 0 <= y + dy < height:
                pixels[x, y + dy] = highlight
    if stage >= 1:
        for x in range(width // 2 - 48, width // 2 + 48):
            y = y_base - 34 + int(abs(x - width // 2) * 0.32)
            for dy in range(3):
                if 0 <= y + dy < height:
                    pixels[x, y + dy] = beam


def pulse_cyan(image: Image.Image, pulse: float) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            if blue > red * 1.2 and green > red * 1.1:
                pixels[x, y] = (
                    min(255, int(red * pulse)),
                    min(255, int(green * pulse)),
                    min(255, int(blue * pulse)),
                    alpha,
                )
    return ImageEnhance.Contrast(image).enhance(1.04)


def lift_dark_visible_pixels(image: Image.Image) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            pixels[x, y] = (max(12, red), max(13, green), max(18, blue), alpha)
    return image


def scrub_purple_fringe(image: Image.Image) -> None:
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            if red > 95 and blue > 95 and green < max(88, min(red, blue) * 0.72):
                luminance = 0.299 * red + 0.587 * green + 0.114 * blue
                if luminance < 80:
                    pixels[x, y] = (18, 42, 56, alpha)
                else:
                    pixels[x, y] = (
                        min(120, int(18 + luminance * 0.20)),
                        min(210, int(92 + luminance * 0.48)),
                        min(245, int(154 + luminance * 0.38)),
                        alpha,
                    )


def is_magenta(red: int, green: int, blue: int) -> bool:
    return abs(red - MAGENTA[0]) < 20 and green < 35 and abs(blue - MAGENTA[2]) < 20


def is_generated_magenta(red: int, green: int, blue: int) -> bool:
    return red > 170 and blue > 140 and green < 115 and red > green * 2.2 and blue > green * 1.8


if __name__ == "__main__":
    raise SystemExit(main())
