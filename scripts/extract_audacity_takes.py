from __future__ import annotations

import argparse
import array
import math
from pathlib import Path
import sqlite3
import wave


SOURCE_RATE = 44_100
OUTPUT_RATE = 22_050
WINDOW_SECONDS = 0.02
ACTIVE_THRESHOLD_DB = -45.0
MAX_INTERNAL_PAUSE_SECONDS = 0.50
MIN_TAKE_SECONDS = 0.30
LEAD_PADDING_SECONDS = 0.30
TAIL_PADDING_SECONDS = 0.20
AUDACITY_FLOAT_FORMAT = 262_159


def read_project_samples(project: Path) -> list[float]:
    uri = f"file:{project.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            "select blockid, sampleformat, samples "
            "from sampleblocks order by blockid"
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        raise ValueError(f"{project}: no Audacity sample blocks found")

    samples: list[float] = []
    for block_id, sample_format, payload in rows:
        if sample_format != AUDACITY_FLOAT_FORMAT:
            raise ValueError(
                f"{project}: block {block_id} uses unsupported "
                f"sample format {sample_format}"
            )
        chunk = array.array("f")
        chunk.frombytes(payload)
        samples.extend(chunk)
    return samples


def find_takes(
    samples: list[float],
    max_internal_pause_seconds: float = MAX_INTERNAL_PAUSE_SECONDS,
) -> list[tuple[int, int]]:
    window = round(SOURCE_RATE * WINDOW_SECONDS)
    levels: list[float] = []
    for start in range(0, len(samples), window):
        chunk = samples[start : start + window]
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        levels.append(20.0 * math.log10(max(rms, 1e-9)))

    active = [level > ACTIVE_THRESHOLD_DB for level in levels]
    bridge = round(max_internal_pause_seconds / WINDOW_SECONDS)
    index = 0
    while index < len(active):
        if active[index]:
            index += 1
            continue
        end = index
        while end < len(active) and not active[end]:
            end += 1
        if index > 0 and end < len(active) and end - index <= bridge:
            active[index:end] = [True] * (end - index)
        index = end

    lead_padding = round(LEAD_PADDING_SECONDS * SOURCE_RATE)
    tail_padding = round(TAIL_PADDING_SECONDS * SOURCE_RATE)
    minimum_windows = round(MIN_TAKE_SECONDS / WINDOW_SECONDS)
    takes: list[tuple[int, int]] = []
    index = 0
    while index < len(active):
        if not active[index]:
            index += 1
            continue
        end = index
        while end < len(active) and active[end]:
            end += 1
        if end - index >= minimum_windows:
            sample_start = max(0, index * window - lead_padding)
            sample_end = min(len(samples), end * window + tail_padding)
            takes.append((sample_start, sample_end))
        index = end
    return takes


def to_pcm16(samples: list[float]) -> array.array:
    return array.array(
        "h",
        (
            round(max(-32768.0, min(32767.0, value * 32768.0)))
            for value in samples
        ),
    )


def write_wav(path: Path, samples: list[float], sample_rate: int) -> None:
    pcm = to_pcm16(samples)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def downsample_2x(samples: list[float]) -> list[float]:
    return [
        (samples[index] + samples[index + 1]) * 0.5
        for index in range(0, len(samples) - 1, 2)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract chronological voice takes from a simple Audacity project."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("event")
    parser.add_argument(
        "--max-internal-pause",
        type=float,
        default=MAX_INTERNAL_PAUSE_SECONDS,
        help=(
            "Maximum silence in seconds to retain inside one take "
            f"(default: {MAX_INTERNAL_PAUSE_SECONDS:.2f})"
        ),
    )
    args = parser.parse_args()
    if args.max_internal_pause < 0:
        parser.error("--max-internal-pause must be non-negative")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    samples = read_project_samples(args.project)
    review = args.output_dir / f"phantom-{args.event}-review.wav"
    write_wav(review, samples, SOURCE_RATE)

    takes = find_takes(samples, args.max_internal_pause)
    for number, (start, end) in enumerate(takes, start=1):
        clean = downsample_2x(samples[start:end])
        path = args.output_dir / f"phantom-{args.event}-take-{number}-clean.wav"
        write_wav(path, clean, OUTPUT_RATE)
        print(
            f"Take {number}: {start / SOURCE_RATE:.2f}-"
            f"{end / SOURCE_RATE:.2f}s -> {path}"
        )

    print(
        f"Wrote {review} ({len(samples) / SOURCE_RATE:.3f}s) "
        f"and {len(takes)} clean takes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
