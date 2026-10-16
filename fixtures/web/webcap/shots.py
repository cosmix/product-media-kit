"""Named PNG stills with element boxes, written for the capture manifest.

A SHOTS scenario in fixtures/web/product.py receives a Shooter:

    async def settings(shooter):
        await shooter.goto("/settings")
        await shooter.page.click("text=Advanced")
        await shooter.shot("dialog", selector="[role=dialog]", boxes={"save": "button.save"})
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from playwright.async_api import Page

from webcap.boxes import element_box, pixel_boxes
from webcap.browser import load, page_url
from webcap.manifest import still_entry
from webcap.media import png_file_size, temp_path
from webcap.names import NAME_RE, check_label, check_name
from webcap.project import base_url, product
from webcap.world import World

__all__ = ["NAME_RE", "Shooter", "check_name"]


class Shooter:
    """Takes a scenario's stills into <out_dir>/<scenario>/<label>.png; `entries` collects them."""

    def __init__(self, page: Page, out_dir: Path, scenario: str, scale: float,
                 world: World | None = None) -> None:
        self.page = page
        self.out_dir = out_dir
        self.scenario = check_name("scenario", scenario)
        self.scale = scale
        self.world = world
        self.entries: list[dict] = []

    async def goto(self, path: str = "/") -> None:
        """Load `path` from the mock server (with a world) or the live product."""
        base = None if self.world is not None else base_url(product())
        await load(self.page, page_url(base, path))

    async def _box(self, selector: str) -> dict:
        return await element_box(self.page, selector, self.scenario)

    async def _capture(self, partial: Path, selector: str | None, full_page: bool) -> tuple[float, float]:
        """Screenshot into `partial`; return the image's origin in viewport CSS px."""
        if selector is not None:
            await self._box(selector)
            await self.page.locator(selector).first.screenshot(path=partial, animations="disabled")
            # Measured after the shot: taking it may scroll the element into view.
            box = await self._box(selector)
            return box["x"], box["y"]
        await self.page.screenshot(path=partial, full_page=full_page, animations="disabled")
        if full_page:
            scroll_x, scroll_y = await self.page.evaluate("[window.scrollX, window.scrollY]")
            return -scroll_x, -scroll_y
        return 0.0, 0.0

    async def shot(self, label: str, *, selector: str | None = None, full_page: bool = False,
                   boxes: Mapping[str, str] | None = None) -> dict:
        """Screenshot the page (or the element `selector` matches) and return its manifest entry.

        `boxes` maps a box name to a CSS selector; each box is recorded in image pixels.
        """
        check_label(self.scenario, label)
        path = self.out_dir / self.scenario / f"{label}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = temp_path(path)
        try:
            origin = await self._capture(partial, selector, full_page)
            size = png_file_size(partial)
            found = {name: await self._box(box_selector) for name, box_selector in (boxes or {}).items()}
            measured = pixel_boxes(f"{self.scenario}/{label}", found, self.scale, origin, size)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        partial.replace(path)
        entry = still_entry(self.scenario, label, size, self.scale, measured, "shots")
        self.entries = [e for e in self.entries if e["id"] != entry["id"]] + [entry]
        return entry
