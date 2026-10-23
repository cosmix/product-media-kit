# Reference: Slack's desktop client, default theme

What `lib/slack_ui.py` follows. Slack is redrawn in code from the sources below; no screenshot is
pasted into a video. The strings the window draws are Slack's own chrome (listed at the end) or
the scene's `SlackContent` (`lib/slack_content.py`).

## Sources

Official (Slack help centre, current design):

- "An overview of Slack's new design", with annotated screenshots of the current layout:
  https://slack.com/help/articles/16764236868755. Its images (zendesk attachments
  34911020115091, 44579520041491, 34910995050899, 32815380873619) show the frame, the rail, the
  sidebar, the channel header with tabs, a message with reactions, the composer.
- "Use dark mode in Slack" (a colour-mode setting, no palette published):
  https://slack.com/help/articles/360019434914
- "Dark mode comes to desktop" (2019), the one official dark-mode screenshot
  (`Dark-Mode-Transparent.png` on slackpress): the near-black rail, charcoal sidebar, blue
  selected channel, `#1a1d21` message pane.
- Message formatting (lists render as "•" lines, emoji inline, links in blue):
  https://docs.slack.dev/messaging/formatting-message-text

Third-party, treated as approximate: Design Compass's write-up of the 2023 redesign with
before/after screenshots (https://designcompass.org/en/2023/08/14/slack-redesign/); UC Riverside's
and MIT's rollout notices (January 2024) for the tab names.

## Layout (current design, measured on the help-centre screenshots)

The client is one frame with two cards inside it:

- Top bar across the whole window (about 44 px logical): back, forward, history at the left of
  the pane area; a search field centred ("Search <workspace>"), roughly 45 % of the width; help
  at the far right.
- Workspace rail at the far left (about 70 px): the workspace tile (rounded square) at the top,
  then Home, DMs, Activity, Later, More as icon + small label, the selected one on a lighter
  rounded tile; at the bottom a round "+" (new) and the viewer's avatar with the presence dot.
- Channel sidebar card (about 260 px logical) with a rounded top-left corner: the workspace name
  in bold with a caret; Threads, Drafts & sent (in the help screenshot also Unreads); the
  "Channels" section header, channel rows "# name", the selected row filled; "Add channels";
  "Direct messages" rows with a small avatar and presence dot; an "Apps" section.
- Message pane: the channel header "# name" in bold with a caret, the members' facepile with
  their count, the huddle button (headset + caret) and more at the right; under it the tabs
  Messages, Files, "+" with the active tab underlined; the message list; the composer at the
  bottom: a bordered rounded box with the formatting toolbar (B, I, S, link, lists, code) on its
  first row, the placeholder "Message #channel", and the action row (+, Aa, emoji, @, video,
  audio) with the green send button at the right.
- A message: a rounded-square avatar (36 px logical) at the left, the sender in bold followed by
  a small grey "APP" badge for apps and the time ("10:29 AM", 12-hour); the text on the lines
  below at 15 px with a 22 px line height; lists as "•" with a 20 px indent; links in blue; the
  :white_check_mark: emoji as a green rounded square with a white tick.
- A new channel shows its start above the first messages: a large "#" tile, "# name" as a title
  and "This is the very beginning of the #name channel."; the first messages of the day sit under
  a "Today" divider (a hairline with the label in a bordered pill).
- Unread channels are bold white, read ones muted; a reaction is a bordered pill with the emoji
  and its count. When a new message arrives at the foot of the list, the earlier messages move
  up by its height.

The recreation scales this by about 1.45 for a 1700x940 window in a 1920x1080 frame, so message
text is 22 px and sidebar text 19 px; chrome labels (the rail's, the badge's) stay small as in
the product. The project's sans stands in for Slack's Lato.

## Colours (the default theme, Aubergine, with the dark-mode pane)

Slack's default sidebar theme is Aubergine; its frame colour is the brand's aubergine `#4A154B`
(brand.slackhq.com names it; the help-centre screenshots of the current design sample exactly
`#4a154b` for the top bar and rail). The sidebar is the theme's deeper purple `#3F0E40`, the
first value of the Aubergine theme string
(`#3F0E40,#350D36,#1164A3,#FFFFFF,#350D36,#FFFFFF,#2BAC76,#CD2553` in the theme picker, also the
colour of the Aubergine swatch in Slack's 2019 dark-mode announcement image). The current design
highlights the selected channel in a lighter purple rather than the classic blue (Design
Compass's "after" screenshot samples `#a471a9` on the light sidebar); on the dark sidebar a
lighter purple `#703a75` stands in. Dark mode leaves the message pane neutral (`#1a1d21`, the
2019 screenshot and Slack's dark-mode theme picker, where every theme's pane is the same dark
grey), so the pane keeps the dark values below.

| Role | Value |
| --- | --- |
| frame: top bar and rail | `#4a154b` (brand aubergine) |
| search field, selected rail tile, "+" | white at 22 % / 22 % / 18 % over the frame |
| channel sidebar card | `#3f0e40` |
| sidebar and rail text, names | `#ffffff`; section headers, placeholders, unselected tabs `#cfc3d0` |
| selected sidebar item | `#703a75`, white text |
| message pane | `#1a1d21` |
| hover / raised surface, composer ground | `#222529` |
| borders, dividers | `#35373b`; composer border lighter, `#4a4d52` |
| pane text, names | `#d1d2d3` (names in bold) |
| secondary pane text (times, placeholders) | `#ababad` |
| links, channel names in text | `#1d9bd1` |
| presence green | `#2bac76`; the send button `#007a5a` |
| APP badge | `#3a3d42` ground, secondary text |

Contrast on the purple: white on `#3f0e40` 14.8:1, `#cfc3d0` on it 8.9:1, white on `#703a75`
8.1:1; all above 4.5:1 for text.

## UI labels used (Slack's own words)

"Search <workspace>" (the search placeholder with the workspace name), "Home", "DMs",
"Activity", "Later", "More", "Threads", "Drafts & sent", "Channels", "Add channels", "Direct
messages", "Apps", "Messages", "Files", "Today", "APP", "Message #<channel>", "Aa".

## Logos

The four-colour Slack icon sits on the workspace tile at the top of the rail (`lib/logos.py`,
unaltered). The posting app's avatar, in the message and the Apps row, is the project's logo
(`win.app_avatar`); people's avatars are initials.
