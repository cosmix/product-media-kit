"""Slack's line icons for lib/slack_ui.py, drawn as simple strokes (motion/reference/slack.md):
the rail's Home, DMs and Activity, the Later bookmark, the More dots, search, plus, the paper
plane (Drafts & sent, the send button), the headset (huddle), a speech bubble (Threads,
Messages), a folder (Files), the composer's emoji face and the thumbs-up reaction. Nothing here
is a logo."""

import skia

from . import gfx

THUMB = "#f5c542"   # the thumbs-up emoji's yellow


def glyph(canvas, kind, cx, cy, color, alpha, s=10.0):
    """An icon `kind` centred on (cx, cy), about 2 s px across."""
    if kind in ("headset", "bubble", "folder", "emoji", "thumb"):
        pane_glyph(canvas, kind, cx, cy, color, alpha, s)
        return
    p = gfx.stroke_paint(color, 1.8, alpha)
    path = skia.Path()
    if kind == "later":
        path.moveTo(cx - s * 0.6, cy - s)
        path.lineTo(cx + s * 0.6, cy - s)
        path.lineTo(cx + s * 0.6, cy + s)
        path.lineTo(cx, cy + s * 0.45)
        path.lineTo(cx - s * 0.6, cy + s)
        path.close()
    elif kind == "more":
        for i in (-1, 0, 1):
            canvas.drawCircle(cx + i * s * 0.6, cy, s * 0.17, gfx.fill_paint(color, alpha))
        return
    elif kind == "search":
        canvas.drawCircle(cx - s * 0.15, cy - s * 0.15, s * 0.62, p)
        path.moveTo(cx + s * 0.3, cy + s * 0.3)
        path.lineTo(cx + s * 0.85, cy + s * 0.85)
    elif kind == "plus":
        path.moveTo(cx - s * 0.7, cy)
        path.lineTo(cx + s * 0.7, cy)
        path.moveTo(cx, cy - s * 0.7)
        path.lineTo(cx, cy + s * 0.7)
    elif kind == "plane":
        path.moveTo(cx - s * 0.9, cy - s * 0.15)
        path.lineTo(cx + s * 0.9, cy - s * 0.75)
        path.lineTo(cx + s * 0.25, cy + s * 0.85)
        path.lineTo(cx - s * 0.1, cy + s * 0.1)
        path.close()
        path.moveTo(cx - s * 0.1, cy + s * 0.1)
        path.lineTo(cx + s * 0.9, cy - s * 0.75)
    canvas.drawPath(path, p)


def pane_glyph(canvas, kind, cx, cy, color, alpha, s=10.0):
    """The headset (huddle), a speech bubble (Threads, Messages), a folder (Files), the
    composer's emoji face and the thumbs-up reaction (filled, in the emoji's yellow)."""
    p = gfx.stroke_paint(color, 1.8, alpha)
    path = skia.Path()
    if kind == "headset":
        path.arcTo(skia.Rect.MakeLTRB(cx - s * 0.8, cy - s * 0.8, cx + s * 0.8, cy + s * 0.8), 180, 180, True)
        path.addRoundRect(skia.Rect.MakeLTRB(cx - s * 0.8, cy, cx - s * 0.3, cy + s * 0.7), 2, 2)
        path.addRoundRect(skia.Rect.MakeLTRB(cx + s * 0.3, cy, cx + s * 0.8, cy + s * 0.7), 2, 2)
    elif kind == "bubble":
        path.addRoundRect(skia.Rect.MakeLTRB(cx - s * 0.85, cy - s * 0.7, cx + s * 0.85, cy + s * 0.45), s * 0.45, s * 0.45)
        path.moveTo(cx - s * 0.5, cy + s * 0.45)
        path.lineTo(cx - s * 0.6, cy + s * 0.9)
        path.lineTo(cx - s * 0.1, cy + s * 0.45)
    elif kind == "folder":
        path.moveTo(cx - s * 0.9, cy - s * 0.55)
        path.lineTo(cx - s * 0.3, cy - s * 0.55)
        path.lineTo(cx - s * 0.1, cy - s * 0.3)
        path.lineTo(cx + s * 0.9, cy - s * 0.3)
        path.lineTo(cx + s * 0.9, cy + s * 0.65)
        path.lineTo(cx - s * 0.9, cy + s * 0.65)
        path.close()
    elif kind == "emoji":
        canvas.drawCircle(cx, cy, s * 0.8, p)
        canvas.drawCircle(cx - s * 0.3, cy - s * 0.2, s * 0.09, gfx.fill_paint(color, alpha))
        canvas.drawCircle(cx + s * 0.3, cy - s * 0.2, s * 0.09, gfx.fill_paint(color, alpha))
        path.arcTo(skia.Rect.MakeLTRB(cx - s * 0.42, cy - s * 0.3, cx + s * 0.42, cy + s * 0.45), 20, 140, True)
    elif kind == "thumb":
        fill = gfx.fill_paint(THUMB, alpha)
        canvas.drawRRect(gfx.rrect(cx - s * 0.9, cy - s * 0.1, s * 0.5, s * 0.95, s * 0.12), fill)      # the cuff
        canvas.drawRRect(gfx.rrect(cx - s * 0.35, cy - s * 0.1, s * 1.2, s * 0.95, s * 0.25), fill)     # the fingers
        canvas.drawRRect(gfx.rrect(cx - s * 0.1, cy - s * 0.95, s * 0.45, s * 1.1, s * 0.22), fill)     # the thumb
        return
    canvas.drawPath(path, p)


def rail_glyph(canvas, kind, cx, cy, color, alpha):
    """Slack's rail icons, as simple outlines: a house (Home), a speech bubble (DMs), a bell (Activity)."""
    p = gfx.stroke_paint(color, 1.8, alpha)
    path = skia.Path()
    if kind == "Home":
        path.moveTo(cx - 10, cy - 1)
        path.lineTo(cx, cy - 10)
        path.lineTo(cx + 10, cy - 1)
        path.lineTo(cx + 10, cy + 9)
        path.lineTo(cx - 10, cy + 9)
        path.close()
    elif kind == "DMs":
        path.addRoundRect(skia.Rect.MakeLTRB(cx - 10, cy - 9, cx + 10, cy + 5), 4, 4)
        path.moveTo(cx - 5, cy + 5)
        path.lineTo(cx - 6, cy + 10)
        path.lineTo(cx, cy + 5)
    else:
        path.moveTo(cx - 9, cy + 5)
        path.lineTo(cx - 7, cy + 1)
        path.lineTo(cx - 7, cy - 4)
        path.arcTo(skia.Rect.MakeLTRB(cx - 7, cy - 11, cx + 7, cy + 3), 180, 180, False)
        path.lineTo(cx + 7, cy + 1)
        path.lineTo(cx + 9, cy + 5)
        path.close()
        path.moveTo(cx - 3, cy + 8)
        path.lineTo(cx + 3, cy + 8)
    canvas.drawPath(path, p)
