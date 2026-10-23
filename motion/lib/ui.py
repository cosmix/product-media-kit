"""UI-like pieces for scenes: perspective panes, status glyphs, node
connectors drawn in over time, typed code, text in the mono face, word wrap and
round avatars with initials."""

import math
from functools import cache

import skia

from . import design, gfx
from .ease import clamp01


@cache
def mono_font(size):
    """The mono face (design.json `fonts.mono`, else the system mono) at `size`."""
    tf = skia.Typeface.MakeFromFile(design.mono(), 0)
    if tf is None:
        raise RuntimeError(f"skia cannot read the mono font {design.mono()}")
    f = skia.Font(tf, size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    return f


def mono_width(s, size):
    f = mono_font(size)
    glyphs = f.textToGlyphs(s)
    return sum(f.getWidths(glyphs)) if glyphs else 0.0


def mono_text(canvas, s, x, y, size, color=gfx.FG, alpha=1.0, align="left"):
    """A string in the mono face. Returns its width."""
    if not s or alpha <= 0.001:
        return 0.0
    w = mono_width(s, size)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    canvas.drawString(s, x, y, mono_font(size), skia.Paint(AntiAlias=True, Color4f=gfx.col(color, alpha)))
    return w


def wrap(text, size, width, weight=400):
    """Greedy word wrap of `text` at `size` px into lines no wider than `width`."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and gfx.text_width(trial, size, weight) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def fit(text, size, width, weight=400):
    """`text` at `size` px cut with an ellipsis to no wider than `width`; unchanged when it fits."""
    if gfx.text_width(text, size, weight) <= width:
        return text
    while text and gfx.text_width(text + "…", size, weight) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def ink(fill):
    """The text colour that reads on `fill`: near-black on a light fill, white on a dark one
    (WCAG relative luminance against 0.179, the threshold design.logo picks variants by)."""
    return "#111418" if design.luminance(fill) >= 0.179 else "#ffffff"


def avatar(canvas, x, y, r, initials, color, alpha, size=None):
    """A round avatar with initials, centred on (x, y), in `ink` on `color`."""
    if alpha <= 0.002:
        return
    canvas.drawCircle(x, y, r, gfx.fill_paint(color, alpha))
    size = size or r * 0.95
    gfx.text(canvas, initials, x, y + size * 0.36, size, ink(color), 600, 0.0, alpha, align="center")


def persp_matrix(x, y, w, h, yaw=0.0, pitch=0.0, focal=2600.0, scale=1.0, dx=0.0, dy=0.0):
    """Matrix mapping the rect's corners to their projection after a small
    3D rotation about the rect centre (yaw about Y, pitch about X)."""
    cx, cy = x + w / 2, y + h / 2
    cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    src, dst = [], []
    for px, py in ((x, y), (x + w, y), (x + w, y + h), (x, y + h)):
        X, Y, Z = (px - cx) * scale, (py - cy) * scale, 0.0
        X, Z = X * cy_ - Z * sy_, X * sy_ + Z * cy_
        Y, Z = Y * cp - Z * sp, Y * sp + Z * cp
        f = focal / (focal + Z)
        src.append(skia.Point(px, py))
        dst.append(skia.Point(cx + dx + X * f, cy + dy + Y * f))
    m = skia.Matrix()
    m.setPolyToPoly(src, dst)
    return m


def status_glyph(canvas, kind, x, y, color, alpha, r=4.5):
    """Small state icon: "open" (hollow circle), "dot", "cross" or "check"."""
    if alpha <= 0.002:
        return
    if kind == "open":
        canvas.drawCircle(x, y, r, gfx.stroke_paint(color, 1.4, alpha))
    elif kind == "dot":
        canvas.drawCircle(x, y, r, gfx.fill_paint(color, alpha))
    elif kind == "cross":
        p = gfx.stroke_paint(color, 1.8, alpha)
        canvas.drawLine(x - r, y - r, x + r, y + r, p)
        canvas.drawLine(x - r, y + r, x + r, y - r, p)
    elif kind == "check":
        path = skia.Path()
        path.moveTo(x - r, y)
        path.lineTo(x - r * 0.25, y + r * 0.75)
        path.lineTo(x + r, y - r * 0.7)
        canvas.drawPath(path, gfx.stroke_paint(color, 1.8, alpha))
    else:
        raise ValueError(f"unknown status glyph {kind!r}")


def edge_path(x0, y0, x1, y1, bend=0.5):
    """Connector between two nodes: leaves the bottom of one and enters the
    top of the next with vertical tangents."""
    p = skia.Path()
    p.moveTo(x0, y0)
    dy = (y1 - y0) * bend
    p.cubicTo(x0, y0 + dy, x1, y1 - dy, x1, y1)
    return p


def trimmed(path, u0, u1):
    if u0 <= 0.0 and u1 >= 1.0:
        return path
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    out = skia.Path()
    pm.getSegment(u0 * L, u1 * L, out, True)
    return out


def draw_edge(canvas, path, u, color, alpha=1.0, width=1.6, glow=1.0, dashed=False):
    """An edge drawn in up to fraction u: optional glow (gfx.GLOW), core, and a
    bead at its head while it grows."""
    if u <= 0.002 or alpha <= 0.002:
        return
    seg = trimmed(path, 0.0, u)
    gfx.glow_stroke(canvas, seg, color, width * 6, 14, 0.16 * alpha * glow)
    gfx.glow_stroke(canvas, seg, color, width * 2.2, 4, 0.30 * alpha * glow)
    p = gfx.stroke_paint(color, width, alpha)
    if dashed:
        p.setPathEffect(skia.DashPathEffect.Make([6, 6], 0))
    canvas.drawPath(seg, p)
    if u < 0.999:
        pm = skia.PathMeasure(path, False)
        pos, _ = pm.getPosTan(pm.getLength() * u)
        gfx.glow_dot(canvas, pos.x(), pos.y(), 7, "#ffffff", 0.5 * alpha, sigma=4)
        canvas.drawCircle(pos.x(), pos.y(), 2.2, gfx.fill_paint("#ffffff", alpha))


def port(canvas, x, y, color, alpha, filled=False):
    """The small connector circle on a node's top/bottom edge."""
    canvas.drawCircle(x, y, 4, gfx.fill_paint(gfx.BG, alpha))
    canvas.drawCircle(x, y, 4, gfx.stroke_paint(color, 1.2, alpha))
    if filled:
        canvas.drawCircle(x, y, 2.2, gfx.fill_paint(color, alpha))


class CodeLines:
    """Syntax-coloured lines typed in progressively.
    lines: list of list[(text, color)]"""

    def __init__(self, lines, size=14, lh=20, weight=425):
        self.lines, self.size, self.lh, self.weight = lines, size, lh, weight
        self.total = sum(len(t) for ln in lines for t, _ in ln)

    def draw(self, canvas, x, y, chars=None, alpha=1.0, gutter=True, line_alpha=None, cursor=True):
        """Draw up to `chars` characters (None = all). Returns the bottom y."""
        n = self.total if chars is None else int(clamp01(chars / max(self.total, 1)) * self.total)
        remaining = n
        cy = y
        cw = gfx.text_width("0", self.size, self.weight)
        for i, ln in enumerate(self.lines):
            la = alpha * (line_alpha(i) if line_alpha else 1.0)
            if gutter:
                gfx.text(canvas, f"{i + 1:>2}", x - 14, cy, self.size * 0.86, gfx.FG2, 400, 0.0, 0.45 * la, align="right")
            cx = x
            done = False
            for t, c in ln:
                if remaining <= 0:
                    done = True
                    break
                shown = t[:remaining]
                remaining -= len(shown)
                gfx.text(canvas, shown, cx, cy, self.size, c, self.weight, 0.0, la)
                cx += cw * len(shown)
            if done or (remaining <= 0 and chars is not None and n < self.total):
                if cursor:
                    canvas.drawRect(skia.Rect.MakeXYWH(cx + 1, cy - self.size * 0.8, cw * 0.9, self.size * 1.05), gfx.fill_paint(gfx.ACCENT, 0.85 * alpha))
                return cy
            cy += self.lh
        return cy

    def line_y(self, y, i):
        return y + i * self.lh
