"""Browser, server and page setup shared by the capture CLI and its selftest."""

from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from aiohttp import web
from playwright.async_api import Browser, Page, async_playwright

from webcap.director import Director
from webcap.page_script import INIT_SCRIPT
from webcap.profiles import profile
from webcap.project import base_url, mode, viewport
from webcap.server import PORT, start
from webcap.world import World

ARGS = [
    "--hide-scrollbars",
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader",
    "--disable-features=OverlayScrollbar",
]
THEMES = ("light", "dark")
PREROLL = 1.5  # seconds of mock time stepped before t = 0, so t = 0 is a settled frame
STEPPER = profile("blog")  # the pre-roll's frame rate; it records nothing


def context_options(module, scale: float) -> dict:
    """Playwright context options from the project's viewport (webcap.project.viewport) and
    THEME."""
    width, height = viewport(module)
    theme = getattr(module, "THEME", "light")
    if theme not in THEMES:
        raise ValueError(f"THEME must be one of {', '.join(THEMES)}, not {theme!r}")
    return {
        "viewport": {"width": width, "height": height},
        "device_scale_factor": scale,
        "color_scheme": theme,
        "reduced_motion": "no-preference",
    }


def page_url(base: str | None, path: str) -> str:
    """`path` on the live product at `base`, or on the mock server when `base` is None."""
    root = f"http://127.0.0.1:{PORT}" if base is None else base.rstrip("/")
    return f"{root}/{path.lstrip('/')}"


async def load(page: Page, url: str) -> None:
    """Navigate and wait until the network is idle and every web font has loaded."""
    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    await page.evaluate("document.fonts.ready.then(() => true)")


@asynccontextmanager
async def serving(app: web.Application):
    """Serve `app` on 127.0.0.1:PORT for the duration of the block."""
    runner = await start(app, PORT)
    try:
        yield
    finally:
        await runner.cleanup()


@asynccontextmanager
async def launch():
    """A headless Chromium."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=ARGS)
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def session(module):
    """(world, browser): mock mode starts the project's mock server; live mode's world is None."""
    async with AsyncExitStack() as stack:
        world = None
        if mode(module) == "mock":
            world = module.World()
            await stack.enter_async_context(serving(module.build_app(world)))
        browser = await stack.enter_async_context(launch())
        yield world, browser


def _report(scenario: str, message: str) -> None:
    print(f"{scenario}: page error: {message}", file=sys.stderr)


async def _warm_up(page: Page, world: World, scenario: str, path: str) -> None:
    world.set_scene(scenario)
    # The page drops a frame older than the one it holds, so it must load at
    # the start of the pre-roll, not at t = 0.
    world.t = -PREROLL
    # Python's clock API takes seconds (or datetimes), not milliseconds.
    epoch = world.clock.epoch_ms() / 1000 - PREROLL - 1.5
    await page.clock.install(time=epoch)
    await load(page, page_url(None, path))
    await page.clock.pause_at(epoch + 1.5)
    stepper = Director(page, world, Path(), STEPPER)  # steps both clocks; records nothing
    stepper.frame = -round(PREROLL * stepper.fps)
    await stepper.hold(PREROLL)


async def open_page(module, world: World | None, browser: Browser, scenario: str,
                    path: str = "/", scale: float = 1.0) -> Page:
    """A fresh context and page on `path`, in the project's viewport, theme and storage.

    Mock mode (a world) sets the world's scene to `scenario`, installs and pauses the page's
    fake clock and steps the pre-roll. Live mode (world None) loads the live URL on the page's
    real clock. The caller closes `page.context`.
    """
    context = await browser.new_context(**context_options(module, scale))
    try:
        storage = json.dumps(getattr(module, "LOCAL_STORAGE", {}))
        await context.add_init_script(INIT_SCRIPT.replace("__STORAGE__", storage))
        page = await context.new_page()
        page.on("console", lambda m: _report(scenario, m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: _report(scenario, str(e)))
        if world is None:
            await load(page, page_url(base_url(module), path))
        else:
            await _warm_up(page, world, scenario, path)
    except BaseException:
        await context.close()
        raise
    return page
