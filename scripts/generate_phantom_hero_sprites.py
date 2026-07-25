from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


LABEL_BY_TILE: dict[int, str] = {}

for tile_index in range(4586, 4650):
    LABEL_BY_TILE[tile_index] = "hover"

for tile_index in range(4650, 4659):
    LABEL_BY_TILE[tile_index] = "stand"

for tile_index in range(4659, 4690):
    LABEL_BY_TILE[tile_index] = "special"

for tile_index in range(4690, 4723):
    LABEL_BY_TILE[tile_index] = "attack"

for tile_index in range(4723, 4741):
    LABEL_BY_TILE[tile_index] = "death_directional"

for tile_index in range(4746, 4778):
    LABEL_BY_TILE[tile_index] = "cast"

for tile_index in range(4778, 4786):
    LABEL_BY_TILE[tile_index] = "death_shared"
LABEL_BY_TILE[4787] = "gravestone"
# Tiles 4788-4791 are shared, detached Priestess casting-effect frames rather
# than character poses. Leave them on the existing recolor path during this
# body/action proof instead of stamping a second full Phantom into the effect.

FRAME_ORDER = ("stand", "hover", "attack", "cast", "special", "dissolve")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--direction-03", required=True, type=Path)
    parser.add_argument("--direction-04", required=True, type=Path)
    parser.add_argument("--direction-05", required=True, type=Path)
    parser.add_argument("--death-concept", required=True, type=Path)
    parser.add_argument("--death-directionals", required=True, type=Path)
    parser.add_argument("--cast-glow", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    direction_paths = (args.sheet, args.direction_03, args.direction_04, args.direction_05)
    frames_by_direction: list[dict[str, Image.Image]] = []
    for path in direction_paths:
        frames = extract_frames(chroma_key(Image.open(path).convert("RGBA")))
        if len(frames) < len(FRAME_ORDER):
            raise ValueError(f"Expected six generated sprite frames in {path}, got {len(frames)}")
        frames_by_direction.append(
            {
                label: prepare_frame(frames[index], label)
                for index, label in enumerate(FRAME_ORDER)
            }
        )

    # The last two Majesty view slots are the exact opposite-side counterparts
    # of the generated front-adjacent and rear-three-quarter views.
    frames_by_direction.append(mirror_direction(frames_by_direction[2]))
    frames_by_direction.append(mirror_direction(frames_by_direction[1]))

    # Majesty's populated unit slots are not stored front-to-back. Stock
    # Peasant/Warrior frames establish the compass turn as:
    #   slot 2 back/north, 3 rear-side, 4 front-side, 5 front/south,
    #   6 opposite front-side, 7 opposite rear-side.
    # Generated sheets are held in the opposite, art-production order:
    #   front, front-side, rear-side, back, mirrored rear-side,
    #   mirrored front-side.
    frames_by_direction = [
        frames_by_direction[index]
        for index in (3, 2, 1, 0, 5, 4)
    ]

    directional_death_grid = extract_grid_frames(
        chroma_key(Image.open(args.death_directionals).convert("RGBA")),
        columns=4,
        rows=3,
    )
    death_frames_by_direction = [
        [
            directional_death_grid[row * 4 + column]
            for row in range(3)
        ]
        for column in range(4)
    ]
    death_frames_by_direction.append(
        [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in death_frames_by_direction[2]]
    )
    death_frames_by_direction.append(
        [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in death_frames_by_direction[1]]
    )
    death_frames_by_direction = [
        death_frames_by_direction[index]
        for index in (3, 2, 1, 0, 5, 4)
    ]

    shared_death_frames = extract_grid_frames(
        chroma_key(Image.open(args.death_concept).convert("RGBA")),
        columns=4,
        rows=2,
    )
    cast_glow_frames = extract_grid_frames(
        chroma_key(Image.open(args.cast_glow).convert("RGBA")),
        columns=4,
        rows=1,
    )
    frame_by_label = frames_by_direction[0]
    frame_by_label["gravestone"] = prepare_frame(shared_death_frames[7], "gravestone")

    for tile_index, label in sorted(LABEL_BY_TILE.items()):
        if label == "death_directional":
            direction = (tile_index - 4723) // 3
            stage = (tile_index - 4723) % 3
            image = prepare_frame(death_frames_by_direction[direction][stage], label)
        elif label == "death_shared":
            # Once the directional body has shattered, use only the approved
            # direction-neutral spectral core and emerging marker phases.
            phase = 5 if tile_index <= 4781 else 6
            image = prepare_frame(shared_death_frames[phase], label)
        elif label == "gravestone":
            image = prepare_frame(shared_death_frames[7], label)
        else:
            direction, stage, stage_count = animation_position(tile_index, label)
            image = animated_frame(
                frames_by_direction[direction],
                label,
                stage,
                stage_count,
            )
        image.save(args.out_dir / f"hero_tile_{tile_index:05d}.png")

    for stage, image in enumerate(cast_glow_frames):
        prepare_frame(image, "cast_glow").save(
            args.out_dir / f"cast_glow_{stage:02d}.png"
        )

    preview = make_preview(frame_by_label)
    preview.save(args.out_dir / "phantom_generated_hero_sprite_preview.png")
    return 0


def mirror_direction(frames: dict[str, Image.Image]) -> dict[str, Image.Image]:
    return {
        label: image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for label, image in frames.items()
    }


def animation_position(tile_index: int, label: str) -> tuple[int, int, int]:
    if label == "hover":
        direction = min(5, max(0, (tile_index - 4586) // 8))
        position = (tile_index - 4586) % 8
        # Each direction block begins with a header/base pose, followed by
        # seven ordinary Walk frames. The engine periodically displays that
        # base pose, so it must belong to this direction—not the preceding one.
        stage = 3 if position == 0 else position - 1
        return direction, stage, 7
    if label == "stand":
        return min(5, max(0, tile_index - 4650)), 0, 1
    if label == "special":
        direction = min(5, max(0, (tile_index - 4659) // 4))
        return direction, min(2, (tile_index - 4659) % 4), 3
    if label == "attack":
        direction = min(5, max(0, (tile_index - 4690) // 4))
        return direction, min(3, (tile_index - 4690) % 4), 4
    if label == "dissolve" and tile_index < 4778:
        direction = min(5, max(0, (tile_index - 4723) // 3))
        return direction, min(1, (tile_index - 4723) % 3), 2
    if label == "cast":
        direction = min(5, max(0, (tile_index - 4746) // 4))
        return direction, min(3, (tile_index - 4746) % 4), 4
    if label == "dissolve":
        return 0, min(7, max(0, tile_index - 4778)), 8
    return 0, 0, 1


def animated_frame(
    direction_frames: dict[str, Image.Image],
    label: str,
    stage: int,
    stage_count: int,
) -> Image.Image:
    if label == "dissolve" and stage_count == 2:
        if stage == 0:
            return transform_action(direction_frames["stand"], rotate=-2.0, scale=1.0)
        return direction_frames["dissolve"].copy()

    image = direction_frames[label].copy()
    if label == "hover":
        cycle = (-1.8, -0.8, 0.8, 1.8, 0.8, -0.8, -1.4)
        return transform_action(image, rotate=cycle[stage], scale=1.0 + (0.01 if stage in (2, 3) else 0.0))
    if label == "attack":
        rotations = (-4.0, -1.5, 1.0, 2.5)
        scales = (0.91, 0.96, 1.0, 1.03)
        return transform_action(image, rotate=rotations[stage], scale=scales[stage])
    if label == "cast":
        brightness = (0.72, 0.84, 0.94, 1.08)
        return ImageEnhance.Brightness(
            # Keep the silhouette and feet locked across the cast. The source
            # pose already communicates the action; rotating the full sprite
            # made several directions visibly grow and shrink in-game.
            transform_action(image, rotate=0.0, scale=1.0)
        ).enhance(brightness[stage])
    if label == "special":
        return ImageEnhance.Brightness(
            transform_action(image, rotate=(-1.0, 0.0, 1.0)[stage], scale=(0.93, 1.0, 1.04)[stage])
        ).enhance((0.78, 0.95, 1.08)[stage])
    if label == "dissolve":
        return progressive_dissolve(image, stage, stage_count)
    return image


def transform_action(image: Image.Image, *, rotate: float, scale: float) -> Image.Image:
    resized = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    rotated = resized.rotate(rotate, resample=Image.Resampling.BICUBIC, expand=True)
    return crop_alpha(rotated, pad=8)


def progressive_dissolve(image: Image.Image, stage: int, stage_count: int) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    progress = stage / max(1, stage_count - 1)
    cutoff = image.height * (0.98 - progress * 0.78)
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            noise = ((x * 37 + y * 19 + stage * 23) % 101) / 100.0
            if y > cutoff and noise < progress * 0.92:
                pixels[x, y] = (red, green, blue, 0)
            elif progress > 0.55:
                pixels[x, y] = (red, green, blue, round(alpha * (1.0 - (progress - 0.55) * 1.7)))
    return crop_alpha(image, pad=8)


def chroma_key(image: Image.Image) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if red > 175 and blue > 155 and green < 115 and red > green * 1.8:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            if green > 165 and red < 95 and blue < 95 and green > red * 1.7 and green > blue * 1.7:
                pixels[x, y] = (0, 0, 0, 0)
                continue

            if green > red and green > blue:
                green = min(green, max(red, blue) + 18)
            if red > green * 1.5 and blue > green * 1.4:
                red = min(red, green + 28)
                blue = min(blue, green + 34)
            pixels[x, y] = (red, green, blue, alpha)
    return image


def extract_frames(sheet: Image.Image) -> list[Image.Image]:
    width, height = sheet.size
    if width >= height and width < height * 2:
        return extract_three_by_two_frames(sheet)

    frames: list[Image.Image] = []
    cell_width = width / len(FRAME_ORDER)
    for index in range(len(FRAME_ORDER)):
        left = int(index * cell_width)
        right = int((index + 1) * cell_width)
        cell = sheet.crop((left, 0, right, height))
        remove_detached_ground_shadow(cell)
        frames.append(crop_alpha(cell, pad=18))
    return frames


def extract_three_by_two_frames(sheet: Image.Image) -> list[Image.Image]:
    cell_width = sheet.width // 3
    cell_height = sheet.height // 2
    frames: list[Image.Image] = []

    for index in range(len(FRAME_ORDER)):
        column = index % 3
        row = index // 3
        left = column * cell_width
        top = row * cell_height
        right = sheet.width if column == 2 else (column + 1) * cell_width
        bottom = sheet.height if row == 1 else (row + 1) * cell_height
        cell = sheet.crop((left, top, right, bottom))

        # The approved special pose's raised staff crosses the nominal row
        # boundary. Restore only that isolated upper fragment; the adjacent
        # movement pose is deliberately excluded.
        if index == 4:
            overlap_top = max(0, cell_height - 80)
            staff_left = left + 145
            staff_right = min(right, left + 250)
            staff = sheet.crop((staff_left, overlap_top, staff_right, cell_height))
            expanded = Image.new(
                "RGBA",
                (cell.width, cell.height + (cell_height - overlap_top)),
                (0, 0, 0, 0),
            )
            expanded.alpha_composite(staff, (staff_left - left, 0))
            expanded.alpha_composite(cell, (0, cell_height - overlap_top))
            cell = expanded

        frames.append(crop_alpha(cell, pad=8))

    return frames


def extract_grid_frames(
    sheet: Image.Image,
    *,
    columns: int,
    rows: int,
) -> list[Image.Image]:
    cell_width = sheet.width // columns
    cell_height = sheet.height // rows
    frames: list[Image.Image] = []
    for row in range(rows):
        for column in range(columns):
            left = column * cell_width
            top = row * cell_height
            right = sheet.width if column == columns - 1 else (column + 1) * cell_width
            bottom = sheet.height if row == rows - 1 else (row + 1) * cell_height
            frames.append(crop_alpha(sheet.crop((left, top, right, bottom)), pad=12))
    return frames


def remove_detached_ground_shadow(image: Image.Image) -> None:
    alpha = image.getchannel("A")
    mask = alpha.load()
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()

    for y in range(height):
        for x in range(width):
            if mask[x, y] == 0 or (x, y) in seen:
                continue

            queue = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            total_luminance = 0.0

            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                red, green, blue, _ = pixels[cx, cy]
                total_luminance += 0.299 * red + 0.587 * green + 0.114 * blue

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in seen
                        or mask[nx, ny] == 0
                    ):
                        continue
                    seen.add((nx, ny))
                    queue.append((nx, ny))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            left, top, right, bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
            component_height = bottom - top
            average_luminance = total_luminance / max(1, len(points))
            low_in_cell = top > int(height * 0.68)
            flat_blob = component_height < int(height * 0.12) and (right - left) > component_height * 2
            dark_blob = average_luminance < 55

            if low_in_cell and flat_blob and dark_blob:
                for px, py in points:
                    pixels[px, py] = (0, 0, 0, 0)


def prepare_frame(image: Image.Image, label: str) -> Image.Image:
    image = crop_alpha(image, pad=6)
    if label == "hover":
        image = remove_detached_frame_artifacts(image, padding=12)
    if label == "cast_glow":
        # The source art is deliberately ice-white so its fine threads survive
        # generation. Tint those threads toward the Phantom's restrained cyan
        # before Majesty palette quantization, without turning them electric.
        alpha = image.getchannel("A")
        image = ImageOps.colorize(
            ImageOps.grayscale(image),
            black=(5, 20, 34),
            white=(126, 218, 246),
            mid=(43, 139, 190),
        ).convert("RGBA")
        image.putalpha(alpha)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    image = ImageEnhance.Color(image).enhance(0.92)
    return image.filter(ImageFilter.SHARPEN)


def remove_detached_frame_artifacts(image: Image.Image, padding: int = 0) -> Image.Image:
    image = image.copy()
    alpha = image.getchannel("A")
    mask = alpha.load()
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int, int, int], list[tuple[int, int]]]] = []

    for y in range(height):
        for x in range(width):
            if mask[x, y] == 0 or (x, y) in seen:
                continue

            queue = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in seen
                        or mask[nx, ny] == 0
                    ):
                        continue
                    seen.add((nx, ny))
                    queue.append((nx, ny))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            components.append((len(points), (min(xs), min(ys), max(xs) + 1, max(ys) + 1), points))

    if not components:
        return image

    _largest_size, largest_bbox, _largest_points = max(components, key=lambda component: component[0])
    largest_left, largest_top, largest_right, largest_bottom = largest_bbox
    keep: set[tuple[int, int]] = set()
    for _size, bbox, points in components:
        left, top, right, bottom = bbox
        close_to_body = (
            left <= largest_right + 26
            and right >= largest_left - 26
            and top <= largest_bottom + 20
            and bottom >= largest_top - 20
        )
        if bbox == largest_bbox or close_to_body:
            keep.update(points)

    for y in range(height):
        for x in range(width):
            if mask[x, y] and (x, y) not in keep:
                pixels[x, y] = (0, 0, 0, 0)

    return crop_alpha(image, pad=padding)


def crop_alpha(image: Image.Image, pad: int = 0) -> Image.Image:
    bbox = image.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    left, top, right, bottom = bbox
    return image.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad),
            min(image.height, bottom + pad),
        )
    )


def make_preview(frame_by_label: dict[str, Image.Image]) -> Image.Image:
    preview_order = FRAME_ORDER + ("gravestone",)
    cell_width = 112
    cell_height = 118
    output = Image.new("RGBA", (cell_width * len(preview_order), cell_height), (30, 32, 33, 255))
    for index, label in enumerate(preview_order):
        frame = frame_by_label[label].copy()
        frame.thumbnail((52, 68), Image.Resampling.LANCZOS)
        frame = frame.resize((frame.width * 2, frame.height * 2), Image.Resampling.NEAREST)
        x = index * cell_width + (cell_width - frame.width) // 2
        y = 20 + ((cell_height - 24) - frame.height) // 2
        output.alpha_composite(frame, (x, y))
    return output.convert("RGB")


if __name__ == "__main__":
    raise SystemExit(main())
