"""Shared harness for postkit tests: a minimal blog project root built in a temp folder."""

import json
from pathlib import Path

import pytest
from PIL import Image

SLUG = "demo-post"
STILLS = {
    "settings/dialog": ((320, 200), (40, 90, 160), {"save": [200, 150, 80, 30]}),
    "settings/menu": ((240, 160), (200, 120, 40), {"item": [20, 20, 100, 24]}),
}


def write_manifest(root: Path, source: str, shots: list[dict]) -> Path:
    """Write captures/<source>/manifest.json in the pinned format and return its path."""
    path = root / "captures" / source / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"source": source, "shots": shots}))
    return path


@pytest.fixture
def make_project(tmp_path: Path) -> Path:
    """A project root with project.json, captures/web/manifest.json and two Pillow-made PNGs."""
    root = tmp_path / "project"
    shots = []
    for shot_id, ((w, h), color, boxes) in STILLS.items():
        file = root / "captures" / "web" / f"{shot_id}.png"
        file.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (w, h), color).save(file)
        shots.append(
            {
                "id": shot_id,
                "kind": "still",
                "file": f"{shot_id}.png",
                "width": w,
                "height": h,
                "scale": 1.0,
                "boxes": boxes,
            }
        )
    write_manifest(root, "web", shots)
    (root / "project.json").write_text(json.dumps({"slug": SLUG}))
    (root / "post").mkdir()
    return root
