# Plan: product-media-kit

## Overview

Rename product-video-kit to product-media-kit and fold `../product-blog-kit` (BK) into it. One kit
makes a product video, a blog post, or both, and whatever one medium produced (captures, the
fixture world, motion stills, logo renders, claims, the fixture story, b-roll) is reused by the
other. Install stays `./install.sh <dest>`, then `claude` in that folder; a new `/mediatime` skill
runs the kickoff. BK was seeded from today's VK (`de38c3c`), so the engines share an ancestor.
BK is deleted after the merge passes its gate.

## Decisions

| Topic | Decision |
| --- | --- |
| Rename | Names inside files only. The human renames the folder and the GitHub repo afterwards |
| BK material | Knowledge base and tests come over, adapted; BK's git history does not |
| Execution | This session, with subagents; no loom plan |
| Project instructions | Kept in the kit as `CLAUDE-project.md`, copied to `<project>/CLAUDE.md` by `install.sh`; the kit root's `CLAUDE.md` is deleted so kit-development sessions never load the lead's instructions |
| Project file | `project.json` `{"slug", "media", "fps", "piano"}`. `install.sh` writes `{"slug": "<slug>", "media": []}` only when absent and never clobbers it. Slug derived from the folder name (lowercase, non-alphanumerics to `-`, `project` when empty), never a failure. `media` is an ordered subset of `["video", "blog"]`, filled by `/mediatime`. `fps` and `piano` are saved by `./configure.sh`, which keeps every other key |
| Frame rate | `project.json` `fps` (int 1-120, default 30 when absent) is the rate of video captures, motion and the master. `edit/edl.py` omits `FPS` and motion omits `--fps` unless the human asks for an override. A saved rate wins over any 60 fps in other instructions |
| Piano | `project.json` `piano`: `vsco` (CC0, default) or `salamander` (CC BY 3.0, credited on screen and in the description). Salamander is never downloaded or used without the human's explicit choice; `setup.sh` fetches it only when selected; the music manifest's `sample_libraries` gates its credit |
| Startup choices | `/mediatime` asks the frame rate (suggest 30) and, with music, the piano, and saves them with `./configure.sh --fps N --piano X`. `install.sh` never prompts; `--fps N --piano X` (both together) pre-answers. A delegated choice is 30 fps and VSCO. The kit-root `.claude/` is not installed, so these rules live in `CLAUDE-project.md`, the mediatime skill and `guides/video.md` |
| Sharing | `export.sh` (`tools/export_project.py`) writes a tar.gz keeping source, media, `captures/` and `outputs/`, omitting environments, caches, `music/samples`, `music/build`, `edit/build`, `post/build`, `captures/*-selftest`, font resolution, Git history and credentials. `inflate.sh` runs `system-deps.sh` then `setup.sh`. Both ship to projects; README "Sharing a project" and HUMAN.md document them |
| Outputs | Video files flat in `outputs/`; the blog in `outputs/blog/` with `outputs/blog/images/`. Names below |
| Revisions | Allocated by scanning `outputs/`; no counter. Tools rewrite the latest revision of their stage by default; `--next` writes max+1; `--revision vN` names one |
| Blog images | One `outputs/blog/images/` shared by all revisions; a rebuild replaces images in place |
| `outputs/` in git | Not ignored: it is the deliverable |
| Guides | `README.md` (shared), `guides/capture.md`, `guides/video.md`, `guides/blog.md`, `HUMAN.md`, `CLAUDE-project.md` |
| Shared records | `claims.md` (claims table) and `scenarios.md` (the one fixture story, with a Media column) at the project root, used by the video script and the blog outline |
| Capture profiles | `--for video\|blog\|both`; default from `project.json` `media`, `blog` without it |
| Viewport | One per project: default 1920x1080 when `media` includes video, else 1440x900; `VIEWPORT` in product.py wins |
| Names | Scenario and label names match `^[a-z0-9]+(-[a-z0-9]+)*$` in both media; VK's `w1_overview` style is gone. No backward compatibility with existing VK or BK projects |
| tuicap scale | Reports `scale: 2.0` (it draws at 2x density) |
| `grain` | Optional design.json key (number >= 0), read only by the edit; the blog ignores it |
| Share copy | `edit/render.py --share` replaces the README ffmpeg snippet |
| `mac_port_testing.md` | Moves to `doc/mac_port_testing.md`, gains webcap-still, tuicap-font and postkit checks |

## Shared interfaces (pinned)

### `project.json`

```json
{"slug": "acme-launch", "media": ["video", "blog"], "fps": 30, "piano": "vsco"}
```

Readers: `edit` (render, subs, credits; fps), `post` (postkit), `fixtures/web`, `fixtures/tui`
(default profile, viewport, video fps), `motion` (fps), `music` (piano), `setup.sh` (scope parsed
with grep/sed; piano through `configure.sh --get piano`). `fps` and `piano` are read through
`tools/project_settings.read` (defaults 30 and `vsco`). Writers: `install.sh` (create only), the
lead through `/mediatime`, `configure.sh` (`fps`, `piano`; keeps the other keys).

### Output names

```text
outputs/draft-<slug>-v<N>.mp4                    edit/render.py --preview
outputs/final-<slug>-v<N>.mp4                    edit/render.py (full)
outputs/<stage>-<slug>-v<N>-range-<A>-<B>.mp4    edit/render.py --range
outputs/draft-<slug>-v<N>-contact-<NN>.png       edit/render.py --contact
outputs/<stage>-<slug>-v<N>.srt                  edit/subs.py [--final]
outputs/<stage>-<slug>-v<N>-credits.txt          edit/credits.py [--final]
outputs/final-<slug>-v<N>-share.mp4              edit/render.py --share
outputs/blog/<stage>-<slug>-v<N>.md              postkit build [--final]
outputs/blog/images/<source>-<scenario>-<label>.<png|gif|webm>
```

`<stage>` is `draft` or `final`. Regex: `^(draft|final)-<slug>-v(\d+)(-[a-z0-9-]+)?\.<ext>$`.
Numbering is per medium and per stage: the video's primary file is `outputs/*.mp4` without a
suffix, the blog's is `outputs/blog/*.md`. Companion files (srt, credits, share, contact, range)
attach to the latest primary of their stage unless `--revision` is given. `edit/editkit/outputs.py`
and `post/src/postkit/outputs.py` implement the same rules (separate uv projects); a kit test
asserts both pick the same names on a fixture tree. Intermediates stay put: `edit/out/mix.wav`,
`edit/build/frames/`, `motion/out/`, `music/out/`, `captures/`.

postkit's ledger moves to `post/build/ledger.json` (gitignored); an image listed there is deleted
only when no `.md` in `outputs/blog/` references it.

### Capture manifest `captures/<source>/manifest.json`

BK's format, extended. Paths relative to `captures/<source>/`; written atomically.

```json
{"source": "web",
 "shots": [
   {"id": "settings/dialog", "kind": "still", "origin": "shots", "file": "settings/dialog.png",
    "width": 2880, "height": 1800, "scale": 2.0, "boxes": {"save": [0, 0, 10, 10]}},
   {"id": "settings/clip", "kind": "clip", "origin": "clip", "file": "settings/clip.gif",
    "webm": "settings/clip.webm", "poster": "settings/clip.png", "video": "settings/clip.mp4",
    "width": 3840, "height": 2160, "scale": 2.0, "fps": 30, "duration": 4.5, "boxes": {},
    "marks": [{"t": 1.2, "event": "open", "key": true}],
    "cursor": [{"t": 0.0, "x": 100, "y": 200, "down": false}], "cursor_space": "css-1920x1080"}]}
```

`video`, `fps`, `marks`, `cursor`, `cursor_space` (web) and `grid`, `cell_px`, `padding_px` (tui)
appear when the video profile ran; `webm` and a GIF `file` appear when the blog or both profile
ran. Under the video profile alone `file` is the poster PNG; a blog added later recaptures with
`--for both`. `origin` is `shots` or `clip`; `manifest.update` merges by scenario and
origin, so a stills-only run never drops clip-derived stills and vice versa. Sources:
`web`, `tui`, `motion`, `broll`, `video` (the last three written by `postkit add`).

Layout: `captures/<source>/<scenario>/<label>.png`, `captures/<source>/<scenario>/clip.{mp4,webm,gif,png}`.

### Capture profiles

| Profile | Scale | FPS | Files |
| --- | --- | --- | --- |
| `blog` | 1 | 30 | `clip.webm` (VP9), `clip.gif` (15 fps, max 960 px), `clip.png` poster |
| `video` | 2 | project `fps` | `clip.mp4` (H.264 crf 10 yuv420p bt709, VK's args), poster, cursor track |
| `both` | 2 | project `fps` | capture once as `video`, then derive WebM and GIF from the mp4 (30 fps, resampled only when the project rate differs; scale x0.5) |

`--draft` (video): scale 1, `ultrafast`, crf 23. Click hold and gap times are given in seconds.

### `fixtures/web/product.py`

`SHOTS = {scenario: async def (shooter)}` and/or `CLIPS = {scenario: async def (director)}`, at
least one. `CLIP_PATHS = {scenario: "/path"}`. Director API: `hold`, `glide`, `click`, `type`,
`press`, `center`, `mark(event, key=False)`, `still(label, boxes=None)`. Optional `VIEWPORT`,
`THEME` (`"light"`/`"dark"`), `LOCAL_STORAGE`, `FONT_PROBES`. Mock: `World`, `build_app(world)`.
Live: `BASE_URL` or env `PRODUCT_URL`. VK's `CLIPS(world, browser, out_dir, scale)` and
`open_scene` are gone. `agent_session.py` and `ansi.py` stay as libraries; `probe.py` is rewritten
over `open_page`; `verify.py` reads the new manifest (video only).

### `fixtures/tui/product.py`

`SHOTS = {scenario: () -> (Recording, list[Still])}` and/or `CLIPS = {scenario: () -> (Recording,
marks)}`, at least one. Optional `prepare()`, `TRUECOLOR`, `NOTES`. `STILL_T` and `SOURCE` are
gone. CLI: `uv run tuicap [scenarios...] [--clips] [--for video|blog|both] [--out DIR] [--draft]
[--selftest]`.

### Edit asset references

`still:<source>/<scenario>/<label>` resolves `captures/<source>/<scenario>/<label>.png`.
`<source>:<scenario>` (for example `web:settings`) resolves `captures/<source>/<scenario>/clip.mp4`,
else `clip.webm` with a printed warning. Manifest entries are keyed by id; capture size uses the
entry's `scale`.

### `postkit add`

```text
uv run postkit add <source>/<scenario>/<label> <file> [--at T | --from T --to T]
```

`<source>` in `motion`, `broll`, `video`. Copies a PNG, or grabs a frame (`--at`) or a segment
(`--from/--to`, GIF + WebM + poster, the capture engines' commands) into
`captures/<source>/<scenario>/<label>.*` and updates that manifest (scale 1, boxes `{}`). Default
frame treatment for these sources is `none`.

### `setup.sh` / `system-deps.sh`

`setup.sh [--check] [--for video|blog|both] [--no-samples] [--help]`; without `--for` it reads
`project.json` `media`, and checks everything when that is empty or absent. Video-only: `xz`,
`unzip`, ffmpeg MISSING with libx264/prores_ks/aac, edit/motion/music envs, GPU probe, samples,
Whisper and Gemini WARNs. Blog-only: `post` env; ffmpeg WARN "clips only". Shared: uv, curl, tar,
rg, tmux, claude, `fixtures/web` and `fixtures/tui` envs, fonts and fallback fonts, brand, skills,
Chromium. libvpx-vp9 is checked from captured output, never `grep -q` under pipefail.
Sample libraries (video scope only, `tools/setup-samples.sh`): VSCO-2 CE always, Salamander only
when `piano` is `salamander`. `setup.sh` never prompts.
`system-deps.sh` installs the union by default (VK table plus BK's Fedora Noto split);
`--for blog` skips Mesa, xz, unzip and uses `ffmpeg-free` on Fedora.

### `/mediatime` (`claude-skills/mediatime/SKILL.md`)

1. Read `project.json` and `NOTES.md`; list existing media and artefacts.
2. Ask which media (video, blog, both) and, for both, the order.
3. With video: ask the frame rate (suggest 30), music and, with music, the piano (VSCO unless the
   human explicitly picks Salamander); save with `./configure.sh --fps N --piano X`. Then run
   `./setup.sh --check --for X`, then `./setup.sh --for X` (`--no-samples` without music); loop on
   `system-deps.sh` for the human until `0 MISSING`.
4. One shared interview group (product, source and PRD, audience and goal, captures and theme,
   guidance, deliverables), then each medium's own group (VK `CLAUDE.md` b; BK
   `CLAUDE-project.md` b), skipping what is known.
5. Gemini key when narration, b-roll or the listening judge is wanted.
6. Brand skill.
7. Write `project.json` `media`, `NOTES.md` (decisions by medium), `rates.json` when billed calls
   are planned, and, when a medium is added to a project that already has one, a reuse inventory
   in `NOTES.md` (`captures/*/manifest.json`, `motion/out/manifest.json`, narration script,
   `claims.md`, `scenarios.md`, b-roll).
8. Start `guides/<medium>.md` Phase 1.

`CLAUDE-project.md`: a first session (no `NOTES.md` or empty `media`) runs the mediatime skill
whatever the human says first; a later session asking for the other medium reruns it.

## README section map (pinned so the guide writers agree)

`README.md`: What you make; How the kit is used; Requirements; Setup (Install into a project,
System packages, Self-tests, Running on macOS, Sharing a project); The team (rules 1-11, Good briefs); Kickoff
(`/mediatime`); Reuse between media; Pipeline and folder map; Engine and project files; Code that
needs your product; Outputs; Brand (`BRAND.md` and `brand/`, The brand skill, The checker);
Design system (`design.json`, Fonts by family, Who reads what, Legibility); Editorial rules;
Project records (`NOTES.md`, `HANDBOOK.md`, Rejected styles, `claims.md` and `scenarios.md`);
Mistakes and pitfalls; Licences and credits.

`guides/capture.md`: Web capture; TUI capture; Manifests; Profiles. `guides/video.md`: VK's
stack rows, CPU-only machines, roles, Phases 1-5, A reusable plan, Deliverable conventions,
Narration, The listening judge, Music, Motion graphics, The logo in a scene, Transitions, B-roll,
The edit, The mix, Subtitles and credits, Review and QA, Encoding, Snippets, `edit/ISSUES.md`,
`COSTS.md`, video mistakes. `guides/blog.md`: roles, Phases 1-5, The post (`draft.md` and
`shot:`, `images.json`, Building and checking, `postkit add`), Review and QA, blog editorial
rules, blog mistakes.

## Work packages

Write sets are disjoint. "Import" means copy the BK file into this repo, then adapt it.

| WP | Tier | Writes | Depends on |
| --- | --- | --- | --- |
| 1 webcap | opus | `fixtures/web/**` | — |
| 2 tuicap | sonnet | `fixtures/tui/**` | — |
| 3 postkit | sonnet | `post/**` | — |
| 4 edit | sonnet | `edit/render.py`, `edit/subs.py`, `edit/credits.py`, `edit/editkit/{assets,shots,outputs}.py`, `edit/pyproject.toml`, `edit/uv.lock` | — |
| 5 plumbing | sonnet | `install.sh`, `setup.sh`, `system-deps.sh`, `claude-settings.json`, `.gitignore`, `claude-skills/{brand,narration}/**`, `tools/**`, `tests/**` except `test_docs_contracts.py` and `smoke.sh` | — |
| 6a shared guides | opus | `README.md`, `guides/{capture,blog}.md`, `HUMAN.md`, `CLAUDE-project.md`, delete `CLAUDE.md`, `claude-skills/mediatime/SKILL.md`, `doc/mac_port_testing.md` (moved), `tests/test_docs_contracts.py`, `tests/smoke.sh` | 1-5 |
| 6b video guide | sonnet | `guides/video.md` | 1-5 |
| 7 knowledge | sonnet | `doc/loom/knowledge/**` | 6a, 6b |

Acceptance per package:

1. `cd fixtures/web && uv run --frozen pytest && uv run --frozen ruff check .`; selftests
   `--for blog` and `--for both` into a scratch dir; ffprobe reports the project fps (30 without
   `project.json`) for `clip.mp4`;
   `clip.gif` exists; numpy in the dependencies.
2. `cd fixtures/tui && uv run --frozen pytest && uv run --frozen ruff check .`;
   `uv run --frozen tuicap --selftest --for both --out <scratch>`; manifest `scale` 2.0.
3. `cd post && uv run --frozen pytest && uv run --frozen ruff check . && uv run --frozen postkit selftest`;
   tests for revisions, `--next`, the ledger rule and `postkit add`.
4. `cd edit && uv run --frozen ruff check .`; `uv run bg_test.py 1`; a contact render on a scratch
   EDL writes `outputs/draft-<slug>-v1-contact-00.png`; unit tests for `outputs.py`.
5. `bash -n install.sh setup.sh system-deps.sh`; `cd tests && uv run --frozen pytest -k 'kit or contracts or brand'`;
   `./install.sh <scratch>/My_Post --no-system` writes `project.json` with slug `my-post` and no
   `doc/`, `tests/`, `captures/`, `outputs/`, `music/samples/`; `./setup.sh --check --for blog`
   there runs no GPU probe.
6. `cd tests && uv run --frozen pytest`; `sh tests/smoke.sh .`; an install contains
   `.claude/skills/mediatime/SKILL.md`; `rg -n 'product-video-kit|product-blog-kit|Product (Video|Blog) Kit|edit/out/intro|post\.json'`
   finds nothing outside `doc/loom/knowledge/mistakes*`.
7. `loom knowledge check`; INDEX.md regenerated; no BK-only claim left (`post.json`, `out/<slug>`,
   "grain does not exist", tuicap `scale: 1.0`).

Then: a `loom-verifier` over every acceptance line on the complete tree, a `loom-code-reviewer`
pass, fixes, and the human's go-ahead before `../product-blog-kit` is deleted.
