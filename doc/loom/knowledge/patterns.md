# Architectural Patterns

> Discovered patterns in the codebase that help agents understand how things work.
> A summary of the current tree: correct a section in place with `replace-section`.

## Virtual-clock frame stepping (webcap)

Nothing in a clip depends on wall time. Per frame `Director.step` ticks the mock `World`, waits for the page to receive every WebSocket message sent, advances Playwright's faked page clock, runs the frame's input, calls `window.__frame()` and takes a CDP screenshot. `World.tick(t)` is the only source of state change and every message goes through `World.send()` so it is counted. Live mode skips the world steps. Detail: [architecture/webcap](architecture/webcap.md).

## Atomic output writes

Every output is written under a temporary name and renamed: webcap through `media.temp_path` and `write_atomic`, tuicap through `.tmp` names, postkit through `common.write_atomic` and `copy_atomic` (`.<name>.part` files, removed by `remove_part_files` on the next build). A failure removes the partial file; a reader never sees a half-written capture.

## tuicap rendering and isolation

Timestamped output bytes (`Recording`) replay through pyte (`VtStream`/`VtScreen`) into a skia raster surface; box-drawing, block and braille glyphs are drawn procedurally, others through `Fonts.pick`. `clean_env` pins `TERM`, `COLORTERM`, a UTF-8 locale and an optional scratch `HOME`, `synth_cli` seeds its typing cadence, and `tmux_server` points `TMUX_TMPDIR` into the fixture folder with its own socket, so captures are reproducible and the operator's tmux is never touched. Detail: [architecture/tuicap](architecture/tuicap.md).

## Project-owned capture modules

The kit ships the engines; each project writes one product module per harness (`<project>/fixtures/web/product.py`, `<project>/fixtures/tui/product.py`) with `SHOTS` and/or `CLIPS` (at least one). Scenario, label and box names share one rule (`^[a-z0-9]+(-[a-z0-9]+)*$`, in `webcap/names.py`, `tuicap/clips.py` and `postkit/common.py`) because they become file names, manifest ids and draft references.

## Capture profiles

`--for video|blog|both` selects scale, frame rate and files in both engines: blog (scale 1, 30 fps, WebM and GIF), video (scale 2, the project's `fps` from `project.json`, default 30, mp4 and cursor track), both (record the mp4, derive WebM and GIF). SHOTS stills are 2x in every profile. The default comes from `project.json` `media`.

## Merge, never overwrite, in the manifests

`manifest.update` replaces a scenario's entries of the origin a run captured (`shots` or `clip`) and keeps every other entry ([mistakes/media-kit-merge](mistakes/media-kit-merge.md)). Rules: [architecture/outputs-and-reuse](architecture/outputs-and-reuse.md).

## Twin modules kept identical by a test

`edit` and `post` are separate uv projects, so the output-naming rules exist twice (`edit/editkit/outputs.py`, `post/src/postkit/outputs.py`); `tests/test_outputs_agree.py` runs both on the same trees. The design.json loaders are likewise per-package copies, each validating the same key lists.

## Validate everything, then write (postkit)

`postkit build` collects every problem and raises one `BuildError` before writing, so a failed build leaves `outputs/blog/` as it was; a ledger (`post/build/ledger.json`) lets the next build delete only files it no longer writes and no post references.

## Placeholders before assets (edit)

`editkit/assets.py` replaces a missing asset with a generated placeholder of the right shape so the cut can be built and timed before captures, scenes or b-roll exist; a full render refuses to run while a placeholder remains.

## Decision log and handbook

`<project>/NOTES.md` is a list of decisions, one bullet each (what the human asked, the rule that follows, what changed), plus rejected styles and every engine patch with file and reason so a kit update can re-apply it. `<project>/HANDBOOK.md` lets the next agent start cold (README "Project records"). `<project>/claims.md` and `<project>/scenarios.md` are the shared records of both media.

## Brand pattern

Optional `<project>/BRAND.md` plus `brand/` at the project root; the brand skill generates `design.json` and the HANDBOOK "Brand" section; nobody hand-edits `design.json`; `setup.sh` and `check.py` warn when it is older than a file it is built from (`<project>/BRAND.md`, `brand/logo*`, `brand/fonts/`, `brand/palette/`, the files it names), never for `tools/fonts.py` output, photos, screenshots or `brand/reference/`. Detail: [architecture/brand-and-design](architecture/brand-and-design.md).
