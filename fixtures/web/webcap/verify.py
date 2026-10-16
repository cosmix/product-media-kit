"""Smoothness check for the clips a video or both capture recorded (their `video` mp4).

For each clip: frame-time jitter from the container timestamps, the share of
frames that repeat their predecessor (no pixel changed by more than codec
noise), and that share restricted to frames where the scripted cursor moved.
Repeats are expected only where nothing on the page animates. The result is
written into each clip's manifest entry as `smoothness`.

    uv run python -m webcap.verify [--dir captures/web]
"""

from __future__ import annotations

import argparse
import itertools
import subprocess
from pathlib import Path

import numpy as np

from webcap import manifest
from webcap.capture import OUT, SOURCE


def frame_times(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return np.array([float(x.strip(",")) for x in out.split()])


def frame_diffs(path: Path, width: int, height: int) -> np.ndarray:
    """Per frame, the largest pixel change from its predecessor, compared at width x height."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
         f"scale={width}:{height}:flags=area,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    ).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, height, width).astype(np.int16)
    # Largest per-pixel change: a frame with none at all repeats its predecessor.
    return np.array([np.abs(b - a).max() for a, b in itertools.pairwise(frames)])


def check(path: Path, entry: dict) -> dict:
    times = frame_times(path)
    deltas = np.diff(times)
    # Compared at CSS size: the area downscale averages codec noise away.
    css = round(entry["width"] / entry["scale"]), round(entry["height"] / entry["scale"])
    diffs = frame_diffs(path, *css)
    dup = diffs <= 2
    cursor = entry.get("cursor", [])
    moving = np.array([
        (a["x"], a["y"]) != (b["x"], b["y"]) for a, b in itertools.pairwise(cursor)
    ][: len(dup)], dtype=bool)
    return {
        "frames": len(times),
        "fps_mean": round(float(1 / deltas.mean()), 3),
        "frame_time_jitter_ms": round(float(deltas.std() * 1000), 4),
        "duplicate_ratio": round(float(dup.mean()), 4),
        "moving_frames": int(moving.sum()),
        "duplicate_ratio_while_cursor_moves": round(float(dup[moving].mean()), 4) if moving.any() else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, default=OUT)
    args = parser.parse_args()
    data = manifest.read(args.dir, SOURCE)
    clips = [e for e in data["shots"] if e["kind"] == "clip" and "video" in e]
    if not clips:
        raise SystemExit(f"{args.dir / manifest.NAME}: no clip with a video file "
                         "(capture with --clips --for video or both)")
    for entry in clips:
        path = args.dir / entry["video"]
        if not path.exists():
            print(f"{entry['id']}: {path} is missing")
            continue
        entry["smoothness"] = check(path, entry)
        print(entry["id"], entry["smoothness"])
    manifest.write(args.dir, data)


if __name__ == "__main__":
    main()
