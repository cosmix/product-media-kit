"""Colours and the bold font from root/design.json, for highlights, callouts and frames.

The bold font is the `fonts.bold` file when design.json names one, else the file
tools/fonts.py resolved for role `fonts.bold` in brand/fonts/resolved.json (only when its
`design_json_sha256` is the hash of the current design.json), else the system's bold DejaVu Sans
from fc-match, else None (Pillow's built-in font).
"""

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

COLORS = {"accent": "#2563eb", "text": "#111111", "background": "#ffffff", "secondary": "#6b7280"}
FONT_EXT = (".ttf", ".otf", ".ttc")
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class Design:
    accent: str = COLORS["accent"]
    text: str = COLORS["text"]
    background: str = COLORS["background"]
    secondary: str = COLORS["secondary"]
    bold_font: Path | None = None


def load(root: Path) -> Design:
    """The design for the project at `root`; ValueError when design.json is malformed."""
    path = root / "design.json"
    data = _read(path)
    colors, fonts = _object(data, "colors", path), _object(data, "fonts", path)
    picked = {}
    for name, default in COLORS.items():
        value = colors.get(name, default)
        if not isinstance(value, str) or not HEX_RE.fullmatch(value):
            raise ValueError(f"{path}: colors.{name} = {value!r}: expected #rrggbb")
        picked[name] = value
    return Design(**picked, bold_font=_bold_font(root, fonts))


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: cannot read: {e}") from e
    if isinstance(data, dict):
        return data
    raise ValueError(f"{path}: expected a JSON object")


def _object(data: dict, key: str, path: Path) -> dict:
    value = data.get(key, {})
    if isinstance(value, dict):
        return value
    raise ValueError(f"{path}: {key} must be an object")


def _bold_font(root: Path, fonts: dict) -> Path | None:
    named = fonts.get("bold")
    if isinstance(named, str) and named.lower().endswith(FONT_EXT) and (root / named).is_file():
        return root / named
    return _resolved_bold(root) or _fc_match()


def _resolved_bold(root: Path) -> Path | None:
    """The `fonts.bold` file of resolved.json; None when it is absent, or was resolved from another design.json."""
    try:
        data = json.loads((root / "brand" / "fonts" / "resolved.json").read_text(encoding="utf-8"))
        current = hashlib.sha256((root / "design.json").read_bytes()).hexdigest()  # as tuicap.design does
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("design_json_sha256") != current:
        return None
    value = data.get("fonts.bold")
    path = root / value if isinstance(value, str) else None
    return path if path is not None and path.is_file() else None


def _fc_match() -> Path | None:
    exe = shutil.which("fc-match")
    if exe is None:
        return None
    try:
        found = subprocess.run([exe, "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True,
                               timeout=10, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(found) if found and Path(found).is_file() else None
