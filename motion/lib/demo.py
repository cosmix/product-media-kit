"""Demo scenes for the recreated windows (render.py --demo slack|linear|github): each window
with obviously generic sample content, animated through its states, so a project sees what the
windows draw and how a scene drives them before writing its own. The app is "Example app"; its
avatar is the project's logo (design.json `logo`) or, without one, its initial. Nothing here is
meant for a video: a project scene supplies its own content (lib/slack_content.py,
lib/linear_content.py, lib/github_content.py)."""

from typing import ClassVar

from . import github_pages, linear_ui, slack_ui
from .ease import seg, smooth
from .github_content import Comment, Commit, PullList, PullRequest, PullRow
from .linear_content import Activity, LinearContent
from .scene import Scene
from .slack_content import Channel, Message, Post, SlackContent
from .win import Person

X, Y, W, H = 60, 40, 1800, 1000          # the window: most of the 1920x1080 frame
APP = "Example app"
A = Person("Person A", "PA", "#9fd3c7")
B = Person("Person B", "PB", "#f2c6a0")
C = Person("Person C", "PC", "#a8c7f0")
PEOPLE = (B, C, A, Person("Person D", "PD", "#d8e3a8"), Person("Person E", "PE", "#f0b8c8", active=False),
          Person("Person F", "PF", "#c8d8f0", active=False))
LOGIN = Person("person-b", "PB", "#9ad0a8")    # GitHub shows people by login

SLACK = SlackContent(
    workspace="workspace",
    channels=(Channel("general", "read"), Channel("team", "selected"), Channel("releases", "unread"),
              Channel("support", "unread"), Channel("random", "read")),
    people=PEOPLE,
    viewer=Person("Person V", "PV", "#c9a7e8"),
    app=APP,
    earlier=(Message(B, "9:41 AM", "Version 2.0 is out. The dashboard looks clean so far."),
             Message(C, "9:44 AM", "Nice. I will keep an eye on the error rate this morning.", reactions=2)),
    post=Post("10:29 AM", ("Example task completed for the sample request", "with every check passing"),
              "Here are the changes for review:", ("example-repo#12", "example-lib#7")),
)

LINEAR = LinearContent(
    workspace="workspace",
    team="TEAM",
    issue="TEAM-101",
    title="Example issue title for the demo window",
    description="A sample description that shows how the issue body wraps across the column of the "
                "issue view. It carries no real content.",
    assignee=A,
    agent=APP,
    delegated="10:02",
    activities=(Activity("Entered planning mode", "10:02",
                         ("1.  First step of an example plan, long enough that", "     it continues on a second line.",
                          "2.  Second step of the plan.", "3.  Add tests for the change.")),
                Activity("Entered implementation mode", "10:05"), Activity("Reviewing", "10:24"),
                Activity("Committing", "10:28")),
)

TITLE = "feat: example change for the demo window"
PULLS = PullList(viewer=LOGIN, tab="Review requests", rows=(
    PullRow("example-org/example-repo", 12, TITLE, "example-app[bot]", label="TEAM-101"),
    PullRow("example-org/example-lib", 7, "feat: a second example change", "example-app[bot]", label="TEAM-101")))
PR = PullRequest(
    owner="example-org", repo="example-repo", number=12, title=TITLE, author="example-app[bot]",
    branch="example/TEAM-101-sample-branch", base="main", additions=120, deletions=8, files=3, commits=2, checks=2,
    open_pulls=1, viewer=LOGIN, reviewer=LOGIN,
    description=Comment(None, "just now", ("• One example finding, written as a bullet",), heading="Summary"),
    timeline=(Commit(TITLE),
              Comment(LOGIN, "just now", ("please add a test for the edge case",), mention="@example-app"),
              Commit("test: cover the edge case")),
)


class SlackDemo(Scene):
    name = "demo_slack"
    nominal = 4.0
    marks: ClassVar[list] = [(0.0, "window in"), (1.0, "post arrives"), (2.2, "links lit")]

    def draw(self, canvas, t, opaque):
        u = self.u(t)
        slack_ui.slack_window(canvas, X, Y, W, H, smooth(seg(u, 0.0, 0.6)), SLACK,
                              reveal=smooth(seg(u, 1.0, 1.7)), highlight=smooth(seg(u, 2.2, 2.8)))


class LinearDemo(Scene):
    name = "demo_linear"
    nominal = 8.0
    marks: ClassVar[list] = [(0.0, "window in"), (0.8, "delegate menu"), (1.4, "delegated"), (2.2, "in progress"),
                             (2.6, "session"), (3.0, "activities")]

    def draw(self, canvas, t, opaque):
        u = self.u(t)
        menu = smooth(seg(u, 0.8, 1.1)) * (1 - smooth(seg(u, 1.45, 1.75)))
        linear_ui.linear_window(canvas, X, Y, W, H, smooth(seg(u, 0.0, 0.6)), LINEAR, menu=menu,
                                chosen=smooth(seg(u, 1.25, 1.45)), delegated=seg(u, 1.5, 2.1),
                                status=seg(u, 2.2, 2.9), session=seg(u, 2.6, 3.1),
                                shown=sum(seg(u, b, b + 1.0) for b in (3.0, 4.4, 5.2, 6.0)))


class GithubDemo(Scene):
    name = "demo_github"
    nominal = 9.0
    marks: ClassVar[list] = [(0.0, "pull requests in"), (0.8, "second row"), (1.6, "labels"), (3.5, "pull request page"),
                             (4.6, "comment"), (5.8, "new commit"), (6.6, "checks")]

    def draw(self, canvas, t, opaque):
        u = self.u(t)
        if u < 4.1:                      # the pull request page covers the list once it is in
            github_pages.pulls_window(canvas, X, Y, W, H, smooth(seg(u, 0.0, 0.6)), PULLS,
                                      shown=1 + seg(u, 0.8, 1.3), labels=seg(u, 1.6, 2.4), scale=1.25)
        github_pages.pr_window(canvas, X, Y, W, H, smooth(seg(u, 3.5, 4.1)), PR,
                               shown=1 + seg(u, 4.6, 5.1) + seg(u, 5.8, 6.3), mention=smooth(seg(u, 5.0, 5.4)),
                               checks=smooth(seg(u, 6.6, 7.0)))


DEMOS = {"slack": SlackDemo, "linear": LinearDemo, "github": GithubDemo}
