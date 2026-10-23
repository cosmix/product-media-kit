# Reference: Linear's issue view, dark theme

What `lib/linear_ui.py` follows. Linear is redrawn in code from the sources below as a realistic
mock of the real app; no screenshot is pasted into a video. The strings the window draws are
Linear's own chrome (listed at the end) or the scene's `LinearContent`
(`lib/linear_content.py`).

## Sources

Official, Linear's own pages (the screenshots were downloaded from `webassets.linear.app` and
read next to the renders):

- Changelog "GitHub Copilot coding agent" (2025-10-28), three screenshots of the agent UI in the
  dark theme: the properties panel with the agent nested under the assignee, the agent session
  card in the Activity feed, and an issue list filtered by Agent:
  https://linear.app/changelog/2025-10-28-github-copilot-agent
- Docs "Agents in Linear": the "Delegate to..." menu (No agent / the agent, with a check) opening
  beside the assignee, with the Properties panel behind it:
  https://linear.app/docs/agents-in-linear
- Docs "Assigning issues": a full dark issue view (title bar, breadcrumb, title, description,
  Activity, the comment box, the Properties panel):
  https://linear.app/docs/assigning-issues
- Docs "Conceptual model": the whole app in the dark theme with the navigation sidebar
  (workspace row, Inbox, My issues, Workspace and Your teams sections, the team's Issues
  selected): https://linear.app/docs/conceptual-model
- Docs "Comment on issues": the Activity feed with event rows, a resolved thread card and the
  comment box: https://linear.app/docs/comment-on-issues
- Developers "Agent interaction": activity types (thought, action, elicitation, response, error),
  session states: https://linear.app/developers/agent-interaction
- Linear's site CSS (`static.linear.app/web/_next/static/css/*.css`), which carries the app's
  colour and type variables: the values below.
- Brand: Inter is Linear's typeface; Mercury White `#F4F5F8` for the monochrome mark:
  https://linear.app/brand

## Layout (measured on the screenshots; logical px are the app's, the window uses 1.5x)

- A tab bar across the whole window (about 36 px): back, forward, history at the left of the
  pane; centred, the issue's status ring and "<id> <title>" in secondary text; "+" at the right.
- The navigation sidebar (about 220 px, the darkest ground): the workspace icon and name with a
  caret, search and compose at the right; Inbox, My issues; a "Workspace" section (Initiatives,
  Projects, Views, More); "Your teams" with the team's tile and name, then Triage, Issues (the
  selected row on a lighter ground), Cycles, Projects, Views. Icons are thin line icons.
- The breadcrumb row (about 40 px): the team's tile and name, "›", the issue id, more, a star;
  a hairline under it across the pane.
- The issue: the title (about 24 px, semibold) with a 42 px left margin, the description at
  15 px in secondary text, the reaction and attachment buttons, "+ Add sub-issues", a hairline,
  then "Activity" (semibold) with "Unsubscribe" and the subscribers' avatars at the right. Event
  rows read "<name> <did something> · <time>" with a small avatar; the comment box
  ("Leave a comment...") sits at the foot of the feed.
- The agent session card: a raised card with a hairline border; its header is the agent's round
  avatar, its name in semibold and the session state in tertiary text ("agent connected" in the
  Copilot screenshot), with an Activity button and more at the right; a hairline under the
  header; rows below with the avatar, the text and the time at the right. Thoughts render as
  secondary text behind a thin rule; actions as "<verb> ..." lines.
- The properties panel (about 300 px) with "Properties" and the link, copy-id and branch
  actions: no row labels, only icon + value: the status ring and name, "Set priority" with the
  dashes when none, the assignee's avatar and name, the delegated agent nested under the
  assignee behind a thin elbow connector, "Set estimate" with the triangle; then "Labels" with a
  "+" and "Project" with "Add to project".
- Status rings: Todo a thin grey ring, In Progress a yellow ring with a partial pie, Done a
  filled indigo circle with a check.

## Colours and type (Linear's CSS variables, dark theme)

| Variable | Value | Used for |
| --- | --- | --- |
| `--color-bg-level-0` | `#08090a` | the sidebar and tab bar |
| `--color-bg-level-1` | `#0f1011` | the pane and panel ground |
| `--color-bg-level-2` / `-3` | `#141516` / `#191a1b` | raised surfaces: the comment box, menus |
| (sampled) | `#17191a` | the agent session card |
| `--color-border-primary` / `-secondary` | `#23252a` / `#34343a` | hairlines; menu and avatar borders |
| `--color-text-primary` | `#f7f8f8` | titles, values, names |
| `--color-text-secondary` | `#d0d6e0` | the description, event names, thoughts |
| `--color-text-tertiary` | `#8a8f98` | section headers, placeholders, times |
| `--color-text-quaternary` | `#62666d` | the breadcrumb separator, the comment placeholder |
| `--color-indigo` / `--color-link-primary` | `#5e6ad2` / `#828fff` | the team tile; links |
| `--color-yellow` | `#f0bf00` (the In Progress ring reads `#f2c94c` in screenshots; kept) | In Progress |
| `--font-regular` | Inter Variable | all text |
| `--font-weight-medium` / `-semibold` | 510 / 590 | medium and semibold (drawn at 400 and 600) |
| `--font-size-regular` / `-small` / `-title2` | 15 / 13 / 24 px | body / UI / the issue title |

The window scales the app by 1.5 for an 1800x1000 window in the 1920x1080 frame: body text
23 px, UI 20 px, the title 32 px (36 would overrun the column), sidebar items 20 px.

## UI labels used (Linear's own words)

"Inbox", "My issues", "Workspace", "Initiatives", "Projects", "Views", "More", "Your teams",
"Triage", "Issues", "Cycles", "Properties", "Todo", "In Progress", "Set priority",
"Set estimate", "Labels", "Project", "Add to project", "Add sub-issues", "Activity",
"Unsubscribe", "Leave a comment...", "Delegate to...", "No agent", "agent connected" (the
session state shown in Linear's Copilot screenshot), "delegated to".

## Logo

The Linear logomark (`lib/logos.py`, Mercury White, unaltered) is the workspace icon atop the
sidebar, where the client shows the workspace's icon. The agent's avatar is the project's logo on
a round tile (`win.app_avatar`).
