"""`postkit add`: bring a PNG, a video frame or a video segment into captures/<source>/.

Sources are motion, broll and video. A PNG is copied; `--at T` grabs one frame as a PNG; a segment
(`--from A --to B`) becomes a GIF (15 fps, at most 960 px wide), a VP9 WebM and a poster PNG, with
the capture engines' ffmpeg settings. The files land in captures/<source>/<scenario>/<label>.* and
captures/<source>/manifest.json gains (or replaces) the entry, written atomically.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from postkit.common import NAME_RE, copy_atomic, part_path, write_atomic

ADD_SOURCES = ("motion", "broll", "video")
GIF_FPS = 15
GIF_MAX_WIDTH = 960
WEBM_FILTER = "scale=trunc(iw/2)*2:trunc(ih/2)*2:out_color_matrix=bt709:out_range=tv,format=yuv420p"
GIF_FILTER = (f"fps={GIF_FPS},scale='min({GIF_MAX_WIDTH},iw)':-2:flags=lanczos,"
              "split[a][b];[a]palettegen[p];[b][p]paletteuse")


class AddError(ValueError):
    """The input cannot be added; the message says what to change."""


def parse_ref(ref: str) -> tuple[str, str, str]:
    """(source, scenario, label) of `<source>/<scenario>/<label>`; AddError when malformed or unsafe."""
    parts = ref.split("/")
    if len(parts) != 3 or parts[0] not in ADD_SOURCES or not all(NAME_RE.fullmatch(p) for p in parts[1:]):
        raise AddError(f"{ref!r}: expected <source>/<scenario>/<label> with source one of "
                       f"{', '.join(ADD_SOURCES)}, scenario and label matching {NAME_RE.pattern}")
    return parts[0], parts[1], parts[2]


def add(root: Path, ref: str, file: Path, *, at: float | None = None, start: float | None = None,
        end: float | None = None) -> list[Path]:
    """Add `file` as shot `ref`; returns the files written under captures/<source>/."""
    source, scenario, label = parse_ref(ref)
    segment = start is not None or end is not None
    if not file.is_file():
        raise AddError(f"{file}: no such file")
    if segment and (start is None or end is None or at is not None):
        raise AddError("use --from and --to together, and not with --at")
    if any(t is not None and t < 0 for t in (at, start, end)) or (segment and end <= start):
        raise AddError("times must be >= 0 and --to must be after --from")
    base = root / "captures" / source
    stem = base / scenario / label
    if segment:
        entry, written = _clip(file, stem, f"{scenario}/{label}", start, end)
    else:
        entry, written = _still(file, stem, f"{scenario}/{label}", at)
    _update_manifest(base / "manifest.json", source, entry)
    return written


def _still(file: Path, stem: Path, shot_id: str, at: float | None) -> tuple[dict, list[Path]]:
    png = stem.with_suffix(".png")
    if at is not None:
        _frame(file, png, at)
    elif file.suffix.lower() == ".png":
        copy_atomic(file, png)
    else:
        raise AddError(f"{file}: not a PNG; give --at T for a frame or --from/--to for a segment")
    return _entry(shot_id, "still", "shots", f"{shot_id}.png", png, {}), [png]


def _clip(file: Path, stem: Path, shot_id: str, start: float, end: float) -> tuple[dict, list[Path]]:
    webm, gif, png = (stem.with_suffix(ext) for ext in (".webm", ".gif", ".png"))
    _ffmpeg(webm, "webm", ["-ss", str(start), "-t", str(end - start), "-i", str(file)],
            ["-an", "-vf", WEBM_FILTER, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32",
             "-pix_fmt", "yuv420p", "-row-mt", "1", "-colorspace", "bt709", "-color_primaries", "bt709",
             "-color_trc", "bt709", "-color_range", "tv"])
    _ffmpeg(gif, "gif", ["-i", str(webm)], ["-filter_complex", GIF_FILTER])
    _frame(webm, png, 0.0)
    extra = {"file": f"{shot_id}.gif", "webm": f"{shot_id}.webm", "poster": f"{shot_id}.png",
             "duration": round(end - start, 3)}
    entry = _entry(shot_id, "clip", "clip", extra["file"], png, extra)
    return entry, [webm, gif, png]


def _entry(shot_id: str, kind: str, origin: str, file: str, png: Path, extra: dict) -> dict:
    try:
        with Image.open(png) as img:
            width, height = img.size
    except (OSError, ValueError) as e:
        raise AddError(f"{png}: not a readable PNG: {e}") from e
    return {"id": shot_id, "kind": kind, "origin": origin, "file": file, "width": width,
            "height": height, "scale": 1.0, "boxes": {}, **extra}


def _frame(video: Path, png: Path, t: float) -> None:
    """One frame of `video` at `t` seconds as a PNG."""
    _ffmpeg(png, "image2", ["-ss", str(t), "-i", str(video)],
            ["-frames:v", "1", "-c:v", "png", "-update", "1"])


def _ffmpeg(target: Path, fmt: str, inputs: list[str], outputs: list[str]) -> None:
    """Run ffmpeg into a part file and replace `target` with it, so a failure leaves nothing half-written."""
    if shutil.which("ffmpeg") is None:
        raise AddError("ffmpeg is not installed; run ./system-deps.sh outside Claude Code")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = part_path(target)
    try:
        result = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, *outputs, "-f", fmt, str(part)],
                                check=False, capture_output=True, text=True)
        if result.returncode != 0 or not part.is_file():
            raise AddError(f"ffmpeg failed for {target.name}: {result.stderr.strip()}")
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)


def _update_manifest(path: Path, source: str, entry: dict) -> None:
    """Write `entry` into the manifest, replacing the entry with the same id; other entries stay."""
    shots: list = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise AddError(f"{path}: cannot read: {e}") from e
        if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
            raise AddError(f'{path}: expected an object with a "shots" list')
        shots = [s for s in data["shots"] if not (isinstance(s, dict) and s.get("id") == entry["id"])]
    shots.append(entry)
    write_atomic(path, (json.dumps({"source": source, "shots": shots}, indent=2) + "\n").encode("utf-8"))
