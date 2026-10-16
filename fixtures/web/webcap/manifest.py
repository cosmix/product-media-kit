"""The capture manifest, captures/<source>/manifest.json: one entry per still or clip.

    {"source": "web", "shots": [{"id": "<scenario>/<label>", "kind": "still" | "clip",
                                 "origin": "shots" | "clip", "file": ..., "width": ...,
                                 "height": ..., "scale": ..., "boxes": {name: [x, y, w, h]}, ...}]}

`origin` says what wrote the entry: a SHOTS scenario (`shots`) or a CLIPS scenario (`clip`: the
clip itself and the stills its director took). Paths are relative to the manifest's folder; boxes
are integer pixels in the image file.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from webcap.media import write_atomic

NAME = "manifest.json"
ORIGINS = ("shots", "clip")


def read(out_dir: Path, source: str) -> dict:
    """The manifest in `out_dir` (an empty one when there is none); ValueError for another
    source's manifest."""
    path = out_dir / NAME
    if not path.exists():
        return {"source": source, "shots": []}
    data = json.loads(path.read_text())
    if data.get("source") != source:
        raise ValueError(f"{path} holds source {data.get('source')!r}, not {source!r}")
    return data


def write(out_dir: Path, data: dict) -> Path:
    """Write the manifest atomically; its path."""
    path = out_dir / NAME
    write_atomic(path, (json.dumps(data, indent=1) + "\n").encode())
    return path


def still_entry(scenario: str, label: str, size: tuple[int, int], scale: float,
                boxes: dict[str, list[int]], origin: str) -> dict:
    """The manifest entry of the still <scenario>/<label>.png."""
    return {
        "id": f"{scenario}/{label}", "kind": "still", "origin": origin,
        "file": f"{scenario}/{label}.png", "width": size[0], "height": size[1],
        "scale": scale, "boxes": boxes,
    }


def update(out_dir: Path, source: str, scenario: str, entries: list[dict],
           origins: Sequence[str] = ORIGINS) -> Path:
    """Replace the entries of `scenario` whose origin is in `origins` with `entries`; keep its
    entries of any other origin and every other scenario's. Sorted by id."""
    prefix = f"{scenario}/"
    ids = [entry["id"] for entry in entries]
    stray = [i for i in ids if not i.startswith(prefix)]
    if stray:
        raise ValueError(f"entries of scenario {scenario!r} must have ids starting {prefix!r}: {stray}")
    foreign = [entry["id"] for entry in entries if entry.get("origin") not in origins]
    if foreign:
        raise ValueError(f"entries {foreign} must have an origin in {list(origins)}")
    data = read(out_dir, source)
    kept = [shot for shot in data.get("shots", [])
            if not shot["id"].startswith(prefix) or shot.get("origin") not in origins]
    every = [*kept, *entries]
    ids = [shot["id"] for shot in every if shot["id"].startswith(prefix)]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate ids in scenario {scenario!r}: {sorted(ids)}")
    data["shots"] = sorted(every, key=lambda shot: shot["id"])
    return write(out_dir, data)


def annotate(out_dir: Path, source: str, key: str, value: Any) -> Path:
    """Set a top-level key beside `shots` (the capture's font report)."""
    if key in ("source", "shots"):
        raise ValueError(f"{key!r} is managed by update()")
    data = read(out_dir, source)
    data[key] = value
    return write(out_dir, data)
