# Testing the kit on macOS

This kit was built and tested on Linux. It has since been changed to run on macOS (Apple Silicon and
Intel), but nobody has run it on a Mac yet: the Mac code paths were checked against library docs and
source, and by faking the platform on Linux. Your job is to run it on a real Mac, find what breaks,
and report back. Work through the checks below in order: each one depends on the ones before it.

This file lives in the kit's `doc/`, which `install.sh` does not copy into projects. Delete it once
the Mac port is confirmed.

## What changed for macOS

Every per-OS choice in the edit lives in `edit/editkit/hw.py`. Elsewhere the code branches on
`sys.platform == "darwin"` (Python) or `uname -s` (shell).

| Area                                 | Linux                                                                                             | macOS                                                                             | Where                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Edit GL context                      | headless EGL, OpenGL 4.1+                                                                         | CGL (moderngl default), OpenGL 4.1 core                                           | `edit/editkit/hw.py`, `edit/editkit/gpu.py`                                           |
| Edit shaders                         | `#version 410`                                                                                    | same                                                                              | `edit/editkit/shaders/*.vert`, `gpu.py` header                                        |
| Motion GL + Skia                     | EGL context, `GrGLInterface.MakeEGL()`                                                            | CGL context (`require=330`), `GrDirectContext.MakeGL()` with the native interface | `motion/lib/gfx.py`                                                                   |
| Decode                               | `-hwaccel cuda`, `scale_cuda` when a probe shows CUDA decode works, else CPU decode and `scale`   | `-hwaccel videotoolbox`, CPU `scale`                                              | `hwaccel()` in `hw.py`, `edit/editkit/decode.py`                                      |
| Fast encode (previews, placeholders) | `h264_nvenc` when a test encode works                                                             | `h264_videotoolbox -b:v 20M` when a test encode works                             | `fast_h264()` in `hw.py`; used by `edit/render.py`, `edit/editkit/assets.py`          |
| Encode fallback                      | `libx264 -preset veryfast` when the hardware encoder is missing or fails                          | same                                                                              | `fast_h264()`                                                                         |
| Design fonts                         | `design.json` paths, else DejaVu Sans and DejaVu Sans Mono (`fc-match`, then `/usr/share/fonts/`) | `design.json` paths, else `/System/Library/Fonts/Helvetica.ttc` and `Menlo.ttc`   | `edit/editkit/design.py`, `motion/lib/design.py`, `fixtures/tui/src/tuicap/design.py` |
| Logo                                 | Skia SVG module (`skia.SVGDOM`) or `skia.Image` for PNG                                           | same                                                                              | `motion/lib/logo.py`                                                                  |
| TUI fallback fonts                   | DejaVu Sans Mono, Noto Sans Symbols2, Noto Sans Symbols, Noto Sans Math, Noto Color Emoji, by family through fontconfig | Menlo, Apple Symbols, Apple Color Emoji, by path in `/System/Library/Fonts/` | `fixtures/tui/src/tuicap/fonts.py`                                         |
| TUI locale                           | `C.UTF-8`                                                                                         | `en_US.UTF-8`                                                                     | `fixtures/tui/src/tuicap/capture.py`                                                  |
| Setup hints                          | apt, dnf                                                                                          | brew                                                                              | `setup.sh`, `system-deps.sh`                                                          |
| `install.sh` path resolution         | `abspath()` function (macOS has no `realpath -m`)                                                 | same                                                                              | `install.sh`                                                                          |
| Play audio                           | `aplay`, `ffplay`                                                                                 | `afplay`                                                                          | `.claude/skills/narration/SKILL.md`                                                   |

Other changes:

- A missing TUI fallback or emoji font is skipped instead of crashing the render.
- `edit/` pins onnxruntime per platform: Intel Macs get 1.23.2 (the last release with Intel Mac
  wheels), every other platform gets 1.30.0.
- The shell scripts are meant to run under macOS's stock `/bin/bash` 3.2; they were tested under a
  bash 3.2.57 built on Linux.
- Music workers start with `spawn` on macOS (the default there). A Linux run forced to `spawn`
  completed, so this should work.

## Known limits

- **macOS version.** `edit/` on Apple Silicon needs macOS 14 or later: `av==19.0.0` has no older
  arm64 wheel. Everything else has wheels from macOS 12.
- **Speed.** No NVENC or CUDA on a Mac: previews encode through VideoToolbox, and decoded frames are
  scaled on the CPU. Expect slower renders than on the Linux machine (an NVIDIA GPU).
- **Edit previews from a bare kit.** `edit/render.py` needs the project's `edit/edl.py` and
  `narration/timeline.json`; in a fresh install it stops with a message naming the missing file.
  Check 4 drives the compositor directly instead.

## Checks

Record for each check: the command, pass or fail, the full error text on failure, and how long it
took. Do not fix failures before writing them down.

### 1. Install and setup

```bash
./install.sh ~/x-media               # copies the kit, then system-deps.sh installs Homebrew packages
cd ~/x-media                         # (open a new terminal first if Homebrew or uv was just installed)
/bin/bash --version | head -n 1      # expect 3.2.x: the scripts must work with it
./setup.sh --check                   # reports only; changes nothing; media empty, so everything
./setup.sh                           # downloads VSCO (about 2.2 GB), Chromium, the Whisper model
./setup.sh --check
./setup.sh --check --for blog        # the blog's scope: no GPU section, ffmpeg a WARN at most
```

Run the full `./setup.sh`: `--no-samples` skips the sample libraries, and check 5 needs them.

Pass when the last full `--check` shows 0 MISSING (the Gemini API key is a WARN line when it is not
set) and:

- both GPU lines (edit compositor, motion graphics) name an Apple, AMD or Intel renderer;
- `ffmpeg encoder h264_videotoolbox` is ok, and there is no `libvpx-vp9` WARN;
- the "Fonts" section shows `ok design.json absent: system fonts and neutral colours in use` (or
  `fonts and colours valid` if the project has a `design.json`), `ok system fonts Helvetica,
  Menlo`, and `fallback fonts` ok;
- the "Brand" section shows `ok BRAND.md` or `WARN BRAND.md optional: run the brand skill in
  Claude Code to create it`, and no MISSING;
- the "Claude Code skills" section is ok for `brand`, `narration` and `begin`;
- every Python environment synced, `post` included (look for wheel or build errors in the
  `./setup.sh` output);
- `--for blog` prints no "GPU (OpenGL)", "Sample libraries" or "Whisper model" section.

Also check that `./setup.sh` ran with no bash syntax errors (`bad substitution`, `syntax error near
unexpected token`): either one means a bash 4 feature slipped in.

### 2. Motion graphics

The riskiest check: Skia's GL context on top of moderngl's CGL context has only been checked
against the docs.

```bash
cd ~/x-media/motion
uv run python render.py --selftest
```

The self-test draws a text card, a circle, a rounded square and a hairline on the plain background
(and the logo, if `design.json` names one), then writes `out/selftest_01.50.png`,
`out/selftest_contact.png` and a 2 s clip `out/selftest.mp4`. It prints `GL_RENDERER` first. Pass
when the still looks right (text in Helvetica, white on black without a `design.json`; no blank
frame) and the clip is 1920x1080 H.264 with 60 frames (2 s at the default 30 fps; 120 with `project.json` `fps` 60):

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,pix_fmt,nb_frames -of compact out/selftest.mp4
```

If Skia's context fails, `gfx.py` raises a clear error naming it; report that text.

### 3. Edit compositor and fonts

```bash
cd ~/x-media/edit
uv run bg_test.py 1
```

Pass when it writes `out/bg_test.mp4` (H.264) with no GL or shader compile errors, and a frame shows
a browser-chrome window titled "edit self-test" around a placeholder, its text in Helvetica.

### 4. Edit preview through VideoToolbox

Exercises VideoToolbox decode, CPU scaling, placeholder encoding (`assets.py`) and the fast encode
(`render.py`).

```bash
cd ~/x-media/edit
mkdir -p out && uv run python -c "from pathlib import Path; from editkit.compositor import PREVIEW, Compositor; from editkit.scene import Timeline, Segment, Plane; from render import encoder; c = Compositor(Timeline(2.0, [Segment('a', 0.0, [Plane('web:demo', 0.0, 2.0, chrome='browser', scale=0.5)])]), PREVIEW); e = encoder(Path('out/mac_preview.mp4'), PREVIEW, 0, 2, None, fast=True); [e.stdin.write(c.render(i / PREVIEW.fps)) for i in range(60)]; e.stdin.close(); print(e.wait())"
ffprobe -v error -show_entries stream=codec_name,profile,width,height,nb_frames -of compact out/mac_preview.mp4
```

Pass when it prints `0`, the file is H.264 with 60 frames, and the frames show the placeholder in a
browser frame. On an Intel Mac, watch for VideoToolbox rejecting `-profile:v high` (open question
below).

### 5. Music

```bash
cd ~/x-media/music
uv run render.py --selftest
```

The self-test renders eight bars of synthesized C major (no samples) to `out/selftest/`. Pass when
it reports loudness and note count; on the Linux reference it gave -16.0 LUFS integrated, true peak
-2.76 dBTP and 104 notes. The sampled instruments and the worker processes (`spawn` on macOS) run
only with a project score: if one exists, also run `uv run render.py` and check for a worker crash
or pickling error.

### 6. TUI capture and its fallback fonts

Checks that Menlo (the mono font when `design.json` names none, and the first fallback), Apple
Symbols and Apple Color Emoji are found and render; the `.ttc` collections load through Skia.

```bash
cd ~/x-media/fixtures/tui
uv run python -c "from tuicap.fonts import fallback_fonts, emoji_font; print(fallback_fonts(), emoji_font())"
uv run tuicap --selftest --for both
uv run python -c "
from pathlib import Path
from tuicap.render import Recording, render_still
render_still(Recording(20, 2, [(0.0, 'ok ✓ ⣿ \U0001f600'.encode())], 0.2, [], False), Path('/tmp/t.png'), 0.1)
"
open /tmp/t.png captures/tui-selftest/selftest/screen.png
```

Pass when:

- the first command prints `/System/Library/Fonts/Menlo.ttc`, `/System/Library/Fonts/Apple
  Symbols.ttf` and `/System/Library/Fonts/Apple Color Emoji.ttc`, and each exists;
- the self-test writes `captures/tui-selftest/selftest/screen.png`, `clip.mp4`, `clip.webm`,
  `clip.gif` and `clip.png`, and `captures/tui-selftest/manifest.json` says `"scale": 2.0`;
- `/tmp/t.png` shows `ok`, the check mark, the braille block and a colour emoji, with no tofu boxes;
  the self-test's still shows its box-drawing, block and braille characters joined cleanly.

### 7. Web capture

```bash
cd ~/x-media/fixtures/web
uv run python -c "
import asyncio
from playwright.async_api import async_playwright
from webcap.browser import ARGS
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True, args=ARGS)
        p = await b.new_page(); await p.set_content('<h1>ok</h1>'); await p.screenshot(path='/tmp/w.png')
        await b.close()
asyncio.run(main())
"
open /tmp/w.png
uv run python -m webcap.capture --selftest --for both
open captures/web-selftest/selftest/page.png
```

The second command checks the stills and both clip encoders at once. Pass when Chromium starts
headless, `/tmp/w.png` shows "ok", and the self-test ends with `selftest ok (both profile)` and
writes `captures/web-selftest/selftest/page.png` at 1920x1200 (the 960x600 test page at scale 2)
with sharp text, plus `clip.mp4`, `clip.webm`, `clip.gif`, `clip.png` and the director's still
`typed.png`. Report any GPU or ANGLE errors from Chromium verbatim. If the project already has
`fixtures/web/product.py`, also capture one clip at draft quality:
`uv run python -m webcap.capture <scenario> --clips --draft`.

### 8. Narration skill playback

```bash
afplay <any .wav from narration/>
```

Only checks that the documented playback command works on the Mac.

### 9. Brand files and the logo

Checks the brand checker and the logo through Skia's SVG module on the Mac. It adds minimal brand
files to the test project and removes them at the end:

```bash
cd ~/x-media
cp .claude/skills/brand/BRAND.template.md BRAND.md
mkdir -p brand/logo brand/fonts brand/palette brand/reference
cat > brand/logo/test-on-dark.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="10" y="10" width="180" height="180" rx="24" fill="white"/>
  <circle cx="300" cy="100" r="80" fill="none" stroke="white" stroke-width="20"/>
</svg>
SVG
printf '{ "logo": { "on_dark": "brand/logo/test-on-dark.svg" } }\n' > design.json
uv run .claude/skills/brand/check.py
./setup.sh --check                               # the "Brand" section
(cd motion && uv run python render.py --selftest && open out/selftest_01.50.png)
rm -r BRAND.md brand design.json                 # back to the neutral defaults
```

Pass when `check.py` prints no MISSING (WARN lines for the empty `brand/fonts` and
`brand/reference` folders are expected) and exits 0, `setup.sh --check` prints `ok logo <path>` in
its "Brand" section, and the still shows the white rounded square and ring of the test logo, sharp
and the right way up, under the self-test card. If the logo is missing or garbled, report the
`check.py` output and any error from `render.py` verbatim.

### 10. postkit

Checks the blog engine: Pillow's image treatment and fonts, and `postkit add` through Homebrew's
ffmpeg. Needs check 2's `motion/out/selftest.mp4` and `selftest_01.50.png`.

```bash
cd ~/x-media/post
uv run postkit selftest
uv run postkit add motion/selftest/still ../motion/out/selftest_01.50.png
uv run postkit add motion/selftest/frame ../motion/out/selftest.mp4 --at 1.0
uv run postkit add motion/selftest/loop ../motion/out/selftest.mp4 --from 0.2 --to 1.8
open ../captures/motion/selftest/frame.png ../captures/motion/selftest/loop.gif
rm -r ../captures/motion                         # back to an empty project
```

Pass when the self-test ends with `selftest: ok`, the three adds exit 0, `captures/motion/` holds
`still.png`, `frame.png`, `loop.gif`, `loop.webm` and `loop.png`, `captures/motion/manifest.json`
lists `selftest/still`, `selftest/frame` and `selftest/loop` with `"scale": 1.0`, and the frame and
the GIF show the self-test card. `postkit selftest` deletes its folder, so it checks the treatment
but leaves nothing to look at.

postkit finds its callout font through `design.json`, else `fc-match "DejaVu Sans:bold"`, else
Pillow's built-in font. A Mac without fontconfig and without a `design.json` bold font takes the
last; see the open questions.

## Open questions only a Mac can answer

- Does `h264_videotoolbox` accept `-profile:v high` on Intel Macs? (check 4)
- Does Chromium start with `--use-angle=swiftshader` on macOS? (check 7)
- Do skia and PIL load `Helvetica.ttc` and `Menlo.ttc` (index 0) as the default fonts? (checks 2,
  3 and 6)
- Does Skia's SVG module on macOS draw the test logo the same as on Linux? (check 9)
- Do postkit's callout numbers look acceptable in Pillow's built-in font, or does postkit need a
  macOS fallback such as `/System/Library/Fonts/Helvetica.ttc`? Build a post with a callout to see
  one. (check 10)
- Does the product's CLI behave under `en_US.UTF-8`? (a real TUI capture, once the project has one)
- How long does each check take compared with Linux? Rough numbers are enough.

## What to report back

1. macOS version, chip (`uname -m`), and `sw_vers` output.
2. The final `./setup.sh --check` output in full.
3. For each check: pass or fail, the error text verbatim, the duration.
4. Answers to the open questions.
5. Every file you changed to get past a failure, with the reason. Keep fixes small and inside the
   file that failed; on Linux the output must stay pixel-identical, so any change to the GPU,
   decode or encode code must keep the Linux branch as it is.

## CPU-only machines (Linux without a GPU)

The same checks apply to a Linux machine or VM with no GPU (a CPU-only Proxmox VM has been tested):
headless EGL then opens Mesa's llvmpipe, which renders on the CPU. `./setup.sh` reports both GPU
lines as WARN ("CPU rendering: much slower") instead of ok; if the context does not open at all,
Mesa is missing: rerun `./system-deps.sh`. Previews encode with libx264 and sources decode on the
CPU.

To try CPU rendering on a machine that has an NVIDIA GPU, point glvnd at Mesa and ask Mesa for
software rendering:

```bash
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json LIBGL_ALWAYS_SOFTWARE=1
```
