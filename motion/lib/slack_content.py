"""What Slack's window (lib/slack_ui.py) shows, as data the scene supplies: the workspace, its
channels, the people in the direct messages, the viewer, the channel's earlier messages and the
app's post. Slack's own chrome ("Threads", "Add channels", "Message #<channel>", ...) is drawn
by the window; every name and line of text here comes from the project, so nothing has a
default."""

from dataclasses import dataclass

from .win import Person

STATES = ("read", "unread", "selected")


@dataclass(frozen=True)
class Channel:
    """A sidebar channel: "read" muted, "unread" in bold, "selected" highlighted and shown."""
    name: str
    state: str

    def __post_init__(self):
        if self.state not in STATES:
            raise ValueError(f"channel #{self.name}: state {self.state!r}, expected one of {', '.join(STATES)}")


@dataclass(frozen=True)
class Message:
    """A person's earlier message in the channel: its time ("9:41 AM"), the text (wrapped to
    the pane) and the count of a thumbs-up reaction, 0 for none."""
    person: Person
    time: str
    text: str
    reactions: int = 0


@dataclass(frozen=True)
class Post:
    """The app's message: its time, the notice after the check emoji (one string per line, each
    re-wrapped when the pane is too narrow for it), the line that introduces the links, and the
    links, one bullet each (slack_window returns their rects)."""
    time: str
    notice: tuple[str, ...]
    intro: str
    links: tuple[str, ...]

    def __post_init__(self):
        if not self.notice:
            raise ValueError("Post.notice is empty: give the notice at least one line")


@dataclass(frozen=True)
class SlackContent:
    """The window's content. `channels` in sidebar order with exactly one selected, the channel
    the pane shows; `people` are the direct messages in order, and the first three make the
    channel header's facepile; `viewer` is the signed-in person (the rail's avatar); `app` is the
    posting app's name (the Apps row and the post's sender, its avatar the project's logo)."""
    workspace: str
    channels: tuple[Channel, ...]
    people: tuple[Person, ...]
    viewer: Person
    app: str
    earlier: tuple[Message, ...]
    post: Post

    def __post_init__(self):
        selected = [c.name for c in self.channels if c.state == "selected"]
        if len(selected) != 1:
            raise ValueError(f"SlackContent.channels: {len(selected)} selected channels, expected exactly one")

    @property
    def channel(self) -> str:
        """The selected channel's name."""
        return next(c.name for c in self.channels if c.state == "selected")
