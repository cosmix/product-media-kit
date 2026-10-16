"""post/images.json: per-shot treatment with `defaults` merged under each entry.

    {"defaults": {...}, "<source>/<scenario>/<label>": {"frame": "browser"|"terminal"|"none",
     "crop": "<box>"|null, "pad": 24, "highlight": ["<box>"], "callouts": ["<box>"], "width": 1600}}

With no `frame`, a web shot gets the browser frame; tui, motion, broll and video shots get none
(tuicap already draws a padded terminal; the others are full frames).
"""

import json
from dataclasses import replace
from pathlib import Path

from postkit.images import Treatment
from postkit.manifest import Shot

KEYS = ("frame", "crop", "pad", "highlight", "callouts", "width")
FRAMES = ("browser", "terminal", "none")
DEFAULT_FRAME = {"web": "browser", "tui": "none", "motion": "none", "broll": "none", "video": "none"}


def read_images_json(root: Path) -> dict[str, dict]:
    """root/post/images.json as {key: object}, {} when absent; ValueError when malformed."""
    path = root / "post" / "images.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: cannot read: {e}") from e
    if isinstance(data, dict) and all(isinstance(value, dict) for value in data.values()):
        return data
    raise ValueError(f'{path}: expected an object mapping "defaults" and shot refs to objects')


def treatment_for(shot: Shot, config: dict[str, dict]) -> tuple[Treatment, list[str]]:
    """The shot's treatment from `defaults` and its own entry, and every problem with it."""
    spec = {**config.get("defaults", {}), **config.get(shot.ref, {})}
    where = f"images.json {shot.ref}"
    errors = [f"{where}: unknown key {k!r} (expected {', '.join(KEYS)})" for k in sorted(set(spec) - set(KEYS))]
    base = Treatment(frame=DEFAULT_FRAME[shot.source])
    treatment = replace(base, **{k: spec[k] for k in KEYS if k in spec})
    errors += [f"{where}: {problem}" for problem in _problems(treatment, shot)]
    return treatment, errors


def _problems(t: Treatment, shot: Shot) -> list[str]:
    out = []
    if t.frame not in FRAMES:
        out.append(f"frame {t.frame!r}: expected one of {', '.join(FRAMES)}")
    for key, value, low in (("pad", t.pad, 0), ("width", t.width, 1)):
        if not isinstance(value, int) or isinstance(value, bool) or value < low:
            out.append(f"{key} {value!r}: expected an integer >= {low}")
    if t.crop is not None and not isinstance(t.crop, str):
        out.append(f"crop {t.crop!r}: expected a box name or null")
    for key, names in (("highlight", t.highlight), ("callouts", t.callouts)):
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            out.append(f"{key} {names!r}: expected a list of box names")
    return out if out or shot.kind == "clip" else _box_problems(t, shot)


def _box_problems(t: Treatment, shot: Shot) -> list[str]:
    known = ", ".join(sorted(shot.boxes)) or "none"
    named = [("crop", t.crop)] if t.crop else []
    named += [("highlight", n) for n in t.highlight] + [("callouts", n) for n in t.callouts]
    out = [f"{key} {name!r}: the shot has no such box (boxes: {known})"
           for key, name in named if name not in shot.boxes]
    if t.crop in shot.boxes:
        x, y, w, h = shot.boxes[t.crop]
        if w == 0 or h == 0 or x >= shot.width or y >= shot.height:
            out.append(f"crop {t.crop!r}: box {[x, y, w, h]} lies outside the {shot.width}x{shot.height} image")
    return out
