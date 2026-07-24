from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


LABEL_BY_TILE: dict[int, str] = {}

for tile_index in range(4587, 4650):
    LABEL_BY_TILE[tile_index] = "hover"

for tile_index in range(4650, 4659):
    LABEL_BY_TILE[tile_index] = "stand"

for tile_index in range(4659, 4690):
    LABEL_BY_TILE[tile_index] = "special"

for tile_index in range(4690, 4723):
    LABEL_BY_TILE[tile_index] = "attack"

for tile_index in range(4723, 4746):
    LABEL_BY_TILE[tile_index] = "dissolve"

for tile_index in range(4746, 4778):
    LABEL_BY_TILE[tile_index] = "cast"

for tile_index in range(4778, 4786):
    LABEL_BY_TILE[tile_index] = "dissolve"
LABEL_BY_TILE[4787] = "gravestone"
for tile_index in range(4788, 4792):
    LABEL_BY_TILE[tile_index] = "cast"

FRAME_ORDER = ("stand", "hover", "attack", "cast", "special", "dissolve")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--gravestone-source", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(args.sheet).convert("RGBA")
    keyed = chroma_key(sheet)
    frames = extract_frames(keyed)
    if len(frames) < len(FRAME_ORDER):
        raise ValueError(f"Expected at least {len(FRAME_ORDER)} generated sprite frames, got {len(frames)}")

    frame_by_label = {
        label: prepare_frame(frames[index], label)
        for index, label in enumerate(FRAME_ORDER)
    }
    if args.gravestone_source:
        frame_by_label["gravestone"] = prepare_frame(
            chroma_key(Image.open(args.gravestone_source).convert("RGBA")),
            "gravestone",
        )
    else:
        frame_by_label["gravestone"] = frame_by_label["dissolve"]

    for tile_index, label in sorted(LABEL_BY_TILE.items()):
        image = frame_by_label[label]
        if should_flip_tile(tile_index):
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        image.save(args.out_dir / f"hero_tile_{tile_index:05d}.png")

    preview = make_preview(frame_by_label)
    preview.save(args.out_dir / "phantom_generated_hero_sprite_preview.png")
    return 0


def chroma_key(image: Image.Image) -> Image.Image:
    image = image.copy()
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if green > 165 and red < 95 and blue < 95 and green > red * 1.7 and green > blue * 1.7:
                pixels[x, y] = (0, 0, 0, 0)
                continue

            if green > red and green > blue:
                green = min(green, max(red, blue) + 18)
            pixels[x, y] = (red, green, blue, alpha)
    return image


def extract_frames(sheet: Image.Image) -> list[Image.Image]:
    width, height = sheet.size
    frames: list[Image.Image] = []
    cell_width = width / len(FRAME_ORDER)
    for index in range(len(FRAME_ORDER)):
        left = int(index * cell_width)
        right = int((index + 1) * cell_width)
        cell = sheet.crop((left, 0, right, height))
        remove_detached_ground_shadow(cell)
        frames.append(crop_alpha(cell, pad=18))
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


def should_flip_tile(tile_index: int) -> bool:
    # Priestess directions 2-4 are mirrored-ish relative to the generated
    # down-right source pose. This is only a first-pass proof; true final art
    # should use generated directional source frames instead.
    return (
        4587 <= tile_index <= 4609
        or 4650 <= tile_index <= 4652
        or 4659 <= tile_index <= 4669
        or 4690 <= tile_index <= 4701
        or tile_index in {4723, 4724, 4726, 4727, 4729, 4730}
        or 4746 <= tile_index <= 4757
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
