# Webcap

> webcap modules, profiles, product.py contract, mock and live modes, Director, manifest

## webcap module map

Package `fixtures/web/webcap/` (run from `fixtures/web` with `uv run python -m <module>`; no console script):
- `names.py`: `NAME_RE` (`^[a-z0-9]+(-[a-z0-9]+)*$`) and `check_name(kind, value)` for scenarios, labels and box names.
- `profiles.py`: `NAMES = ("video", "blog", "both")`, `STILL_SCALE = 2.0`, frozen `Profile(name, scale, fps, draft)` with `.video`, `.blog`, `.encoders`; `profile(name, draft)`.
- `encode.py`: the ffmpeg commands (`mp4_command`, `webm_command`, `derived_webm_command`, `gif_command`), `check_frame_size`, `ffmpeg_problem(profile)`; `setparams` bt709 filter (see [mistakes/media-kit-merge](../mistakes/media-kit-merge.md)).
- `project.py`: `product()` imports `<project>/fixtures/web/product.py`, runs `mode()` and `check_names()`; `media()`, `default_profile()`, `viewport(module)` read `<project>/project.json`; a `ProjectError` becomes a one-line `SystemExit`. `base_url(module)` is env `PRODUCT_URL` (wins), else `BASE_URL`.
- `world.py`: `EPOCH`, frozen `Clock`, `World(scenes)` with `set_scene`, `async tick(t)`, `async send(ws, data)`.
- `server.py`: `PORT = 7373`, `require_env(name, what)`, `serve_dist(app, dist)`, a preview `main` (`--scene`, `--port`).
- `browser.py`: `context_options` (VIEWPORT, THEME, reduced motion), `session(module)`, `open_page(...)`; `page_script.py` holds `INIT_SCRIPT`.
- `shots.py` (`Shooter`), `boxes.py` (`pixel_box`, `pixel_boxes`), `director.py` (`Director`, `Clip`), `manifest.py` (`update`, `annotate`), `capture.py` (`run`, `run_selftest`, `main`), `selftest.py` (built-in page).
- Kept libraries and tools: `agent_session.py` and `ansi.py` (scripted coding-agent terminal pane for a product that shows one), `probe.py` (`python -m webcap.probe <scenario> --out DIR <times...>`: scale 1 stills at clip times to check choreography, over `open_page`), `verify.py` (`python -m webcap.verify`: smoothness of every clip with a `video` file, written into the entry; video and both only).

## Profiles and CLI

`uv run python -m webcap.capture [scenarios...] [--clips] [--for video|blog|both] [--draft] [--out DIR] [--selftest]`. Default `--for` comes from `project.json` `media` (video and blog: both; video: video; else blog). `--draft` (video and both only; blog is a usage error) means scale 1, ultrafast, crf 23. `--clips` without an ffmpeg that has the profile's encoders exits naming them (video libx264, blog libvpx-vp9, both needs both). `--selftest` accepts only `--out`, `--for`, `--draft`, writes `captures/web-selftest/` and skips its clip with a stderr note when ffmpeg lacks an encoder.

| Profile | Scale | FPS | Clip files |
| --- | --- | --- | --- |
| `blog` | 1 | 30 | `clip.webm` (VP9), `clip.gif` (15 fps, max 960 px), `clip.png` poster |
| `video` | 2 | 60 | `clip.mp4` (H.264 crf 10, yuv420p, bt709), poster, cursor track |
| `both` | 2 | 60 | recorded once as video; WebM (30 fps, half size) and GIF derived from the mp4 |

SHOTS stills are scale 2.0 in every profile.

## product.py contract

`<project>/fixtures/web/product.py`: `SHOTS = {scenario: async def (shooter)}` and/or `CLIPS = {scenario: async def (director)}` (at least one), `CLIP_PATHS = {scenario: "/path"}`. Optional `VIEWPORT` ((w, h) CSS px; default 1920x1080 when `media` includes video, else 1440x900), `THEME` ("light" or "dark"), `LOCAL_STORAGE`, `FONT_PROBES`. The label `clip` is reserved. Two modes, picked by `project.mode()`:
- live: `BASE_URL` or env `PRODUCT_URL` names a running product; `world` is None and pages run in real time.
- mock: `World` (built with no arguments, one scene per scenario) and `build_app(world)`; the mock's WebSocket handler sends through `World.send`, and the app ends with `serve_dist(app, require_env("PRODUCT_WEB_DIST", ...))`.

Mock gotchas: `open_page` calls `world.set_scene(scenario)`, so a scenario without a World scene raises `KeyError`; the page clock is installed and paused, so a `setTimeout(100)` fires only after `shooter.page.clock.run_for(ms)`, and the world stays near clip time 0 unless the scenario ticks it.

## Shooter and Director

`Shooter.goto(path)` and `shot(label, *, selector=None, full_page=False, boxes=None)` write `<out>/<scenario>/<label>.png` through a temp file and return the manifest entry (origin `shots`); a box partly outside the image is clipped, wholly outside raises `ValueError` naming `<scenario>/<label>`.

`Director` steps one virtual frame at a time (1/fps): `step()` ticks the world (mock only), waits until the page has received every message sent (`window.__rx` against `world.sent`), advances the page clock, plays the frame's input, runs `__frame()` and takes a CDP screenshot. Nothing depends on screenshot time. Choreography: `hold`, `glide`, `click` (seconds), `type`, `press`, `center`, `mark(event, key=False)`, `still(label, boxes)` (a still taken inside a clip, origin `clip`). Headless Chromium draws no pointer; the video profile records a per-frame cursor track (`cursor`, `cursor_space`) the edit draws.

## Manifest

`manifest.update(out_dir, source, scenario, entries, origins=ORIGINS)` replaces the scenario's entries whose origin is in `origins` and keeps every other origin and scenario; it rejects a stray or duplicate id and entries with a foreign origin, and writes atomically. Contract and fields: [architecture/outputs-and-reuse](outputs-and-reuse.md).
