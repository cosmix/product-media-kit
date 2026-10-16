"""`postkit selftest`: build and check a small made-up project in a temporary folder."""

import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from postkit.assemble import BuildError, build
from postkit.check import check, report

WEB_BOXES = {"dialog": [320, 180, 800, 540], "name": [380, 300, 680, 48], "save": [960, 620, 120, 44]}
TUI_BOXES = {"table": [40, 120, 760, 320]}
DRAFT = """---
title: Selftest
---

# A settings tour

![The settings dialog](shot:web/settings/dialog "Settings")

![The status table](shot:tui/status/main)
"""
IMAGES_JSON = {
    "defaults": {"width": 1200},
    "web/settings/dialog": {"crop": "dialog", "highlight": ["save"], "callouts": ["name", "save"]},
    "tui/status/main": {"frame": "terminal", "highlight": ["table"]},
}


def make_demo(root: Path) -> None:
    """Write a project: a web and a tui still with their manifests, project.json, a draft and images.json."""
    _web_still(root / "captures" / "web" / "settings" / "dialog.png")
    _tui_still(root / "captures" / "tui" / "status" / "main.png")
    _manifest(root, "web", "settings/dialog", (1440, 900), WEB_BOXES)
    _manifest(root, "tui", "status/main", (1200, 720), TUI_BOXES)
    (root / "project.json").write_text(json.dumps({"slug": "selftest", "media": ["blog"]}), encoding="utf-8")
    (root / "post").mkdir()
    (root / "post" / "draft.md").write_text(DRAFT, encoding="utf-8")
    (root / "post" / "images.json").write_text(json.dumps(IMAGES_JSON, indent=2), encoding="utf-8")


def run() -> int:
    """Build then check the demo project; 0 only when the check finds no ERROR."""
    with tempfile.TemporaryDirectory(prefix="postkit-selftest-") as tmp:
        root = Path(tmp)
        make_demo(root)
        try:
            result = build(root)
        except BuildError as e:
            print(f"selftest: build failed:\n{e}", file=sys.stderr)
            return 1
        for path in result.written:
            print(f"wrote {path}")
        errors = report(check(root))
        print(f"selftest: {'FAILED' if errors else 'ok'}")
        return 1 if errors else 0


def _manifest(root: Path, source: str, shot_id: str, size: tuple[int, int], boxes: dict) -> None:
    entry = {"id": shot_id, "kind": "still", "file": f"{shot_id}.png", "width": size[0], "height": size[1],
             "scale": 1.0, "boxes": boxes}
    path = root / "captures" / source / "manifest.json"
    path.write_text(json.dumps({"source": source, "shots": [entry]}, indent=2), encoding="utf-8")


def _web_still(path: Path) -> None:
    img = Image.new("RGB", (1440, 900), "#f9fafb")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 240, 900], fill="#e5e7eb")
    x, y, w, h = WEB_BOXES["dialog"]
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill="#ffffff", outline="#d1d5db", width=2)
    x, y, w, h = WEB_BOXES["name"]
    draw.rectangle([x, y, x + w, y + h], fill="#ffffff", outline="#9ca3af", width=2)
    x, y, w, h = WEB_BOXES["save"]
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill="#16a34a")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _tui_still(path: Path) -> None:
    img = Image.new("RGB", (1200, 720), "#0b1020")
    draw = ImageDraw.Draw(img)
    for row in range(16):
        color = "#93c5fd" if row % 4 == 0 else "#d1d5db"
        draw.rectangle([60, 140 + row * 18, 60 + 300 + (row * 37) % 400, 150 + row * 18], fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
