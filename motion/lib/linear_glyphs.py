"""Linear's thin line icons for lib/linear_ui.py (motion/reference/linear.md), drawn as strokes:
the sidebar's (inbox, my issues, triage, cycles, more, search, compose, initiatives, projects,
views), the properties panel's (link, branch, estimate) and the pane's (back, forward, history,
star, plus, caret, check, the dashed "no agent" ring). Nothing here is a logo."""

import math

import skia

from . import gfx, ui


def stroke(color, alpha, w=1.7):
    return gfx.stroke_paint(color, w, alpha)


def nav_glyph(canvas, kind, cx, cy, color, alpha, s=9.0):
    """The sidebar's line icons: inbox tray, my issues (a person), triage (a circle with a dot),
    cycles (a circle with a play mark), more (dots), search, compose, and the shapes of
    `shape_glyph` (initiatives, projects, views)."""
    if kind in ("mountain", "cube", "layers"):
        shape_glyph(canvas, kind, cx, cy, color, alpha, s)
        return
    p, path = stroke(color, alpha), skia.Path()
    if kind == "inbox":
        path.addRoundRect(skia.Rect.MakeLTRB(cx - s, cy - s * 0.8, cx + s, cy + s * 0.8), 3, 3)
        path.moveTo(cx - s, cy + s * 0.1)
        path.lineTo(cx - s * 0.4, cy + s * 0.1)
        path.lineTo(cx - s * 0.2, cy + s * 0.4)
        path.lineTo(cx + s * 0.2, cy + s * 0.4)
        path.lineTo(cx + s * 0.4, cy + s * 0.1)
        path.lineTo(cx + s, cy + s * 0.1)
    elif kind == "person":
        canvas.drawCircle(cx, cy, s, p)
        canvas.drawCircle(cx, cy - s * 0.25, s * 0.32, p)
        path.arcTo(skia.Rect.MakeLTRB(cx - s * 0.6, cy + s * 0.1, cx + s * 0.6, cy + s * 1.3), 200, 140, True)
    elif kind == "triage":
        canvas.drawCircle(cx, cy, s, p)
        canvas.drawCircle(cx, cy, s * 0.25, gfx.fill_paint(color, alpha))
    elif kind == "cycles":
        canvas.drawCircle(cx, cy, s, p)
        path.moveTo(cx - s * 0.25, cy - s * 0.45)
        path.lineTo(cx + s * 0.45, cy)
        path.lineTo(cx - s * 0.25, cy + s * 0.45)
        path.close()
    elif kind == "more":
        for i in (-1, 0, 1):
            canvas.drawCircle(cx + i * s * 0.6, cy, s * 0.16, gfx.fill_paint(color, alpha))
    elif kind == "search":
        canvas.drawCircle(cx - s * 0.15, cy - s * 0.15, s * 0.62, p)
        path.moveTo(cx + s * 0.3, cy + s * 0.3)
        path.lineTo(cx + s * 0.85, cy + s * 0.85)
    elif kind == "compose":
        path.addRoundRect(skia.Rect.MakeLTRB(cx - s * 0.8, cy - s * 0.6, cx + s * 0.5, cy + s * 0.8), 2.5, 2.5)
        path.moveTo(cx - s * 0.1, cy + s * 0.15)
        path.lineTo(cx + s * 0.85, cy - s * 0.8)
    canvas.drawPath(path, p)


def shape_glyph(canvas, kind, cx, cy, color, alpha, s=9.0):
    """Initiatives (a mountain), projects (a cube) and views (layers)."""
    path = skia.Path()
    if kind == "mountain":
        path.moveTo(cx - s, cy + s * 0.7)
        path.lineTo(cx - s * 0.35, cy - s * 0.6)
        path.lineTo(cx + s * 0.1, cy + s * 0.1)
        path.lineTo(cx + s * 0.4, cy - s * 0.3)
        path.lineTo(cx + s, cy + s * 0.7)
        path.close()
    elif kind == "cube":
        for i in range(6):
            ang = math.pi / 3 * i - math.pi / 2
            px, py = cx + s * 0.95 * math.cos(ang), cy + s * 0.95 * math.sin(ang)
            path.lineTo(px, py) if i else path.moveTo(px, py)
        path.close()
        for ex, ey in ((0, s * 0.95), (-s * 0.82, -s * 0.47), (s * 0.82, -s * 0.47)):
            path.moveTo(cx, cy)
            path.lineTo(cx + ex, cy + ey)
    elif kind == "layers":
        for dy in (-s * 0.35, s * 0.35):
            path.moveTo(cx - s, cy + dy)
            path.lineTo(cx, cy + dy - s * 0.55)
            path.lineTo(cx + s, cy + dy)
            path.lineTo(cx, cy + dy + s * 0.55)
            path.close()
    canvas.drawPath(path, stroke(color, alpha))


def panel_glyph(canvas, kind, cx, cy, color, alpha, s=9.0):
    """The properties panel's icons: link, branch and the estimate triangle."""
    p, path = stroke(color, alpha), skia.Path()
    if kind == "link":
        path.addArc(skia.Rect.MakeLTRB(cx - s, cy - s * 0.45, cx + s * 0.1, cy + s * 0.45), 60, 240)
        path.addArc(skia.Rect.MakeLTRB(cx - s * 0.1, cy - s * 0.45, cx + s, cy + s * 0.45), 240, 240)
        path.moveTo(cx - s * 0.35, cy)
        path.lineTo(cx + s * 0.35, cy)
    elif kind == "branch":
        canvas.drawCircle(cx - s * 0.5, cy - s * 0.65, s * 0.25, p)
        canvas.drawCircle(cx - s * 0.5, cy + s * 0.65, s * 0.25, p)
        canvas.drawCircle(cx + s * 0.55, cy - s * 0.3, s * 0.25, p)
        path.moveTo(cx - s * 0.5, cy - s * 0.4)
        path.lineTo(cx - s * 0.5, cy + s * 0.4)
        path.moveTo(cx + s * 0.55, cy - s * 0.05)
        path.quadTo(cx + s * 0.55, cy + s * 0.4, cx - s * 0.25, cy + s * 0.5)
    elif kind == "estimate":
        path.moveTo(cx, cy - s * 0.85)
        path.lineTo(cx + s * 0.95, cy + s * 0.7)
        path.lineTo(cx - s * 0.95, cy + s * 0.7)
        path.close()
        path.moveTo(cx, cy - s * 0.85)
        path.lineTo(cx, cy + s * 0.7)
    canvas.drawPath(path, p)


def ui_glyph(canvas, kind, cx, cy, color, alpha, s=9.0):
    """The pane's icons: back and forward arrows, history, star, plus, a caret, a check, a dashed
    "no agent" ring, and the panel's `panel_glyph` kinds."""
    if kind in ("link", "branch", "estimate"):
        panel_glyph(canvas, kind, cx, cy, color, alpha, s)
        return
    p, path = stroke(color, alpha), skia.Path()
    if kind in ("back", "forward"):
        d = -1 if kind == "back" else 1
        path.moveTo(cx - s * 0.8 * d, cy)
        path.lineTo(cx + s * 0.8 * d, cy)
        path.moveTo(cx + s * 0.2 * d, cy - s * 0.6)
        path.lineTo(cx + s * 0.8 * d, cy)
        path.lineTo(cx + s * 0.2 * d, cy + s * 0.6)
    elif kind == "history":
        canvas.drawCircle(cx, cy, s * 0.85, p)
        path.moveTo(cx, cy - s * 0.45)
        path.lineTo(cx, cy)
        path.lineTo(cx + s * 0.35, cy + s * 0.25)
    elif kind == "star":
        for i in range(10):
            r = s if i % 2 == 0 else s * 0.45
            ang = -math.pi / 2 + i * math.pi / 5
            px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
            path.lineTo(px, py) if i else path.moveTo(px, py)
        path.close()
    elif kind == "plus":
        path.moveTo(cx - s * 0.7, cy)
        path.lineTo(cx + s * 0.7, cy)
        path.moveTo(cx, cy - s * 0.7)
        path.lineTo(cx, cy + s * 0.7)
    elif kind == "caret":
        path.moveTo(cx - s * 0.45, cy - s * 0.2)
        path.lineTo(cx, cy + s * 0.25)
        path.lineTo(cx + s * 0.45, cy - s * 0.2)
    elif kind == "check":
        ui.status_glyph(canvas, "check", cx, cy, color, alpha, r=s * 0.6)
        return
    elif kind == "noagent":
        p.setPathEffect(skia.DashPathEffect.Make([3.2, 3.2], 0))
        canvas.drawCircle(cx, cy, s, p)
        canvas.drawCircle(cx, cy - s * 0.25, s * 0.3, stroke(color, alpha))
        return
    canvas.drawPath(path, p)
