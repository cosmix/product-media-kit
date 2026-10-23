"""What GitHub's pages (lib/github_pages.py) show, as data the scene supplies: the pull requests
list (github.com/pulls) and one pull request's page with its timeline. GitHub's own chrome
("Conversation", "Ready for review", "ProTip!", ...) is drawn by the pages; every name and line
of text here comes from the project. `author` is the app's login ("<name>[bot]"); its avatar is
the project's logo."""

from dataclasses import dataclass

from .github_ui import SUBNAV
from .win import Person


@dataclass(frozen=True)
class PullRow:
    """One pull request in the list: the repository ("owner/repo", muted before the title), its
    number, the title, the author's login, an optional label pill ("" for none), when it was
    `opened` ("just now", "3 days ago") and whether it is a `draft` (the draft octicon and the
    "• Draft" tag; False shows the open pull request octicon in green)."""
    repo: str
    number: int
    title: str
    author: str
    label: str = ""
    opened: str = "just now"
    draft: bool = True


@dataclass(frozen=True)
class PullList:
    """github.com/pulls: the signed-in `viewer`, the subnav view `tab` (one of SUBNAV; it fills
    in the search query), the rows, and the count of closed pull requests in the list header."""
    viewer: Person
    tab: str
    rows: tuple[PullRow, ...]
    closed: int = 0

    def __post_init__(self):
        if self.tab not in SUBNAV:
            raise ValueError(f"PullList.tab {self.tab!r}: expected one of {', '.join(SUBNAV)}")


@dataclass(frozen=True)
class Comment:
    """A timeline comment: the author (a win.Person; None for the pull request's author, the
    app), when ("just now"), an optional bold heading, and the body, one string per line at
    20 px (write "• " for a bullet). `mention` ("@name", "" for none) opens the first line in
    the link colour and is highlighted with pr_window's `mention`."""
    author: Person | None
    when: str
    lines: tuple[str, ...]
    heading: str = ""
    mention: str = ""


@dataclass(frozen=True)
class Commit:
    """A commit in the timeline, by the app: its message."""
    message: str


@dataclass(frozen=True)
class PullRequest:
    """One pull request's page, a draft by default. The header shows `owner` / `repo` and the
    `viewer`'s avatar, the repository tabs `open_pulls` as the Pull requests counter; the title
    row `number`, `commits` (the Commits counter and "wants to merge N commits") from `branch`
    into `base`; the tab row `checks` and `files` as counters and +`additions` −`deletions`;
    `description` opens the timeline, the `timeline` entries follow it (Comment or Commit); the
    sidebar lists the `reviewer`. `draft` False shows the green Open label and a merge box that
    offers "Merge pull request". `checks` 0 leaves the checks row out of the merge box."""
    owner: str
    repo: str
    number: int
    title: str
    author: str
    branch: str
    base: str
    additions: int
    deletions: int
    files: int
    commits: int
    checks: int
    open_pulls: int
    viewer: Person
    reviewer: Person
    description: Comment
    timeline: tuple[Comment | Commit, ...]
    draft: bool = True
