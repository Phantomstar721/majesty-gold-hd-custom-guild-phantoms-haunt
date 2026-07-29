from __future__ import annotations

import argparse
import math
from collections import deque
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


MAGENTA = (255, 0, 255)
ACTIVE_FRAME_COUNT = 8
SHADOW_MARKERS = {
    247: (156, 33, 24, 255),
    248: (178, 0, 178, 255),
    249: (204, 0, 204, 255),
    250: (229, 0, 229, 255),
}
# Keep the finished-building projection extending toward the upper-left in
# sprite coordinates, matching Majesty's light source over the viewer's right
# shoulder, while fitting the complete shadow inside the reduced Haunt TILE.
SHADOW_SHEAR = 0.45
SHADOW_VERTICAL_SCALE = 0.75
MAX_SHADOW_BODY_GAP = 14
SHADOW_PROFILES: dict[str, tuple[float, float]] = {
    # shear controls leftward reach; vertical scale controls how far the
    # silhouette is laid down toward the ground. Low construction/rubble
    # states must not cast the tower-length shadow of the finished guild.
    "build_0": (0.10, 0.94),
    "build_1": (0.27, 0.87),
    "build_2": (0.43, 0.80),
    "inactive": (SHADOW_SHEAR, SHADOW_VERTICAL_SCALE),
    "active": (SHADOW_SHEAR, SHADOW_VERTICAL_SCALE),
    "damaged": (0.47, 0.79),
    "damaged_b": (0.43, 0.81),
    "collapsed_intermediate": (0.27, 0.88),
    "destroyed": (0.12, 0.92),
}

TILE_SPECS_BY_LEVEL: dict[int, dict[int, tuple[str, int, int]]] = {
    1: {
        1502: ("build_0", 276, 229),
        1503: ("build_1", 276, 229),
        1504: ("build_2", 276, 229),
        1505: ("inactive", 276, 229),
        1506: ("active_0", 276, 229),
        1508: ("destroyed", 260, 158),
        1529: ("damaged", 276, 229),
        1530: ("damaged_b", 276, 225),
        1531: ("collapsed_intermediate", 276, 207),
    },
    2: {
        1558: ("build_0", 276, 250),
        1559: ("build_2", 276, 250),
        1561: ("inactive", 276, 250),
        1562: ("active_0", 276, 250),
        1508: ("destroyed", 260, 165),
        1532: ("damaged", 276, 242),
        1533: ("damaged_b", 276, 224),
        1534: ("collapsed_intermediate", 276, 204),
    },
    3: {
        1563: ("build_0", 276, 275),
        1564: ("build_2", 276, 275),
        1565: ("inactive", 276, 275),
        1566: ("active_0", 276, 275),
        1508: ("destroyed", 260, 170),
        1535: ("damaged", 276, 265),
        1536: ("damaged_b", 276, 242),
        1537: ("collapsed_intermediate", 276, 218),
    },
}

BUILD_FRAME_DIMS: list[tuple[int, int, int]] = []

EMPTY_TILE_DIMS_BY_LEVEL: dict[int, dict[int, tuple[int, int]]] = {
    1: {tile_index: (115, 106) for tile_index in range(1511, 1517)},
    2: {tile_index: (115, 106) for tile_index in range(1517, 1523)},
    3: {tile_index: (115, 106) for tile_index in range(1523, 1529)},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--level", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--active-source", type=Path)
    parser.add_argument("--damaged-source", type=Path)
    parser.add_argument("--destroyed-source", type=Path)
    parser.add_argument("--construction-sheet", type=Path)
    parser.add_argument("--construction-early-source", type=Path)
    parser.add_argument("--construction-late-source", type=Path)
    parser.add_argument("--damaged-b-sample", required=True, type=Path)
    parser.add_argument("--collapsed-intermediate-sample", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(args.sheet).convert("RGBA")
    if args.level == 1:
        variants = split_variants(sheet)
    else:
        if not args.active_source or not args.damaged_source or not args.destroyed_source:
            parser.error(
                "levels 2 and 3 require --active-source, --damaged-source, "
                "and --destroyed-source"
            )
        active = crop_generated_magenta(
            Image.open(args.active_source).convert("RGBA")
        )
        damaged = crop_generated_magenta(
            Image.open(args.damaged_source).convert("RGBA")
        )
        destroyed = crop_generated_magenta(
            Image.open(args.destroyed_source).convert("RGBA")
        )
        variants = {
            "inactive": deactivate_spectral_lights(active),
            "active": active,
            "damaged": damaged,
            "destroyed": destroyed,
        }
    variants["damaged_b"] = crop_generated_magenta(
        Image.open(args.damaged_b_sample).convert("RGBA")
    )
    variants["collapsed_intermediate"] = crop_generated_magenta(
        Image.open(args.collapsed_intermediate_sample).convert("RGBA")
    )
    construction_variants = (
        split_construction_variants(Image.open(args.construction_sheet).convert("RGBA"))
        if args.construction_sheet
        else {}
    )
    if args.construction_early_source:
        construction_variants[0] = crop_generated_magenta(
            Image.open(args.construction_early_source).convert("RGBA")
        )
    if args.construction_late_source:
        construction_variants[2] = crop_generated_magenta(
            Image.open(args.construction_late_source).convert("RGBA")
        )

    specs = dict(TILE_SPECS_BY_LEVEL[args.level])
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
        image = render_variant(
            variants,
            variant_name,
            width,
            height,
            construction_variants,
            level=args.level,
        )
        path_base = args.out_dir / f"building_tile_{tile_index:05d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.convert("RGB").tobytes())

    active_spec = next(
        spec for spec in specs.values() if spec[0] == "active_0"
    )
    active_width = active_spec[1]
    active_height = active_spec[2]
    for frame_index in range(ACTIVE_FRAME_COUNT):
        image = render_variant(
            variants,
            f"active_{frame_index}",
            active_width,
            active_height,
            construction_variants,
            level=args.level,
        )
        path_base = args.out_dir / f"building_active_frame_{frame_index:02d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.convert("RGB").tobytes())

    for tile_index, (width, height) in EMPTY_TILE_DIMS_BY_LEVEL[args.level].items():
        image = Image.new("RGB", (width, height), (0, 0, 0))
        path_base = args.out_dir / f"building_tile_{tile_index:05d}"
        image.save(path_base.with_suffix(".png"))
        path_base.with_suffix(".rgb").write_bytes(image.tobytes())

    return 0


def deactivate_spectral_lights(image: Image.Image) -> Image.Image:
    """Create the inactive state without changing approved architecture."""
    inactive = image.copy()
    pixels = inactive.load()
    for y in range(inactive.height):
        for x in range(inactive.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            spectral = (
                blue > 125
                and green > 105
                and blue > red * 1.25
                and green > red * 1.05
            )
            if spectral:
                luminance = int(0.299 * red + 0.587 * green + 0.114 * blue)
                pixels[x, y] = (
                    max(10, int(luminance * 0.28)),
                    max(18, int(luminance * 0.42)),
                    max(28, int(luminance * 0.58)),
                    alpha,
                )
    # The approved L2/L3 architecture is already authored with its own surface
    # lighting. Only extinguish the spectral highlights here; globally dimming
    # the frame makes the complete building look as though it were painted
    # with Majesty's reserved ground-shadow controls.
    return inactive


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
    """Flood away the connected magenta background and its antialias spill.

    The source sheet's nominally solid background contains many near-magenta
    pixels blended with the building's dark outline. Treating only exact
    magenta as transparent leaves a purple fringe which the ice-color grading
    can turn into a bright cyan halo.
    """
    pixels = image.load()
    exterior: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    def enqueue_if_background(x: int, y: int, *, seed: bool = False) -> None:
        if (x, y) in exterior:
            return
        red, green, blue, alpha = pixels[x, y]
        if alpha == 0:
            pass
        elif seed:
            if not is_generated_magenta(red, green, blue):
                return
        elif not is_exterior_magenta_spill(red, green, blue):
            return
        exterior.add((x, y))
        queue.append((x, y))

    # Seed every keyed background region, including pockets enclosed by balcony
    # rails and other architecture. Flooding only from the cell perimeter leaves
    # those interior pockets dirty magenta.
    for y in range(image.height):
        for x in range(image.width):
            enqueue_if_background(x, y, seed=True)

    while queue:
        x, y = queue.popleft()
        for neighbor_y in range(max(0, y - 1), min(image.height, y + 2)):
            for neighbor_x in range(max(0, x - 1), min(image.width, x + 2)):
                enqueue_if_background(neighbor_x, neighbor_y)

    for x, y in exterior:
        pixels[x, y] = (0, 0, 0, 0)

    bbox: tuple[int, int, int, int] | None = None
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
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
    *,
    level: int,
) -> Image.Image:
    if variant_name.startswith("build_"):
        stage = int(variant_name.rsplit("_", 1)[1])
        if stage in construction_variants:
            return render_construction_variant(
                construction_variants[stage],
                stage,
                width,
                height,
                level=level,
            )
        return render_build_stage(variants, stage, width, height)

    base_name = variant_name.split("_", 1)[0]
    source_name = variant_name if variant_name in variants else base_name
    source = prepare_building_source(variants[source_name])
    if variant_name.startswith("active_"):
        frame = int(variant_name.rsplit("_", 1)[1])
        pulse = 1.0 + 0.10 * math.sin((frame / 8.0) * math.tau)
        source = pulse_cyan(source, pulse)
    source = grade_for_ice_palette(source)

    target = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    margin_x = 3
    margin_y = 2
    scale = min((width - margin_x * 2) / source.width, (height - margin_y * 2) / source.height)
    scale_multiplier = {
        "damaged_b": 0.88,
        "collapsed_intermediate": 0.92,
    }.get(variant_name, 1.0)
    if level in (2, 3) and variant_name == "damaged_b":
        scale_multiplier = 1.0
    scale *= scale_multiplier
    if level in (2, 3) and (
        variant_name in {"inactive", "damaged", "damaged_b"}
        or variant_name.startswith("active_")
    ):
        scale *= 0.96
    scaled_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(scaled_size, Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    source = lift_dark_visible_pixels(source)
    source = harden_alpha_edge(source)
    x = (width - source.width) // 2
    x += state_x_offset(variant_name, level=level)
    y = height - source.height - margin_y
    target.alpha_composite(source, (x, y))
    scrub_purple_fringe(target)
    shadow_shear, shadow_vertical_scale = shadow_profile(variant_name)
    if level in (2, 3) and (
        variant_name in {"inactive", "damaged", "damaged_b"}
        or variant_name.startswith("active_")
    ):
        # Taller upgrade art magnifies the stock L1 projection until it clips
        # the fixed left edge. Preserve the building scale and shorten only
        # the horizontal lay-down component for these full-height states.
        shadow_shear *= 0.68
    add_cast_shadow(
        target,
        shadow_shear,
        shadow_vertical_scale,
    )
    if (
        variant_name in {"damaged_b", "collapsed_intermediate"}
        or level in (2, 3)
        and (
            variant_name in {"inactive", "damaged"}
            or variant_name.startswith("active_")
        )
    ):
        assert_transparent_side_gutter(
            target,
            label=variant_name,
            include_top=True,
        )
    return target.convert("RGB")


def render_construction_variant(
    source: Image.Image,
    stage: int,
    width: int,
    height: int,
    *,
    level: int,
) -> Image.Image:
    source = grade_for_ice_palette(source)
    target = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    margin_x = 2
    margin_y = 3
    scale = min((width - margin_x * 2) / source.width, (height - margin_y * 2) / source.height)
    # The proof-sheet art nearly exhausts the fixed TILE canvas before its
    # projected shadow is added. Leave a real safety margin instead of letting
    # the early construction silhouettes flatten against a frame edge.
    scale *= {
        (3, 2): 0.84,
    }.get((level, stage), (0.94, 0.94, 0.96)[stage])
    scaled_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    source = source.resize(scaled_size, Image.Resampling.LANCZOS).filter(ImageFilter.SHARPEN)
    source = lift_dark_visible_pixels(source)
    source = harden_alpha_edge(source)
    x = (width - source.width) // 2
    y = height - source.height - margin_y
    target.alpha_composite(source, (x, y))
    scrub_purple_fringe(target)
    add_cast_shadow(
        target,
        *shadow_profile(f"build_{stage}"),
        bottom_gutter=3,
        shadow_mask_open_size=(9, 7, 5)[stage],
        shadow_mask_close_size=(15, 11, 7)[stage],
        # Preserve the full documented pit-fill reach for scaffold notches.
        # The y-dependent taper and frame-1 bottom clearance—not a narrower
        # horizontal domain—are what prevent shadow wrapping at the foreground.
        shadow_facing_depth=MAX_SHADOW_BODY_GAP,
        shadow_bottom_clearance=(
            9
            if level in (2, 3) and stage == 0
            else (10, 0, 0)[stage]
        ),
    )
    assert_transparent_side_gutter(target, label=f"construction frame {stage}")
    return target.convert("RGB")


def state_x_offset(variant_name: str, *, level: int) -> int:
    # The old offsets compensated for near-magenta background pixels that kept
    # each half-sheet at its full cell width. With a true chroma crop, both
    # building states already share the tile center.
    return {
        "damaged_b": 10,
        "collapsed_intermediate": 8,
    }.get(variant_name, 0) if level == 1 else 0


def render_build_stage(variants: dict[str, Image.Image], stage: int, width: int, height: int) -> Image.Image:
    target = Image.new("RGBA", (width, height), (0, 0, 0, 0))
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
    add_cast_shadow(
        target,
        *shadow_profile(f"build_{stage}"),
        bottom_gutter=3,
        shadow_mask_open_size=(9, 7, 5)[stage],
        shadow_mask_close_size=(15, 11, 7)[stage],
        shadow_facing_depth=(5, 8, 10)[stage],
        shadow_bottom_clearance=(10, 0, 0)[stage],
    )
    return target.convert("RGB")


def shadow_profile(variant_name: str) -> tuple[float, float]:
    if variant_name.startswith("build_"):
        return SHADOW_PROFILES[variant_name]
    if variant_name in SHADOW_PROFILES:
        return SHADOW_PROFILES[variant_name]
    base_name = variant_name.split("_", 1)[0]
    return SHADOW_PROFILES[base_name]


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
    source = harden_alpha_edge(source)
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


def harden_alpha_edge(image: Image.Image, threshold: int = 18) -> Image.Image:
    """Convert resized antialias fringe into a clean palette-art boundary."""
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < threshold:
                pixels[x, y] = (0, 0, 0, 0)
            elif alpha < 255:
                pixels[x, y] = (red, green, blue, 255)
    return image


def scrub_purple_fringe(image: Image.Image) -> None:
    """Remove only exterior chroma spill; never recolor it as cyan artwork."""
    pixels = image.load()
    while True:
        remove: list[tuple[int, int]] = []
        for y in range(image.height):
            for x in range(image.width):
                red, green, blue, alpha = pixels[x, y]
                if alpha == 0 or not is_exterior_magenta_spill(red, green, blue):
                    continue
                touches_transparency = any(
                    pixels[neighbor_x, neighbor_y][3] == 0
                    for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                    for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                    if (neighbor_x, neighbor_y) != (x, y)
                )
                if touches_transparency:
                    remove.append((x, y))
        if not remove:
            return
        for x, y in remove:
            pixels[x, y] = (0, 0, 0, 0)


def add_cast_shadow(
    image: Image.Image,
    shear: float = SHADOW_SHEAR,
    vertical_scale: float = SHADOW_VERTICAL_SCALE,
    *,
    bottom_gutter: int = 2,
    shadow_mask_open_size: int | None = None,
    shadow_mask_close_size: int | None = None,
    shadow_facing_depth: int | None = None,
    shadow_bottom_clearance: int = 0,
) -> None:
    """Paint Majesty's reserved 247-250 ground-shadow keys behind the building.

    Surface lighting remains in the authored sprite. A ground-plane silhouette
    is not a valid self-shadow mask for an isometric building and applying it to
    body pixels incorrectly darkens front-facing walls.
    """
    pixels = image.load()
    body_mask = Image.new("L", image.size, 0)
    body_pixels = body_mask.load()
    row_left_edges: list[int | None] = [None] * image.height
    bbox: tuple[int, int, int, int] | None = None
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            body_pixels[x, y] = 255
            if row_left_edges[y] is None:
                row_left_edges[y] = x
            if bbox is None:
                bbox = (x, y, x + 1, y + 1)
            else:
                left, top, right, bottom = bbox
                bbox = (min(left, x), min(top, y), max(right, x + 1), max(bottom, y + 1))

    if bbox is None:
        return

    row_right_edges: list[int | None] = [None] * image.height
    column_top_edges: list[int | None] = [None] * image.width
    column_bottom_edges: list[int | None] = [None] * image.width
    for y in range(image.height):
        for x in range(image.width):
            if not body_pixels[x, y]:
                continue
            row_right_edges[y] = x
            if column_top_edges[x] is None:
                column_top_edges[x] = y
            column_bottom_edges[x] = y
    body_envelope = Image.new("L", image.size, 0)
    body_envelope_pixels = body_envelope.load()
    for y, left_edge in enumerate(row_left_edges):
        right_edge = row_right_edges[y]
        if left_edge is None or right_edge is None:
            continue
        for x in range(left_edge, right_edge + 1):
            top_edge = column_top_edges[x]
            bottom_edge = column_bottom_edges[x]
            if top_edge is not None and bottom_edge is not None and top_edge <= y <= bottom_edge:
                body_envelope_pixels[x, y] = 255

    # Reserve two transparent rows below every world sprite. This prevents the
    # rounded entrance step and the projected shadow from flattening against
    # the fixed TILE boundary.
    base_y = min(bbox[3] - 1, image.height - bottom_gutter - 1)
    max_shadow_y = max(bbox[1], base_y - shadow_bottom_clearance)
    inverse_affine = (
        1.0,
        -shear / vertical_scale,
        shear * base_y / vertical_scale,
        0.0,
        1.0 / vertical_scale,
        -(1.0 - vertical_scale) * base_y / vertical_scale,
    )
    cast_body_mask = body_mask
    if shadow_mask_open_size:
        cast_body_mask = (
            cast_body_mask
            .filter(ImageFilter.MinFilter(shadow_mask_open_size))
            .filter(ImageFilter.MaxFilter(shadow_mask_open_size))
        )
    if shadow_mask_close_size:
        cast_body_mask = (
            cast_body_mask
            .filter(ImageFilter.MaxFilter(shadow_mask_close_size))
            .filter(ImageFilter.MinFilter(shadow_mask_close_size))
        )
        cast_pixels = cast_body_mask.load()
        for mask_y in range(image.height):
            for mask_x in range(image.width):
                if not (
                    bbox[0] <= mask_x < bbox[2]
                    and bbox[1] <= mask_y < bbox[3]
                ):
                    cast_pixels[mask_x, mask_y] = 0

    projected = cast_body_mask.transform(
        image.size,
        Image.Transform.AFFINE,
        inverse_affine,
        resample=Image.Resampling.BILINEAR,
        fillcolor=0,
    )
    projected = projected.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.15))
    shadow_pixels = projected.load()
    for y in range(image.height):
        for x in range(image.width):
            if not body_pixels[x, y]:
                continue
            is_boundary = any(
                not body_pixels[neighbor_x, neighbor_y]
                for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                if (neighbor_x, neighbor_y) != (x, y)
            )
            if not is_boundary:
                continue
            red, green, blue, _alpha = pixels[x, y]
            luminance = 0.299 * red + 0.587 * green + 0.114 * blue
            if luminance >= 42:
                continue
            # Keep the authored hue. Borrowing a nearby "bright enough" pixel
            # can copy a cyan window or rune onto a long stretch of dark edge.
            lift = math.ceil(42 - luminance)
            pixels[x, y] = (
                min(255, red + lift),
                min(255, green + lift),
                min(255, blue + lift),
                255,
            )

    for y in range(image.height):
        if y > max_shadow_y:
            continue
        for x in range(image.width):
            if body_pixels[x, y]:
                continue
            left_edge = row_left_edges[y]
            right_edge = row_right_edges[y]
            effective_depth = (
                None
                if shadow_facing_depth is None
                else min(shadow_facing_depth, max(0, max_shadow_y - y))
            )
            shadow_facing_right = (
                right_edge
                if effective_depth is None or left_edge is None
                else min(right_edge or left_edge, left_edge + effective_depth)
            )
            if (
                left_edge is not None
                and x >= left_edge
                and (shadow_facing_right is None or x > shadow_facing_right)
            ):
                continue
            intensity = shadow_pixels[x, y]
            if intensity >= 190:
                pixels[x, y] = SHADOW_MARKERS[248]
            elif intensity >= 72:
                pixels[x, y] = SHADOW_MARKERS[249]
            elif intensity >= 10:
                pixels[x, y] = SHADOW_MARKERS[250]

    fill_shadow_body_pits(
        image,
        body_mask,
        row_left_edges,
        row_right_edges,
        base_y=max_shadow_y,
        max_gap=MAX_SHADOW_BODY_GAP,
        shadow_facing_depth=shadow_facing_depth,
    )
    fill_directional_shadow_body_runs(
        image,
        body_mask,
        max_y=max_shadow_y,
        max_gap=MAX_SHADOW_BODY_GAP,
    )
    fill_enclosed_shadow_holes(
        image,
        max_y=max_shadow_y,
    )

    control_colors = set(SHADOW_MARKERS.values())
    magenta_colors = {
        SHADOW_MARKERS[248],
        SHADOW_MARKERS[249],
        SHADOW_MARKERS[250],
    }
    seam_source = image.copy()
    seam_pixels = seam_source.load()
    for y in range(image.height):
        for x in range(image.width):
            if body_pixels[x, y]:
                continue
            if seam_pixels[x, y] not in control_colors:
                continue
            touches_body = False
            for neighbor_y in range(max(0, y - 1), min(image.height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2)):
                    if neighbor_x == x and neighbor_y == y:
                        continue
                    if body_pixels[neighbor_x, neighbor_y]:
                        touches_body = True
            if touches_body:
                pixels[x, y] = SHADOW_MARKERS[247]

    notch_source = image.copy()
    notch_pixels = notch_source.load()
    for y in range(image.height):
        for x in range(image.width):
            _red, _green, _blue, alpha = notch_pixels[x, y]
            if alpha != 0 or not body_envelope_pixels[x, y]:
                continue
            touches_magenta = False
            for neighbor_y in range(max(0, y - 1), min(image.height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2)):
                    if neighbor_x == x and neighbor_y == y:
                        continue
                    if notch_pixels[neighbor_x, neighbor_y] in magenta_colors:
                        touches_magenta = True
            if touches_magenta:
                pixels[x, y] = SHADOW_MARKERS[247]

    # Literal final seam rule: a transparent pixel that directly touches both
    # magenta shadow and real body art is the missing seam pixel. Paint that
    # pixel red. Do not infer a convex body envelope or extend body colors;
    # either approach damages concave stair-step edges like balcony railings.
    seam_source = image.copy()
    seam_pixels = seam_source.load()
    for y in range(image.height):
        if y > max_shadow_y:
            continue
        for x in range(image.width):
            _red, _green, _blue, alpha = seam_pixels[x, y]
            if alpha != 0:
                continue
            neighbors = [
                (neighbor_x, neighbor_y)
                for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                if (neighbor_x, neighbor_y) != (x, y)
            ]
            touches_magenta = any(
                seam_pixels[neighbor_x, neighbor_y] in magenta_colors
                for neighbor_x, neighbor_y in neighbors
            )
            touches_body = any(
                body_pixels[neighbor_x, neighbor_y]
                for neighbor_x, neighbor_y in neighbors
            )
            if touches_magenta and touches_body:
                pixels[x, y] = SHADOW_MARKERS[247]

    final_seam_source = image.copy()
    final_seam_pixels = final_seam_source.load()
    for y in range(max_shadow_y + 1):
        for x in range(image.width):
            if final_seam_pixels[x, y][3] != 0:
                continue
            neighbors = [
                (neighbor_x, neighbor_y)
                for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                if (neighbor_x, neighbor_y) != (x, y)
            ]
            if any(
                final_seam_pixels[neighbor_x, neighbor_y] in magenta_colors
                for neighbor_x, neighbor_y in neighbors
            ) and any(
                body_pixels[neighbor_x, neighbor_y]
                for neighbor_x, neighbor_y in neighbors
            ):
                pixels[x, y] = SHADOW_MARKERS[247]

    normalize_directional_shadow_seams(
        image,
        body_mask,
        max_y=max_shadow_y,
        max_gap=MAX_SHADOW_BODY_GAP,
    )

    for y in range(max_shadow_y + 1, image.height):
        for x in range(image.width):
            if pixels[x, y] in control_colors:
                pixels[x, y] = (0, 0, 0, 0)

    seam_violations = 0
    orphan_red_pixels = 0
    invalid_body_edge_pixels = 0
    black_sandwich_pixels = 0
    black_sandwich_points: list[tuple[int, int]] = []
    for y in range(image.height):
        for x in range(image.width):
            is_magenta = pixels[x, y] in magenta_colors
            is_red = pixels[x, y] == SHADOW_MARKERS[247]
            red_touches_envelope = bool(body_envelope_pixels[x, y])
            if body_pixels[x, y]:
                is_boundary = any(
                    not body_pixels[neighbor_x, neighbor_y]
                    for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                    for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                    if (neighbor_x, neighbor_y) != (x, y)
                )
                if is_boundary:
                    edge_red, edge_green, edge_blue, edge_alpha = pixels[x, y]
                    edge_luminance = (
                        0.299 * edge_red + 0.587 * edge_green + 0.114 * edge_blue
                    )
                    if edge_alpha != 255 or edge_luminance < 42:
                        invalid_body_edge_pixels += 1
            for neighbor_y in range(max(0, y - 1), min(image.height, y + 2)):
                for neighbor_x in range(max(0, x - 1), min(image.width, x + 2)):
                    if neighbor_x == x and neighbor_y == y:
                        continue
                    _red, _green, _blue, neighbor_alpha = pixels[neighbor_x, neighbor_y]
                    touches_authored_body = bool(body_pixels[neighbor_x, neighbor_y])
                    touches_envelope_notch = (
                        neighbor_alpha == 0 and bool(body_envelope_pixels[neighbor_x, neighbor_y])
                    )
                    if is_magenta and (touches_authored_body or touches_envelope_notch):
                        seam_violations += 1
                    if is_red and (
                        touches_authored_body or bool(body_envelope_pixels[neighbor_x, neighbor_y])
                    ):
                        red_touches_envelope = True
            if is_red and not red_touches_envelope:
                orphan_red_pixels += 1
            _red, _green, _blue, pixel_alpha = pixels[x, y]
            if pixel_alpha == 0 and y <= max_shadow_y:
                neighbors = [
                    (neighbor_x, neighbor_y)
                    for neighbor_y in range(max(0, y - 1), min(image.height, y + 2))
                    for neighbor_x in range(max(0, x - 1), min(image.width, x + 2))
                    if (neighbor_x, neighbor_y) != (x, y)
                ]
                touches_magenta = any(
                    pixels[neighbor_x, neighbor_y] in magenta_colors
                    for neighbor_x, neighbor_y in neighbors
                )
                touches_body = any(
                    body_pixels[neighbor_x, neighbor_y]
                    for neighbor_x, neighbor_y in neighbors
                )
                if touches_magenta and touches_body:
                    black_sandwich_pixels += 1
                    black_sandwich_points.append((x, y))
    if seam_violations:
        raise ValueError(
            f"Generated shadow has {seam_violations} direct magenta/body seam contacts"
        )
    if orphan_red_pixels:
        raise ValueError(
            f"Generated shadow has {orphan_red_pixels} red pixels outside the body envelope"
        )
    if invalid_body_edge_pixels:
        raise ValueError(
            f"Generated body has {invalid_body_edge_pixels} transparent or dark edge pixels"
        )
    if black_sandwich_pixels:
        raise ValueError(
            f"Generated shadow has {black_sandwich_pixels} black pixels between shadow and body: "
            f"{black_sandwich_points[:12]}"
        )


def fill_shadow_body_pits(
    image: Image.Image,
    body_mask: Image.Image,
    row_left_edges: list[int | None],
    row_right_edges: list[int | None],
    *,
    base_y: int,
    max_gap: int,
    shadow_facing_depth: int | None,
) -> None:
    """Bridge every narrow transparent channel between shadow and sprite art.

    These channels are not necessarily enclosed components: a balcony notch or
    scaffold opening can remain connected to the exterior transparent field.
    Detecting only literal one-pixel sandwiches therefore misses the deeper
    black "pits" seen in game. Instead, measure the transparent-space distance
    from both the projected magenta shadow and the authored body. Any channel
    whose complete bridge is no wider than ``max_gap`` is shadow territory.

    This operation runs before the red seam is derived. It fills the whole
    channel with the nearest existing magenta band; the later seam pass changes
    only the final pixels touching actual artwork to control index 247.
    """
    pixels = image.load()
    body_pixels = body_mask.load()
    magenta_colors = {
        SHADOW_MARKERS[248],
        SHADOW_MARKERS[249],
        SHADOW_MARKERS[250],
    }

    def neighbors(x: int, y: int):
        for neighbor_y in range(max(0, y - 1), min(base_y + 1, y + 2)):
            for neighbor_x in range(max(0, x - 1), min(image.width, x + 2)):
                if (neighbor_x, neighbor_y) != (x, y):
                    yield neighbor_x, neighbor_y

    def is_shadow_facing(x: int, y: int) -> bool:
        left_edge = row_left_edges[y]
        right_edge = row_right_edges[y]
        effective_depth = (
            None
            if shadow_facing_depth is None
            else min(shadow_facing_depth, max(0, base_y - y))
        )
        shadow_facing_right = (
            right_edge
            if effective_depth is None or left_edge is None
            else min(right_edge or left_edge, left_edge + effective_depth)
        )
        return (
            left_edge is None
            or x < left_edge
            or (shadow_facing_right is not None and x <= shadow_facing_right)
        )

    shadow_distance: dict[tuple[int, int], int] = {}
    shadow_color: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    shadow_queue: deque[tuple[int, int]] = deque()
    body_distance: dict[tuple[int, int], int] = {}
    body_queue: deque[tuple[int, int]] = deque()

    for y in range(base_y + 1):
        for x in range(image.width):
            pixel = pixels[x, y]
            if pixel in magenta_colors:
                shadow_distance[(x, y)] = 0
                shadow_color[(x, y)] = pixel
                shadow_queue.append((x, y))
            if body_pixels[x, y]:
                body_distance[(x, y)] = 0
                body_queue.append((x, y))

    while shadow_queue:
        x, y = shadow_queue.popleft()
        distance = shadow_distance[(x, y)]
        if distance >= max_gap:
            continue
        for point in neighbors(x, y):
            if point in shadow_distance:
                continue
            neighbor_x, neighbor_y = point
            if not is_shadow_facing(neighbor_x, neighbor_y):
                continue
            if pixels[neighbor_x, neighbor_y][3] != 0:
                continue
            shadow_distance[point] = distance + 1
            shadow_color[point] = shadow_color[(x, y)]
            shadow_queue.append(point)

    while body_queue:
        x, y = body_queue.popleft()
        distance = body_distance[(x, y)]
        if distance >= max_gap:
            continue
        for point in neighbors(x, y):
            if point in body_distance:
                continue
            neighbor_x, neighbor_y = point
            if not is_shadow_facing(neighbor_x, neighbor_y):
                continue
            if pixels[neighbor_x, neighbor_y][3] != 0:
                continue
            body_distance[point] = distance + 1
            body_queue.append(point)

    bridge = {
        point
        for point, distance_from_shadow in shadow_distance.items()
        if pixels[point[0], point[1]][3] == 0
        and point in body_distance
        and distance_from_shadow + body_distance[point] <= max_gap + 1
    }
    for x, y in bridge:
        pixels[x, y] = shadow_color[(x, y)]

    unfilled = [
        (x, y)
        for x, y in bridge
        if pixels[x, y] not in magenta_colors
    ]
    if unfilled:
        raise ValueError(
            "Shadow/body pit fill left transparent bridge pixels: "
            f"{unfilled[:12]}"
        )


def fill_directional_shadow_body_runs(
    image: Image.Image,
    body_mask: Image.Image,
    *,
    max_y: int,
    max_gap: int,
) -> None:
    """Fill finite transparent runs directly bounded by shadow and body.

    The distance-based pass intentionally limits its search to the
    upper-left-facing envelope. Complex scaffold rows can contain an isolated
    left beam before a second, deeper body edge, making that envelope too
    conservative. A finite run with shadow on one end and authored body on the
    other is unambiguously a pit, regardless of the row's first body pixel.
    """
    pixels = image.load()
    body_pixels = body_mask.load()
    magenta_colors = {
        SHADOW_MARKERS[248],
        SHADOW_MARKERS[249],
        SHADOW_MARKERS[250],
    }
    width, height = image.size

    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y <= max_y

    for _iteration in range(max_gap):
        fills: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for y in range(max_y + 1):
                for x in range(width):
                    if pixels[x, y][3] != 0:
                        continue
                    previous_x = x - dx
                    previous_y = y - dy
                    if (
                        in_bounds(previous_x, previous_y)
                        and pixels[previous_x, previous_y][3] == 0
                    ):
                        continue
                    before_is_shadow = (
                        in_bounds(previous_x, previous_y)
                        and pixels[previous_x, previous_y] in magenta_colors
                    )
                    before_is_body = (
                        in_bounds(previous_x, previous_y)
                        and bool(body_pixels[previous_x, previous_y])
                    )
                    run: list[tuple[int, int]] = []
                    end_x, end_y = x, y
                    while (
                        len(run) < max_gap
                        and in_bounds(end_x, end_y)
                        and pixels[end_x, end_y][3] == 0
                    ):
                        run.append((end_x, end_y))
                        end_x += dx
                        end_y += dy
                    if (
                        not run
                        or not in_bounds(end_x, end_y)
                        or pixels[end_x, end_y][3] == 0
                    ):
                        continue
                    after_is_shadow = pixels[end_x, end_y] in magenta_colors
                    after_is_body = bool(body_pixels[end_x, end_y])
                    if not (
                        (before_is_shadow and after_is_body)
                        or (before_is_body and after_is_shadow)
                    ):
                        continue
                    shadow_color = (
                        pixels[previous_x, previous_y]
                        if before_is_shadow
                        else pixels[end_x, end_y]
                    )
                    for point in run:
                        fills[point] = shadow_color

        if not fills:
            break
        for (x, y), color in fills.items():
            pixels[x, y] = color


def fill_enclosed_shadow_holes(
    image: Image.Image,
    *,
    max_y: int,
) -> None:
    """Fill transparent components enclosed solely by shadow controls."""
    pixels = image.load()
    width, _height = image.size
    magenta_colors = {
        SHADOW_MARKERS[248],
        SHADOW_MARKERS[249],
        SHADOW_MARKERS[250],
    }
    transparent = {
        (x, y)
        for y in range(max_y + 1)
        for x in range(width)
        if pixels[x, y][3] == 0
    }

    def neighbors8(x: int, y: int):
        for neighbor_y in range(max(0, y - 1), min(max_y + 1, y + 2)):
            for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                if (neighbor_x, neighbor_y) != (x, y):
                    yield neighbor_x, neighbor_y

    while transparent:
        component: set[tuple[int, int]] = set()
        pending = [transparent.pop()]
        touches_exterior = False
        boundary: list[tuple[tuple[int, int], tuple[int, int, int, int]]] = []
        while pending:
            x, y = pending.pop()
            component.add((x, y))
            if x == 0 or x == width - 1 or y == 0 or y == max_y:
                touches_exterior = True
            for neighbor in neighbors8(x, y):
                neighbor_x, neighbor_y = neighbor
                if neighbor in transparent:
                    transparent.remove(neighbor)
                    pending.append(neighbor)
                elif neighbor not in component and pixels[neighbor_x, neighbor_y][3] != 0:
                    boundary.append((neighbor, pixels[neighbor_x, neighbor_y]))

        if touches_exterior or not boundary:
            continue
        if any(color not in magenta_colors for _point, color in boundary):
            continue

        # Multi-source propagation retains the nearest authored feather band
        # instead of painting a conspicuous flat block in a lighter shadow.
        assignments: dict[tuple[int, int], tuple[int, int, int, int]] = {}
        queue: deque[tuple[int, int]] = deque()
        for boundary_point, color in boundary:
            boundary_x, boundary_y = boundary_point
            for point in neighbors8(boundary_x, boundary_y):
                if point in component and point not in assignments:
                    assignments[point] = color
                    queue.append(point)
        while queue:
            x, y = queue.popleft()
            for point in neighbors8(x, y):
                if point in component and point not in assignments:
                    assignments[point] = assignments[(x, y)]
                    queue.append(point)
        for (x, y), color in assignments.items():
            pixels[x, y] = color


def normalize_directional_shadow_seams(
    image: Image.Image,
    body_mask: Image.Image,
    *,
    max_y: int,
    max_gap: int,
) -> None:
    """Move an early red endpoint across any newly exposed final pit."""
    pixels = image.load()
    body_pixels = body_mask.load()
    width, _height = image.size
    control_colors = set(SHADOW_MARKERS.values())

    def in_bounds(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y <= max_y

    magenta_colors = {
        SHADOW_MARKERS[248],
        SHADOW_MARKERS[249],
        SHADOW_MARKERS[250],
    }

    def nearest_magenta_color(x: int, y: int) -> tuple[int, int, int, int]:
        for radius in range(1, max_gap + 1):
            candidates: list[
                tuple[int, int, tuple[int, int, int, int]]
            ] = []
            for candidate_y in range(max(0, y - radius), min(max_y + 1, y + radius + 1)):
                for candidate_x in range(max(0, x - radius), min(width, x + radius + 1)):
                    color = pixels[candidate_x, candidate_y]
                    if color not in magenta_colors:
                        continue
                    distance = abs(candidate_x - x) + abs(candidate_y - y)
                    candidates.append((distance, candidate_y * width + candidate_x, color))
            if candidates:
                return min(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]
        return SHADOW_MARKERS[248]

    for _iteration in range(max_gap):
        repairs: list[
            tuple[
                tuple[int, int],
                list[tuple[int, int]],
            ]
        ] = []
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for y in range(max_y + 1):
                for x in range(width):
                    if pixels[x, y][3] != 0:
                        continue
                    previous_x, previous_y = x - dx, y - dy
                    if not in_bounds(previous_x, previous_y):
                        continue
                    if pixels[previous_x, previous_y] not in control_colors:
                        continue
                    run: list[tuple[int, int]] = []
                    end_x, end_y = x, y
                    while (
                        len(run) < max_gap
                        and in_bounds(end_x, end_y)
                        and pixels[end_x, end_y][3] == 0
                    ):
                        run.append((end_x, end_y))
                        end_x += dx
                        end_y += dy
                    if (
                        run
                        and in_bounds(end_x, end_y)
                        and bool(body_pixels[end_x, end_y])
                    ):
                        repairs.append(((previous_x, previous_y), run))

        if not repairs:
            break
        for shadow_endpoint, run in repairs:
            endpoint_x, endpoint_y = shadow_endpoint
            fill_color = (
                pixels[endpoint_x, endpoint_y]
                if pixels[endpoint_x, endpoint_y] in magenta_colors
                else nearest_magenta_color(endpoint_x, endpoint_y)
            )
            if pixels[endpoint_x, endpoint_y] == SHADOW_MARKERS[247]:
                pixels[endpoint_x, endpoint_y] = fill_color
            for run_x, run_y in run:
                pixels[run_x, run_y] = fill_color

    seam_source = image.copy()
    seam_pixels = seam_source.load()
    for y in range(max_y + 1):
        for x in range(width):
            if seam_pixels[x, y] not in {
                SHADOW_MARKERS[248],
                SHADOW_MARKERS[249],
                SHADOW_MARKERS[250],
            }:
                continue
            if any(
                body_pixels[neighbor_x, neighbor_y]
                for neighbor_y in range(max(0, y - 1), min(max_y + 1, y + 2))
                for neighbor_x in range(max(0, x - 1), min(width, x + 2))
                if (neighbor_x, neighbor_y) != (x, y)
            ):
                pixels[x, y] = SHADOW_MARKERS[247]


def assert_transparent_side_gutter(
    image: Image.Image,
    *,
    label: str,
    include_top: bool = False,
) -> None:
    """Reject fixed-canvas clipping before a frame reaches TILE encoding."""
    pixels = image.load()
    occupied = [
        (x, y)
        for y in range(image.height)
        for x in (0, image.width - 1)
        if pixels[x, y][3] != 0
    ]
    if include_top:
        occupied.extend(
            (x, 0)
            for x in range(image.width)
            if pixels[x, 0][3] != 0
        )
    if occupied:
        raise ValueError(
            f"{label} touches a fixed TILE top/side boundary: {occupied[:12]}"
        )


def is_transparent_pixel(red: int, green: int, blue: int) -> bool:
    return red < 10 and green < 10 and blue < 12


def is_magenta(red: int, green: int, blue: int) -> bool:
    return abs(red - MAGENTA[0]) < 20 and green < 35 and abs(blue - MAGENTA[2]) < 20


def is_generated_magenta(red: int, green: int, blue: int) -> bool:
    return red > 170 and blue > 140 and green < 115 and red > green * 2.2 and blue > green * 1.8


def is_exterior_magenta_spill(red: int, green: int, blue: int) -> bool:
    return (
        red > 65
        and blue > 65
        and green < min(red, blue) * 0.78
        and abs(red - blue) < 105
    )


if __name__ == "__main__":
    raise SystemExit(main())
