# Tuicap

> tuicap modules, render pipeline, profiles, product.py contract, CLI, fallback fonts

## tuicap module map (fixtures/tui/src/tuicap)

Package `tuicap` (script `tuicap = tuicap.clips:main`; run `uv run tuicap` from `fixtures/tui`). Modules: `capture` (pty and synthetic recordings, `clean_env`, `synth_cli`), `tmux_clip` (shell recordings, `tmux_server`), `render` (pyte replay, skia drawing, stills, clips), `encode` (ffmpeg commands per profile), `glyphs` (procedural box, block and braille drawing), `palette`, `design` (design.json loader), `fonts` (fallback font lookup), `shots` (`Still`), `manifest` (`update`), `clips` (the CLI). Tests: `fixtures/tui/tests/` (`test_contracts.py`, `test_tuicap.py`, `test_profiles.py`).

## Render pipeline

- Constants in `render.py`: `CELL_W = 28` px at 2x density, `CELL_H = 58`, `PAD = 48`. Images are drawn at that density and entries report `scale: 2.0`, so postkit's decoration weight matches a web still's.
- `VtScreen`/`VtStream` subclass pyte to add SU/SD scrolling and private DSR. `Geometry(cols, rows).size` rounds each side up to even.
- `Fonts` loads `design.mono()` through skia, builds bold and italic variants, adds the fallback fonts and the emoji font; `pick(char, bold, italic)` walks terminal font, fallbacks, emoji. `glyphs.Procedural` draws box-drawing, block and braille characters itself.
- `TerminalRenderer.render_base` paints backgrounds as merged runs, then glyphs; `frame` overlays the cursor.
- `render_still(rec, png, t)` replays events up to `t` and writes one PNG (no ffmpeg). `render_recording(rec, out_dir, label, profile="blog", draft=False)` replays frames into `encode.encoder` (rawvideo RGBA on stdin): blog gives VP9 WebM at 30 fps, video gives H.264 mp4 at 60 fps (crf 10, draft 23), both records the mp4 and derives the WebM; the GIF (15 fps, max 960 px) and poster follow. `--draft` affects the mp4 only.
- `Recording(cols, rows, events, duration, inputs, show_cursor=True)`; `cell_box(...)` converts a half-open cell range to image pixels and raises `ValueError` when empty or outside the grid.

## Capture helpers

`capture.clean_env(home, tz=None, drop=())` pins `TERM`, `COLORTERM` and a UTF-8 locale so the operator's config cannot leak; `record_pty` drives a child in a pty; `synth_cli(prompt, command, output, cols, rows, seed, lead, tail) -> (Recording, marks)` types a command with seeded cadence and reveals real output in bursts. `tmux_clip.tmux_server(socket, tmpdir, env)` isolates tmux with a short `TMUX_TMPDIR` (socket path under 100 bytes), `record_shell(...)` records an interactive bash.

## Fonts and palette

`fonts.family_file(family)` asks `fc-list` (timeout `FC_TIMEOUT` = 10 s) for a family's regular style; `fallback_fonts()` is DejaVu Sans Mono, Noto Sans Symbols2, Noto Sans Symbols, Noto Sans Math on Linux (Menlo and Apple Symbols files on macOS); `emoji_font()` is Noto Color Emoji (Apple Color Emoji on macOS). A missing family contributes no font. `palette` reads `colors.background` and `colors.text` lazily; `TRUECOLOR` maps a program's hard-coded hex to palette hex.

## product.py contract and CLI

`<project>/fixtures/tui/product.py`: `SHOTS = {scenario: () -> (Recording, [Still])}` and/or `CLIPS = {scenario: () -> (Recording, marks)}` (at least one), optional `prepare()`, `TRUECOLOR`, `NOTES = {scenario or "scenario/label": text}` (written as `notes` on entries). `Still(label, t, boxes={name: (row0, col0, row1, col1)})`, half-open. Label `clip` is reserved.

`uv run tuicap [scenarios...] [--clips] [--for video|blog|both] [--out DIR] [--draft] [--selftest]`. `--for` defaults from `<project>/project.json` like webcap. A CLIPS-only product with no `--clips` exits with "nothing to capture ... pass --clips". Scenario names are deduplicated; `--clips` and `--selftest` need ffmpeg (stills do not); `--selftest` renders a canned terminal into `captures/tui-selftest/`. A run replaces only the scenario's entries of the origin it captured. Output: `captures/tui/<scenario>/<label>.png`, `clip.mp4`, `clip.webm`, `clip.gif`, `clip.png`, and `captures/tui/manifest.json` with source "tui".
