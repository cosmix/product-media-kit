"""The checks tests/test_motion_windows_draw.py runs inside motion's own environment (skia, numpy:
`uv run --project motion python tests/motion_window_checks.py <check>`), on a CPU raster surface so no
GPU is needed. Exit 0 and the line "ok" mean the check passed; anything else is a failure."""

import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(KIT), str(KIT / "motion")]

import numpy as np
import skia
from lib import demo, github_pages, github_ui, linear_ui, slack_ui
from lib.github_content import Comment, PullList, PullRequest, PullRow
from lib.linear_content import Activity, LinearContent
from lib.slack_content import Channel, Post, SlackContent

X, Y, W, H = demo.X, demo.Y, demo.W, demo.H
CLEAR = (255, 0, 255, 255)


def surface():
    s = skia.Surface.MakeRasterN32Premul(1920, 1080)
    s.getCanvas().clear(skia.Color4f(1, 0, 1, 1))
    return s


def pixels(s):
    return s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


def painted(s):
    """True when the surface holds anything but the clear colour."""
    return bool((pixels(s) != np.array(CLEAR, dtype=np.uint8)).any())


def raises(exc, fn):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"{fn} did not raise {exc.__name__}")


def errors():
    raises(ValueError, lambda: Channel("a", "bogus"))
    raises(ValueError, lambda: Post("9:00", (), "intro", ()))
    ch = (Channel("a", "selected"), Channel("b", "selected"))
    raises(ValueError, lambda: SlackContent("w", ch, (), demo.A, "app", (), demo.SLACK.post))
    raises(ValueError, lambda: SlackContent("w", (Channel("a", "read"),), (), demo.A, "app", (), demo.SLACK.post))
    raises(ValueError, lambda: PullList(demo.LOGIN, "Nobody", ()))


def imports():
    assert set(demo.DEMOS) == {"slack", "linear", "github"}
    for cls in demo.DEMOS.values():
        assert cls().name.startswith("demo_")


def demos():
    for key, cls in demo.DEMOS.items():
        scene = cls()
        for t in (0.0, 0.5, 1.2, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, scene.duration):
            s = surface()
            scene.draw(s.getCanvas(), t, True)
        assert painted(s), f"demo {key} drew nothing at its end"


def empty_slack():
    content = SlackContent("w", (Channel("a", "selected"),), (), demo.A, "App", (),
                           Post("9:00", ("done",), "intro", ()))
    for reveal in (0.0, 0.5, 1.0):
        s = surface()
        slack_ui.slack_window(s.getCanvas(), X, Y, W, H, 1.0, content, reveal)
        assert painted(s)


def empty_linear():
    content = LinearContent("w", "T", "T-1", "", "", demo.A, "App", "10:00", ())
    s = surface()
    linear_ui.linear_window(s.getCanvas(), X, Y, W, H, 1.0, content, delegated=1.0, session=1.0, shown=0.0)
    assert painted(s)
    long_name = LinearContent("a very long workspace name that must not reach the search glyph" * 2, "T", "T-1", "x", "x",
                              demo.A, "App", "10:00", ())
    linear_ui.linear_window(surface().getCanvas(), X, Y, W, H, 1.0, long_name)


def empty_github():
    pulls = PullList(demo.LOGIN, "Created", ())
    s = surface()
    assert github_pages.pulls_window(s.getCanvas(), X, Y, W, H, 1.0, pulls, scale=1.25) == []
    assert painted(s)
    bare = PullRequest(owner="o", repo="r", number=1, title="", author="app[bot]", branch="b", base="main", additions=0,
                       deletions=0, files=0, commits=0, checks=0, open_pulls=0, viewer=demo.LOGIN, reviewer=demo.LOGIN,
                       description=Comment(None, "just now", ()), timeline=(), draft=False)
    for pr in (bare, demo.PR, PullRequest(**{**vars(demo.PR), "draft": False, "checks": 0})):
        s = surface()
        github_pages.pr_window(s.getCanvas(), X, Y, W, H, 1.0, pr)
        assert painted(s)
    row = PullRow("o/r", 3, "title", "app[bot]", opened="3 days ago", draft=False)
    github_pages.pulls_window(surface().getCanvas(), X, Y, W, H, 1.0, PullList(demo.LOGIN, "Created", (row,)))


def same(a, b):
    return np.allclose(np.array(a, dtype=float), np.array(b, dtype=float))


def anchors():
    for reveal in (0.0, 1.0):
        hidden = slack_ui.slack_window(surface().getCanvas(), X, Y, W, H, 0.0, demo.SLACK, reveal)
        shown = slack_ui.slack_window(surface().getCanvas(), X, Y, W, H, 1.0, demo.SLACK, reveal)
        if reveal == 1.0:
            assert same(hidden["message"], shown["message"]) and same(hidden["avatar"], shown["avatar"])
            assert same(hidden["links"], shown["links"]) and len(shown["links"]) == len(demo.SLACK.post.links)
    for scale in (1.0, 1.25):
        hidden = github_pages.pulls_window(surface().getCanvas(), X, Y, W, H, 0.0, demo.PULLS, scale=scale)
        shown = github_pages.pulls_window(surface().getCanvas(), X, Y, W, H, 1.0, demo.PULLS, scale=scale)
        assert same(hidden, shown) and len(shown) == len(demo.PULLS.rows)


def linear_title():
    """A title longer than the column wraps and pushes the feed down by whole lines."""
    short = demo.LINEAR
    long = LinearContent(**{**vars(short), "title": "word " * 30})
    tops = [linear_ui.issue_body(surface().getCanvas(), 100, 100, 900, 1.0, c) for c in (short, long)]
    extra = tops[1] - tops[0]
    assert extra > 0 and extra % linear_ui.TITLE_LH == 0, extra


def linear_feed():
    """Activities past the comment box are not drawn: the gap above the box is the window ground."""
    acts = tuple(Activity(f"Step {i}", "10:00", ("a thought", "on two lines")) for i in range(30))
    content = LinearContent(**{**vars(demo.LINEAR), "activities": acts})
    frames = []
    for session in (0.0, 1.0):
        s = surface()
        linear_ui.linear_window(s.getCanvas(), X, Y, W, H, 1.0, content, delegated=1.0, session=session, shown=30.0)
        frames.append(pixels(s)[:, 460:1100, :3].astype(int))
    diff = np.abs(frames[1] - frames[0]).sum(axis=2).sum(axis=1)       # per row: how much the card changes
    comment_top = Y + H - 88
    assert diff[Y + 500:comment_top - 16].sum() > 0, "the session card was not drawn"
    assert diff[comment_top - 15:comment_top].sum() == 0, "the feed runs into the comment box"


def merge_box():
    probe = (84 + 72 + 815, 120)    # right of the draft box's button, inside its second section
    boxes = []
    for checks in (0, 3):
        s = surface()
        github_ui.merge_box(s.getCanvas(), 84, 0, 900, 1.0, checks)
        boxes.append(tuple(pixels(s)[probe[1], probe[0]]))
    assert boxes[0] == CLEAR, "checks=0 still draws the checks row's space"
    assert boxes[1] != CLEAR


if __name__ == "__main__":
    globals()[sys.argv[1]]()
    print("ok")
