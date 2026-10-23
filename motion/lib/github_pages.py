"""GitHub's two pages as whole windows, laid out from the pieces in lib/github_ui.py
(motion/reference/github.md): `pulls_window`, github.com/pulls with its rows, and `pr_window`,
a pull request's page with its timeline. The content is lib/github_content.py's; the
states (rows and entries arriving, a label or mention lighting up) are the scene's to time."""

from . import gfx, win
from . import github_ui as G
from .ease import clamp01, smooth, stagger
from .github_content import Commit

T = win.GITHUB
GAP, COMMIT_H = 16, 48       # between timeline entries; a commit row's height
SIDE_W = 300                 # the pull request page's sidebar, 56 px right of the timeline


def map_rect(r, x, y, s):
    """A rect drawn at scale `s` about (x, y), in canvas space."""
    return (x + (r[0] - x) * s, y + (r[1] - y) * s, r[2] * s, r[3] * s)


def pulls_window(canvas, x, y, w, h, alpha, page, *, shown=None, labels=1.0, scale=1.0):
    """github.com/pulls (lib/github_content.PullList) in (x, y, w, h): the global header, the
    subnav and query of page.tab, the list box with the rows, the ProTip! and the footer. The
    window is drawn at the rect's size and the page inside it at `scale` (1.25 gives an
    1800x1000 window the presence of a 1440x800 page). shown counts the rows in (default all; a
    fraction fades the next one in); labels 0..1 fades the rows' labels in, one after another.
    Returns the titles' rects in canvas space, one per row, also while the window is hidden."""
    n = len(page.rows)
    shown = n if shown is None else shown
    pw, ph = w / scale, h / scale
    px, pcw = x + 96, pw - 192            # the page's content column
    ly = y + G.HEADER_H + 108             # the list box
    rects = [map_rect(G.row_title_rect(px, ly + 64 + i * G.ROW_H, row), x, y, scale) for i, row in enumerate(page.rows)]
    if alpha <= 0.002:
        return rects
    win.window(canvas, T, x, y, w, h, alpha)
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    canvas.translate(-x, -y)
    G.header(canvas, x, y, pw, alpha, [("Pull requests", True)], page.viewer)
    G.pulls_toolbar(canvas, px, y + G.HEADER_H + 36, pcw, alpha, page.tab)
    win.box(canvas, T, px, ly, pcw, 64 + n * G.ROW_H, alpha)
    G.list_header(canvas, px, ly, pcw, alpha, n, page.closed)
    step = 0.3 / max(1, n - 1)
    for i, row in enumerate(page.rows):
        la = smooth(stagger(labels, i, 0.0, step, 1.0 - step * (n - 1)))
        G.pr_row(canvas, px, ly + 64 + i * G.ROW_H, pcw, alpha * smooth(shown - i), row, label_alpha=la, rule=i > 0)
    G.page_footer(canvas, px, y + ph - 220, pcw, alpha)
    canvas.restore()
    return rects


def comment_height(c):
    return 52 + 34 + (34 if c.heading else 0) + 32 * max(0, len(c.lines) - 1) + 24


def entry_height(e):
    return COMMIT_H if isinstance(e, Commit) else comment_height(e)


def comment(canvas, x, y, w, alpha, c, app, mention):
    """A Comment entry: the box with its header, the bold heading, the @mention (its chip
    lit by `mention`) and the body lines."""
    bx, by = G.comment_box(canvas, x, y, w, comment_height(c), alpha, c.when, c.author, app)
    if alpha <= 0.002:
        return
    ly = by + 34
    if c.heading:
        gfx.text(canvas, c.heading, bx, ly, 21, T.text, 600, 0.0, alpha)
        ly += 34
    lx = bx
    if c.mention:
        mw = gfx.text_width(c.mention, 20, 600)
        canvas.drawRRect(gfx.rrect(bx - 6, ly - 24, mw + 12, 34, 6), gfx.fill_paint(win.GH_ACCENT_MUTED, alpha * mention))
        lx += gfx.text(canvas, c.mention, bx, ly, 20, T.link, 600, 0.0, alpha) + 8
    for i, line in enumerate(c.lines):
        gfx.text(canvas, line, lx if i == 0 else bx, ly + i * 32, 20, T.text, 400, 0.0, alpha)


def timeline(canvas, x, y, w, alpha, pr, steps, mention, checks):
    """The description, then each entry rising in with its progress in `steps`, the entries
    below and the merge box easing down to make room; the timeline's line runs through the
    avatars' column from the description to the merge box."""
    top = y + comment_height(pr.description)
    ys, ey = [], top + GAP
    for e, p in zip(pr.timeline, steps):
        ys.append(ey)
        ey += (entry_height(e) + GAP) * smooth(p)
    gfx.hairline(canvas, x + 28, top, x + 28, ey, alpha, T.border, width=2)
    comment(canvas, x, y, w, alpha, pr.description, pr.author, mention)
    last = max((i for i, e in enumerate(pr.timeline) if isinstance(e, Commit)), default=None)
    for i, (e, p, yy) in enumerate(zip(pr.timeline, steps, ys)):
        a, dy = win.rise(p)
        if isinstance(e, Commit):
            G.commit_row(canvas, x, yy + dy, w, alpha * a, e.message, pr.author, check_alpha=checks if i == last else 1.0, line=False)
        else:
            comment(canvas, x, yy + dy, w, alpha * a, e, pr.author, mention)
    G.merge_box(canvas, x, ey, w, alpha, pr.checks, pr.draft)


def pr_window(canvas, x, y, w, h, alpha, pr, *, shown=None, mention=1.0, checks=1.0):
    """A pull request's page (lib/github_content.PullRequest) in (x, y, w, h), laid out for a
    window about 1800x1000: the repository header and tabs, the title and its Draft or Open
    state, the tab row with its counters and the diffstat, the timeline (the description, then
    pr.timeline) with the merge box under it, and the sidebar. shown counts the timeline entries
    in (default all; a fraction is the next one arriving, and the Conversation counter follows
    the comments that are in);
    mention 0..1 lights the comments' @mentions; checks 0..1 fades in the latest commit's check."""
    cy = G.frame(canvas, x, y, w, h, alpha, [(pr.owner, False), (pr.repo, True)], pr.viewer, nav="Pull requests",
                 counts={"Pull requests": pr.open_pulls})
    if alpha <= 0.002:
        return
    shown = len(pr.timeline) if shown is None else shown
    steps = [clamp01(shown - i) for i in range(len(pr.timeline))]
    comments = sum(not isinstance(e, Commit) for e, p in zip(pr.timeline, steps) if p >= 0.5)
    cx, cw = x + 72, w - 144                  # the page's content column
    tw = cw - SIDE_W - 56                     # the timeline's width
    canvas.save()
    canvas.clipRRect(gfx.rrect(x, y, w, h, 10), True)
    ty = G.pr_title(canvas, cx, cy, alpha, pr.title, pr.number, pr.commits, pr.branch, pr.base, pr.author, pr.draft)
    tabs = {"Conversation": comments, "Commits": pr.commits, "Checks": pr.checks, "Files changed": pr.files}
    ty = G.pr_tabs(canvas, cx, ty + 8, cw, alpha, tabs, "Conversation", f"+{pr.additions}", f"−{pr.deletions}")
    timeline(canvas, cx, ty + 28, tw, alpha, pr, steps, mention, checks)
    G.sidebar(canvas, cx + tw + 56, ty + 60, SIDE_W, alpha, pr.reviewer)
    canvas.restore()
