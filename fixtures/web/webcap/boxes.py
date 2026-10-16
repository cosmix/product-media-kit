"""Element boxes: measured in CSS px on the page, recorded as integer pixels of the image."""

from __future__ import annotations

from collections.abc import Mapping

from playwright.async_api import Page

from webcap.names import check_name


async def element_box(page: Page, selector: str, scenario: str) -> dict:
    """The first visible element matching `selector`, as a CSS-px bounding box; LookupError
    naming the scenario when none is visible."""
    locator = page.locator(selector)
    box = await locator.first.bounding_box() if await locator.count() else None
    if box is None:
        raise LookupError(f"{scenario}: no visible element matches {selector!r}")
    return box


def pixel_box(box: Mapping[str, float], scale: float, origin: tuple[float, float],
              size: tuple[int, int]) -> list[int]:
    """A CSS-px bounding box as [x, y, w, h] integer pixels of the image, clipped to it.

    `origin` is the image's top-left corner in the box's CSS coordinates; `size` the image's
    (width, height) in pixels. A box wholly outside the image raises ValueError.
    """
    width, height = size
    x0 = min(max(round((box["x"] - origin[0]) * scale), 0), width)
    y0 = min(max(round((box["y"] - origin[1]) * scale), 0), height)
    x1 = min(max(round((box["x"] + box["width"] - origin[0]) * scale), 0), width)
    y1 = min(max(round((box["y"] + box["height"] - origin[1]) * scale), 0), height)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"{dict(box)} lies outside the {width}x{height} image")
    return [x0, y0, x1 - x0, y1 - y0]


def pixel_boxes(where: str, boxes: Mapping[str, Mapping[str, float]], scale: float,
                origin: tuple[float, float], size: tuple[int, int]) -> dict[str, list[int]]:
    """Each named CSS-px box as image pixels; a box outside the image raises ValueError naming
    `where` (the shot's scenario/label) and the box."""
    measured = {}
    for name, box in boxes.items():
        check_name("box", name)
        try:
            measured[name] = pixel_box(box, scale, origin, size)
        except ValueError as err:
            raise ValueError(f"{where}: box {name!r}: {err}") from err
    return measured
