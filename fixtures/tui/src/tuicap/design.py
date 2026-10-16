"""The project's design file, design.json at the project root (README.md, "Design system"):
fonts, colours, grain and logo, every key optional. An unnamed font role falls back to a system
font; a named path must exist; a named family resolves through brand/fonts/resolved.json, which
tools/fonts.py writes. The brand skill generates the file from BRAND.md (README.md, "Brand")."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from functools import cache, lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DESIGN_JSON = ROOT / "design.json"
HELP = f"{DESIGN_JSON} (README.md, \"Design system\")"
FONT_KEYS = {"regular", "bold", "italic", "bold_italic", "mono", "weights", "family"}
FONT_EXT = (".ttf", ".otf", ".ttc")  # a font role ending so is a path, anything else a family name
RESOLVED = ROOT / "brand" / "fonts" / "resolved.json"  # tools/fonts.py: role key -> font file
LOGO_KEYS = ("on_dark", "on_light")  # the logo for a dark ground, the logo for a light ground
OBJECT_KEYS = ("fonts", "colors", "logo", "fonts.weights")  # keys whose value must be a JSON object
COLORS = {"background": "#000000", "text": "#ffffff", "secondary": "#a0a0a0", "accent": "#ffffff"}
FC_TIMEOUT = 10  # seconds
SYSTEM = {"mono": ("DejaVu Sans Mono", "Menlo.ttc", "DejaVuSansMono.ttf")}  # fc-match family, macOS, Linux file


def read() -> dict:
    """design.json parsed, {} when absent; ValueError when it is not JSON or has the wrong shape."""
    if not DESIGN_JSON.exists():
        return {}
    try:
        data = json.loads(DESIGN_JSON.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"{HELP}: not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(  # noqa: TRY004 - the documented error is ValueError
            f"{HELP}: expected a JSON object at the top level, got {type(data).__name__}")
    try:
        check_objects(data)
    except ValueError as e:
        raise ValueError(f"{HELP}: {e}") from e
    return data


def check_objects(data: dict) -> None:
    """ValueError naming the first of fonts, colors, logo and fonts.weights that is not an object."""
    for key in OBJECT_KEYS:
        value = data
        for part in key.split("."):
            value = value.get(part, {}) if isinstance(value, dict) else {}
        if not isinstance(value, dict):
            raise ValueError(f"{key} = {value!r}: expected an object")  # noqa: TRY004 - the documented error is ValueError


@lru_cache(maxsize=1)
def load() -> dict:
    data = read()
    bad = validate(data)
    if bad:
        raise ValueError(f"{HELP}: {bad[0]}")
    fonts, logos = data.get("fonts", {}), data.get("logo", {})
    named = {k: v for k, v in font_roles(fonts).items() if not is_family(v)}
    named.update({f"logo.{k}": v for k, v in logos.items()})
    for key, rel in named.items():
        if not (ROOT / str(rel)).is_file():
            raise FileNotFoundError(f"{key} in {DESIGN_JSON} is {rel!r}, but {ROOT / str(rel)} does not exist")
    return data


def validate(data: dict) -> list[str]:
    """Every problem in a parsed design.json, [] when it is valid (files are not checked);
    ValueError when fonts, colors, logo or fonts.weights is not an object."""
    check_objects(data)
    fonts, colors, logos = data.get("fonts", {}), data.get("colors", {}), data.get("logo", {})
    bad = [f"unknown key {k}" for k in sorted(set(data) - {"fonts", "colors", "grain", "logo"})]
    bad += [f"unknown key fonts.{k}" for k in sorted(set(fonts) - FONT_KEYS)]
    family = fonts.get("family", "x")
    if not isinstance(family, str) or not family.strip() or not is_family(family):
        bad.append(f"fonts.family = {family!r}: expected a family name")
    bad += [f"{k} = {v!r}: expected a font file path or a family name" for k, v in font_roles(fonts).items()
            if not isinstance(v, str) or not v.strip()]
    bad += [f"colors.{k} = {v!r}: expected one of {', '.join(COLORS)} as #rrggbb" for k, v in colors.items()
            if k not in COLORS or not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v))]
    grain = data.get("grain", 0)
    if isinstance(grain, bool) or not isinstance(grain, (int, float)) or grain < 0:
        bad.append(f"grain = {grain!r}: expected a number >= 0")
    bad += [f"unknown key logo.{k}" for k in sorted(set(logos) - set(LOGO_KEYS))]
    bad += [f"logo.{k} = {v!r}: expected an .svg or .png path" for k, v in logos.items()
            if not str(v).lower().endswith((".svg", ".png"))]
    return bad


def is_family(value) -> bool:
    return not str(value).lower().endswith(FONT_EXT)


def font_roles(fonts: dict) -> dict:
    """{role key: path or family name}; `family` fills regular, bold, italic and bold_italic
    for each of those the file leaves unset."""
    roles = {f"fonts.{k}": v for k, v in fonts.items() if k not in ("weights", "family")}
    if fonts.get("family"):
        roles = {**{f"fonts.{k}": fonts["family"] for k in ("regular", "bold", "italic", "bold_italic")}, **roles}
    roles.update({f"fonts.weights.{w}": v for w, v in fonts.get("weights", {}).items()})
    return roles


@lru_cache(maxsize=1)
def resolved() -> dict:
    """resolved.json when it was built from this design.json, else {}."""
    try:
        data = json.loads(RESOLVED.read_text())
    except (OSError, ValueError):
        return {}
    ok = isinstance(data, dict) and data.get("design_json_sha256") == hashlib.sha256(DESIGN_JSON.read_bytes()).hexdigest()
    return data if ok else {}


def font_path(key: str, value: str) -> str:
    """The file for a role: the path under the project root, or the family's file from resolved.json."""
    if not is_family(value):
        return str(ROOT / value)
    path = resolved().get(key)
    if not isinstance(path, str) or not (ROOT / path).is_file():
        raise FileNotFoundError(f"{key} in {DESIGN_JSON} names the family {value!r}, which {RESOLVED} does not "
                                f"resolve to a file here: run `uv run tools/fonts.py` from the project root {ROOT}")
    return str(ROOT / path)


def color(name: str) -> str:
    return load().get("colors", {}).get(name, COLORS[name])


def mono() -> str:
    value = font_roles(load().get("fonts", {})).get("fonts.mono")
    return font_path("fonts.mono", value) if value else system("mono")


def fc_match(family: str) -> str:
    """The file fontconfig picks for a family; "" when it fails or times out."""
    try:
        return subprocess.run(["fc-match", "-f", "%{file}", family], check=False, capture_output=True,
                              text=True, timeout=FC_TIMEOUT).stdout
    except subprocess.TimeoutExpired:
        return ""


@cache
def system(kind: str) -> str:
    family, mac, linux = SYSTEM[kind]
    paths = [f"/System/Library/Fonts/{mac}"] if sys.platform == "darwin" else []
    if sys.platform != "darwin" and shutil.which("fc-match"):
        paths.append(fc_match(family))
    paths += [f"/usr/share/fonts/{d}/{linux}" for d in ("truetype/dejavu", "TTF", "dejavu")]
    path = next((p for p in paths if p and Path(p).is_file()), None)
    if path is None:
        raise FileNotFoundError(f"no system font {family}: install it or name a font file in {HELP}")
    return path
