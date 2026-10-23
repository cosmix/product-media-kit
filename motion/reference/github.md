# Reference: GitHub's web UI, dark default theme

What `lib/github_ui.py` and `lib/github_pages.py` follow: the pull requests list
(github.com/pulls) and a pull request's page, realistic and using most of the frame. Everything
is drawn in code from the sources below; no screenshot is pasted into a video. The names and
text come from the scene's `lib/github_content.py`; GitHub's own labels are listed at the end.

## Sources

Official:

- Primer design tokens, dark theme CSS (every colour below is read from this file):
  https://cdn.jsdelivr.net/npm/@primer/primitives/dist/css/functional/themes/dark.css
- Octicons (MIT), path data used as-is at 16 px, scaled (`lib/icons.py`): `three-bars`,
  `search`, `plus`, `triangle-down`, `inbox`, `issue-opened`, `code`, `play`, `table`, `shield`,
  `graph`, `comment-discussion`, `checklist`, `file-diff`, `check`, `gear`, `git-pull-request`,
  `git-pull-request-draft`, `git-commit` and `check-circle-fill` from
  https://raw.githubusercontent.com/primer/octicons/main/icons/<name>-16.svg (`play-16` from the
  npm build, https://unpkg.com/@primer/octicons@19.15.0/build/svg/play-16.svg); the GitHub mark
  is in `lib/logos.py`.
- The global navigation (menu button, mark, context crumbs at the left; search, create, Issues,
  Pull requests, Inbox and the avatar at the right):
  https://github.blog/changelog/2023-06-14-new-global-navigation-is-now-in-public-beta/ (the page is
  no longer served; the layout was confirmed by observation)
- The pull request page's tabs ("Conversation", "Commits", "Checks", "Files changed") and the
  merge box:
  https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests
- The refreshed repository pull requests list (collapsible filter sidebar, compact mode, status
  check counts; GA 2026-09-21) and the global pull requests dashboard (github.com/pulls, on by
  default since 2026-04-23, with an Inbox view and a list view):
  https://github.blog/changelog/2026-09-21-refreshed-repository-pull-requests-page-generally-available
  https://github.blog/changelog/2026-04-23-global-pull-requests-dashboard-moves-to-opt-out-public-preview
  Neither page describes the row layout; the list view's structure below is observed.

Observed on github.com (dark default, 2025-2026), unverified by a document: the header's
measurements, the list row and the pull request page's layout.

## Tokens used (dark)

| Role | Token | Value |
| --- | --- | --- |
| page ground | bgColor-default | `#0d1117` |
| box headers, comment headers | bgColor-muted | `#151b23` |
| global header | bgColor-inset | `#010409` |
| buttons, inputs | control-bgColor-rest | `#212830` |
| borders | borderColor-default | `#3d444d` |
| text | fgColor-default | `#f0f6fc` |
| secondary text | fgColor-muted | `#9198a1` |
| links, branch chips | fgColor-accent | `#4493f8` on bgColor-accent-muted `#388bfd1a` |
| selected subnav item | bgColor-accent-emphasis | `#1f6feb`, white text |
| counters | bgColor-neutral-muted | `#656c7633` (drawn flat as `#262c36`) |
| passed checks, added lines | fgColor-success | `#3fb950` |
| removed lines | fgColor-danger | `#f85149` |
| Draft state label | bgColor-neutral-emphasis | `#656c76`, white text |
| active tab underline | underlineNav-borderColor-active | `#f78166` |

## Layout, as drawn (1920x1080; about 1.4x GitHub's 14 px base)

The pages are laid out for an 1800x1000 window at (60, 40). Body text is 20 px and up (GitHub's
14 px), titles 23 px in the list and 34 px on the pull request page (GitHub's 32 px at weight
400). The project's sans stands in for GitHub's system sans; its mono for the monospace in the
branch chips and the diffstat.

Global header, 80 px, inset ground, 1 px border under it: menu button (44 px bordered square,
`three-bars`), the GitHub mark (44 px, in the text colour, unaltered), the context crumbs at 22 px
("owner / repo" with the repository in bold; "Pull requests" on the global page); at the right the
search box (440x44, "Type / to search", a "/" key cap), the create button ("+" with a caret), a
divider, the Issues, Pull requests and Inbox icon buttons, the viewer's avatar (44 px).

Repository tabs, 64 px: Code, Issues, Pull requests, Actions, Projects, Security, Insights, each
with its octicon (muted) and label (text colour, semibold when active); counters as round pills;
the active tab underlined in orange, a 1 px border under the row.

The pull requests list (github.com/pulls, list view): the segmented subnav "Created | Assigned |
Mentioned | Review requests" (the selected item filled accent-emphasis), the search input
holding the view's query (`is:open is:pr review-requested:@me archived:false` for Review
requests; `author:@me`, `assignee:@me`, `mentions:@me` for the others); the list box (1 px
border, 6 px radius) with its muted header ("N Open", "N Closed", the Visibility / Organization /
Sort menus) and one 128 px row per pull request: the draft octicon (muted), the repository in
muted text, the title in semibold, the label pill, then the meta line "#N opened just now by
<author> • Draft". Under the list the "ProTip!" line and the site footer (the small mark,
"© 2026 GitHub, Inc.", Terms ... Do not share my personal information) along the bottom edge,
where the real page shows them. The list can be drawn at 1.25x inside the window (laid out at
1440x800) so a few rows have presence: title 29 px, meta 25 px on screen.

The pull request page: title with the number in muted text; the Draft state label (grey pill,
draft octicon) and "<author> wants to merge N commits into <base> from <branch>" with the
branches as monospace chips on the accent-muted ground; the tab row (Conversation, Commits,
Checks, Files changed with octicons and counters) and the diffstat "+N −N" with five blocks at
the right; a rule. Below, the timeline and the 300 px sidebar: the author's avatar in a 56 px
column at the left of each comment box (an app: its logo on a rounded square, as apps get square
avatars; a person: a round avatar), the box with a muted header "<login> commented <when>" and a
caret toward the avatar; commit rows on the timeline's 2 px line (commit octicon, small avatar,
message, the check at the right); the draft merge box: "All checks have passed / N successful
checks", then "This pull request is still a work in progress / Draft pull requests cannot be
merged." with the "Ready for review" button. Sidebar sections with a gear each: Reviewers (the
reviewer), Assignees ("No one—assign yourself"), Labels ("None yet"), Projects ("None yet"),
Milestone ("No milestone"), Development ("None yet").

## UI labels used (GitHub's own words)

"Pull requests", "Type / to search", "Code", "Issues", "Actions", "Projects", "Security",
"Insights", "Created", "Assigned", "Mentioned", "Review requests", the four views' queries,
"Open", "Closed", "Visibility", "Organization", "Sort", "opened", "by", "Draft", "ProTip!",
"Find everything you created by searching is:pr author:@me.", "© 2026 GitHub, Inc.", "Terms",
"Privacy", "Security", "Status", "Docs", "Contact", "Manage cookies", "Do not share my personal
information", "wants to merge N commits into", "from", "Conversation", "Commits", "Checks",
"Files changed", "commented", "All checks have passed", "successful checks", "This pull request
is still a work in progress", "Draft pull requests cannot be merged.", "Ready for review",
"Reviewers", "Assignees", "No one—assign yourself", "Labels", "None yet", "Projects",
"Milestone", "No milestone", "Development". The list rows leave out the diffstat, which the real
list does not show; the numbers stay on the pull request page's tab row.
