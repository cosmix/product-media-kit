"""The project's own capture module, fixtures/web/product.py, and its project.json.

At least one of `SHOTS` ({scenario: async def (shooter: webcap.shots.Shooter) -> None}) and
`CLIPS` ({scenario: async def (director: webcap.director.Director) -> None}). Optional:
`CLIP_PATHS` ({scenario: "/path"}, default "/"); `VIEWPORT` ((width, height) in CSS px, default
from project.json: 1920x1080 when its media include video, else 1440x900); `THEME` ("light" or
"dark", the page's color scheme, default "light"); `LOCAL_STORAGE` ({key: JSON value} set before
every page load, e.g. the UI theme); `FONT_PROBES` ((scene, path, {label: CSS selector}), reported
in the manifest as the fonts each element rendered with).

Two ways to run the product:

- live: `BASE_URL` (or env `PRODUCT_URL`, which wins) points at a running product; pages load
  from there in real time.
- mock: `World` (a webcap.world.World subclass, built with no arguments, one scene per
  scenario) and `build_app(world) -> aiohttp.web.Application` (a mock server around the built
  frontend); pages load from it on a scripted clock.

Scenario names (the keys of SHOTS and CLIPS) match webcap.names.NAME_RE.

<project>/project.json ({"slug": ..., "media": ["video", "blog"], "fps": 30, "piano": "vsco"})
sets the default capture profile (webcap.profiles), the viewport and the video frame rate.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the project root, for tools/
from tools.metrics import timed  # noqa: F401 - the capture entry points import it from here
from tools.project_settings import read as project_settings

from webcap.names import check_name

WEB = Path(__file__).resolve().parents[1]
ROOT = WEB.parents[1]  # the project: fixtures/web/../..
MEDIA = ("video", "blog")


class ProjectError(ValueError):
    """product.py or project.json does not meet the contract above."""


def base_url(module) -> str | None:
    """The live product's URL: env PRODUCT_URL when set and non-empty, else module BASE_URL."""
    return os.environ.get("PRODUCT_URL") or getattr(module, "BASE_URL", None) or None


def mode(module) -> str:
    """The run mode: live when there is a base URL, else mock.

    Raises ProjectError naming every attribute the mode needs and the module lacks.
    """
    live = base_url(module) is not None
    needed = () if live else ("World", "build_app")
    missing = [name for name in needed if not hasattr(module, name)]
    if not hasattr(module, "SHOTS") and not hasattr(module, "CLIPS"):
        missing.insert(0, "SHOTS or CLIPS")
    if missing:
        hint = "" if live else " (or set BASE_URL / PRODUCT_URL to capture a running product)"
        raise ProjectError(f"missing {', '.join(missing)}{hint}")
    return "live" if live else "mock"


def check_names(module) -> None:
    """Every SHOTS and CLIPS key is a valid scenario name."""
    for attr in ("SHOTS", "CLIPS"):
        for key in getattr(module, attr, {}):
            try:
                check_name(f"{attr} scenario", key)
            except ValueError as err:
                raise ProjectError(str(err)) from None


def media(path: Path | None = None) -> list[str]:
    """project.json's `media` (default <ROOT>/project.json); [] when the file or key is absent.

    Raises ProjectError for unreadable JSON or a medium outside MEDIA.
    """
    path = path or ROOT / "project.json"
    if not path.exists():
        return []
    try:
        chosen = json.loads(path.read_text()).get("media") or []
    except (ValueError, AttributeError) as err:
        raise ProjectError(f"{path}: not a JSON object: {err}") from None
    if not isinstance(chosen, list) or any(m not in MEDIA for m in chosen):
        raise ProjectError(f"{path}: media must be a list of {', '.join(MEDIA)}, not {chosen!r}")
    return chosen


def default_profile(path: Path | None = None) -> str:
    """The capture profile project.json's media call for: both, video, or blog (the default)."""
    chosen = set(media(path))
    if chosen == set(MEDIA):
        return "both"
    return "video" if "video" in chosen else "blog"


def fps(path: Path | None = None) -> int:
    """project.json's `fps` (default <ROOT>/project.json), the video and both profiles' frame
    rate; 30 when the file or key is absent (tools/project_settings.py).

    Raises ProjectError for a value outside 1-120.
    """
    path = path or ROOT / "project.json"
    try:
        return project_settings(path.parent)["fps"]
    except ValueError as err:
        raise ProjectError(str(err)) from None


def viewport(module, path: Path | None = None) -> tuple[int, int]:
    """The module's VIEWPORT, else 1920x1080 when project.json's media include video, else
    1440x900."""
    if hasattr(module, "VIEWPORT"):
        return tuple(module.VIEWPORT)
    return (1920, 1080) if "video" in media(path) else (1440, 900)


@lru_cache(maxsize=1)
def product():
    path = WEB / "product.py"
    if not path.exists():
        sys.exit(f"no capture module: create {path} defining SHOTS or CLIPS (see webcap/project.py)")
    if str(WEB) not in sys.path:
        sys.path.insert(0, str(WEB))
    module = importlib.import_module("product")
    try:
        mode(module)
        check_names(module)
    except ProjectError as err:
        sys.exit(f"{path}: {err}")
    return module
