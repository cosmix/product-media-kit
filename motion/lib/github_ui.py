"""GitHub's web UI in the dark default theme, drawn from Primer's tokens and the product's layout
(motion/reference/github.md): the global header with the GitHub mark, the repository navigation,
the pull request list page (toolbar, list box, rows) and the pull request page (title and state
row, tab row with the diffstat, timeline comments and commits, the merge box, the sidebar). The
names and text come from the scene (lib/github_content.py); the UI's own labels are GitHub's
(reference/github.md, "UI labels used"). Sizes are about 1.4x GitHub's 14 px base so body text
stays 20 px and up at 1080p. lib/github_pages.py lays these pieces out as whole pages."""

import datetime

import skia

from . import gfx, logos, ui, win
from .icons import octicon

T = win.GITHUB
CONTROL = "#212830"            # control-bgColor-rest: buttons, inputs
SELECTED = "#1f6feb"           # bgColor-accent-emphasis: the selected subnav item
COUNTER = "#262c36"            # bgColor-neutral-muted (#656c76 at 20 %) over the page ground
HEADER_H, NAV_H, ROW_H = 80, 64, 128   # the global header, the repository tabs, a pull request row
R = 6                          # Primer's border radius
NAV = [("Code", "code"), ("Issues", "issue-opened"), ("Pull requests", "git-pull-request"), ("Actions", "play"),
       ("Projects", "table"), ("Security", "shield"), ("Insights", "graph")]
# github.com/pulls: the subnav's views and the search query each one fills in
QUERIES = {"Created": "is:open is:pr author:@me archived:false",
           "Assigned": "is:open is:pr assignee:@me archived:false",
           "Mentioned": "is:open is:pr mentions:@me archived:false",
           "Review requests": "is:open is:pr review-requested:@me archived:false"}
SUBNAV = tuple(QUERIES)


# ---------------------------------------------------------------- controls


def button(canvas, s, x, y, w, h, alpha, icon=None, caret=False, fill=CONTROL, color=None):
    """Primer's default button: control ground, 1 px border, optional leading icon and caret."""
    if alpha <= 0.002:
        return
    rr = gfx.rrect(x, y, w, h, R)
    canvas.drawRRect(rr, gfx.fill_paint(fill, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(T.border, 1.0, alpha))
    tx = x + 14
    if icon:
        octicon(canvas, icon, tx, y + h / 2 - 10, 20, color or T.muted, alpha)
        tx += 30
    if s:
        tx += gfx.text(canvas, s, tx, y + h / 2 + 7, 20, color or T.text, 500, 0.0, alpha) + 8
    if caret:
        octicon(canvas, "triangle-down", tx - 4, y + h / 2 - 9, 18, T.muted, alpha)


def icon_button(canvas, name, x, y, alpha, size=44):
    button(canvas, "", x, y, size, size, alpha, fill=T.inset)
    octicon(canvas, name, x + size / 2 - 11, y + size / 2 - 11, 22, T.muted, alpha)


def counter(canvas, n, x, y, alpha, size=16):
    """The small round counter after a tab label. Returns its width."""
    return win.badge(canvas, str(n), x, y, COUNTER, alpha, size=size, text_color=T.text)


def search_box(canvas, x, y, w, h, alpha, placeholder="Type / to search", kbd=True):
    rr = gfx.rrect(x, y, w, h, R)
    canvas.drawRRect(rr, gfx.fill_paint(T.bg, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(T.border, 1.0, alpha))
    octicon(canvas, "search", x + 14, y + h / 2 - 10, 20, T.muted, alpha)
    gfx.text(canvas, placeholder, x + 46, y + h / 2 + 7, 20, T.muted, 400, 0.0, alpha)
    if kbd:
        canvas.drawRRect(gfx.rrect(x + w - 42, y + h / 2 - 14, 28, 28, 4), gfx.stroke_paint(T.border, 1.0, alpha))
        gfx.text(canvas, "/", x + w - 28, y + h / 2 + 6, 17, T.muted, 400, 0.0, alpha, align="center")


# ---------------------------------------------------------------- chrome


def header(canvas, x, y, w, alpha, crumbs, viewer):
    """The global header (80 px, inset ground): the menu button, the GitHub mark, the context
    `crumbs`, (text, bold) pairs ("owner / repo", the last in bold); at the right the search box,
    the create button, the Issues, Pull requests and Inbox buttons and the `viewer`'s avatar."""
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, HEADER_H), gfx.fill_paint(T.inset, alpha))
    gfx.hairline(canvas, x, y + HEADER_H, x + w, y + HEADER_H, alpha, T.border)
    icon_button(canvas, "three-bars", x + 24, y + 18, alpha)
    logos.github(canvas, x + 86, y + 18, 44, T.text, alpha)
    bx = x + 150
    for i, (s, bold) in enumerate(crumbs):
        if i:
            bx += gfx.text(canvas, "/", bx, y + 49, 22, T.muted, 400, 0.0, alpha) + 12
        bx += gfx.text(canvas, s, bx, y + 49, 22, T.text, 600 if bold else 400, 0.0, alpha) + 12
    rx = x + w - 24 - 44
    ui.avatar(canvas, rx + 22, y + 40, 22, viewer.initials, viewer.color, alpha, size=18)
    for name in ("inbox", "git-pull-request", "issue-opened"):
        rx -= 58
        icon_button(canvas, name, rx, y + 18, alpha)
    rx -= 16
    gfx.hairline(canvas, rx, y + 28, rx, y + 52, alpha, T.border)
    rx -= 16 + 76
    button(canvas, "", rx, y + 18, 76, 44, alpha, icon="plus", caret=True, fill=T.inset)
    search_box(canvas, rx - 14 - 440, y + 18, 440, 44, alpha)


def repo_nav(canvas, x, y, w, alpha, active, counts):
    """The repository's tabs (Code ... Insights) with octicons, counters and the orange underline."""
    tx = x + 24
    for label, icon in NAV:
        on = label == active
        lw = gfx.text_width(label, 20, 600 if on else 400)
        iw = 14 + 30 + lw + 14
        octicon(canvas, icon, tx + 14, y + 22, 20, T.muted, alpha)
        gfx.text(canvas, label, tx + 44, y + 40, 20, T.text, 600 if on else 400, 0.0, alpha)
        if label in counts:
            iw += counter(canvas, counts[label], tx + 44 + lw + 8, y + 33, alpha) + 8
        if on:
            canvas.drawRRect(gfx.rrect(tx, y + NAV_H - 3, iw, 3, 1.5), gfx.fill_paint(win.GH_TAB, alpha))
        tx += iw + 8
    gfx.hairline(canvas, x, y + NAV_H, x + w, y + NAV_H, alpha, T.border)


def frame(canvas, x, y, w, h, alpha, crumbs, viewer, nav=None, counts=None):
    """The window with the global header and, for a repository page, its tabs with `nav`
    active. Returns the content y; the canvas is left unclipped."""
    cy = y + HEADER_H + (NAV_H if nav else 0)
    if alpha <= 0.002:
        return cy
    win.window(canvas, T, x, y, w, h, alpha)
    header(canvas, x, y, w, alpha, crumbs, viewer)
    if nav:
        repo_nav(canvas, x, y + HEADER_H, w, alpha, nav, counts or {})
    canvas.restore()
    return cy


# ---------------------------------------------------------------- the pull request list


def pulls_toolbar(canvas, x, y, w, alpha, tab):
    """github.com/pulls: the segmented subnav (Created ... Review requests) with `tab` selected,
    and the search input holding that view's query. 44 px tall."""
    widths = [gfx.text_width(s, 20, 500) + 40 for s in SUBNAV]
    gw = sum(widths)
    group = gfx.rrect(x, y, gw, 44, R)
    canvas.save()
    canvas.clipRRect(group, True)
    tx = x
    for s, sw in zip(SUBNAV, widths):
        on = s == tab
        if on:
            canvas.drawRect(skia.Rect.MakeXYWH(tx, y, sw, 44), gfx.fill_paint(SELECTED, alpha))
        gfx.text(canvas, s, tx + 20, y + 29, 20, "#ffffff" if on else T.text, 500, 0.0, alpha)
        tx += sw
        if tx < x + gw:
            gfx.hairline(canvas, tx, y, tx, y + 44, alpha, T.border)
    canvas.restore()
    canvas.drawRRect(group, gfx.stroke_paint(T.border, 1.0, alpha))
    sx = x + gw + 24
    rr = gfx.rrect(sx, y, x + w - sx, 44, R)
    canvas.drawRRect(rr, gfx.fill_paint(T.bg, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(T.border, 1.0, alpha))
    octicon(canvas, "search", sx + 14, y + 12, 20, T.muted, alpha)
    gfx.text(canvas, QUERIES[tab], sx + 46, y + 29, 20, T.text, 400, 0.0, alpha)


FOOTER = ("Terms", "Privacy", "Security", "Status", "Docs", "Contact", "Manage cookies", "Do not share my personal information")


def page_footer(canvas, x, y, w, alpha, tip="Find everything you created by searching is:pr author:@me."):
    """Under a list: the "ProTip!" line, and the site footer along the window's bottom edge:
    the small mark, the copyright and the footer links. `y` is the ProTip baseline."""
    tx = gfx.text(canvas, "ProTip!", x + 20, y, 19, T.muted, 600, 0.0, alpha) + 6
    gfx.text(canvas, tip, x + 20 + tx, y, 19, T.muted, 400, 0.0, alpha)
    fy = y + 160
    win.rule(canvas, T, x, fy - 40, x + w, alpha)
    logos.github(canvas, x, fy - 18, 24, T.muted, alpha)
    gfx.text(canvas, f"© {datetime.date.today().year} GitHub, Inc.", x + 36, fy, 18, T.muted, 400, 0.0, alpha)
    lx, ly = x + 320, fy
    for s in FOOTER:                               # the links wrap to a second row when the page is narrow, as GitHub's do
        lw = gfx.text_width(s, 18)
        if lx + lw > x + w:
            lx, ly = x + 320, ly + 30
        lx += gfx.text(canvas, s, lx, ly, 18, T.link, 400, 0.0, alpha) + 34


def list_header(canvas, x, y, w, alpha, open_n, closed_n):
    """The list box's muted header: "N Open", "N Closed" and the filter menus. 64 px tall."""
    canvas.save()
    canvas.clipRRect(gfx.rrect(x, y, w, 400, R), True)
    canvas.drawRect(skia.Rect.MakeXYWH(x, y, w, 64), gfx.fill_paint(T.panel, alpha))
    canvas.restore()
    win.rule(canvas, T, x + 1, y + 64, x + w - 1, alpha)
    octicon(canvas, "git-pull-request", x + 24, y + 21, 22, T.text, alpha)
    tx = x + 58
    tx += gfx.text(canvas, f"{open_n} Open", tx, y + 40, 20, T.text, 600, 0.0, alpha) + 28
    octicon(canvas, "check", tx, y + 21, 22, T.muted, alpha)
    gfx.text(canvas, f"{closed_n} Closed", tx + 32, y + 40, 20, T.muted, 400, 0.0, alpha)
    rx = x + w - 24
    for s in ("Sort", "Organization", "Visibility"):
        rx -= 18
        octicon(canvas, "triangle-down", rx, y + 23, 18, T.muted, alpha)
        rx -= gfx.text_width(s, 20, 400) + 4
        gfx.text(canvas, s, rx, y + 40, 20, T.muted, 400, 0.0, alpha)
        rx -= 32


def pr_row(canvas, x, y, w, alpha, row, label_alpha=0.0, rule=False):
    """One pull request in the list (lib/github_content.PullRow): the draft or open octicon, the
    repository (muted) and the title, the label when it has one, and the meta line. Returns the
    title's rect (x, y, w, h). ROW_H tall."""
    if rule:
        win.rule(canvas, T, x + 1, y, x + w - 1, alpha)
    if row.draft:
        octicon(canvas, "git-pull-request-draft", x + 24, y + 32, 22, T.muted, alpha)
    else:
        octicon(canvas, "git-pull-request", x + 24, y + 32, 22, T.green, alpha)
    tx = x + 64
    tx += gfx.text(canvas, row.repo, tx, y + 50, 21, T.muted, 400, 0.0, alpha) + 12
    tw = gfx.text(canvas, row.title, tx, y + 50, 23, T.text, 600, 0.0, alpha)
    if row.label:
        win.badge(canvas, row.label, tx + tw + 14, y + 42, T.border, alpha * label_alpha, size=17, fill=False, text_color=T.text)
    mx = x + 64
    mx += gfx.text(canvas, f"#{row.number} opened {row.opened} by", mx, y + 92, 20, T.muted, 400, 0.0, alpha) + 7
    mx += gfx.text(canvas, row.author, mx, y + 92, 20, T.muted, 400, 0.0, alpha) + 10
    if row.draft:
        gfx.text(canvas, "• Draft", mx, y + 92, 20, T.muted, 400, 0.0, alpha)
    return row_title_rect(x, y, row)


def row_title_rect(x, y, row):
    """The title's rect (x, y, w, h) in the pull request row at (x, y), whether drawn or not."""
    return (x + 64 + gfx.text_width(row.repo, 21) + 12, y + 28, gfx.text_width(row.title, 23, 600), 30)


# ---------------------------------------------------------------- the pull request page


def pr_title(canvas, x, y, alpha, title, number, commits, branch, base, author, draft=True):
    """The pull request's title with its number, then the Draft (or Open) state label and the
    "<author> wants to merge N commits into <base> from <branch>" sentence with the branch
    chips. Returns the y below."""
    tw = gfx.text(canvas, title, x, y + 58, 34, T.text, 400, 0.0, alpha)
    gfx.text(canvas, f"#{number}", x + tw + 14, y + 58, 34, T.muted, 400, 0.0, alpha)
    bx = x + win.gh_state(canvas, x, y + 104, alpha, draft) + 16
    bx += gfx.text(canvas, author, bx, y + 111, 20, T.text, 600, 0.0, alpha) + 8
    bx += gfx.text(canvas, f"wants to merge {commits} commit{'s' if commits != 1 else ''} into", bx, y + 111, 20, T.muted, 400, 0.0, alpha) + 10
    bx += win.gh_ref(canvas, base, bx, y + 104, alpha) + 10
    bx += gfx.text(canvas, "from", bx, y + 111, 20, T.muted, 400, 0.0, alpha) + 10
    win.gh_ref(canvas, branch, bx, y + 104, alpha)
    return y + 136


PR_TABS = [("Conversation", "comment-discussion"), ("Commits", "git-commit"), ("Checks", "checklist"), ("Files changed", "file-diff")]


def pr_tabs(canvas, x, y, w, alpha, counts, active, plus, minus):
    """The pull request's tab row with octicons and counters, the diffstat (`plus`, `minus`)
    at the right, and the rule under it. `y` is the row's top; 56 px tall."""
    tx = x
    for label, icon in PR_TABS:
        on = label == active
        lw = gfx.text_width(label, 20, 600 if on else 400)
        octicon(canvas, icon, tx + 12, y + 16, 20, T.muted, alpha)
        gfx.text(canvas, label, tx + 42, y + 34, 20, T.text if on else T.muted, 600 if on else 400, 0.0, alpha)
        cw = counter(canvas, counts[label], tx + 42 + lw + 8, y + 27, alpha) + 8 if counts.get(label) else 0
        iw = 12 + 30 + lw + cw + 12
        if on:
            canvas.drawRRect(gfx.rrect(tx, y + 53, iw, 3, 1.5), gfx.fill_paint(win.GH_TAB, alpha))
        tx += iw + 8
    rx = x + w
    for i in range(5):                        # the five diffstat blocks: four added, one removed
        rx -= 16
        canvas.drawRRect(gfx.rrect(rx, y + 24, 12, 12, 2), gfx.fill_paint(T.green if i else T.red, alpha))
    rx -= 10 + ui.mono_width(minus, 19)
    ui.mono_text(canvas, minus, rx, y + 34, 19, T.red, alpha)
    rx -= 10 + ui.mono_width(plus, 19)
    ui.mono_text(canvas, plus, rx, y + 34, 19, T.green, alpha)
    win.rule(canvas, T, x - 72, y + 56, x + w + 72, alpha)
    return y + 56


def comment_box(canvas, x, y, w, h, alpha, when, user, app):
    """A timeline comment: the author's avatar in the left column, then the bordered box with
    its muted header ("<login> commented <when>") and the caret pointing at the avatar. `user`
    is a win.Person; None is the app `app` (its login), with the app's avatar. Returns the
    body's (x, y)."""
    if alpha <= 0.002:
        return x + 72 + 24, y + 52
    if user:
        ui.avatar(canvas, x + 28, y + 28, 28, user.initials, user.color, alpha, size=22)
    else:
        win.app_avatar(canvas, x + 28, y + 28, 56, app, alpha)
    bx, bw = x + 72, w - 72
    win.box(canvas, T, bx, y, bw, h, alpha)
    canvas.save()
    canvas.clipRRect(gfx.rrect(bx, y, bw, h, R), True)
    canvas.drawRect(skia.Rect.MakeXYWH(bx, y, bw, 52), gfx.fill_paint(T.panel, alpha))
    canvas.restore()
    win.rule(canvas, T, bx + 1, y + 52, bx + bw - 1, alpha)
    caret = skia.Path()
    caret.moveTo(bx, y + 18)
    caret.lineTo(bx - 10, y + 27)
    caret.lineTo(bx, y + 36)
    caret.close()
    canvas.drawPath(caret, gfx.fill_paint(T.panel, alpha))
    canvas.drawLine(bx, y + 18, bx - 10, y + 27, gfx.stroke_paint(T.border, 1.0, alpha, cap="butt"))
    canvas.drawLine(bx - 10, y + 27, bx, y + 36, gfx.stroke_paint(T.border, 1.0, alpha, cap="butt"))
    nx = bx + 24
    nx += gfx.text(canvas, user.name if user else app, nx, y + 33, 20, T.text, 600, 0.0, alpha) + 8
    gfx.text(canvas, f"commented {when}", nx, y + 33, 20, T.muted, 400, 0.0, alpha)
    return bx + 24, y + 52


def commit_row(canvas, x, y, w, alpha, message, app, check_alpha=0.0, line=True):
    """A commit in the timeline: the vertical line through the left column, the commit octicon
    on it, the app's small avatar, the message and the check status at the right. 48 px tall."""
    if alpha <= 0.002:
        return
    if line:
        gfx.hairline(canvas, x + 28, y - 16, x + 28, y + 64, alpha, T.border, width=2)
    canvas.drawRect(skia.Rect.MakeXYWH(x + 14, y + 10, 28, 28), gfx.fill_paint(T.bg, alpha))
    octicon(canvas, "git-commit", x + 17, y + 13, 22, T.muted, alpha)
    win.app_avatar(canvas, x + 84, y + 24, 24, app, alpha)
    gfx.text(canvas, message, x + 108, y + 32, 20, T.text, 400, 0.0, alpha)
    octicon(canvas, "check-circle-fill", x + w - 42, y + 14, 20, T.green, alpha * check_alpha)


def merge_box(canvas, x, y, w, alpha, checks, draft=True):
    """The merge box: the checks row ("All checks have passed", `checks` successful; left out
    when `checks` is 0), then for a `draft` "still a work in progress" with the "Ready for
    review" button, otherwise "no conflicts" with the green "Merge pull request" button. 176 px
    tall, 88 without the checks row."""
    if alpha <= 0.002:
        return
    bx, bw = x + 72, w - 72
    win.box(canvas, T, bx, y, bw, 176 if checks else 88, alpha)
    if checks:
        octicon(canvas, "check-circle-fill", bx + 24, y + 29, 30, T.green, alpha)
        gfx.text(canvas, "All checks have passed", bx + 72, y + 40, 21, T.text, 600, 0.0, alpha)
        gfx.text(canvas, f"{checks} successful check{'s' if checks != 1 else ''}", bx + 72, y + 68, 19, T.muted, 400, 0.0, alpha)
        win.rule(canvas, T, bx + 1, y + 88, bx + bw - 1, alpha)
    s = y + 88 if checks else y               # the top of the section under the checks row
    canvas.drawCircle(bx + 39, s + 44, 15, gfx.fill_paint(win.GH_DRAFT if draft else win.GH_OPEN, alpha))
    octicon(canvas, "git-pull-request-draft" if draft else "check", bx + 30, s + 35, 18, "#ffffff", alpha)
    if draft:
        gfx.text(canvas, "This pull request is still a work in progress", bx + 72, s + 40, 21, T.text, 600, 0.0, alpha)
        gfx.text(canvas, "Draft pull requests cannot be merged.", bx + 72, s + 68, 19, T.muted, 400, 0.0, alpha)
        button(canvas, "Ready for review", bx + bw - 24 - 196, s + 22, 196, 44, alpha)
    else:
        gfx.text(canvas, "This branch has no conflicts with the base branch", bx + 72, s + 40, 21, T.text, 600, 0.0, alpha)
        gfx.text(canvas, "Merging can be performed automatically.", bx + 72, s + 68, 19, T.muted, 400, 0.0, alpha)
        button(canvas, "Merge pull request", bx + bw - 24 - 236, s + 22, 236, 44, alpha, fill=win.GH_OPEN, color="#ffffff")


SIDEBAR = [("Reviewers", None), ("Assignees", "No one—assign yourself"), ("Labels", "None yet"),
           ("Projects", "None yet"), ("Milestone", "No milestone"), ("Development", "None yet")]


def sidebar(canvas, x, y, w, alpha, reviewer):
    """The right sidebar: Reviewers (with the `reviewer`, a win.Person), Assignees, Labels,
    Projects, Milestone and Development, each with its gear and a rule under it."""
    for i, (heading, value) in enumerate(SIDEBAR):
        sy = y + i * 100
        gfx.text(canvas, heading, x, sy, 19, T.muted, 600, 0.0, alpha)
        octicon(canvas, "gear", x + w - 18, sy - 16, 18, T.muted, alpha)
        if value is None:
            ui.avatar(canvas, x + 14, sy + 32, 14, reviewer.initials, reviewer.color, alpha, size=11)
            gfx.text(canvas, reviewer.name, x + 38, sy + 39, 20, T.text, 400, 0.0, alpha)
        else:
            gfx.text(canvas, value, x, sy + 39, 20, T.muted, 400, 0.0, alpha)
        win.rule(canvas, T, x, sy + 66, x + w, alpha)
