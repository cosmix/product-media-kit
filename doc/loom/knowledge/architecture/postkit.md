# Postkit

> postkit modules, build, check and add flow, treatments, ledger

## postkit module map

Package `postkit` in `post/src/postkit/` (Pillow only; script `postkit = postkit.cli:main`; run `uv run postkit <build|check|add|selftest> [--root DIR]` from `post/`; `--root` defaults to the project root). Tests: `post/tests/` (`test_contracts.py`, `test_postkit.py`, `test_postkit_internals.py`, `test_outputs.py`, `test_revisions.py`, `test_add.py`, `conftest.py`).
- `cli.py`: argument parsing; `build` returns 1 on `BuildError`, `check` the number of ERRORs; `--next` and `--revision vN` on build.
- `common.py`: `NAME_RE`, `SHOT = "shot:"`, `IMAGE_RE`, `LEFTOVER_RE`, front-matter and fenced-block skipping (`body_matches`; inline code spans are not skipped), `read_slug` (from `<project>/project.json`; the error says install.sh writes it), `blog_dir`, `write_atomic`, `copy_atomic`, `remove_part_files`.
- `outputs.py`: `output_path`, `latest_revision`, `NAME_RE(slug, ext)`; the twin of `edit/editkit/outputs.py` ([architecture/outputs-and-reuse](outputs-and-reuse.md)).
- `manifest.py`: `load_shots(root)` reads the manifests of `SOURCES = ("web", "tui", "motion", "broll", "video")` (each optional) into frozen `Shot` records keyed `<source>/<scenario>/<label>`; every problem is collected and raised as one `ManifestError` (positive `width` and `height`, `scale` above 0, four non-negative integers per box, `file`, `webm`, `poster` inside the manifest's folder).
- `config.py`: `read_images_json`, `treatment_for` merges `defaults` under a shot's entry and validates `frame`, `crop`, `pad`, `highlight`, `callouts`, `width`. Default frame by source: `browser` for web, `none` for tui, motion, broll, video.
- `design.py`: accent (default `#2563eb`) and the bold font: `fonts.bold` file, else `brand/fonts/resolved.json` (when its `design_json_sha256` matches), else `fc-match "DejaVu Sans:bold"` (timeout 10 s), else Pillow's built-in font. There is no macOS fallback font.
- `images.py`: `treat(...)` crops to a box plus `pad`, outlines highlights in the accent, draws numbered callout circles, frames, resizes to at most `width` (never upscaled); `pad`, strokes and frames scale with the shot's `scale`. A clip is copied untouched (GIF and WebM beside it); the poster is not copied.
- `frames.py` (`CHROMES`, fixed colours), `assemble.py` (`build`), `check.py` (`check`, `report`), `add.py`, `selftest.py`.

## Build, check and add

`build [--final] [--next | --revision vN]` reads and validates everything first (slug, `<project>/post/draft.md`, images.json, manifests, design, referenced shots and readability through `img.load()`, output-name collisions) and raises all problems as one `BuildError` before writing. Then it removes stale `.part` files, treats each referenced shot into `outputs/blog/images/<source>-<scenario>-<label>.<png|gif|webm>` (one folder shared by every revision; a rebuild replaces images in place) and writes `outputs/blog/<stage>-<slug>-v<N>.md` with `shot:` targets rewritten to `images/<file>`.

The ledger `post/build/ledger.json` lists files postkit wrote; an image from an earlier build is deleted only when it is no longer written and no `.md` in `outputs/blog/` references it.

`check [--file PATH]` defaults to the latest draft and latest final. ERROR: no built post, a missing, absolute or escaping link, unreadable image, empty alt text, leftover `shot:` link, non-UTF-8 file. WARN: image wider than 2400 px, GIF over 10 MB, an image in `outputs/blog/images/` no post references (scans all posts). Exit code is the ERROR count.

`add <source>/<scenario>/<label> <file> [--at T | --from T --to T]` (source `motion`, `broll` or `video`) copies a PNG, grabs a frame (`--at`) or cuts a segment (`--from/--to`: GIF, WebM, poster) into `captures/<source>/<scenario>/<label>.*` and updates that manifest (scale 1.0, boxes `{}`). The WebM filter converts with the bt709 matrix.
