"""What the recreated third-party windows share (lib/slack_ui.py, lib/linear_ui.py,
lib/github_ui.py; motion/reference/): each product's theme (GitHub's dark default from Primer's
tokens, Linear's dark theme, Slack's default Aubergine: aubergine frame, dark message pane), a
person as the windows show one, the window itself (a rounded rectangle with a soft shadow and a
hairline, clipped), bordered boxes, rules and rounded badges in a theme's colours, GitHub's pull
request state label (Draft or Open) and branch chip, and the app's avatar: the project's logo
(design.json `logo`, lib/logo.py) on the project's ground or, without a logo, the app's initial
on the accent colour."""

from dataclasses import dataclass

import skia

from . import design, gfx, icons, logo, ui
from .ease import cubic_out, smooth


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str          # the main ground
    inset: str       # the darker ground (GitHub's global header, Linear's sidebar, Slack's sidebar)
    panel: str       # raised surfaces, box headers
    border: str
    text: str
    muted: str
    link: str
    green: str
    yellow: str
    red: str
    accent: str      # Linear's indigo, GitHub's accent, Slack's blue
    todo: str = "#8a8f98"


GITHUB = Theme("GitHub", "#0d1117", "#010409", "#151b23", "#3d444d", "#f0f6fc", "#9198a1", "#4493f8",
               "#3fb950", "#d29922", "#f85149", "#4493f8")
LINEAR = Theme("Linear", "#0f1011", "#08090a", "#161718", "#23252a", "#e5e5e6", "#8a8f98", "#828fff",
               "#4cb782", "#f2c94c", "#eb5757", "#5e6ad2", todo="#9a9ca3")
SLACK = Theme("Slack", "#1a1d21", "#19171d", "#222529", "#35373b", "#d1d2d3", "#ababad", "#1d9bd1",
              "#2bac76", "#e8a317", "#e01e5a", "#1d9bd1")
GH_ACCENT_MUTED = "#1a3a5c"   # bgColor-accent-muted (#388bfd at 10 %) over the page ground
GH_DRAFT = "#656c76"          # bgColor-neutral-emphasis: the Draft state label
GH_OPEN = "#238636"           # bgColor-success-emphasis: the Open state label, the Merge pull request button
GH_TAB = "#f78166"            # the selected repository tab's underline
MARK = 0.68                   # the logo's share of the app avatar's tile


@dataclass(frozen=True)
class Person:
    """A person in a window: the name (GitHub shows it as the login), the initials on the
    avatar, the avatar's colour (#rrggbb) and, for Slack's presence dot, active or away."""
    name: str
    initials: str
    color: str
    active: bool = True


def rise(u, px=10):
    """A fade with a small upward push, for a row or card arriving: (alpha, dy)."""
    return smooth(u), px * (1 - cubic_out(u))


def shadow(canvas, x, y, w, h, alpha, radius=10, sigma=26, offset=16, strength=0.55):
    """A subtle, soft drop shadow under a window or card: a blurred dark rectangle offset
    downwards."""
    if alpha <= 0.002:
        return
    p = gfx.fill_paint("#000000", strength * alpha)
    p.setImageFilter(skia.ImageFilters.Blur(sigma, sigma))
    canvas.drawRRect(gfx.rrect(x, y + offset, w, h, radius), p)


def window(canvas, theme, x, y, w, h, alpha, radius=10):
    """The window's shadow, ground and hairline; clips to the window until canvas.restore()."""
    shadow(canvas, x, y, w, h, alpha, radius)
    rr = gfx.rrect(x, y, w, h, radius)
    canvas.drawRRect(rr, gfx.fill_paint(theme.bg, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(gfx.HAIR, 1.0, alpha))
    canvas.save()
    canvas.clipRRect(rr, True)


def box(canvas, theme, x, y, w, h, alpha=1.0, fill=None, radius=6):
    """A bordered box inside a window, in the theme's colours."""
    if alpha <= 0.002:
        return
    rr = gfx.rrect(x, y, w, h, radius)
    canvas.drawRRect(rr, gfx.fill_paint(fill or theme.bg, alpha))
    canvas.drawRRect(rr, gfx.stroke_paint(theme.border, 1.0, alpha))


def rule(canvas, theme, x1, y, x2, alpha=1.0):
    gfx.hairline(canvas, x1, y, x2, y, alpha, theme.border)


def badge(canvas, s, x, y, color, alpha, size=16, fill=True, text_color=None, mono=False, radius=None):
    """A rounded label: filled (state labels, chips) or outlined. Returns its width."""
    if alpha <= 0.002:
        return 0.0
    tw = ui.mono_width(s, size) if mono else gfx.text_width(s, size, 500)
    w, h = tw + 22, size + 14
    rr = gfx.rrect(x, y - h / 2, w, h, h / 2 if radius is None else radius)
    if fill:
        canvas.drawRRect(rr, gfx.fill_paint(color, alpha))
    else:
        canvas.drawRRect(rr, gfx.stroke_paint(color, 1.2, alpha))
    tc = text_color or (ui.ink(color) if fill else color)
    if mono:
        ui.mono_text(canvas, s, x + 11, y + size * 0.36, size, tc, alpha)
    else:
        gfx.text(canvas, s, x + 11, y + size * 0.36, size, tc, 500, 0.0, alpha)
    return w


def gh_state(canvas, x, y, alpha, draft=True, size=18):
    """GitHub's pull request state label with its octicon: the grey "Draft" or, when `draft` is
    False, the green "Open". Returns its width."""
    if alpha <= 0.002:
        return 0.0
    label, icon, fill = ("Draft", "git-pull-request-draft", GH_DRAFT) if draft else ("Open", "git-pull-request", GH_OPEN)
    tw = gfx.text_width(label, size, 500)
    w, h = tw + size + 34, size + 16
    canvas.drawRRect(gfx.rrect(x, y - h / 2, w, h, h / 2), gfx.fill_paint(fill, alpha))
    icons.octicon(canvas, icon, x + 12, y - size / 2 - 1, size + 2, "#ffffff", alpha)
    gfx.text(canvas, label, x + size + 22, y + size * 0.36, size, "#ffffff", 500, 0.0, alpha)
    return w


def gh_ref(canvas, s, x, y, alpha, size=18):
    """GitHub's branch chip: monospace accent text on the accent-muted ground. Returns its width."""
    return badge(canvas, s, x, y, GH_ACCENT_MUTED, alpha, size=size, text_color=GITHUB.link, mono=True, radius=6)


def app_avatar(canvas, cx, cy, size, name, alpha, radius=None):
    """The app's avatar, `size` px square and centred, round when `radius` is size / 2 (a
    rounded square by default, as apps get): the project's logo (lib/logo.py, the variant for
    the project's background) fitted inside a tile of that background or, when design.json names
    no logo, the first letter of `name` on the accent colour."""
    if alpha <= 0.002:
        return
    rr = gfx.rrect(cx - size / 2, cy - size / 2, size, size, size * 0.22 if radius is None else radius)
    if not design.load().get("logo"):
        canvas.drawRRect(rr, gfx.fill_paint(gfx.ACCENT, alpha))
        gfx.text(canvas, name[:1].upper(), cx, cy + size * 0.18, size * 0.5, ui.ink(gfx.ACCENT), 700, 0.0, alpha, align="center")
        return
    canvas.drawRRect(rr, gfx.fill_paint(gfx.BG, alpha))
    box_w = size * MARK
    _, h = logo.size(box_w)
    logo.draw(canvas, cx, cy, box_w * min(1.0, box_w / h), alpha)
