"""Treat a shot for the post: crop, highlight, number, frame and resize a still; copy a clip.

Box coordinates are image pixels in the capture. Sizes in a Treatment (`pad`) and the drawn
decoration (outline, callout circles, frame) are multiplied by the shot's scale, so a 2x capture
looks the same as a 1x capture once both are resized for the post.
"""

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from postkit.common import copy_atomic, write_atomic
from postkit.design import Design
from postkit.frames import frame
from postkit.manifest import Box, Shot

WHITE = "#ffffff"


@dataclass
class Treatment:
    frame: str = "none"  # "browser", "terminal" or "none"
    crop: str | None = None  # a box name: crop to it plus `pad`
    pad: int = 24
    highlight: list[str] = field(default_factory=list)  # box names outlined in the accent colour
    callouts: list[str] = field(default_factory=list)  # box names numbered 1, 2, ... at their corner
    width: int = 1600  # the largest width of the result; never upscaled


def output_name(shot: Shot) -> str:
    """The file name of a shot in outputs/blog/images/: a still is a PNG, a clip keeps its GIF suffix."""
    suffix = ".png" if shot.kind == "still" else (shot.path.suffix.lower() or ".gif")
    return shot.name + suffix


def treat(shot: Shot, treatment: Treatment, design: Design, dest: Path) -> list[Path]:
    """Write the treated shot to `dest` (a clip's WebM beside it) atomically; return every path written."""
    if shot.kind == "clip":
        return _copy_clip(shot, dest)
    unit = shot.scale
    with Image.open(shot.path) as src:
        img = src.convert("RGBA")
    crop_box = shot.boxes[treatment.crop] if treatment.crop else None
    img, (dx, dy) = _crop(img, crop_box, round(treatment.pad * unit))
    draw = ImageDraw.Draw(img)
    for name in treatment.highlight:
        _highlight(draw, _moved(shot.boxes[name], dx, dy), design.accent, unit)
    _callouts(draw, img.size, [_moved(shot.boxes[n], dx, dy) for n in treatment.callouts], design, unit)
    img = frame(img, treatment.frame, unit)
    if img.width > treatment.width:
        height = max(1, round(img.height * treatment.width / img.width))
        img = img.resize((treatment.width, height), Image.Resampling.LANCZOS)
    alpha_min, _ = img.getextrema()[3]
    if alpha_min == 255:
        img = img.convert("RGB")
    png = BytesIO()
    img.save(png, format="PNG", optimize=True)
    write_atomic(dest, png.getvalue())
    return [dest]


def _copy_clip(shot: Shot, dest: Path) -> list[Path]:
    copy_atomic(shot.path, dest)
    written = [dest]
    if shot.webm is not None:
        webm = dest.with_suffix(".webm")
        copy_atomic(shot.webm, webm)
        written.append(webm)
    return written


def _crop(img: Image.Image, box: Box | None, pad: int) -> tuple[Image.Image, tuple[int, int]]:
    """`img` cropped to `box` grown by `pad` and clamped to the image, and the crop's top-left."""
    if box is None:
        return img, (0, 0)
    x, y, w, h = box
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(img.width, x + w + pad), min(img.height, y + h + pad)
    if x1 <= x0 or y1 <= y0:
        return img, (0, 0)
    return img.crop((x0, y0, x1, y1)), (x0, y0)


def _moved(box: Box, dx: int, dy: int) -> Box:
    x, y, w, h = box
    return (x - dx, y - dy, w, h)


def _highlight(draw: ImageDraw.ImageDraw, box: Box, color: str, unit: float) -> None:
    """A rounded outline just outside `box`, so it never covers the element it marks."""
    x, y, w, h = box
    stroke = max(1, round(4 * unit))
    bounds = [x - stroke, y - stroke, x + w - 1 + stroke, y + h - 1 + stroke]
    draw.rounded_rectangle(bounds, radius=round(6 * unit) + stroke, outline=color, width=stroke)


def _callouts(draw: ImageDraw.ImageDraw, size: tuple[int, int], boxes: list[Box], design: Design,
              unit: float) -> None:
    """Filled accent circles numbered 1, 2, ... centred on each box's top-left corner."""
    if not boxes:
        return
    r = round(14 * unit)
    font = _font(design, round(16 * unit))
    for n, (x, y, _, _) in enumerate(boxes, start=1):
        cx = min(max(x, r), max(r, size[0] - r))  # keep the whole circle on the image
        cy = min(max(y, r), max(r, size[1] - r))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=design.accent)
        draw.text((cx, cy), str(n), fill=WHITE, font=font, anchor="mm")


def _font(design: Design, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if design.bold_font is not None:
        try:
            return ImageFont.truetype(str(design.bold_font), size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)
