from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_phantom_guild as builder  # noqa: E402
from create_phantom_hero_death_review import (  # noqa: E402
    body_bottom,
    font,
    render_tile,
    tile_hotspot,
)


def main() -> int:
    cam = ROOT / "dist/PhantomGuildPoc/Data/phantom_maindata.cam"
    output_path = ROOT / "artifacts/reviews/phantom-cast-engine-review.png"
    glow_output_path = ROOT / "artifacts/reviews/phantom-cast-glow-engine-review.png"
    tiles = builder.read_cam_entries(cam, b"TILE")
    palettes = builder.read_cam_entries(cam, b"SPLT")
    by_name = {entry.name.rstrip(b"\x00"): entry for entry in tiles}

    scale = 3
    cell_width = 350
    cell_height = 315
    card = Image.new("RGB", (cell_width * 4, cell_height * 8), (18, 22, 28))
    glow_card = Image.new("RGB", (cell_width * 4, cell_height * 8), (18, 22, 28))
    draw = ImageDraw.Draw(card)
    glow_draw = ImageDraw.Draw(glow_card)

    for direction in range(8):
        for stage in range(4):
            source_tile = 4746 + direction * 4 + stage
            draw_frame(
                card,
                draw,
                by_name,
                palettes,
                source_tile,
                stage,
                direction,
                cell_width,
                cell_height,
                scale,
            )
            draw_frame(
                glow_card,
                glow_draw,
                by_name,
                palettes,
                source_tile,
                stage,
                direction,
                cell_width,
                cell_height,
                scale,
                overlay_name=f"PHM1CastGlowD{direction}F{stage}".encode("ascii"),
                label_prefix="BODY + GLOW",
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(output_path, optimize=True)
    glow_card.save(glow_output_path, optimize=True)
    print(output_path)
    print(glow_output_path)
    return 0


def draw_frame(
    card: Image.Image,
    draw: ImageDraw.ImageDraw,
    by_name: dict[bytes, builder.CamEntry],
    palettes: list[builder.CamEntry],
    source_tile: int,
    column: int,
    row: int,
    cell_width: int,
    cell_height: int,
    scale: int,
    *,
    overlay_name: bytes | None = None,
    label_prefix: str = "CAST",
) -> None:
    name = f"PHM1PhantomTile{source_tile - 4586}".encode("ascii")
    tile = by_name[name].data
    frame = render_tile(tile, palettes)
    if overlay_name is not None:
        overlay_tile = by_name[overlay_name].data
        overlay = render_tile(overlay_tile, palettes)
        if overlay.size != frame.size or tile_hotspot(overlay_tile) != tile_hotspot(tile):
            raise ValueError(f"{overlay_name!r} does not share its body frame canvas")
        frame = Image.alpha_composite(frame.convert("RGBA"), overlay.convert("RGBA"))
    hotspot_x, hotspot_y = tile_hotspot(tile)
    base_y = body_bottom(tile)
    decoded = builder.decode_indexed_v3_tile(tile)
    body_points = (
        [
            (x, y)
            for y, row_pixels in enumerate(decoded[2])
            for x, value in enumerate(row_pixels)
            if value != 0 and not 247 <= value <= 250
        ]
        if decoded is not None
        else []
    )
    body_width = (
        max(x for x, _y in body_points) - min(x for x, _y in body_points) + 1
        if body_points
        else 0
    )
    body_height = (
        max(y for _x, y in body_points) - min(y for _x, y in body_points) + 1
        if body_points
        else 0
    )
    native_width, native_height = frame.size
    frame = frame.resize(
        (native_width * scale, native_height * scale),
        Image.Resampling.NEAREST,
    )

    cell_left = column * cell_width
    cell_top = row * cell_height
    world_x = cell_left + cell_width // 2
    world_y = cell_top + 220
    draw.line(
        (cell_left + 15, world_y, cell_left + cell_width - 15, world_y),
        fill=(55, 68, 82),
    )
    draw.line(
        (world_x, cell_top + 10, world_x, cell_top + 245),
        fill=(55, 68, 82),
    )
    card.paste(
        frame,
        (world_x - hotspot_x * scale, world_y - hotspot_y * scale),
        frame,
    )
    draw.text(
        (cell_left + 10, cell_top + 255),
        f"{label_prefix} D{row}  F{column + 1}  TILE {source_tile}",
        font=font(15),
        fill=(220, 230, 240),
    )
    draw.text(
        (cell_left + 10, cell_top + 282),
        f"{native_width}x{native_height}  body {body_width}x{body_height}  base "
        f"{base_y - hotspot_y:+d}" if base_y is not None else "no body",
        font=font(14),
        fill=(145, 164, 183),
    )


if __name__ == "__main__":
    raise SystemExit(main())
