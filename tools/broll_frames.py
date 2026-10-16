"""B-roll continuity for tools/genvideo.py: an "images" entry frame:<shot id>, frame:<shot id>@last or
frame:<shot id>@<seconds> names a frame of another shot's clip, which ffmpeg extracts to a png.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

ID = r"[A-Za-z0-9_-]+"
FRAME = re.compile(rf"frame:({ID})(?:@(last|\d+(?:\.\d+)?))?")
GRAMMAR = "frame:<shot id>, frame:<shot id>@last or frame:<shot id>@<seconds>"


def parse(sid, name):
    """(shot id, "last" or the seconds as written) for a frame: entry, None for a path."""
    if not name.startswith("frame:"):
        return None
    m = FRAME.fullmatch(name)
    if m is None:
        raise ValueError(f"[{sid}] {name!r} is not {GRAMMAR}")
    return m[1], m[2] or "last"


def parents(shot):
    """Shot ids a shot's well-formed frame: entries name, first use first; [] for a malformed shot."""
    names = shot.get("images") if isinstance(shot, dict) else None
    if not isinstance(names, list):
        return []
    found = (FRAME.fullmatch(n) for n in names if isinstance(n, str))
    return list(dict.fromkeys(m[1] for m in found if m))


def extract(sid, clip, at, folder, length):
    """Write frame `at` ("last" or seconds) of `clip` to folder/<clip stem>@<at>.png afresh; return its path.

    `length(clip)` is the clip's seconds or None, for the error when the clip has no such frame.
    """
    parent = clip.stem
    seek, take = (["-sseof", "-1"], ["-update", "1"]) if at == "last" else (["-ss", at], ["-frames:v", "1"])
    out = folder / f"{parent}@{at}.png"
    try:
        err = ffmpeg_png([*seek, "-i", str(clip), *take], out)
    except OSError as e:  # ffmpeg missing, the folder unwritable
        raise ValueError(f"[{sid}] cannot extract frame:{parent}@{at} with ffmpeg: {e}") from e
    if err is None:
        return out
    secs = length(clip)
    known = f" (the clip is {secs} s long)" if secs is not None else ""
    what = "the last frame" if at == "last" else f"a frame at {at} s"
    why = f": {err[:300]}" if err else ""
    raise ValueError(f"[{sid}] ffmpeg cannot read {what} from {parent}'s clip{known}{why}")


def ffmpeg_png(args, out):
    """Run ffmpeg `args` into a temporary png, then move it to `out`: None when written, else ffmpeg's stderr.

    The temporary file is this call's own, since two shots may extract the same frame at once.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{out.stem}.", suffix=".tmp.png", dir=out.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", *args, str(tmp)], check=False, capture_output=True,
                           text=True)
        if r.returncode == 0 and tmp.stat().st_size > 0:
            os.replace(tmp, out)
            return None
        return r.stderr.strip()
    finally:
        tmp.unlink(missing_ok=True)
