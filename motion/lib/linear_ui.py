"""Linear's issue view in the dark theme, redrawn from the product (motion/reference/linear.md):
the tab bar, the dim navigation sidebar, the breadcrumb row, the issue with its Activity feed and
agent session, and the properties panel at the right, where a delegated agent sits nested under
the assignee. Colours are the variables of Linear's own CSS; Inter is Linear's typeface. Strings
are Linear's chrome or the scene's lib/linear_content.LinearContent. `linear_window` draws the
whole view; the pieces it is built from are public for a scene that lays the view out itself."""

import skia

from . import gfx, icons, logos, ui, win
from .ease import clamp01, seg, smooth
from .linear_glyphs import nav_glyph, stroke, ui_glyph
from .win import rise

# Linear's dark theme: --color-bg-level-0..3, --color-text-primary..quaternary, --color-border-*
BG0, BG1, BG2, BG3 = "#08090a", "#0f1011", "#141516", "#191a1b"
CARD = "#17191a"                   # the agent session card (sampled from Linear's screenshot)
BORDER, BORDER2 = "#23252a", "#34343a"
TEXT, TEXT2, TEXT3, TEXT4 = "#f7f8f8", "#d0d6e0", "#8a8f98", "#62666d"
SELECTED = "#1f2023"               # the selected sidebar row
INDIGO, LINK, YELLOW = "#5e6ad2", "#828fff", "#f2c94c"
TABBAR, CRUMB = 54, 58             # the tab bar's and the breadcrumb row's heights
SB, PANEL = 330, 440               # the sidebar's and the properties panel's widths
T = win.LINEAR                     # status ring colours (todo grey, yellow, indigo)
TITLE_LH = 42                      # the issue title's line height at 32 px
ROW, THOUGHT_LH = 48, 28           # an activity row's pitch; a thought's line height
STATUS_SWAP = 0.43                 # status progress at which Todo has faded and In Progress starts


def agent(canvas, cx, cy, r, name, alpha):
    """An agent's round avatar: the app's avatar (the project's logo) in a thin ring."""
    win.app_avatar(canvas, cx, cy, 2 * r, name, alpha, radius=r)
    canvas.drawCircle(cx, cy, r, gfx.stroke_paint(BORDER2, 1.0, alpha))


def person(canvas, cx, cy, r, who, alpha):
    """A person's round avatar with initials."""
    ui.avatar(canvas, cx, cy, r, who.initials, who.color, alpha, size=r * 0.9)


def team_tile(canvas, cx, cy, size, alpha):
    """A team's icon tile: a tinted rounded square with a small ring."""
    canvas.drawRRect(gfx.rrect(cx - size / 2, cy - size / 2, size, size, 4), gfx.fill_paint(INDIGO, 0.28 * alpha))
    canvas.drawCircle(cx, cy, size * 0.22, gfx.stroke_paint(LINK, 1.6, alpha))


def frame(canvas, x, y, w, h, alpha, content, status="todo"):
    """The window: the tab bar with the issue's tab (its status ring in `status`), the sidebar,
    the breadcrumb row and the properties panel's divider. Returns (content x, content y, panel x)."""
    px, py = x + SB, y + TABBAR
    if alpha <= 0.002:
        return px, py + CRUMB, x + w - PANEL
    win.window(canvas, T, x, y, w, h, alpha)
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, TABBAR), gfx.fill_paint(BG0, alpha))
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, SB, h), gfx.fill_paint(BG0, alpha))
    for i, kind in enumerate(("back", "forward", "history")):
        ui_glyph(canvas, kind, px + 40 + i * 38, y + TABBAR / 2, TEXT3, alpha, 8)
    label = f"{content.issue} {content.title}"
    tw = gfx.text_width(label, 20, 400)
    icons.linear_status(canvas, status, x + (w - tw) / 2 - 22, y + TABBAR / 2, 8, alpha, T)
    gfx.text(canvas, label, x + (w - tw) / 2, y + TABBAR / 2 + 7, 20, TEXT2, 400, 0.0, alpha)
    ui_glyph(canvas, "plus", x + w - 36, y + TABBAR / 2, TEXT3, alpha, 8)
    canvas.drawLine(x + SB, py, x + SB, y + h, gfx.stroke_paint(BORDER, 1.0, alpha, cap="butt"))
    sidebar(canvas, x, py, h - TABBAR, alpha, content)
    bx = px + 36
    team_tile(canvas, bx + 10, py + CRUMB / 2, 20, alpha)
    bx += 34
    bx += gfx.text(canvas, content.team, bx, py + CRUMB / 2 + 7, 20, TEXT2, 400, 0.0, alpha) + 14
    bx += gfx.text(canvas, "›", bx, py + CRUMB / 2 + 7, 20, TEXT4, 400, 0.0, alpha) + 14
    bx += gfx.text(canvas, content.issue, bx, py + CRUMB / 2 + 7, 20, TEXT, 400, 0.0, alpha) + 26
    nav_glyph(canvas, "more", bx, py + CRUMB / 2, TEXT3, alpha, 7)
    ui_glyph(canvas, "star", bx + 36, py + CRUMB / 2, TEXT3, alpha, 8)
    panel_x = x + w - PANEL
    canvas.drawLine(px, py + CRUMB, panel_x, py + CRUMB, gfx.stroke_paint(BORDER, 1.0, alpha, cap="butt"))
    canvas.drawLine(panel_x, py, panel_x, y + h, gfx.stroke_paint(BORDER, 1.0, alpha, cap="butt"))
    canvas.restore()
    return px, py + CRUMB, panel_x


def sidebar(canvas, x, y, h, alpha, content):
    """The navigation sidebar: the workspace row with the Linear mark, Inbox and My issues, the
    Workspace and Your teams sections, with the team's Issues selected."""
    lx = x + 22
    logos.linear(canvas, lx, y + 26, 24, alpha)
    name = ui.fit(content.workspace, 20, SB - 72 - 97)    # the name and its caret stop short of the search glyph
    tw = gfx.text(canvas, name, lx + 36, y + 45, 20, TEXT, 400, 0.0, alpha)
    ui_glyph(canvas, "caret", lx + 46 + tw, y + 38, TEXT3, alpha, 7)
    nav_glyph(canvas, "search", x + SB - 72, y + 38, TEXT3, alpha, 8)
    canvas.drawRRect(gfx.rrect(x + SB - 50, y + 22, 32, 32, 7), gfx.fill_paint(BG2, alpha))
    canvas.drawRRect(gfx.rrect(x + SB - 50, y + 22, 32, 32, 7), gfx.stroke_paint(BORDER, 1.0, alpha))
    nav_glyph(canvas, "compose", x + SB - 34, y + 38, TEXT2, alpha, 7)
    yy = y + 104
    for kind, label in (("inbox", "Inbox"), ("person", "My issues")):
        nav_glyph(canvas, kind, lx + 10, yy - 7, TEXT3, alpha, 8.5)
        gfx.text(canvas, label, lx + 36, yy, 20, TEXT2, 400, 0.0, alpha)
        yy += 42
    yy += 18
    gfx.text(canvas, "Workspace", lx, yy, 17, TEXT3, 400, 0.0, alpha)
    ui_glyph(canvas, "caret", lx + gfx.text_width("Workspace", 17, 400) + 14, yy - 5, TEXT4, alpha, 6)
    yy += 42
    for kind, label in (("mountain", "Initiatives"), ("cube", "Projects"), ("layers", "Views"), ("more", "More")):
        nav_glyph(canvas, kind, lx + 10, yy - 7, TEXT3, alpha, 8.5)
        gfx.text(canvas, label, lx + 36, yy, 20, TEXT2, 400, 0.0, alpha)
        yy += 42
    yy += 18
    gfx.text(canvas, "Your teams", lx, yy, 17, TEXT3, 400, 0.0, alpha)
    ui_glyph(canvas, "caret", lx + gfx.text_width("Your teams", 17, 400) + 14, yy - 5, TEXT4, alpha, 6)
    yy += 42
    team_tile(canvas, lx + 10, yy - 7, 20, alpha)
    tw = gfx.text(canvas, content.team, lx + 36, yy, 20, TEXT2, 400, 0.0, alpha)
    ui_glyph(canvas, "caret", lx + 50 + tw, yy - 7, TEXT4, alpha, 6)
    yy += 42
    for kind, label in (("triage", "Triage"), (None, "Issues"), ("cycles", "Cycles"), ("cube", "Projects"), ("layers", "Views")):
        if label == "Issues":
            canvas.drawRRect(gfx.rrect(x + 12, yy - 27, SB - 24, 38, 6), gfx.fill_paint(SELECTED, alpha))
            icons.linear_status(canvas, "todo", lx + 26, yy - 7, 7, alpha, T)
        else:
            nav_glyph(canvas, kind, lx + 26, yy - 7, TEXT3, alpha, 8)
        gfx.text(canvas, label, lx + 52, yy, 20, TEXT if label == "Issues" else TEXT2, 400, 0.0, alpha)
        yy += 42


def properties_header(canvas, x, y, alpha):
    """"Properties" with the link, copy-id and branch actions at the right of the panel."""
    gfx.text(canvas, "Properties", x + 28, y, 20, TEXT3, 400, 0.0, alpha)
    ui_glyph(canvas, "link", x + PANEL - 112, y - 7, TEXT3, alpha, 8)
    canvas.drawRRect(gfx.rrect(x + PANEL - 82, y - 15, 24, 16, 4), stroke(TEXT3, alpha, 1.4))
    gfx.text(canvas, "ID", x + PANEL - 70, y - 3, 10, TEXT3, 600, 0.0, alpha, align="center")
    ui_glyph(canvas, "branch", x + PANEL - 36, y - 7, TEXT3, alpha, 8)


def prop_row(canvas, x, y, alpha, label, color=TEXT, icon=None):
    """A property value row: its icon, drawn by `icon(cx, cy)`, then the label."""
    if alpha <= 0.002:
        return
    if icon:
        icon(x + 40, y - 7)
    gfx.text(canvas, label, x + 68, y, 21, color, 400, 0.0, alpha)


def nested_connector(canvas, x, y1, y2, alpha):
    """The thin elbow that hangs a delegated agent under the assignee."""
    path = skia.Path()
    path.moveTo(x, y1)
    path.lineTo(x, y2 - 8)
    path.quadTo(x, y2, x + 8, y2)
    path.lineTo(x + 14, y2)
    canvas.drawPath(path, gfx.stroke_paint(BORDER2, 1.5, alpha, cap="butt"))


def popover(canvas, x, y, alpha, chosen, name):
    """Linear's "Delegate to..." menu beside the assignee: No agent, then the agent `name`, with
    the check on the chosen row (`chosen` 0 = No agent, 1 = the agent)."""
    if alpha <= 0.002:
        return
    w, h = 380, 176
    win.shadow(canvas, x, y, w, h, alpha, radius=10, sigma=18, offset=10, strength=0.5)
    rr = gfx.rrect(x, y, w, h, 10)
    canvas.drawRRect(rr, gfx.fill_paint(BG3, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(BORDER2, 1.0, alpha))
    gfx.text(canvas, "Delegate to...", x + 22, y + 40, 20, TEXT3, 400, 0.0, alpha)
    canvas.drawLine(x, y + 62, x + w, y + 62, gfx.stroke_paint(BORDER2, 1.0, alpha, cap="butt"))
    ui_glyph(canvas, "noagent", x + 36, y + 96, TEXT3, alpha, 9)
    gfx.text(canvas, "No agent", x + 62, y + 103, 21, TEXT, 400, 0.0, alpha)
    ui_glyph(canvas, "check", x + w - 32, y + 96, TEXT, alpha * (1 - chosen), 9)
    agent(canvas, x + 36, y + 146, 11, name, alpha)
    gfx.text(canvas, name, x + 62, y + 153, 21, TEXT, 400, 0.0, alpha)
    ui_glyph(canvas, "check", x + w - 32, y + 146, TEXT, alpha * chosen, 9)


def activity_header(canvas, x, y, right, alpha, content):
    """"Activity" with Unsubscribe and the subscribers (the assignee and the agent) at the right."""
    gfx.text(canvas, "Activity", x, y, 24, TEXT, 600, 0.0, alpha)
    gfx.text(canvas, "Unsubscribe", right - 72, y - 1, 20, TEXT3, 400, 0.0, alpha, align="right")
    person(canvas, right - 40, y - 8, 13, content.assignee, alpha)
    agent(canvas, right - 18, y - 8, 13, content.agent, alpha)


def session_card(canvas, x, y, w, h, alpha, state, name):
    """The agent session block in the activity feed: a raised card headed by the agent's avatar,
    name and state, with Activity and more at the right. Returns the y below the header."""
    if alpha <= 0.002:
        return y + 62
    rr = gfx.rrect(x, y, w, h, 10)
    canvas.drawRRect(rr, gfx.fill_paint(CARD, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(BORDER, 1.0, alpha))
    agent(canvas, x + 36, y + 31, 14, name, alpha)
    nx = x + 62
    nx += gfx.text(canvas, name, nx, y + 38, 21, TEXT, 600, 0.0, alpha) + 12
    gfx.text(canvas, state, nx, y + 38, 20, TEXT3, 400, 0.0, alpha)
    nav_glyph(canvas, "more", x + w - 36, y + 31, TEXT3, alpha, 7)
    gfx.text(canvas, "Activity", x + w - 72, y + 38, 20, TEXT2, 400, 0.0, alpha, align="right")
    nav_glyph(canvas, "layers", x + w - 170, y + 31, TEXT2, alpha, 7)
    canvas.drawLine(x, y + 62, x + w, y + 62, gfx.stroke_paint(BORDER, 1.0, alpha, cap="butt"))
    return y + 62


def activity_row(canvas, x, y, w, alpha, label, when, name):
    """One agent activity: the agent's small avatar, the action and its time at the right."""
    if alpha <= 0.002:
        return
    agent(canvas, x + 36, y - 7, 11, name, alpha)
    gfx.text(canvas, label, x + 62, y, 21, TEXT, 400, 0.0, alpha)
    gfx.text(canvas, when, x + w - 28, y, 19, TEXT3, 400, 0.0, alpha, align="right")


def comment_box(canvas, x, y, w, alpha):
    """The collapsed comment box at the foot of the activity feed: "Leave a comment..." with the
    attachment and send buttons."""
    if alpha <= 0.002:
        return
    rr = gfx.rrect(x, y, w, 60, 10)
    canvas.drawRRect(rr, gfx.fill_paint(BG2, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(BORDER, 1.0, alpha))
    gfx.text(canvas, "Leave a comment...", x + 22, y + 37, 21, TEXT4, 400, 0.0, alpha)
    ui_glyph(canvas, "link", x + w - 80, y + 30, TEXT3, alpha, 8)
    canvas.drawCircle(x + w - 34, y + 30, 15, gfx.fill_paint(BG3, alpha))
    canvas.drawCircle(x + w - 34, y + 30, 15, gfx.stroke_paint(BORDER2, 1.0, alpha))
    p = stroke(TEXT3, alpha)
    canvas.drawLine(x + w - 34, y + 37, x + w - 34, y + 23, p)
    canvas.drawLine(x + w - 34, y + 23, x + w - 39, y + 28, p)
    canvas.drawLine(x + w - 34, y + 23, x + w - 29, y + 28, p)


def thought(canvas, x, y, lines, alpha, lh=THOUGHT_LH):
    """An agent thought under its activity: secondary text behind a thin left rule."""
    if alpha <= 0.002:
        return
    canvas.drawRect(skia.Rect.MakeXYWH(x + 62, y - 22, 2, lh * len(lines) + 2), gfx.fill_paint(BORDER2, alpha))
    for i, line in enumerate(lines):
        gfx.text(canvas, line, x + 84, y + i * lh, 21, TEXT2, 400, 0.0, alpha)


# ---------------------------------------------------------------- the whole issue view


def thought_height(activity):
    return THOUGHT_LH * len(activity.thought) + 24 if activity.thought else 0


def issue_body(canvas, x, top, right, alpha, content):
    """The title and the description, each wrapped to the column (everything below moves down
    by the extra lines), the reaction and attachment buttons, "Add sub-issues", a hairline and
    the Activity header. Returns the feed's top."""
    titles = ui.wrap(content.title, 32, right - x, 600)
    for i, line in enumerate(titles):
        gfx.text(canvas, line, x, top + 70 + i * TITLE_LH, 32, TEXT, 600, 0.0, alpha)
    dy = TITLE_LH * (max(1, len(titles)) - 1)
    lines = ui.wrap(content.description, 23, right - x)
    for i, line in enumerate(lines):
        gfx.text(canvas, line, x, top + 112 + dy + i * 34, 23, TEXT2, 400, 0.0, alpha)
    y = top + 112 + dy + 34 * (max(1, len(lines)) - 1)     # the last description line's baseline
    canvas.drawCircle(x + 12, y + 38, 9, gfx.stroke_paint(TEXT3, 1.6, alpha))
    ui_glyph(canvas, "plus", x + 24, y + 30, TEXT3, alpha, 4)
    ui_glyph(canvas, "link", right - 14, y + 38, TEXT3, alpha, 8)
    ui_glyph(canvas, "plus", x + 10, y + 80, TEXT3, alpha, 6)
    gfx.text(canvas, "Add sub-issues", x + 28, y + 87, 20, TEXT3, 400, 0.0, alpha)
    gfx.hairline(canvas, x, y + 116, right, y + 116, alpha, BORDER)
    activity_header(canvas, x, y + 162, right, alpha, content)
    return y + 194


def feed(canvas, x, y, right, alpha, content, delegated, session, shown, limit):
    """The delegation event ("<assignee> delegated to <agent> · <time>"), then the agent session
    card, which grows with each activity and its thought as `shown` counts them in. The card
    stops at `limit` (the comment box's top less a gap) and a row or thought that would cross it
    is not drawn: at h=1000 with a two-line description about six activities fit, fewer when
    they carry thoughts (a four-line thought takes as much as three activities)."""
    da, dy = rise(seg(delegated, 0.2, 1.0))
    a = alpha * da
    person(canvas, x + 12, y + dy - 7, 10, content.assignee, a)
    ex = x + 34
    ex += gfx.text(canvas, content.assignee.name, ex, y + dy, 20, TEXT2, 400, 0.0, a) + 7
    ex += gfx.text(canvas, "delegated to", ex, y + dy, 20, TEXT3, 400, 0.0, a) + 7
    ex += gfx.text(canvas, content.agent, ex, y + dy, 20, TEXT2, 400, 0.0, a) + 9
    gfx.text(canvas, f"·  {content.delegated}", ex, y + dy, 20, TEXT3, 400, 0.0, a)
    sa, sdy = rise(session)
    sy = y + 24 + sdy
    acts = content.activities
    steps = [clamp01(shown - i) for i in range(len(acts))]
    grown = sum(ROW * smooth(seg(p, 0.0, 0.5)) + thought_height(act) * smooth(seg(p, 0.6, 1.0)) for p, act in zip(steps, acts))
    card_h = min(62 + 20 + grown + 6, max(0.0, limit - sy))
    bottom = sy + card_h - 14                       # a baseline below this belongs to a row that does not fit
    ry = session_card(canvas, x, sy, right - x, card_h, alpha * sa, "agent connected", content.agent) + 42
    canvas.save()
    canvas.clipRect(skia.Rect.MakeLTRB(x, sy, right, sy + card_h))
    offset = 0.0
    for i, (p, act) in enumerate(zip(steps, acts)):
        ra, rdy = rise(seg(p, 0.15, 0.65))
        row_y = ry + i * ROW + offset
        if row_y > bottom:
            break
        activity_row(canvas, x, row_y + rdy, right - x, alpha * ra, act.label, act.time, content.agent)
        if act.thought:
            ta, tdy = rise(seg(p, 0.6, 1.0))
            ty = ry + (i + 1) * ROW + offset
            if ty + THOUGHT_LH * (len(act.thought) - 1) <= bottom:
                thought(canvas, x, ty + tdy, act.thought, alpha * ta)
            offset += thought_height(act) * ta
    canvas.restore()


def properties(canvas, x, top, alpha, content, menu, chosen, delegated, status):
    """The properties panel: status (Todo fading to In Progress with `status`), priority, the
    assignee, the agent hung under it once delegated (the rows below move down to make room),
    estimate, labels, project; and the Delegate to... menu beside the assignee."""
    properties_header(canvas, x, top - 22, alpha)
    rows = [top + 40 + i * 54 for i in range(5)]      # status, priority, assignee, agent, estimate
    a_todo = alpha * (1 - smooth(seg(status, 0.0, STATUS_SWAP)))
    a_prog = alpha * smooth(seg(status, STATUS_SWAP, 1.0))
    prop_row(canvas, x, rows[0], a_todo, "Todo", icon=lambda cx, cy: icons.linear_status(canvas, "todo", cx, cy, 8, a_todo, T))
    prop_row(canvas, x, rows[0], a_prog, "In Progress", icon=lambda cx, cy: icons.linear_status(canvas, "progress", cx, cy, 8, a_prog, T))
    prop_row(canvas, x, rows[1], alpha, "Set priority", TEXT3, icon=lambda cx, cy: icons.linear_priority_none(canvas, cx + 2, cy, TEXT3, alpha))
    prop_row(canvas, x, rows[2], alpha, content.assignee.name, icon=lambda cx, cy: person(canvas, cx, cy, 10, content.assignee, alpha))
    da, ddy = rise(seg(delegated, 0.1, 0.9), 6)
    nested_connector(canvas, x + 40, rows[2] + 8, rows[3] - 7, alpha * da)
    prop_row(canvas, x + 32, rows[3] + ddy, alpha * da, content.agent, icon=lambda cx, cy: agent(canvas, cx, cy, 10, content.agent, alpha * da))
    ey = rows[3] + 54 * smooth(seg(delegated, 0.0, 0.8))
    prop_row(canvas, x, ey, alpha, "Set estimate", TEXT3, icon=lambda cx, cy: ui_glyph(canvas, "estimate", cx, cy, TEXT3, alpha, 8))
    gfx.text(canvas, "Labels", x + 28, ey + 62, 20, TEXT3, 400, 0.0, alpha)
    canvas.drawCircle(x + 40, ey + 100, 13, gfx.stroke_paint(BORDER2, 1.2, alpha))
    ui_glyph(canvas, "plus", x + 40, ey + 100, TEXT3, alpha, 6)
    gfx.text(canvas, "Project", x + 28, ey + 158, 20, TEXT3, 400, 0.0, alpha)
    prop_row(canvas, x, ey + 200, alpha, "Add to project", TEXT3, icon=lambda cx, cy: nav_glyph(canvas, "cube", cx, cy, TEXT3, alpha, 8))
    popover(canvas, x - 392, rows[2] - 30, alpha * menu, chosen, content.agent)


def linear_window(canvas, x, y, w, h, alpha, content, *, menu=0.0, chosen=0.0, delegated=0.0, status=0.0,
                  session=0.0, shown=0.0):
    """Draw Linear's issue view of `content` (lib/linear_content.LinearContent) in (x, y, w, h);
    laid out for a window about 1800x1000. Each state runs 0..1 and is the scene's to time:
    menu: the Delegate to... menu's opacity; chosen: its check moving from No agent to the agent;
    delegated: the agent hanging under the assignee and the delegation event in the feed;
    status: Todo turning In Progress (the tab bar's ring swaps at STATUS_SWAP);
    session: the agent session card rising in.
    shown counts the activities in (0 .. len(activities)); a fraction is the next one arriving:
    its row, then its thought."""
    kind = "progress" if status >= STATUS_SWAP else "todo"
    cx, cy, px = frame(canvas, x, y, w, h, alpha, content, kind)
    if alpha <= 0.002:
        return
    canvas.save()
    canvas.clipRRect(gfx.rrect(x, y, w, h, 10), True)
    fx, right = cx + 64, px - 64
    fy = issue_body(canvas, fx, cy, right, alpha, content)
    feed(canvas, fx, fy, right, alpha, content, delegated, session, shown, y + h - 88 - 16)
    comment_box(canvas, fx, y + h - 88, right - fx, alpha)
    properties(canvas, px, cy, alpha, content, menu, chosen, delegated, status)
    canvas.restore()
