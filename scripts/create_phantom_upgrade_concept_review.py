from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_phantom_guild import (  # noqa: E402
    read_cam_entries,
    tile_palette_colors,
)


GAME_DATA = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\Data")
LEVEL_ONE_SOURCE = ROOT / "assets/source/buildings/haunt/level-1/sprite-sheet.png"
LEVEL_TWO_CONCEPT = ROOT / "assets/source/buildings/haunt/level-2/active.png"
LEVEL_THREE_CONCEPT = ROOT / "assets/source/buildings/haunt/level-3/active.png"
REFERENCE_OUTPUT = ROOT / "artifacts/references/stock-guild-upgrade-progression.png"
REVIEW_OUTPUT = ROOT / "artifacts/reviews/phantom-haunt-level-progression.png"
STATE_REVIEW_OUTPUT = ROOT / "artifacts/reviews/phantom-haunt-upgrade-state-approval.png"

UPGRADE_STATE_SOURCES = {
    2: {
        "ACTIVE": LEVEL_TWO_CONCEPT,
        "UPGRADE EARLY": ROOT / "assets/source/buildings/haunt/level-2/upgrade-early.png",
        "UPGRADE LATE": ROOT / "assets/source/buildings/haunt/level-2/upgrade-late.png",
        "DAMAGED": ROOT / "assets/source/buildings/haunt/level-2/damaged.png",
        "DAMAGED B": ROOT / "assets/source/buildings/haunt/level-2/damaged-b.png",
        "COLLAPSE": ROOT / "assets/source/buildings/haunt/level-2/collapsed.png",
        "DESTROYED": ROOT / "assets/source/buildings/haunt/level-2/destroyed.png",
    },
    3: {
        "ACTIVE": LEVEL_THREE_CONCEPT,
        "UPGRADE EARLY": ROOT / "assets/source/buildings/haunt/level-3/upgrade-early.png",
        "UPGRADE LATE": ROOT / "assets/source/buildings/haunt/level-3/upgrade-late.png",
        "DAMAGED": ROOT / "assets/source/buildings/haunt/level-3/damaged.png",
        "DAMAGED B": ROOT / "assets/source/buildings/haunt/level-3/damaged-b.png",
        "COLLAPSE": ROOT / "assets/source/buildings/haunt/level-3/collapsed.png",
        "DESTROYED": ROOT / "assets/source/buildings/haunt/level-3/destroyed.png",
    },
}

STOCK_ACTIVE_TILES = (
    ("DAUROS", (1472, 1487, 1494)),
    ("KRYPTA", (1646, 1681, 1686)),
    ("WIZARD GUILD", (1801, 1909, 1960)),
)

MAGENTA = (255, 0, 255)
BACKGROUND = (18, 23, 32)
PANEL = (34, 42, 56)
PRIMARY = (234, 241, 248)
SECONDARY = (145, 164, 188)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def decode_stock_tile(
    tile_index: int,
    tiles: list,
    palettes: list,
) -> Image.Image:
    tile = tiles[tile_index].data
    decoded = decode_stock_indexed_v3_tile(tile)
    colors = tile_palette_colors(tile, palettes)
    if decoded is None or colors is None:
        raise ValueError(f"Could not decode stock TILE {tile_index}")
    height, width, pixels = decoded
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    output = image.load()
    for y, row in enumerate(pixels):
        for x, palette_index in enumerate(row):
            if palette_index == 0 or 247 <= palette_index <= 250:
                continue
            red, green, blue = colors[palette_index]
            output[x, y] = (red, green, blue, 255)
    return image


def decode_stock_indexed_v3_tile(
    tile: bytes,
) -> tuple[int, int, list[list[int]]] | None:
    """Decode stock TILE v3 rows, whose count and row-end flag share a u16."""
    if len(tile) < 26 or struct.unpack_from("<H", tile, 0)[0] != 3:
        return None
    height = struct.unpack_from("<H", tile, 2)[0]
    width = struct.unpack_from("<H", tile, 4)[0]
    offset_base = 26
    if height <= 0 or width <= 0 or offset_base + height * 4 > len(tile):
        return None
    offsets = [
        struct.unpack_from("<I", tile, offset_base + row * 4)[0]
        for row in range(height)
    ]
    pixels = [[0 for _ in range(width)] for _ in range(height)]
    for row_index, relative_offset in enumerate(offsets):
        start = offset_base + relative_offset
        end = (
            offset_base + offsets[row_index + 1]
            if row_index + 1 < height
            else len(tile)
        )
        if start < offset_base or end > len(tile) or start > end:
            return None
        position = start
        while position + 4 <= end:
            x_end, count_word = struct.unpack_from("<HH", tile, position)
            position += 4
            count = count_word & 0x7FFF
            if count > x_end or position + count > end:
                return None
            x_start = x_end - count
            for offset, palette_index in enumerate(tile[position : position + count]):
                x = x_start + offset
                if 0 <= x < width:
                    pixels[row_index][x] = palette_index
            position += count
            if count_word & 0x8000:
                break
    return height, width, pixels


def subject_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    rgba = image.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    source = rgba.load()
    output = mask.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = source[x, y]
            generated_magenta = (
                alpha > 0
                and red > 205
                and blue > 170
                and green < 85
                and red > green * 2.4
            )
            output[x, y] = 255 if alpha > 0 and not generated_magenta else 0
    return mask.getbbox() or (0, 0, image.width, image.height)


def fit_subject(
    image: Image.Image,
    size: tuple[int, int],
    margin: int = 28,
    top_clearance: int = 0,
) -> Image.Image:
    cropped = image.convert("RGBA").crop(subject_bounds(image))
    scale = min(
        (size[0] - margin * 2) / cropped.width,
        (size[1] - margin * 2 - top_clearance) / cropped.height,
    )
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.Resampling.LANCZOS,
    )
    target = Image.new("RGB", size, MAGENTA)
    target.paste(
        resized,
        (
            (size[0] - resized.width) // 2,
            size[1] - margin - resized.height,
        ),
        resized,
    )
    return target


def level_one_active() -> Image.Image:
    sheet = Image.open(LEVEL_ONE_SOURCE).convert("RGBA")
    return sheet.crop((sheet.width // 2, 0, sheet.width, sheet.height // 2))


def create_stock_reference() -> None:
    maindata = GAME_DATA / "maindata.cam"
    tiles = read_cam_entries(maindata, b"TILE")
    palettes = read_cam_entries(maindata, b"SPLT")
    cell_size = (520, 430)
    card = Image.new("RGB", (1740, 1510), BACKGROUND)
    draw = ImageDraw.Draw(card)
    draw.text((58, 36), "STOCK GUILD UPGRADE PROGRESSION", font=font(46), fill=PRIMARY)
    draw.text(
        (60, 94),
        "Supporting massing and ornament reference only — levels 1, 2, and 3",
        font=font(24),
        fill=SECONDARY,
    )

    for row, (name, tile_indices) in enumerate(STOCK_ACTIVE_TILES):
        y = 180 + row * 435
        draw.text((24, y + 165), name, font=font(25), fill=PRIMARY)
        for column, tile_index in enumerate(tile_indices):
            x = 170 + column * 520
            panel = fit_subject(decode_stock_tile(tile_index, tiles, palettes), cell_size)
            card.paste(panel, (x, y))
            draw.text(
                (x + 18, y + 14),
                f"LEVEL {column + 1}",
                font=font(22),
                fill=(25, 27, 34),
            )

    REFERENCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(REFERENCE_OUTPUT, optimize=True)


def create_concept_review() -> None:
    missing = [
        path
        for path in (LEVEL_TWO_CONCEPT, LEVEL_THREE_CONCEPT)
        if not path.is_file()
    ]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing generated upgrade concepts: {missing_text}")

    frames = (
        ("LEVEL 1 — CURRENT", "Approved architecture", level_one_active()),
        ("LEVEL 2 — PROPOSED", "Icy Touch + Gravekeeper", Image.open(LEVEL_TWO_CONCEPT)),
        (
            "LEVEL 3 — PROPOSED",
            "Endless Winter + Rush unto Death",
            Image.open(LEVEL_THREE_CONCEPT),
        ),
    )
    panel_size = (760, 720)
    card = Image.new("RGB", (2400, 930), BACKGROUND)
    draw = ImageDraw.Draw(card)
    draw.text((55, 34), "PHANTOMS HAUNT — LEVEL PROGRESSION CONCEPTS", font=font(46), fill=PRIMARY)
    draw.text(
        (57, 92),
        "Architecture approval sheet — engine construction, damage, shadow, and seam states follow after selection",
        font=font(23),
        fill=SECONDARY,
    )

    for column, (title, subtitle, image) in enumerate(frames):
        x = 45 + column * 785
        y = 165
        draw.rounded_rectangle(
            (x - 4, y - 4, x + panel_size[0] + 4, y + panel_size[1] + 4),
            radius=14,
            fill=PANEL,
        )
        card.paste(
            fit_subject(image, panel_size, margin=42, top_clearance=78),
            (x, y),
        )
        draw.text((x + 18, y + 18), title, font=font(28), fill=(24, 26, 32))
        draw.text((x + 18, y + 58), subtitle, font=font(21), fill=(48, 54, 66))

    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(REVIEW_OUTPUT, optimize=True)


def create_state_review() -> None:
    missing = [
        path
        for level_sources in UPGRADE_STATE_SOURCES.values()
        for path in level_sources.values()
        if not path.is_file()
    ]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing upgrade-state concepts: {missing_text}")

    state_names = (
        "ACTIVE",
        "UPGRADE EARLY",
        "UPGRADE LATE",
        "DAMAGED",
        "DAMAGED B",
        "COLLAPSE",
        "DESTROYED",
    )
    panel_size = (410, 430)
    panel_gap = 18
    left = 82
    top = 205
    row_gap = 62
    card_width = (
        left * 2
        + panel_size[0] * len(state_names)
        + panel_gap * (len(state_names) - 1)
    )
    card_height = top + panel_size[1] * 2 + row_gap + 70
    card = Image.new("RGB", (card_width, card_height), BACKGROUND)
    draw = ImageDraw.Draw(card)
    draw.text(
        (55, 32),
        "PHANTOMS HAUNT — UPGRADE STATE APPROVAL",
        font=font(44),
        fill=PRIMARY,
    )
    draw.text(
        (57, 91),
        "Approve architecture and destruction progression before derivative frames, shadows, palette encoding, and CAM integration",
        font=font(21),
        fill=SECONDARY,
    )
    draw.text(
        (57, 127),
        "Representative concepts only — solid magenta is intentional extraction background",
        font=font(20),
        fill=SECONDARY,
    )

    for row, level in enumerate((2, 3)):
        y = top + row * (panel_size[1] + row_gap)
        draw.text(
            (20, y + panel_size[1] // 2 - 22),
            f"L{level}",
            font=font(30),
            fill=PRIMARY,
        )
        for column, state_name in enumerate(state_names):
            x = left + column * (panel_size[0] + panel_gap)
            draw.rounded_rectangle(
                (x - 4, y - 4, x + panel_size[0] + 4, y + panel_size[1] + 4),
                radius=13,
                fill=PANEL,
            )
            art_panel = fit_subject(
                Image.open(UPGRADE_STATE_SOURCES[level][state_name]),
                (panel_size[0], panel_size[1] - 54),
                margin=18,
            )
            card.paste(art_panel, (x, y + 54))
            draw.text(
                (x + 18, y + 13),
                state_name,
                font=font(21),
                fill=PRIMARY,
            )

    STATE_REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(STATE_REVIEW_OUTPUT, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stock-only",
        action="store_true",
        help="Extract only the stock upgrade reference sheet.",
    )
    args = parser.parse_args()

    create_stock_reference()
    print(REFERENCE_OUTPUT)
    if not args.stock_only:
        create_concept_review()
        print(REVIEW_OUTPUT)
        create_state_review()
        print(STATE_REVIEW_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
