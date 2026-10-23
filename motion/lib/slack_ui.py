"""Slack's desktop client in its default theme, redrawn from the current design
(motion/reference/slack.md): the aubergine frame with the top search bar and the workspace rail
(the workspace tile, Home, DMs, Activity, Later, More; new and the viewer's avatar at the
bottom), the channel sidebar (workspace name, Threads, Drafts & sent, the Channels section with
the selected and unread channels, Direct messages, Apps) and the message pane, which keeps
the dark mode's neutral ground: the channel
header with its members and tabs, the "Today" divider, the earlier messages, the app's post and
the composer. The strings are Slack's own chrome or the scene's lib/slack_content.SlackContent;
Inter stands in for Slack's Lato."""

import skia

from . import gfx, icons, logos, ui, win
from .ease import clamp01, cubic_out, seg, smooth
from .slack_glyphs import glyph, rail_glyph

S = win.SLACK
# Slack's default theme, Aubergine (reference/slack.md): the frame, rail and top bar in Slack's
# brand aubergine, the channel sidebar in the theme's deeper purple, white text on both; the
# message pane keeps the dark mode's neutral ground
FRAME = "#4a154b"          # the frame around the cards: top bar and rail (brand aubergine)
SIDEBAR = "#3f0e40"        # the channel sidebar card (the Aubergine theme's column colour)
SELECTED = "#703a75"       # the selected sidebar item, white text (a lighter purple in the current design)
SIDE_TEXT, SIDE_MUTED = "#ffffff", "#cfc3d0"   # sidebar and rail text; section headers, placeholders, read channels
SEND = "#007a5a"           # the composer's send button
WHITE = "#ffffff"
TOP, RAIL, SIDE = 52, 72, 300              # the top bar's height, the rail's and the sidebar's widths
HEADER, TABS, COMPOSER = 70, 46, 118       # the channel header, its tab row and the composer box
MSG_LINE = 32                              # the message's line height at 22 px


def tile(canvas, cx, cy, size, alpha, color, radius=None):
    """A rounded-square tile (avatars, the workspace icon)."""
    canvas.drawRRect(gfx.rrect(cx - size / 2, cy - size / 2, size, size, radius or size * 0.22), gfx.fill_paint(color, alpha))


def person_tile(canvas, cx, cy, size, person, alpha, presence=True, ring=SIDEBAR):
    """A person's avatar as Slack draws it: a rounded square with initials and, when asked, the
    presence dot (green when active, a hollow ring when away), ringed in the ground it sits on."""
    tile(canvas, cx, cy, size, alpha, person.color)
    gfx.text(canvas, person.initials, cx, cy + size * 0.17, size * 0.44, ui.ink(person.color), 600, 0.0, alpha, align="center")
    if presence:
        r = size * 0.16
        dx, dy = cx + size / 2 - r * 0.6, cy + size / 2 - r * 0.6
        canvas.drawCircle(dx, dy, r + 2, gfx.fill_paint(ring, alpha))
        if person.active:
            canvas.drawCircle(dx, dy, r, gfx.fill_paint(S.green, alpha))
        else:
            canvas.drawCircle(dx, dy, r - 1, gfx.stroke_paint(SIDE_MUTED, 1.5, alpha))


def frame(canvas, x, y, w, h, alpha, content):
    """The aubergine frame: the top bar with back, forward, history and the search field, then
    the rail with the workspace tile, the five tabs, new and the viewer's avatar."""
    nav = gfx.stroke_paint(SIDE_MUTED, 1.8, 0.9 * alpha)
    for i, d in enumerate((-1, 1)):
        cx, cy = x + RAIL + 40 + i * 34, y + TOP / 2
        canvas.drawLine(cx - 7 * d, cy, cx + 7 * d, cy, nav)
        canvas.drawLine(cx + 7 * d, cy, cx + 2 * d, cy - 5, nav)
        canvas.drawLine(cx + 7 * d, cy, cx + 2 * d, cy + 5, nav)
    cx, cy = x + RAIL + 112, y + TOP / 2
    canvas.drawCircle(cx, cy, 8, nav)
    canvas.drawLine(cx, cy - 4, cx, cy, nav)
    canvas.drawLine(cx, cy, cx + 3, cy + 2, nav)
    sw = min(w * 0.42, 720)
    sx = x + (w - sw) / 2 + RAIL / 2
    canvas.drawRRect(gfx.rrect(sx, y + 9, sw, TOP - 18, 7), gfx.fill_paint(WHITE, 0.22 * alpha))
    glyph(canvas, "search", sx + 20, y + TOP / 2, SIDE_MUTED, alpha, 8)
    gfx.text(canvas, f"Search {content.workspace}", sx + 40, y + TOP / 2 + 6, 17, SIDE_MUTED, 400, 0.0, alpha)
    rx = x + RAIL / 2
    tile(canvas, rx, y + TOP + 40, 42, alpha, WHITE, 10)
    logos.slack(canvas, rx - 13, y + TOP + 27, 26, alpha)
    for i, (item, kind) in enumerate((("Home", "Home"), ("DMs", "DMs"), ("Activity", "Activity"), ("Later", "later"), ("More", "more"))):
        cy = y + TOP + 108 + i * 74
        if cy + 44 > y + h - 140:      # a short window drops the last tabs, as Slack's rail does
            break
        if i == 0:
            canvas.drawRRect(gfx.rrect(rx - 20, cy - 20, 40, 40, 9), gfx.fill_paint(WHITE, 0.22 * alpha))
        color = WHITE if i == 0 else SIDE_MUTED
        if kind in ("Home", "DMs", "Activity"):
            rail_glyph(canvas, kind, rx, cy, color, alpha)
        else:
            glyph(canvas, kind, rx, cy, color, alpha)
        gfx.text(canvas, item, rx, cy + 36, 14, color, 500, 0.0, alpha, align="center")
    canvas.drawCircle(rx, y + h - 118, 19, gfx.fill_paint(WHITE, 0.18 * alpha))
    glyph(canvas, "plus", rx, y + h - 118, WHITE, alpha, 9)
    person_tile(canvas, rx, y + h - 50, 40, content.viewer, alpha, ring=FRAME)


def sidebar(canvas, x, y, h, alpha, content):
    """The channel sidebar card: the workspace name, Threads and Drafts & sent, then the lists.
    `x` is the card's left edge."""
    canvas.save()
    canvas.clipRRect(gfx.rrect(x, y, SIDE + 12, h, 10), True)
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, SIDE + 12, h), gfx.fill_paint(SIDEBAR, alpha))
    tx = x + 20
    tw = gfx.text(canvas, content.workspace, tx, y + 42, 23, WHITE, 700, 0.0, alpha)
    caret(canvas, tx + tw + 16, y + 35, WHITE, alpha)
    canvas.drawLine(x, y + 62, x + SIDE, y + 62, gfx.stroke_paint(WHITE, 1.0, 0.14 * alpha, cap="butt"))
    for i, (kind, label) in enumerate((("bubble", "Threads"), ("plane", "Drafts & sent"))):
        yy = y + 96 + i * 38
        glyph(canvas, kind, tx + 10, yy - 7, SIDE_MUTED, alpha, 8.5)
        gfx.text(canvas, label, tx + 34, yy, 19, SIDE_TEXT, 400, 0.0, alpha)
    sidebar_lists(canvas, x, y + 190, alpha, content)
    canvas.restore()


def sidebar_lists(canvas, x, y, alpha, content):
    """The Channels section (read channels muted, unread bold, the selected one highlighted),
    Direct messages with presence, and Apps with the app."""
    tx, pitch = x + 20, 36
    gfx.text(canvas, "Channels", tx, y, 17, SIDE_MUTED, 500, 0.0, alpha)
    yy = y + 36
    for channel in content.channels:
        if channel.state == "selected":
            canvas.drawRRect(gfx.rrect(x + 8, yy - 25, SIDE - 16, pitch - 2, 7), gfx.fill_paint(SELECTED, alpha))
        color, weight = (WHITE, 700) if channel.state != "read" else (SIDE_MUTED, 400)
        gfx.text(canvas, "#", tx + 2, yy, 19, color, weight, 0.0, alpha)
        gfx.text(canvas, channel.name, tx + 34, yy, 19, color, weight, 0.0, alpha)
        yy += pitch
    glyph(canvas, "plus", tx + 10, yy - 7, SIDE_MUTED, alpha, 6)
    gfx.text(canvas, "Add channels", tx + 34, yy, 19, SIDE_MUTED, 400, 0.0, alpha)
    yy += 46
    gfx.text(canvas, "Direct messages", tx, yy, 17, SIDE_MUTED, 500, 0.0, alpha)
    yy += 36
    for person in content.people:
        person_tile(canvas, tx + 10, yy - 7, 22, person, alpha)
        gfx.text(canvas, person.name, tx + 34, yy, 19, SIDE_TEXT, 400, 0.0, alpha)
        yy += pitch
    yy += 10
    gfx.text(canvas, "Apps", tx, yy, 17, SIDE_MUTED, 500, 0.0, alpha)
    yy += 36
    win.app_avatar(canvas, tx + 10, yy - 7, 22, content.app, alpha)
    gfx.text(canvas, content.app, tx + 34, yy, 19, SIDE_TEXT, 400, 0.0, alpha)


def caret(canvas, cx, cy, color, alpha, s=4.5):
    p = gfx.stroke_paint(color, 1.8, alpha)
    canvas.drawLine(cx - s, cy - s / 2, cx, cy + s / 2, p)
    canvas.drawLine(cx, cy + s / 2, cx + s, cy - s / 2, p)


def header(canvas, x, y, w, alpha, content):
    """The channel header with the members' facepile (the first three people) and count, the
    huddle button and more, then the Messages / Files tabs."""
    hx = x + 24
    hx += gfx.text(canvas, "#", hx, y + 44, 26, S.text, 700, 0.0, alpha) + 8
    hx += gfx.text(canvas, content.channel, hx, y + 44, 26, S.text, 700, 0.0, alpha) + 16
    caret(canvas, hx, y + 36, S.muted, alpha)
    bx = x + w - 150
    fx = bx - 128
    canvas.drawRRect(gfx.rrect(fx, y + 17, 112, 36, 7), gfx.stroke_paint(S.border, 1.2, alpha))
    for i, person in enumerate(content.people[:3]):
        person_tile(canvas, fx + 24 + i * 18, y + 35, 24, person, alpha, presence=False)
    gfx.text(canvas, str(len(content.people) + 1), fx + 92, y + 41, 17, S.muted, 400, 0.0, alpha, align="center")
    canvas.drawRRect(gfx.rrect(bx, y + 17, 84, 36, 7), gfx.stroke_paint(S.border, 1.2, alpha))
    glyph(canvas, "headset", bx + 24, y + 35, S.text, alpha, 9)
    canvas.drawLine(bx + 50, y + 25, bx + 50, y + 45, gfx.stroke_paint(S.border, 1.0, alpha, cap="butt"))
    caret(canvas, bx + 67, y + 34, S.text, alpha, 4)
    glyph(canvas, "more", x + w - 36, y + 35, S.text, alpha, 8)
    ty, tx = y + HEADER, x + 24
    for i, (kind, label) in enumerate((("bubble", "Messages"), ("folder", "Files"))):
        color = S.text if i == 0 else S.muted
        glyph(canvas, kind, tx + 9, ty + 20, color, alpha, 8)
        lw = gfx.text(canvas, label, tx + 28, ty + 27, 18, color, 500 if i == 0 else 400, 0.0, alpha)
        if i == 0:
            canvas.drawRRect(gfx.rrect(tx - 4, ty + TABS - 3, lw + 36, 3, 1.5), gfx.fill_paint(S.text, alpha))
        tx += lw + 60
    glyph(canvas, "plus", tx + 8, ty + 21, S.muted, alpha, 6)
    win.rule(canvas, S, x, ty + TABS, x + w, alpha)
    return ty + TABS


def divider(canvas, x, y, w, alpha):
    """The "Today" date divider: a hairline with the label in a bordered pill."""
    tw = gfx.text_width("Today", 16, 700)
    pw = tw + 36
    win.rule(canvas, S, x + 24, y, x + w - 24, alpha)
    canvas.drawRRect(gfx.rrect(x + (w - pw) / 2, y - 16, pw, 32, 16), gfx.fill_paint(S.bg, alpha))
    canvas.drawRRect(gfx.rrect(x + (w - pw) / 2, y - 16, pw, 32, 16), gfx.stroke_paint(S.border, 1.2, alpha))
    gfx.text(canvas, "Today", x + w / 2, y + 6, 16, S.text, 700, 0.0, alpha, align="center")


def human_height(lines, reaction):
    return 24 + MSG_LINE * len(lines) + 14 + (38 if reaction else 0)


def human_message(canvas, x, y, alpha, message, lines):
    """A person's message: the avatar tile, the name in bold with the time, the text `lines`,
    and a thumbs-up reaction pill when the message has reactions. Returns its height."""
    person, reaction = message.person, message.reactions
    person_tile(canvas, x + 44, y + 22, 42, person, alpha, presence=False)
    tx = x + 80
    nx = tx + gfx.text(canvas, person.name, tx, y + 24, 22, S.text, 700, 0.0, alpha) + 10
    gfx.text(canvas, message.time, nx, y + 24, 17, S.muted, 400, 0.0, alpha)
    for i, line in enumerate(lines):
        gfx.text(canvas, line, tx, y + 24 + (i + 1) * MSG_LINE, 22, S.text, 400, 0.0, alpha)
    if reaction:
        ry = y + 24 + MSG_LINE * len(lines) + 14
        canvas.drawRRect(gfx.rrect(tx, ry, 58, 28, 14), gfx.fill_paint(S.panel, alpha))
        canvas.drawRRect(gfx.rrect(tx, ry, 58, 28, 14), gfx.stroke_paint(S.border, 1.2, alpha))
        glyph(canvas, "thumb", tx + 19, ry + 14, S.text, alpha, 8)
        gfx.text(canvas, str(reaction), tx + 42, ry + 20, 15, S.text, 500, 0.0, alpha)
    return human_height(lines, reaction)


def notice_lines(notice, text_w):
    """The notice's lines for a text column `text_w` wide: each given line re-wrapped when the
    pane is too narrow for it (the first behind the check emoji); when the first line itself
    wraps, the whole notice flows as one paragraph behind the emoji."""
    first = ui.wrap(notice[0], 22, text_w - 32)
    if len(first) == 1:
        return first + [part for line in notice[1:] for part in ui.wrap(line, 22, text_w)]
    return ui.wrap(" ".join(notice), 22, text_w - 32)


def message(canvas, x, y, alpha, highlight, lines, content):
    """The app's post: the app's avatar (the project's logo), its name with the APP badge and
    the time, the check emoji and the notice `lines`, then the intro and the bulleted links.
    Returns (link rects, avatar centre)."""
    post = content.post
    ax, ay = x + 44, y + 22
    win.app_avatar(canvas, ax, ay, 42, content.app, alpha)
    tx = x + 80
    nx = tx + gfx.text(canvas, content.app, tx, y + 24, 22, S.text, 700, 0.0, alpha) + 8
    nx += win.badge(canvas, "APP", nx, y + 17, "#3a3d42", alpha, size=12, text_color=S.muted, radius=4) + 8
    gfx.text(canvas, post.time, nx, y + 24, 17, S.muted, 400, 0.0, alpha)
    ly = y + 24 + MSG_LINE
    icons.slack_check(canvas, tx + 12, ly - 8, 22, alpha)
    for i, line in enumerate(lines):
        gfx.text(canvas, line, tx + (32 if i == 0 else 0), ly + i * MSG_LINE, 22, S.text, 400, 0.0, alpha)
    ly += len(lines) * MSG_LINE + 14
    gfx.text(canvas, post.intro, tx, ly, 22, S.text, 400, 0.0, alpha)
    links = []
    for j, ref in enumerate(post.links):
        yy = ly + (j + 1) * MSG_LINE
        lw = gfx.text_width(ref, 22, 400)
        rect = (tx + 36 - 8, yy - 24, lw + 16, 32)
        if highlight > 0.002:
            p = gfx.fill_paint(S.link, 0.22 * highlight * alpha)
            p.setImageFilter(skia.ImageFilters.Blur(10, 10))
            canvas.drawRRect(gfx.rrect(*rect, 8), p)
            canvas.drawRRect(gfx.rrect(*rect, 8), gfx.fill_paint(S.link, 0.14 * highlight * alpha))
        gfx.text(canvas, "•", tx + 14, yy, 22, S.text, 400, 0.0, alpha)
        gfx.text(canvas, ref, tx + 36, yy, 22, S.link, 400, 0.0, alpha)
        links.append(rect)
    return links, (ax, ay)


def composer(canvas, x, y, w, alpha, channel):
    """The composer box: the formatting toolbar, the placeholder and the action row with send."""
    cx, cw = x + 20, w - 40
    rr = gfx.rrect(cx, y, cw, COMPOSER, 10)
    canvas.drawRRect(rr, gfx.fill_paint(S.panel, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint("#4a4d52", 1.2, alpha))
    tx = cx + 18
    for s, weight, italic in (("B", 700, False), ("I", 400, True), ("S", 400, False)):
        f = gfx.font(17, weight, italic)
        canvas.drawString(s, tx, y + 26, f, skia.Paint(AntiAlias=True, Color4f=gfx.col(S.muted, alpha)))
        if s == "S":
            canvas.drawLine(tx - 1, y + 20, tx + 11, y + 20, gfx.stroke_paint(S.muted, 1.4, alpha, cap="butt"))
        tx += 30
    canvas.drawLine(tx - 6, y + 12, tx - 6, y + 30, gfx.stroke_paint(S.border, 1.0, alpha, cap="butt"))
    ui.mono_text(canvas, "</>", tx + 6, y + 26, 15, S.muted, alpha)
    gfx.text(canvas, f"Message #{channel}", cx + 18, y + 68, 21, S.muted, 400, 0.0, alpha)
    by = y + COMPOSER - 22
    canvas.drawCircle(cx + 32, by, 13, gfx.fill_paint(WHITE, 0.10 * alpha))
    glyph(canvas, "plus", cx + 32, by, S.text, alpha, 6.5)
    gfx.text(canvas, "Aa", cx + 60, by + 6, 17, S.muted, 500, 0.0, alpha)
    glyph(canvas, "emoji", cx + 110, by, S.muted, alpha, 8)
    gfx.text(canvas, "@", cx + 136, by + 6, 18, S.muted, 400, 0.0, alpha)
    sx = cx + cw - 64
    canvas.drawRRect(gfx.rrect(sx, by - 16, 50, 32, 6), gfx.fill_paint(SEND, alpha))
    glyph(canvas, "plane", sx + 17, by, WHITE, alpha, 7)
    canvas.drawLine(sx + 33, by - 9, sx + 33, by + 9, gfx.stroke_paint(WHITE, 1.0, 0.5 * alpha, cap="butt"))
    caret(canvas, sx + 42, by - 1, WHITE, alpha, 3.5)


def history(canvas, x, w, my0, msg_h, slide, alpha, content, text_w):
    """The earlier messages under the "Today" divider, at the foot of the pane: they sit where
    the post will be and move up by its height as it arrives (`slide` 0..1)."""
    earlier = [(m, ui.wrap(m.text, 22, text_w)) for m in content.earlier]
    stack = sum(human_height(ls, m.reactions) for m, ls in earlier) + 8
    ey = my0 - 8 - stack + msg_h * (1 - slide)
    divider(canvas, x, ey - 30, w, alpha)
    for m, ls in earlier:
        ey += human_message(canvas, x, ey, alpha, m, ls)


def slack_window(canvas, x, y, w, h, alpha, content, reveal, highlight=0.0) -> dict:
    """Draw Slack's desktop window showing the selected channel of `content`
    (lib/slack_content.SlackContent).
    reveal 0..1: the app's post arriving (0 = the channel without it, 1 = fully in).
    highlight 0..1: a soft emphasis on the post's links (for something landing on them).
    Returns canvas-space anchors: {"message": (x, y, w, h), "links": [(x, y, w, h), ...], "avatar": (cx, cy)}."""
    reveal, highlight = clamp01(reveal), clamp01(highlight)
    px, pw = x + RAIL + SIDE, w - RAIL - SIDE                 # the message pane
    # the earlier messages slide up first, then the post fades in below them, as Slack's list does
    slide, ra = smooth(seg(reveal, 0.0, 0.55)), smooth(seg(reveal, 0.5, 1.0))
    dy = 14 * (1 - cubic_out(seg(reveal, 0.5, 1.0)))
    text_w = pw - 80 - 24                                     # the text column beside the avatars
    lines = notice_lines(content.post.notice, text_w)
    msg_h = 24 + (len(lines) + 1 + len(content.post.links)) * MSG_LINE + 14 + 12
    my0 = y + h - 16 - COMPOSER - 20 - msg_h                  # the post, once in
    my = my0 + dy
    anchors = {"message": (px, my, pw, msg_h), "links": [], "avatar": (px + 44, my + 22)}
    if alpha <= 0.002:   # nothing visible, but callers aim at the links before the window shows
        anchors["links"], anchors["avatar"] = message(canvas, px, my, 0.0, 0.0, lines, content)
        return anchors
    win.window(canvas, S, x, y, w, h, alpha)
    # the aubergine frame, then the message pane as a dark card with a rounded top-left corner
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, h), gfx.fill_paint(FRAME, alpha))
    canvas.drawRRect(gfx.rrect(px, y + TOP, pw + 10, h - TOP + 10, 10), gfx.fill_paint(S.bg, alpha))
    frame(canvas, x, y, w, h, alpha, content)
    sidebar(canvas, x + RAIL, y + TOP, h - TOP, alpha, content)
    top = header(canvas, px, y + TOP, pw, alpha, content)
    canvas.save()
    canvas.clipRect(skia.Rect.MakeLTRB(px + 1, top + 1, x + w, y + h - 16 - COMPOSER - 8))
    history(canvas, px, pw, my0, msg_h, slide, alpha, content, text_w)
    links, avatar = message(canvas, px, my, alpha * ra, highlight * ra, lines, content)
    # at small heights the list scrolls under the tabs: a short fade into the pane colour at the
    # top, shortened so it never covers the post once that reaches the top
    fh = min(56.0, max(0.0, my - 6 - top))
    if fh > 1:
        fade = skia.Paint(AntiAlias=True)
        fade.setShader(skia.GradientShader.MakeLinear([(px, top), (px, top + fh)], [gfx.col(S.bg, alpha), gfx.col(S.bg, 0.0)]))
        canvas.drawRect(skia.Rect.MakeLTRB(px, top, x + w, top + fh), fade)
    canvas.restore()
    composer(canvas, px, y + h - 16 - COMPOSER, pw, alpha, content.channel)
    canvas.restore()
    anchors["links"], anchors["avatar"] = links, avatar
    return anchors
