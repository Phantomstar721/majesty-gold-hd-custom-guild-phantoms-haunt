from __future__ import annotations

import argparse
import array
import math
from pathlib import Path
import wave


SAMPLE_RATE = 22_050
TARGET_PEAK_DB = -6.0
LOUDNESS_GAIN = 3.5
LIMITER_CEILING_DB = -1.0


def read_mono_pcm16(path: Path) -> list[float]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1:
            raise ValueError(f"{path}: expected mono audio")
        if wav.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16-bit PCM audio")
        if wav.getframerate() != SAMPLE_RATE:
            raise ValueError(f"{path}: expected {SAMPLE_RATE} Hz audio")
        frames = wav.readframes(wav.getnframes())

    samples = array.array("h")
    samples.frombytes(frames)
    return [sample / 32768.0 for sample in samples]


def resample_for_pitch(samples: list[float], speed: float) -> list[float]:
    """Lower pitch by slowing playback slightly; this also lengthens the delivery."""
    output_length = round(len(samples) / speed)
    output: list[float] = []
    for index in range(output_length):
        position = index * speed
        left = int(position)
        fraction = position - left
        right = min(left + 1, len(samples) - 1)
        output.append(samples[left] * (1.0 - fraction) + samples[right] * fraction)
    return output


def low_pass(samples: list[float], alpha: float) -> list[float]:
    output: list[float] = []
    state = 0.0
    for sample in samples:
        state += alpha * (sample - state)
        output.append(state)
    return output


def spectral_double(
    samples: list[float],
    semitones: float,
    window_seconds: float = 0.032,
) -> list[float]:
    """Create a same-duration, artifact-friendly granular pitch-shifted double."""
    pitch_factor = 2.0 ** (semitones / 12.0)
    delay_rate = 1.0 - pitch_factor
    window = max(8, round(window_seconds * SAMPLE_RATE))
    output: list[float] = []

    for index in range(len(samples)):
        phase_a = (index * delay_rate / window) % 1.0
        phase_b = (phase_a + 0.5) % 1.0

        def delayed(phase: float) -> float:
            position = index - phase * window
            if position <= 0:
                return 0.0
            left = int(position)
            fraction = position - left
            right = min(left + 1, len(samples) - 1)
            return samples[left] * (1.0 - fraction) + samples[right] * fraction

        weight_a = math.sin(math.pi * phase_a) ** 2
        weight_b = math.sin(math.pi * phase_b) ** 2
        output.append(delayed(phase_a) * weight_a + delayed(phase_b) * weight_b)

    return output


def add_layer(
    destination: list[float],
    source: list[float],
    delay_seconds: float,
    gain: float,
) -> None:
    delay = round(delay_seconds * SAMPLE_RATE)
    for index, sample in enumerate(source):
        target = index + delay
        if target < len(destination):
            destination[target] += sample * gain


def process(samples: list[float]) -> list[float]:
    # The main voice is lowered about 1.8 semitones. The measured slowdown is
    # intentional: it gives the Phantom a grave, weary weight without changing
    # the close ghost-halo treatment below.
    main = resample_for_pitch(samples, speed=0.9013)

    # A darker, independently pitch-shifted copy supplies the audible revenant quality.
    ghost = spectral_double(main, semitones=-4.0)
    ghost = low_pass(ghost, alpha=0.30)

    tail_seconds = 0.24
    output = [0.0] * (len(main) + round(tail_seconds * SAMPLE_RATE))
    add_layer(output, main, delay_seconds=0.0, gain=1.0)
    # Keep the double nearly coincident with the performance. The short granular
    # window and 4 ms offset read as shifting overtones instead of a second speaker.
    add_layer(output, ghost, delay_seconds=0.004, gain=0.25)

    # A dense, quiet halo avoids any one reflection reading as a literal echo.
    ambience = low_pass(main, alpha=0.34)
    add_layer(output, ambience, delay_seconds=0.018, gain=0.070)
    add_layer(output, ambience, delay_seconds=0.033, gain=0.055)
    add_layer(output, ambience, delay_seconds=0.049, gain=0.043)
    add_layer(output, ambience, delay_seconds=0.071, gain=0.030)
    add_layer(output, ambience, delay_seconds=0.096, gain=0.018)

    target_peak = 10.0 ** (TARGET_PEAK_DB / 20.0)
    peak = max(abs(sample) for sample in output)
    normalization = target_peak / peak
    output = [sample * normalization for sample in output]

    # Majesty's stock voices are substantially louder than a conventionally
    # normalized spoken recording. Apply the approved 3.5x makeup gain through
    # a smooth limiter so the average voice rises without hard PCM clipping.
    limiter_ceiling = 10.0 ** (LIMITER_CEILING_DB / 20.0)
    output = [
        limiter_ceiling * math.tanh(sample * LOUDNESS_GAIN / limiter_ceiling)
        for sample in output
    ]

    fade_samples = round(0.008 * SAMPLE_RATE)
    for index in range(fade_samples):
        output[-1 - index] *= index / fade_samples

    return output


def write_mono_pcm16(path: Path, samples: list[float]) -> None:
    pcm = array.array(
        "h",
        (
            round(max(-32768.0, min(32767.0, sample * 32768.0)))
            for sample in samples
        ),
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the reproducible Phantom revenant voice treatment."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    samples = read_mono_pcm16(args.input)
    processed = process(samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_mono_pcm16(args.output, processed)
    print(
        f"Wrote {args.output} "
        f"({len(processed) / SAMPLE_RATE:.3f}s, mono {SAMPLE_RATE} Hz PCM16)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
