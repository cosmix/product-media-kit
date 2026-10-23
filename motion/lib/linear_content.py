"""What Linear's issue window (lib/linear_ui.py) shows, as data the scene supplies: the workspace
and team, the issue, its assignee, the agent it is delegated to and the agent's activities.
Linear's own chrome ("Inbox", "Properties", "Delegate to...", "agent connected", ...) is drawn
by the window; every name and line of text here comes from the project, so nothing has a
default."""

from dataclasses import dataclass

from .win import Person


@dataclass(frozen=True)
class Activity:
    """One agent activity in the session card: the action ("Entered planning mode"), its time
    ("10:02") and, optionally, an agent thought under it, one string per line (kept as given, so
    a numbered plan can hang its continuation lines)."""
    label: str
    time: str
    thought: tuple[str, ...] = ()


@dataclass(frozen=True)
class LinearContent:
    """The window's content. `team` is the team's name or key (the sidebar's team, the
    breadcrumb); `issue` the issue's id; `description` is wrapped to the column; `agent` is the
    agent's name, its avatar the project's logo; `delegated` the time of the delegation event."""
    workspace: str
    team: str
    issue: str
    title: str
    description: str
    assignee: Person
    agent: str
    delegated: str
    activities: tuple[Activity, ...]
