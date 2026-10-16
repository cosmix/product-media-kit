# Architecture

> High-level component relationships, data flow, and module dependencies.
> A summary of the current tree: correct a section in place with `replace-section`.

## Kit repo versus installed project

Nobody works inside the kit repo. `./install.sh <project-dir>` copies the engines into a project folder, derives the slug from the folder name and writes `project.json` (`{"slug": ..., "media": []}`); the `/mediatime` skill fills `media` (an ordered subset of video and blog) and saves the video's `fps` and `piano` through `./configure.sh`. The lead's instructions live in the kit as `claude-project.md` and install copies them to `<project>/CLAUDE.md`, so agents developing the kit never load them. The kit's own files (`install.sh`, `claude-skills/`, `claude-settings.json`, `doc/`, `tests/`) are not copied. Later kit updates reach a project only through `install.sh --force`. Scripts and the installed layout: [architecture/kit-plumbing](architecture/kit-plumbing.md).

## One kit, two media

A product video and a blog post are built from the same sources: one fixture world, one set of captures, shared `<project>/claims.md` and `<project>/scenarios.md`, one brand. Only the two capture harnesses talk to the product; each loads one project-owned product module from its folder. Deliverables land in `outputs/` (video) and `outputs/blog/` (post), named `<stage>-<slug>-v<N>`. Names, revisions, the manifest contract and the reuse paths between media: [architecture/outputs-and-reuse](architecture/outputs-and-reuse.md).

## Capture engines

`fixtures/web/webcap/` captures a web UI with headless Chromium (Playwright) into PNG stills with element boxes and clips, in a mock (`World` plus `build_app`, scripted clock) or live (`BASE_URL`/`PRODUCT_URL`) mode. `fixtures/tui/src/tuicap/` records a program in a pty (or synthesises a typed CLI session), replays it through pyte and draws with skia. Both take `--for video|blog|both` (default from `project.json`) and write `captures/<source>/manifest.json`. Detail: [architecture/webcap](architecture/webcap.md), [architecture/tuicap](architecture/tuicap.md).

## Blog side

`post/src/postkit/` (Pillow) turns `<project>/post/draft.md` plus the manifests into `outputs/blog/<stage>-<slug>-v<N>.md` and `outputs/blog/images/`; the draft links captures as `shot:<source>/<scenario>/<label>`; `postkit add` brings motion, b-roll and video frames in as captures. Detail: [architecture/postkit](architecture/postkit.md).

## Video side

`narration/timeline.json` is the only clock ([architecture/narration](architecture/narration.md)). `motion/` renders scenes ([architecture/motion](architecture/motion.md)), `music/` renders the soundtrack ([architecture/music](architecture/music.md)), and `edit/` composites everything on the GPU from the project's `<project>/edit/edl.py`, mixes audio and encodes ([architecture/edit](architecture/edit.md)). Each of these is a separate uv project.

## Brand

`claude-skills/brand/` turns `<project>/BRAND.md` plus `brand/` into `design.json` (keys `fonts`, `colors`, `logo`, optional `grain`); `tools/fonts.py` resolves family-named fonts to files; five loaders read it. Detail: [architecture/brand-and-design](architecture/brand-and-design.md).

## Tests and gates

Each package has its own pytest suite run with `uv run --frozen pytest` from the package: `fixtures/web/tests`, `fixtures/tui/tests`, `post/tests`, `edit/tests`, and `tests/` for the kit (`test_kit.py` install, setup and system-deps behaviour on a fake kit, `test_brand.py`, `test_docs_contracts.py` guide commands, links and section references, `test_outputs_agree.py` the twin outputs modules, `test_contracts.py`). `tests/smoke.sh <kit-dir>` installs the kit into a scratch project and runs the selftests; it needs ffmpeg. Lint gate: `uv run --frozen ruff check .` per package with ruff's defaults; `ruff format` is not a gate. Conventions: [conventions](conventions.md).
