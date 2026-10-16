"""Window frames drawn around a treated still: a light browser window, a dark terminal window."""

from dataclasses import dataclass

from PIL import Image, ImageDraw

DOTS = ("#ff5f57", "#febc2e", "#28c840")


@dataclass(frozen=True)
class Chrome:
    bar: str  # title bar fill
    border: str  # outer border and the line under the title bar


CHROMES = {
    "browser": Chrome(bar="#f3f4f6", border="#d1d5db"),
    "terminal": Chrome(bar="#1f2937", border="#111827"),
}


def frame(img: Image.Image, kind: str, unit: float) -> Image.Image:
    """`img` inside a rounded window with a title bar and three dots; `none` returns it as is.

    `unit` is the shot's device scale, so the frame has the same size relative to the content
    on a 1x and a 2x capture.
    """
    if kind == "none":
        return img
    chrome = CHROMES[kind]
    bar, edge, radius = round(36 * unit), max(1, round(unit)), round(10 * unit)
    inner = Image.new("RGBA", (img.width, img.height + bar), chrome.bar)
    inner.paste(img, (0, bar))
    draw = ImageDraw.Draw(inner)
    draw.line([(0, bar - 1), (inner.width, bar - 1)], fill=chrome.border, width=edge)
    _dots(draw, bar, unit)
    mask = Image.new("L", inner.size, 0)
    inner_radius = max(0, radius - edge)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner.width - 1, inner.height - 1], radius=inner_radius, fill=255)
    canvas = Image.new("RGBA", (inner.width + 2 * edge, inner.height + 2 * edge), (0, 0, 0, 0))
    outer = [0, 0, canvas.width - 1, canvas.height - 1]
    ImageDraw.Draw(canvas).rounded_rectangle(outer, radius=radius, fill=chrome.border)
    canvas.paste(inner, (edge, edge), mask)
    return canvas


def _dots(draw: ImageDraw.ImageDraw, bar: int, unit: float) -> None:
    r, gap, cy = round(6 * unit), round(8 * unit), bar // 2
    x = round(14 * unit)
    for color in DOTS:
        draw.ellipse([x, cy - r, x + 2 * r, cy + r], fill=color)
        x += 2 * r + gap
