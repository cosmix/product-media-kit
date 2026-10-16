"""captures/tui/manifest.json: the shared capture manifest the post kit reads."""

from __future__ import annotations

import json
from pathlib import Path


def update(out_dir: Path, source: str, scenario: str, origin: str, entries: list[dict]) -> Path:
    """Replace every entry of `scenario` whose origin (`shots` or `clip`) is `origin` by `entries`,
    keep the rest, and write manifest.json atomically: a stills-only run never drops the
    scenario's clip entry and the reverse. An entry of another scenario or origin, a repeated id
    or a manifest of another source is an error."""
    prefix = f"{scenario}/"
    ids = [entry["id"] for entry in entries]
    stray = [i for i in ids if not i.startswith(prefix)]
    if stray:
        raise ValueError(f"entries of scenario {scenario!r} must have ids starting {prefix!r}: {stray}")
    wrong = [e["id"] for e in entries if e.get("origin") != origin]
    if wrong:
        raise ValueError(f"entries of origin {origin!r} must carry that origin: {wrong}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate ids in scenario {scenario!r}: {sorted(ids)}")
    path = out_dir / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {"source": source, "shots": []}
    if manifest.get("source") != source:
        raise ValueError(f"{path} holds source {manifest.get('source')!r}, not {source!r}")
    shots = [s for s in manifest.get("shots", [])
             if not (str(s["id"]).startswith(prefix) and s.get("origin") == origin)]
    manifest["shots"] = sorted([*shots, *entries], key=lambda s: s["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("manifest.json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp.replace(path)
    return path
