"""The capture's selftest: a built-in page on the mock server's port, no product.py needed.

It stands in for a project module (SHOTS, CLIPS, VIEWPORT) and a mock World, so the selftest
runs the same open_page / Shooter / Director path a real capture does.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aiohttp import web

from webcap.profiles import Profile
from webcap.server import no_store
from webcap.world import Clock, World

SCENARIO = "selftest"
VIEWPORT = (960, 600)
HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>webcap selftest</title>
<style>
  body { margin: 0; font: 16px/1.5 system-ui, sans-serif; background: #f6f7f9; color: #1d2330; }
  main { max-width: 520px; margin: 96px auto; padding: 32px; background: #fff;
         border-radius: 12px; box-shadow: 0 2px 12px rgb(0 0 0 / 8%); }
  h1 { margin: 0 0 24px; font-size: 28px; }
  label { display: block; margin-bottom: 8px; font-weight: 600; }
  input { width: 100%; box-sizing: border-box; padding: 10px 12px; font: inherit;
          border: 1px solid #c4c9d4; border-radius: 8px; }
  button { margin-top: 20px; padding: 10px 20px; font: inherit; font-weight: 600; color: #fff;
           background: #3657e8; border: 0; border-radius: 8px; }
</style>
</head>
<body>
<main>
  <h1>webcap selftest</h1>
  <form>
    <label for="name">Project name</label>
    <input id="name" name="name" placeholder="my-product" autocomplete="off">
    <button type="button">Save</button>
  </form>
</main>
</body>
</html>
"""


def app() -> web.Application:
    async def index(_request: web.Request) -> web.StreamResponse:
        return no_store(web.Response(text=HTML, content_type="text/html"))

    application = web.Application()
    application.router.add_get("/", index)
    return application


def world() -> World:
    return World({SCENARIO: Clock(((0.0, 0.0), (1.0, 1.0)))})


async def page(shooter) -> None:
    await shooter.goto("/")
    await shooter.shot("page", boxes={"button": "button"})


async def clip(director) -> None:
    await director.hold(0.4)
    x, y = await director.center("input")
    await director.glide(x, y, 0.5)
    await director.click()
    await director.type("demo")
    director.mark("typed", key=True)
    await director.hold(0.6)
    await director.still("typed", boxes={"name": "input"})


MODULE = SimpleNamespace(VIEWPORT=VIEWPORT, SHOTS={SCENARIO: page}, CLIPS={SCENARIO: clip})


def _size_problem(entry: dict) -> str | None:
    want = (round(VIEWPORT[0] * entry["scale"]), round(VIEWPORT[1] * entry["scale"]))
    got = (entry["width"], entry["height"])
    if got == want:
        return None
    return (f"selftest: {entry['file']} is {got[0]}x{got[1]}, expected {want[0]}x{want[1]} "
            f"(viewport {VIEWPORT[0]}x{VIEWPORT[1]} at scale {entry['scale']})")


def _clip_problem(entry: dict, out: Path, profile: Profile) -> str | None:
    keys = ["file", "poster", *["webm"] * profile.blog, *["video"] * profile.video]
    missing = [key for key in keys if not entry.get(key) or not (out / entry[key]).is_file()]
    if missing:
        return f"selftest: {entry['id']} lacks {', '.join(missing)}"
    if profile.video and not (entry.get("cursor") and entry.get("fps") == profile.fps):
        return f"selftest: {entry['id']} lacks a cursor track or fps {profile.fps}"
    return None


def check(entries: list[dict], out: Path, profile: Profile) -> str | None:
    """A message when an entry's image is not VIEWPORT x its scale, a clip lacks a file its
    profile writes, or a recorded clip came without its director's still; else None."""
    for entry in entries:
        problem = _size_problem(entry)
        if problem is None and entry["kind"] == "clip":
            problem = _clip_problem(entry, out, profile)
        if problem:
            return problem
    kinds = {(e["kind"], e["origin"]) for e in entries}
    if ("clip", "clip") in kinds and ("still", "clip") not in kinds:
        return "selftest: the clip's director still is missing"
    return None
