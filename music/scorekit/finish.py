"""Finish a generated song (a Lyria take) into the project's soundtrack.

The take is resampled to 48 kHz, its beat and bar grid measured from the audio (beatgrid), cut
from `start` to `end` with both snapped to the nearest bar accent, faded out over its last `fade`
seconds, and mastered to scorekit's -16 LUFS with a -1 dBTP true-peak ceiling (mix.master). The
manifest carries the keys render.py writes where they apply (no stems, no sections, no sample
libraries) plus `source`, which names the take and the edits.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr

from .beatgrid import BeatGrid, measure
from .library import SR
from .mix import master
from .timing import narration_windows

TARGET_LUFS = -16.0
CEILING_DBTP = -1.0
CREDIT = "## Lyria soundtrack"


def load(path: Path) -> tuple[np.ndarray, int]:
    """(48 kHz stereo float, the file's own sample rate)."""
    x, rate = sf.read(path, always_2d=True)
    x = np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x[:, :2]
    return (x if rate == SR else soxr.resample(x, rate, SR)), rate


def _nearest(times: np.ndarray, t: float) -> float:
    return float(times[np.abs(times - t).argmin()])


def plan_cut(grid: BeatGrid, length: float, start: float, end: float | None) -> tuple[float, float, list[str]]:
    """(first, last) second of the take to keep, both on bar accents (a start of 0 stays 0), and notes
    for the human. `end` is the soundtrack's length from `start`; None keeps every whole bar."""
    downs = grid.downbeats(0.0, length)
    first = 0.0 if start == 0 else _nearest(downs, start)
    usable = downs[downs >= first + 4 * grid.period - 1e-6]
    if not len(usable):
        raise ValueError(f"the take holds less than one bar after {first:.2f} s")
    if end is None:
        return first, float(usable[-1]), [f"no --end and no timeline: kept every whole bar, {usable[-1] - first:.2f} s"]
    last = _nearest(usable, first + end)
    notes = []
    if first + end > usable[-1] + 2 * grid.period:
        notes.append(f"the take has {usable[-1] - first:.2f} s of whole bars from {first:.2f} s, "
                     f"less than the {end:.2f} s asked for")
    elif abs(last - first - end) > 0.005:
        notes.append(f"end snapped from {end:.2f} s to {last - first:.2f} s (a bar accent): set the "
                     "timeline's total to it, or pass --end")
    return first, last, notes


def manifest(grid: BeatGrid, first: float, total: float, report: dict, folder: str, source: dict) -> dict:
    downs = np.maximum(grid.downbeats(first - 0.02, first + total) - first, 0.0)
    bar0 = float(downs[0])
    beats = grid.beats(first + bar0, first + total) - first
    bpm = round(grid.bpm, 3)
    return {
        "sample_rate": SR, "duration": round(total, 4), "bpm": bpm, "time_signature": "4/4",
        "bar_0_at": round(bar0, 4), "bar_length": round(4 * grid.period, 5),
        "tempo_map": [{"bar": 0.0, "bpm": bpm, "at": round(bar0, 4)}],
        "downbeats": [round(float(t), 4) for t in downs],
        "beats": [round(float(t), 4) for t in beats],
        "sections": [], "speech_windows": narration_windows(),
        "file": f"{folder}/soundtrack.wav", "stems": {},
        "format": "WAV PCM 24-bit, 48 kHz, stereo", "loudness": report,
        "sample_libraries": [], "source": source,
    }


def finish(take: Path, out: Path, start: float, end: float | None, fade: float,
           source: dict) -> tuple[dict, list[str]]:
    """Write out/soundtrack.wav from `take` (removing any out/stems/); return (manifest, notes)."""
    x, rate = load(take)
    grid = measure(x)
    first, last, notes = plan_cut(grid, len(x) / SR, start, end)
    cut = x[round(first * SR):round(last * SR)]
    total = len(cut) / SR
    if not 0 < fade < total:
        raise ValueError(f"--fade must be above 0 and under the soundtrack's {total:.2f} s")
    mix, _, report = master({"mix": cut}, total, TARGET_LUFS, CEILING_DBTP, fade)
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "soundtrack.wav", mix.astype(np.float32), SR, subtype="PCM_24")
    shutil.rmtree(out / "stems", ignore_errors=True)  # stems of an earlier score would not match
    source = source | {"sample_rate": rate, "start": round(first, 4), "end": round(last, 4),
                       "fade": fade, "requested_end": end}
    return manifest(grid, first, total, report, out.name, source), notes


def write_credit(path: Path, lines: list[str]) -> None:
    """Replace (or add, at the end) the Lyria soundtrack section of music/CREDITS.md. It has no
    Licence line, so editkit.credit_data never puts it on screen."""
    text = path.read_text() if path.exists() else "# Sample credits\n"
    text = re.sub(rf"^{CREDIT}\n.*?(?=^## |\Z)", "", text, flags=re.MULTILINE | re.DOTALL)
    path.write_text(text.rstrip("\n") + f"\n\n{CREDIT}\n\n" + "\n".join(lines) + "\n")
