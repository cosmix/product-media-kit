# Capture

The web and terminal captures serve both media: the edit places their clips and stills in the
video, the post links their stills and GIFs. Each capture engine loads one project module,
`product.py` in its folder, and writes `captures/<source>/<scenario>/` plus one manifest per
source. Read [README.md](../README.md), "Code that needs your product", "Reuse between media" and
"`claims.md` and `scenarios.md`" first: the scenarios to capture, their media and the fixture
story come from `scenarios.md`.

- [Web capture](#web-capture)
- [TUI capture](#tui-capture)
- [Manifests](#manifests)
- [Profiles](#profiles)

## Web capture

Owner: web capture. Folders: `fixtures/web/` to `captures/web/`.

The engine drives headless Chromium with Playwright. A page loads in the project's viewport and
colour scheme, with `LOCAL_STORAGE` set before the app reads it, and waits until the network is
idle and the web fonts have loaded. The viewport is one per project: 1920x1080 when `media` in
`project.json` includes the video, else 1440x900; `VIEWPORT` in `product.py` wins. Stills from
`SHOTS` are taken at device scale 2 in every profile (a 1920x1080 viewport gives a 3840x2160
PNG); clips follow the profile ([Profiles](#profiles)).

**Two ways to run the product.**

- **Mock**: `product.py` defines `World` and `build_app(world)`, an aiohttp mock of the product's
  server that serves the real built frontend (`PRODUCT_WEB_DIST`) and answers the API calls the
  frontend makes, from the frontend's own schema, with the fixture story as data. Pages load from
  it on a scripted clock, so every capture is the same on every run. The mock listens on
  `127.0.0.1:7373`. A live stream the UI shows can be scripted too: a terminal websocket can replay
  a coding-agent session built with `webcap.agent_session`, which redraws the way an Ink terminal
  UI does (sober text, a spinner, an input box), with `webcap.ansi` for its colours.
- **Live**: `product.py` sets `BASE_URL`, or the environment sets `PRODUCT_URL` (which wins), to a
  running instance. Pages load from it in real time; the page's own clock is still stepped for
  clips, but the server's data arrives as it comes. Use it when the product cannot be mocked in
  reasonable time, seed the instance with the fixture story first, and log in as a fixture
  account.

**The project's module** is `fixtures/web/product.py` (loaded by `webcap/project.py`). It
defines `SHOTS`, `CLIPS` or both:

| Name               | Required    | Meaning                                                                                                          |
| ------------------ | ----------- | ---------------------------------------------------------------------------------------------------------------- |
| `SHOTS`            | one of both | `{scenario: async def (shooter: webcap.shots.Shooter) -> None}`: the stills                                      |
| `CLIPS`            | one of both | `{scenario: async def (director: webcap.director.Director) -> None}`: one clip per scenario                     |
| `CLIP_PATHS`       | no          | `{scenario: "/path"}`: where each clip's page opens (default `/`)                                                |
| `World`            | mock mode   | a subclass of `webcap.world.World`, built with no arguments, with one scene (a `Clock`) per scenario             |
| `build_app(world)` | mock mode   | the aiohttp `web.Application`: the product's API routes, then `serve_dist(app, dist)`                            |
| `BASE_URL`         | live mode   | the running product's URL; env `PRODUCT_URL` wins                                                                |
| `VIEWPORT`         | no          | `(width, height)` in CSS px; default from `project.json` as above                                                |
| `THEME`            | no          | `"light"` or `"dark"`, the page's colour scheme, default `"light"`                                               |
| `LOCAL_STORAGE`    | no          | `{key: value}` written to the page's localStorage (as JSON) before every load, for a theme or a dismissed banner |
| `FONT_PROBES`      | no          | `(scenario, path, {label: CSS selector})`: the manifest's `fonts` key reports the font files each element used  |

Scenario and label names match `^[a-z0-9]+(-[a-z0-9]+)*$`. The label `clip` is reserved for the
scenario's clip, so a still named `clip` is an error.

**`Shooter`** (`webcap/shots.py`) takes a scenario's stills into
`captures/web/<scenario>/<label>.png`:

- `await shooter.goto(path="/")` loads a path from the mock or the live product.
- `await shooter.shot(label, *, selector=None, full_page=False, boxes=None)` takes the viewport,
  the whole page (`full_page=True`) or one element (`selector`), and records each box in `boxes`
  (`{box name: CSS selector}`) as `[x, y, w, h]` integer pixels of the image. A box partly
  outside the image is clipped to it; a box wholly outside it raises an error naming
  `<scenario>/<label>` and the box, and a selector that matches no visible element raises an
  error naming the scenario.
- `shooter.page` is the Playwright page, for clicks, typing and waits between shots;
  `shooter.world` is the mock's `World` (`None` in live mode).

CSS animations are disabled for a still. In mock mode the page's clock is paused at the scene's
start: timers, debounces and toasts stand still until the scenario advances them with
`await shooter.page.clock.run_for(ms)`. The mock's story stays at its first moment unless the
scenario calls `await shooter.world.tick(t)`.

**`Director`** (`webcap/director.py`) records a clip from the page `CLIP_PATHS` names. The engine
starts and finishes the recording around the scenario's function; every call advances whole
frames on a virtual clock, so motion is the same on every run and there is no frame-time jitter.
For each frame the mock's clock, the page's faked clock (timers, `requestAnimationFrame`, `Date`)
and every CSS animation advance to the same instant, then the frame is captured.

| Call                                            | What it does                                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `await hold(seconds)`                           | records frames with no input                                                                     |
| `await glide(x, y, seconds, arc=0.08)`          | an eased pointer move along a slight arc                                                         |
| `await click(count=1, hold=0.1, gap=0.12)`      | presses and releases at the pointer (seconds); marks a click or double-click                     |
| `await type(text, cps=13.0, jitter=0.35)`       | types at a human pace                                                                            |
| `await press(key)`                              | one key, such as `"Enter"`                                                                       |
| `await center(selector) -> (x, y)`              | the point to glide to                                                                            |
| `mark(event, key=False)`                        | an event at the clip's current time in the manifest entry; key marks are what the edit syncs to |
| `await still(label, boxes=None) -> dict`        | writes the current frame as `<scenario>/<label>.png` (origin `clip`), boxes measured on the page |

Attributes: `fps`, `scale`, `profile`, `t` (seconds of virtual time), `page`, `world`. A clip's
frame is `VIEWPORT` times the clip's scale, and both its sides must be even. Headless Chromium
draws no mouse pointer: under the video profile the manifest carries a per-frame cursor track and
the edit draws the pointer and the click on native select popups, which do not render headless;
a GIF for the post shows what the clicks and typing do, never the pointer. The director draws a
text caret on the virtual clock.

A skeleton in mock mode (`story.py` is the fixture story from `scenarios.md` as data; the routes
are your product's):

```python
import json

from aiohttp import web

import story
from webcap.server import no_store, require_env, serve_dist
from webcap.world import Clock, World as BaseWorld

THEME = "light"
LOCAL_STORAGE = {"<app>:sidebar": "open"}
SCENES = {
    "settings": Clock(((0.0, 0.0), (1.0, 1.0))),
    "overview": Clock(((0.0, 0.0), (20.0, 3200.0))),   # 20 clip seconds tell 3200 story seconds
}


class World(BaseWorld):
    def __init__(self):
        super().__init__(SCENES)                       # one scene per SHOTS and CLIPS scenario
        self.sockets = set()
        self.last = None

    async def tick(self, t):
        await super().tick(t)
        body = json.dumps(story.snapshot(self.story_s()))
        if body != self.last:                          # publish on change, as the real server does
            self.last = body
            for ws in list(self.sockets):
                await self.send(ws, body)              # send() counts messages; the director waits for each


def build_app(world):
    async def projects(_request):
        return no_store(web.json_response(story.PROJECTS))

    async def updates(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        world.sockets.add(ws)
        world.last = None                              # a new page gets the current state at once
        try:
            async for _ in ws:
                pass
        finally:
            world.sockets.discard(ws)
        return ws

    app = web.Application()
    app.router.add_get("/api/projects", projects)
    app.router.add_get("/api/updates", updates)
    serve_dist(app, require_env("PRODUCT_WEB_DIST", "point it at the product's built web frontend"))
    return app


async def settings(shooter):
    await shooter.goto("/projects/acme-api/settings")
    await shooter.page.click("text=Advanced")
    await shooter.page.clock.run_for(400)             # let the panel's transition timers run
    await shooter.shot("dialog", boxes={
        "dialog": "[role=dialog]",
        "name": "[role=dialog] input[name=name]",
        "save": "[role=dialog] button[type=submit]",
    })


async def overview(director):
    await director.hold(1.0)
    x, y = await director.center("<selector of what the narration or the prose names>")
    await director.glide(x, y, 0.8)
    await director.click()
    director.mark("dialog opens", key=True)
    await director.hold(2.5)
    await director.still("final", boxes={"dialog": "[role=dialog]"})


SHOTS = {"settings": settings}
CLIPS = {"overview": overview}
CLIP_PATHS = {"overview": "/projects/acme-api"}
```

`Clock` maps clip seconds to story seconds piecewise-linearly, so a clip can race through a long
run and then play at wall speed; its `epoch` sets the page's wall clock (dates and "x min ago"
labels). Override `World.set_scene` to reset the mock's state between scenarios. For live mode,
drop `World`, `build_app` and the clock calls, and set `BASE_URL` (or export `PRODUCT_URL`).

```bash
cd fixtures/web
export PRODUCT_WEB_DIST=/path/to/product/web/dist PRODUCT_REPO=/path/to/product
uv run python -m webcap.capture                           # every SHOTS scenario into captures/web/
uv run python -m webcap.capture settings                  # one scenario; the rest of the manifest stays
uv run python -m webcap.capture --clips                   # every SHOTS and every CLIPS scenario
uv run python -m webcap.capture overview --clips          # one clip
uv run python -m webcap.capture overview --clips --draft  # a quick scale-1 check (video and both)
uv run python -m webcap.capture --clips --for both        # clips for the video and the post at once
uv run python -m webcap.capture settings --out /tmp/try   # somewhere else, to look before replacing
uv run python -m webcap.verify                            # smoothness of the video clips
uv run python -m webcap.probe overview --out /tmp/p 0.5 3 8   # scale-1 screenshots at clip seconds
uv run python -m webcap.server --scene settings           # the mock on the wall clock at http://127.0.0.1:7373/
```

- `--for video|blog|both` picks the profile; without it the capture follows `project.json`:
  `both` for a project with both media, `video` for the video alone, else `blog`.
- `--draft` applies to the video and both profiles (scale 1, `ultrafast`, crf 23); with the blog
  profile it is a usage error.
- `--clips` needs ffmpeg with the profile's encoders (`libx264` for video, `libvpx-vp9` for blog,
  both for both) and otherwise stops with `--clips needs ffmpeg with <encoders>: <problem>`.
  Stills need no ffmpeg.
- `webcap.verify [--dir captures/web]` checks every clip that has a `video` file: frame-time
  jitter from the container timestamps, the share of frames that repeat their predecessor, and
  that share where the scripted cursor moved. It writes `smoothness` into each entry. Repeats are
  expected only where nothing on the page animates.
- `webcap.probe <scenario> [--path /] --out DIR <times...>` steps the page on the virtual clock as
  a clip does, without playing input, and writes `<scenario>-<t>.png` at scale 1: a cheap check of
  the mock's state at given clip seconds before recording.
- `webcap.server --scene <name> [--port 7373]` serves the mock on the wall clock for a look in a
  browser. Stop it before capturing: both use port 7373.

A full set of video clips took about 33 minutes in a finished project. Keep a table of scenarios
with media, labels, clip lengths and key marks in `HANDBOOK.md`.

**Faithfulness**: show only what the real UI renders. When it has a quirk (a counter that stays 0
during an event, a label that repeats a word), keep the real behaviour and tell the lead, who
decides whether the script or the post works around it, and record it as a bug in the product's
own tracker instead of faking it.

Lessons from finished projects:

| What went wrong                                                                                           | Rule                                                                                                                              |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| A selector stopped matching after a product change: `<scenario>: no visible element matches '<selector>'` | Prefer roles, labels and visible text (`[role=dialog]`, `text=Save`) over generated class names; recapture only that scenario    |
| In mock mode a toast or a debounced field never appeared in the still                                    | Advance the page's timers with `await shooter.page.clock.run_for(ms)` before the shot                                             |
| Mock mode stopped with `KeyError: no scene '<name>'`                                                      | Give `World` a `Clock` for every `SHOTS` and `CLIPS` scenario                                                                     |
| Capture failed to start because port 7373 was in use                                                      | Stop the live preview (`webcap.server`) or any other capture first                                                                |
| `box ... lies outside the WxH image` when shooting one element                                            | Boxes are measured on the shot's image: take the viewport and crop in `images.json` instead                                       |
| A post's GIF relied on seeing where the pointer went                                                      | Keep blog clips to visible changes (typing, a panel opening); show a click target as a highlighted still                          |

## TUI capture

Owner: TUI capture. Folders: `fixtures/tui/` to `captures/tui/`.

The real product binary runs in a pseudo-terminal at a fixed grid size; `pyte` interprets its
output; the screen at a given moment is drawn with skia in the mono font from `design.json` (or
the system monospace font), with box-drawing characters drawn as lines that join cleanly. The
cell size is fitted to the font, and bold and italic are synthesised, so any monospace font
works. Images are drawn at 2x density, and the manifest says `scale: 2.0`: a cell is 28 by 58 px
with 48 px of padding around the grid, so a 100-column terminal gives a 2896 px wide image. The
background and text colours come from `design.json`; the other terminal colours are softened ANSI
colours in `src/tuicap/palette.py`, and `TRUECOLOR` maps colours a program hard-codes onto them.
The captures part of the HANDBOOK "Brand" section says how close the terminal should stay to the
product's real theme.

**The project's module** is `fixtures/tui/product.py`, loaded by the `tuicap` command
(`src/tuicap/clips.py`). It defines `SHOTS`, `CLIPS` or both:

| Name        | Required    | Meaning                                                                                              |
| ----------- | ----------- | ---------------------------------------------------------------------------------------------------- |
| `SHOTS`     | one of both | `{scenario: function() -> (Recording, list[Still])}`                                                 |
| `CLIPS`     | one of both | `{scenario: function() -> (Recording, marks)}`, rendered as `<scenario>/clip` with `--clips`        |
| `prepare()` | no          | builds the fixture workspace; runs once before any scenario                                          |
| `TRUECOLOR` | no          | `{hex: palette hex}`, both six lower-case hex digits without `#`, for colours the program hard-codes |
| `NOTES`     | no          | `{scenario or "scenario/label": text}`, written to the manifest entry as `notes`                     |

`marks` is a list of `(t, event)`, `(t, event, key)` or `{"t": seconds, "event": name, "key": bool}`;
the manifest gets the dict form with `key` false unless given, as the web director writes them.

**`Still(label, t, boxes={})`** (`tuicap.shots`) is one PNG at `<scenario>/<label>.png`: the
screen as it is at `t` seconds into the recording (every output event at or before `t` is on
screen). `boxes` maps a box name to a half-open cell range `(row0, col0, row1, col1)`: rows
`row0` to `row1 - 1`, columns `col0` to `col1 - 1`, counted from 0. `tuicap` converts each to
`[x, y, w, h]` pixels in the manifest; a range outside the grid stops the run with an error. A
scenario's labels are unique and none is `clip`, and a box name follows the same rule as a
scenario or label name; each breach stops the run with an error.

A skeleton:

```python
import os
import subprocess
from pathlib import Path

from tuicap.capture import clean_env, prompt, record_pty, run_capture_output, synth_cli
from tuicap.render import Recording
from tuicap.shots import Still

HERE = Path(__file__).resolve().parent
BIN = os.environ.get("PRODUCT_BIN", "<product>")
HOME = HERE / "home"                     # scratch HOME holding fixture config
WS = HERE / "ws"                         # the fixture workspace
DROP = ("<PRODUCT>_",)                   # the product's own variables never reach a capture


def prepare():
    WS.mkdir(exist_ok=True)
    subprocess.run([BIN, "init", "acme-api"], cwd=WS, env=clean_env(HOME, drop=DROP), check=True)


def status():
    """A typed command and its real output, cut at a line boundary to fit the grid."""
    out = run_capture_output([BIN, "status"], WS, clean_env(HOME, drop=DROP), 100)
    return synth_cli(prompt("~/acme-api"), f"{BIN} status", out, 100, 24, seed=1)


def status_still():
    rec, _ = status()
    # row 0 holds the prompt and the command; the output starts on row 1
    return rec, [Still("main", rec.duration - 0.05, {"table": (1, 0, 9, 100)})]


def watch():
    """An interactive view, recorded live; keys are sent on a schedule."""
    events, inputs = record_pty([BIN, "watch"], WS, clean_env(HOME, drop=DROP), 120, 30,
                                [(3.0, b"j"), (3.6, b"\r"), (6.0, b"q")], total=6.5)
    return Recording(120, 30, events, 6.0, inputs)


SHOTS = {
    "status": status_still,
    "watch": lambda: (watch(), [Still("list", 2.8), Still("detail", 5.5, {"panel": (2, 60, 28, 120)})]),
}
CLIPS = {
    "status": status,
    "watch": lambda: (watch(), [{"t": 3.6, "event": "detail opens", "key": True}]),
}
```

Engine pieces:

- `tuicap.capture.record_pty(argv, cwd, env, cols, rows, actions, total)` records a program with
  timed keystrokes (`(seconds, bytes)`, or a callable run at that time).
- `tuicap.capture.run_capture_output(argv, cwd, env, cols)` runs a command in a pty so it colours,
  and returns its output.
- `tuicap.capture.synth_cli(prompt, command, output, cols, rows, seed, lead, tail)` builds a
  typed-command shot around real output, cut at a line boundary so it fits, and returns
  `(Recording, marks)`; `typing_schedule` gives human cadence.
- `tuicap.capture.clean_env(home, tz, drop)` builds the environment a capture runs in.
- `tuicap.render.Recording(cols, rows, events, duration, inputs, show_cursor=True)`: times are
  seconds from the start, negative for pre-roll. `render_still(rec, png, t)` draws one PNG;
  `render_recording(rec, out_dir, label, profile="blog", draft=False)` renders a clip in a
  profile; `cell_box(...)` converts a cell range to pixels.
- `tuicap.tmux_clip.tmux_server(socket, tmpdir, env, conf)` runs an isolated tmux server and
  `tuicap.tmux_clip.record_shell(...)` records an operator typing into a shell, for a shot inside
  tmux.

`SHOTS` and `CLIPS` functions run one after another (each records in real time); the rendering
then runs in parallel. A scenario in both runs its program twice, so its still and its clip come
from two recordings.

```bash
cd fixtures/tui
export PRODUCT_REPO=/path/to/product PRODUCT_BIN=/path/to/product/bin/<product>
uv run tuicap                       # every SHOTS scenario into captures/tui/
uv run tuicap status                # one scenario; the rest of the manifest stays
uv run tuicap --clips               # every SHOTS and every CLIPS scenario
uv run tuicap watch --clips         # one scenario's stills and clip
uv run tuicap --clips --for both    # clips for the video and the post at once
uv run tuicap --clips --draft       # a fast, lower quality mp4 for previews
uv run tuicap status --out /tmp/try
```

`--for` follows the same default as the web capture; `--draft` affects the mp4 only. Clips need
ffmpeg: `tuicap --clips` and `tuicap --selftest` exit with a message when it is not on PATH;
stills do not need it. A product that defines only `CLIPS` captures nothing without `--clips`, and
`tuicap` says so. Each run prints every file it wrote with its size.

Fonts: on Linux the fallback fonts for glyphs the mono font lacks (DejaVu Sans Mono, Noto Sans
Symbols2, Noto Sans Symbols, Noto Sans Math, Noto Color Emoji) are found by family through
fontconfig, wherever the distribution installs them; on macOS they are Menlo, Apple Symbols and
Apple Color Emoji from `/System/Library/Fonts/`. A missing fallback is skipped, and a glyph no
font has draws as the mono font's empty box.

Lessons that hold for any CLI:

- A TUI that talks to a daemon over a socket needs a stand-in daemon in `fixtures/tui/` that
  speaks the product's wire format and plays the fixture story; a real run would start real work.
- Build the fixture workspace with the product's real init command in `prepare()`. Run config UIs
  with `HOME` pointed at a scratch home.
- A tmux shot: isolate it with a `tmpdir` inside the fixture so the user's tmux is never touched,
  and keep that path short: a Unix socket path holds about 104-108 bytes, and `tmux_server`
  refuses a longer one.
- CLI shots run read-only commands against `PRODUCT_REPO`. Some commands refresh a cache there, a
  known side effect.
- A long output scrolls the interesting rows off the grid: `synth_cli` cuts at a line boundary to
  fit; raise `rows`, or show the part that matters with a box and a crop.
- A light brand background can make yellow and cyan terminal text hard to read: `colors.background`
  and `colors.text` are the terminal's, so check every terminal still and ask the human when it
  fails.

Keep a table of scenarios with media, grid sizes, labels and key times in `HANDBOOK.md`; note any
that exist but are unused.

## Manifests

Each source has one `captures/<source>/manifest.json`, written atomically. Paths are relative to
`captures/<source>/`; entries are sorted by id.

```text
captures/<source>/
├── manifest.json
└── <scenario>/
    ├── <label>.png                      a still
    └── clip.mp4, clip.webm, clip.gif, clip.png   the clip, in the files its profile wrote
```

```json
{"source": "web",
 "shots": [
   {"id": "settings/dialog", "kind": "still", "origin": "shots", "file": "settings/dialog.png",
    "width": 3840, "height": 2160, "scale": 2.0, "boxes": {"save": [3112, 1904, 220, 88]}},
   {"id": "overview/clip", "kind": "clip", "origin": "clip", "file": "overview/clip.gif",
    "webm": "overview/clip.webm", "poster": "overview/clip.png", "video": "overview/clip.mp4",
    "width": 3840, "height": 2160, "scale": 2.0, "fps": 30, "duration": 4.5, "boxes": {},
    "marks": [{"t": 1.2, "event": "dialog opens", "key": true}],
    "cursor": [{"t": 0.0, "x": 100, "y": 200, "down": false}], "cursor_space": "css-1920x1080"}]}
```

| Key                                   | In                       | Meaning                                                                                                   |
| ------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------- |
| `id`                                  | every entry              | `<scenario>/<label>`; a clip's label is `clip`. The post's `shot:` references and the edit's keys use it |
| `kind`                                | every entry              | `still` or `clip`                                                                                         |
| `origin`                              | every entry              | `shots` (from `SHOTS`) or `clip` (the clip and the stills its director took)                             |
| `file`                                | every entry              | a still's PNG; a clip's GIF when the blog or both profile ran, else its poster PNG                        |
| `width`, `height`, `scale`            | every entry              | the image's pixel size and its device scale; the size in CSS px or cells is pixels / `scale`              |
| `boxes`                               | every entry              | `{name: [x, y, w, h]}` in integer pixels of the image                                                     |
| `poster`, `duration`, `marks`         | clip                     | the last frame as PNG; seconds; `[{t, event, key}]`                                                       |
| `webm`                                | clip, blog or both       | the VP9 WebM beside the GIF                                                                               |
| `video`, `fps`                        | clip, video or both      | the H.264 mp4 the edit uses, and its frame rate                                                           |
| `cursor`, `cursor_space`              | web clip, video or both  | the per-frame pointer track in CSS px of the viewport, for the edit to draw                               |
| `grid`, `cell_px`, `padding_px`       | TUI clip, video or both  | the terminal's columns and rows, the cell size and the padding, for the edit to frame the terminal        |
| `notes`                               | TUI, when `NOTES` names it | free text from `product.py`                                                                             |
| `fonts`                               | web, with `FONT_PROBES`  | the font files each probed element rendered with                                                          |
| `smoothness`                          | web clip with `video`    | written by `webcap.verify`                                                                                |

A clip entry's `width` and `height` are the size of the recorded frames (the mp4, or the blog
profile's WebM, and the poster), never of the GIF, which is at most 960 px wide, or of the `both`
profile's half-size WebM. `grid` is a string, `"<cols>x<rows>"`.

**Merging.** A run rewrites only the scenarios it captured, and within a scenario only the
origin it ran: a stills-only run keeps the scenario's clip and the stills its director took, and a
clips run keeps its `SHOTS` stills. The edit and postkit read entries by id, so recapturing one
scenario changes nothing else.

**Sources.** `web` and `tui` are written by the capture engines; `motion`, `broll` and `video` by
`postkit add`, which brings a PNG, a video frame or a segment into
`captures/<source>/<scenario>/<label>.*` with scale 1 and no boxes ([blog.md](blog.md),
"`postkit add`").

**References into a manifest.**

| Who  | Reference                         | Resolves to                                                                       |
| ---- | --------------------------------- | --------------------------------------------------------------------------------- |
| edit | `web:<scenario>`, `tui:<scenario>` | `captures/<source>/<scenario>/clip.mp4`, else `clip.webm` with a printed warning |
| edit | `still:<source>/<scenario>/<label>` | `captures/<source>/<scenario>/<label>.png`                                     |
| post | `shot:<source>/<scenario>/<label>`  | the entry with that id: its PNG, or for a clip its GIF and WebM                |

## Profiles

A profile decides how a clip is recorded and which files it gets. Stills from `SHOTS` are the same
in every profile (web scale 2, TUI 2x density).

| Profile | Scale | FPS     | Files                                                                                                         |
| ------- | ----- | ------- | ------------------------------------------------------------------------------------------------------------- |
| `blog`  | 1     | 30      | `clip.webm` (VP9), `clip.gif` (15 fps, at most 960 px wide), `clip.png` poster                                |
| `video` | 2     | project | `clip.mp4` (H.264 crf 10, yuv420p, bt709), `clip.png` poster, the cursor track (web) or grid (TUI)            |
| `both`  | 2     | project | records once as `video`, then derives the WebM (30 fps, half size) and the GIF from the mp4; full-size poster |

"project" is `project.json` `fps`, the video's frame rate (default 30, set with `./configure.sh`).
The `both` profile's WebM is resampled to 30 fps only when that rate differs.

- **Default**: `--for` from `project.json` `media`: video and blog give `both`, video alone
  `video`, anything else `blog`.
- **`--draft`** (video and both): scale 1, `ultrafast`, crf 23, for a quick look at the
  choreography. A draft clip is never the one the edit's master uses: recapture without it.
- **Encoders**: `video` needs ffmpeg's `libx264`, `blog` its `libvpx-vp9`, `both` both. The
  self-tests skip their clip with a note when the encoder is missing; a real `--clips` run stops.
- **Adding a medium**: a clip captured under one profile lacks the other medium's files. Recapture
  it with `--for both`; the stills need nothing.
