# The blog post

How the team writes a blog post about the product: plain markdown with its images beside it,
every claim checked against the code, every image captured from the product with the same fixture
story. Read [README.md](../README.md) first ("The team", "Reuse between media", "Outputs",
"Editorial rules", "Project records"); the captures are in [capture.md](capture.md).

- [Roles](#roles)
- [Phase 1: learn the product and the PRD](#phase-1-learn-the-product-and-the-prd)
- [Phase 2: outline and scenarios](#phase-2-outline-and-scenarios)
- [Phase 3: captures and draft](#phase-3-captures-and-draft)
- [Phase 4: build and review loop](#phase-4-build-and-review-loop)
- [Phase 5: finishing](#phase-5-finishing)
- [The post](#the-post)
  - [`draft.md` and `shot:` references](#draftmd-and-shot-references)
  - [`images.json`: image treatment](#imagesjson-image-treatment)
  - [Building and checking](#building-and-checking)
  - [`postkit add`](#postkit-add)
- [Review and QA](#review-and-qa)
  - [How the lead reviews without a browser](#how-the-lead-reviews-without-a-browser)
  - [QA checklist (every final build)](#qa-checklist-every-final-build)
- [Blog editorial rules](#blog-editorial-rules)
- [Blog mistakes](#blog-mistakes)

## Roles

| Role                | Tier                                                     | Owns                                                                                                              | Job                                                                  |
| ------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| lead (main session) | Opus                                                     | the README's lead files (`claims.md`, `scenarios.md`, the records, the brand), `post/outline.md`, `post/draft.md`, `post/images.json` | claims, outline, scenarios, briefs, draft, builds, review, decisions |
| web capture         | Opus                                                     | `fixtures/web/product.py` and its fixture data, `captures/web/`                                                   | mock server or live mode, stills and clips of the web UI            |
| TUI capture         | Sonnet for plain CLI output; Opus for an interactive TUI | `fixtures/tui/product.py` and its fixture files, `captures/tui/`                                                  | stills and clips of the CLI and terminal UIs                         |
| writer (optional)   | Opus                                                     | `post/draft.md`, only while the lead has handed it over                                                           | a first draft of a long post from the approved outline               |

Only the roles the post needs exist: no web capture for a CLI-only product, no TUI capture for a
web-only one. In a project that also makes the video, the capture teammates serve both media from
one `product.py` each. By default the lead writes the draft itself; it hands `post/draft.md` to a
writer only for a long post, and takes the file back when the writer reports. `postkit add` runs
are the lead's: it owns the `captures/motion/`, `captures/broll/` and `captures/video/` they write.

## Phase 1: learn the product and the PRD

Read the PRD in full, then the parts of the product's code the feature touches: the commands, the
settings, the UI routes, the help text, the defaults. Every claim the post will make goes into the
claims table in `claims.md` at the project root ([README.md](../README.md), "`claims.md` and
`scenarios.md`"), with its source and the post section that uses it. In a project that already has
a video, start from its claims: a claim verified for the script needs no second check, only a new
"Used in" entry.

A claim is verified only when the code shows it. When the PRD and the code disagree, the code wins
and the lead asks the human how the post should treat it. An unverified claim does not go into the
draft.

## Phase 2: outline and scenarios

**`post/outline.md`**: the post's sections in order, each with its point in one line, the claims it
makes (by number in `claims.md`) and the images it shows (by `shot:` id).

**`scenarios.md`**: one row per scenario, the unit a capture teammate works in, with `blog` or
`both` in the Media column. A scenario is one user goal shown as stills, an optional clip, or
both. The fixture story at the top of the file is the one the video uses too; the post adds rows,
never a second story. Name the boxes each still needs: the draft and `images.json` refer to them.

The human approves both files before any capture starts. Record the approval in `NOTES.md`.

## Phase 3: captures and draft

The lead spawns the capture teammates in one message, each with a complete brief (README "Good
briefs"), and writes the draft (or briefs the writer) while they work. The draft can reference
shots before they exist: `postkit build` reports every unknown `shot:` id at once, so a build run
mid-way lists what is still to come.

Before briefing, read the reuse inventory in `NOTES.md` when the project has a video: stills and
clips already captured are linked as they are, clips captured under the video profile alone are
recaptured with `--for both`, and motion stills, b-roll and frames of the cut come in through
[`postkit add`](#postkit-add).

## Phase 4: build and review loop

1. When a capture teammate reports, the lead Reads every new PNG in `captures/<source>/` and checks
   the boxes in its manifest ([Review and QA](#review-and-qa)).
2. The lead writes `post/images.json` for the crops, highlights and callouts, then builds:

   ```bash
   cd post && uv run postkit build
   ```

3. The lead Reads every image in `outputs/blog/images/` the build wrote and the whole post, fixes
   what it finds, and only then points the human at the post.
4. The human sends short notes. The lead writes each to `NOTES.md` first, then applies it. The
   first build after the human has reviewed a revision uses `--next`, so the reviewed revision
   stays.

| Kind of note                                      | What it turns into                                                                                   |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| A claim is wrong or overstated                    | Correct `claims.md`, then every sentence and caption that makes it (and the script, if a video uses it); record the rule in `NOTES.md` |
| A product term is wrong                           | Correct the draft, the alt texts and the fixture data; record the term in `NOTES.md`                 |
| An image shows the wrong state or data            | Fix the fixture story, then recapture every scenario that shows it, in every medium                  |
| An image is too busy                              | Crop it to a box in `images.json`, or ask the capture teammate for a box around the part that matters |
| The order or length is wrong                      | Change the outline first, then the draft                                                             |
| The look is wrong (colours, fonts, frame)         | Change `BRAND.md` with the human, rerun the brand skill, rebuild                                     |
| The human asks the lead to stop asking and decide | From then on the lead decides and reports, asking nothing                                            |

**Propagating a change.** The order is always the same: record the decision in `NOTES.md`; change
the source (`claims.md`, the outline, `scenarios.md`, `product.py`); recapture only the scenarios
it touches (`uv run python -m webcap.capture <scenario>` or `uv run tuicap <scenario>` keeps the
rest of the manifest); update `images.json` when a box name changed; rebuild; review the changed
images before the human sees them.

## Phase 5: finishing

- **`postkit check`** shows no ERROR. Read each WARN and fix it or record why it stays.
- **Alt text** on every image says what the image shows, in the product's terms
  ([Blog editorial rules](#blog-editorial-rules)).
- **The first image.** Many sites use the post's first image as its preview card. Make it the
  image that best shows the feature, cropped so it reads at a small size.
- **Front matter**, when the platform needs it: the fields the human named at kickoff, nothing
  else.
- **The final build**: `uv run postkit build --final`, then `uv run postkit check`. It writes
  `outputs/blog/final-<slug>-v<N>.md` beside the drafts.
- **Final paths.** Tell the human where the post is and that `outputs/blog/` moves as one folder:
  the markdown links `images/<file>` relatively. To publish, copy the final `.md` and the images
  it links.

## The post

The post's name comes from `project.json`: the slug names every revision,
`outputs/blog/<stage>-<slug>-v<N>.md` (README "Outputs"). Change the slug only with the human, and
rebuild.

### `draft.md` and `shot:` references

`post/draft.md` is the post in markdown. A leading YAML front matter block is copied through
untouched. An image is a markdown image whose URL is a shot reference,
`shot:<source>/<scenario>/<label>`, with an optional title. `<source>` is `web`, `tui`, or one
`postkit add` wrote (`motion`, `broll`, `video`):

```markdown
---
title: "Rename projects from Settings"
date: 2026-10-20
---

# Rename projects from Settings

Open the project's Settings and choose Advanced. The name field is at the top (1); Save
applies the change (2).

![The Advanced settings dialog of project acme-api, with the name field marked 1 and the Save button marked 2](shot:web/settings/dialog "Advanced settings")

![Typing acme-api as the first project's name and pressing Enter](shot:web/first-run/clip)

![Output of acme status: three environments, staging marked degraded](shot:tui/status/main)
```

The build replaces each reference with `images/<source>-<scenario>-<label>.png` (`.gif` for a
clip, with the WebM copied beside it) and keeps the alt text and the title. Every reference needs
alt text. Links that are not `shot:` references pass through untouched: a remote `https://`
image, or an image the human supplies that the lead places in `outputs/blog/images/` by hand.

### `images.json`: image treatment

`post/images.json` is optional. `defaults` applies to every shot; an entry keyed by a shot
reference (without `shot:`) overrides it per key:

```json
{
  "defaults": { "width": 1400 },
  "web/settings/dialog": { "crop": "dialog", "highlight": ["save"], "callouts": ["name", "save"] },
  "tui/status/main": { "frame": "terminal", "highlight": ["table"] }
}
```

| Key         | Default                                    | Meaning                                                                                          |
| ----------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `frame`     | `"browser"` for web, `"none"` for the rest | `"browser"` (a light window with three dots), `"terminal"` (a dark window), or `"none"`          |
| `crop`      | `null`                                     | a box name: crop to that box plus `pad`, clamped to the image                                    |
| `pad`       | `24`                                       | pixels around a crop, multiplied by the shot's scale                                             |
| `highlight` | `[]`                                       | box names outlined in the accent colour, just outside the box so the element stays readable     |
| `callouts`  | `[]`                                       | box names numbered 1, 2, ... in list order, a filled accent circle on each box's top-left corner |
| `width`     | `1600`                                     | the largest width of the result in pixels; never upscaled                                        |

The order is crop, highlight, callouts, frame, resize. Box names are the ones in the manifest.
Outlines, circles and frames are drawn at the shot's scale, so web and terminal stills (both
scale 2) and a 1x still from `postkit add` look the same once resized. Clips are copied as they
are: their GIF and WebM get no treatment, and the keys above are not applied to them. Number
callouts in the order the prose names them, and say the numbers in the text. tui, motion, broll
and video shots get no frame by default: tuicap already draws a padded terminal, and the others are
full frames.

### Building and checking

```bash
cd post
uv run postkit build                  # rewrites the latest draft (v1 when none)
uv run postkit build --next           # the next draft revision
uv run postkit build --revision v2    # draft v2
uv run postkit build --final          # the latest final (v1 when none)
uv run postkit check                  # the latest draft and the latest final
uv run postkit check --file ../outputs/blog/draft-acme-launch-v2.md
```

All take `--root DIR` (default: the project root). `project.json` must exist
(`project.json: missing (install.sh writes it)` otherwise).

Every build, check and add run is timed under the `blog` category in `METRICS.md` at the project
root. Rebuild that report with `uv run tools/metrics.py` from the project root.

**`build`** reads `post/draft.md`, `post/images.json`, `design.json` and the capture manifests,
validates every input first and writes nothing when any is wrong; it then lists every problem at
once, one per line: a missing `project.json` or `draft.md`, empty alt text, an unknown shot (with
the known ones), a capture file that is missing or unreadable, an `images.json` key or value that
is wrong, a box name the shot does not have, an `images.json` entry for a shot that no manifest
has, two shots that would write the same file (`web/a-b/c` and `web/a/b-c` both give `web-a-b-c`),
a malformed `design.json`. On success it prints every file it wrote.

`outputs/blog/` after two drafts and a final:

```text
outputs/blog/
├── draft-acme-launch-v1.md
├── draft-acme-launch-v2.md
├── final-acme-launch-v1.md
└── images/                          # shared by every revision
    ├── web-settings-dialog.png      # a treated still
    ├── web-first-run-clip.gif       # a clip, as linked
    ├── web-first-run-clip.webm      # the same clip, copied beside the GIF
    └── tui-status-main.png
```

Every revision links the one `images/` folder, and a rebuild replaces an image in place, so an
older revision shows the current treatment of an image it shares. The ledger
`post/build/ledger.json` lists the images postkit wrote. An image the previous build wrote and
this one did not is deleted, and printed as `removed <path>`, only when no `.md` in
`outputs/blog/` links it. postkit never deletes a file it did not write, so a hand-placed image
survives every build; losing the ledger only means nothing is deleted.

**`check`** reads the latest draft and the latest final as built, or the post `--file` names:

| Level | Problem                                                                                                        |
| ----- | -------------------------------------------------------------------------------------------------------------- |
| ERROR | no built post; a post outside `outputs/blog/`; `project.json` missing or malformed                             |
| ERROR | an image link whose target is missing, absolute, or outside `outputs/blog/`; a leftover `shot:` link; empty alt text |
| ERROR | a linked file that is not a readable image                                                                     |
| WARN  | an image wider than 2400 px; a GIF over 10 MB                                                                  |
| WARN  | a file in `outputs/blog/images/` that no post in `outputs/blog/` references (a linked GIF's WebM counts)       |

Remote `http://` and `https://` images pass. It prints `LEVEL message` lines and a summary,
`<n> error(s), <m> warning(s)`, and exits 1 on any ERROR.

### `postkit add`

```text
uv run postkit add <source>/<scenario>/<label> <file> [--at T | --from T --to T]
```

Brings what the video made into the post's captures, so the draft links it as
`shot:<source>/<scenario>/<label>` like any capture. `<source>` is `motion`, `broll` or `video`;
the scenario and label follow the naming rule in `scenarios.md`.

- A PNG is copied as it is.
- A video needs `--at T` (one frame, as a PNG) or `--from A --to B` (a segment: a GIF at 15 fps,
  at most 960 px wide, a VP9 WebM and a poster PNG, made with the capture engines' ffmpeg
  settings). Both need ffmpeg.
- The files land in `captures/<source>/<scenario>/<label>.*`, and that source's manifest gains or
  replaces the entry (scale 1, no boxes), written atomically.

```bash
cd post
uv run postkit add motion/endcard/logo ../motion/out/endcard_01.50.png
uv run postkit add motion/pitch/graph ../motion/out/pitch.mp4 --at 6.2
uv run postkit add broll/city/loop ../broll/candidates/03_city.mp4 --from 1.0 --to 4.0
uv run postkit add video/intro/hero ../outputs/final-acme-launch-v2.mp4 --at 12.0
```

Pick frames by time from `narration/timeline.json` and the motion manifest's marks, never by
guessing; a frame mid-transition or mid-fade reads as a defect on the page. Without boxes, crop
and callout keys cannot apply: show a part of a motion still with a new render at that framing, or
take the web capture instead. Credit b-roll as `broll/CREDITS.md` says.

## Review and QA

### How the lead reviews without a browser

Claude Code's Read tool shows images, so every capture and every built image can be looked at:

- **Each still**: Read `captures/<source>/<scenario>/<label>.png`. Check the state against the
  scenario row: the right screen, the fixture story's data, no error banner, no loading spinner,
  no half-finished transition.
- **Each box**: the manifest gives `[x, y, w, h]` per box. A box that frames the wrong element
  shows in the built image: Read `outputs/blog/images/` after a build with the box highlighted.
- **Each clip**: Read its poster, `clip.png` (the last frame). For the frames in between, a
  contact sheet:

  ```bash
  ffmpeg -loglevel error -y -i captures/web/first-run/clip.webm -vf "fps=2,scale=480:-1,tile=4x3" -frames:v 1 /tmp/sheet.png
  ```

- **The built post**: Read the built `.md` in full and every image it links, then run the check:

  ```bash
  cd post && uv run postkit check
  ```

Defects found this way before the human sees them: a crop that cuts a label in half, a callout
circle covering the text it numbers, a still taken before the data loaded, a terminal still cut
mid-output, alt text that describes a different image after a recapture.

### QA checklist (every final build)

- `uv run postkit check` prints `0 error(s)`; every WARN is fixed or recorded in `NOTES.md` with
  the reason;
- every claim in the draft is marked verified in `claims.md`;
- every image shows the fixture story's data, and the same names everywhere, the video included;
- the image files' times are later than the captures and the edits they should contain (rebuild
  after every recapture);
- nothing from "Rejected styles" in `NOTES.md` anywhere;
- every alt text matches its image as built;
- callout numbers match the numbers the prose names;
- the first image is the one chosen for the preview card;
- front matter has exactly the fields the platform needs;
- headings, code blocks and links follow [Blog editorial rules](#blog-editorial-rules).

## Blog editorial rules

The README's "Editorial rules" hold; these add what is particular to a post:

- **Alt text says what the image shows**: the screen, the state and the parts the prose points to,
  in the product's terms ("The Advanced settings dialog with the name field marked 1"), never
  "screenshot of" or a caption's marketing line.
- **Headings say what the section does** ("Rename a project", "Check the result"), never a pun or a
  teaser.
- **Code blocks name their language** (` ```bash `, ` ```toml `, ` ```text ` for output), and show
  commands a reader can run as written, against the fixture story's names.
- **Written for reading.** Reuse the video's terms, claims and pitch wording, never its spoken
  sentences: a narration line read on a page sounds like a script.
- **Length** by default 1,200 to 1,800 words; a launch announcement, a how-to or a deep dive, as
  agreed at kickoff.

## Blog mistakes

| Area   | What goes wrong                                                                   | Rule                                                                                            |
| ------ | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Images | A GIF over 10 MB (`postkit check` WARN)                                           | Shorten the clip's holds, or show the end state as a still                                      |
| Images | A 3840 px still from a video project shown at full size                           | Keep `width` (default 1600) or crop to a box; never raise `width` past 2400                     |
| Images | A frame added with `postkit add` caught a transition or a fade                    | Take the time from the timeline and the motion marks; Read the PNG before linking it            |
| Build  | `images.json` still names a shot the draft or the captures dropped                | Delete the entry; the build lists every such key                                                |
| Build  | A hand-placed file in `outputs/blog/images/` that nothing links stays forever     | postkit deletes only its own files; remove it by hand, `postkit check` lists it                 |
| Build  | A rebuild overwrote the draft revision the human was reading                      | Build with `--next` after every review                                                          |
| Reuse  | The post linked a clip captured for the video alone and showed its poster, a still | Recapture it with `--for both` for a GIF, or link one of its stills on purpose                 |
| Review | A capture teammate reported a still as fine; the box was on the wrong element    | The lead Reads every image itself                                                               |
