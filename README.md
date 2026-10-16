# Product Media Kit

Humans start with [HUMAN.md](HUMAN.md); agents start with `CLAUDE.md`.

This kit makes media about a piece of software from its code: a two-to-three-minute intro or demo
video, a blog post, or both. A team of Claude Code agents does the work while one human reviews
and steers. Nothing is edited by hand in a video editor or an image editor; every frame and every
image comes from code that can be re-run. Whatever one medium produced (captures, the fixture
world, motion stills, logo renders, the verified claims, the fixture story, b-roll) is reused by
the other.

The kit is the engine and these guides. It holds no video and no post: the script, the score, the
scenes, the capture choreography, the edit decision list, the outline, the draft and the image
treatment are code and data the team writes for your product, each against a small interface the
engine loads. [Engine and project files](#engine-and-project-files) separates the engine from the
files a project writes. Each engine has a self-test that runs with no project files.

The guides:

| File                                     | What it holds                                                                                                               |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `README.md` (this file)                  | what both media share: setup, the team, kickoff, reuse, the folder map, outputs, brand, design, editorial rules, records     |
| [`guides/capture.md`](guides/capture.md) | web and terminal capture, manifests and capture profiles, used by both media                                                |
| [`guides/video.md`](guides/video.md)     | the video: roles, phases, narration, music, motion graphics, b-roll, the edit, the mix, subtitles, encoding, video QA       |
| [`guides/blog.md`](guides/blog.md)       | the blog post: roles, phases, the draft, image treatment, building and checking, blog QA                                    |
| [`HUMAN.md`](HUMAN.md)                   | the human's guide                                                                                                           |
| `CLAUDE.md`                              | the project instructions every agent session loads (`claude-project.md` in the kit)                                         |

## Contents

- [What you make](#what-you-make)
  - [The stack](#the-stack)
- [How the kit is used](#how-the-kit-is-used)
- [Requirements](#requirements)
- [Setup](#setup)
  - [Install into a project](#install-into-a-project)
  - [System packages](#system-packages)
  - [Self-tests](#self-tests)
  - [Running on macOS](#running-on-macos)
  - [Sharing a project](#sharing-a-project)
- [The team](#the-team)
  - [Rules that make the team work](#rules-that-make-the-team-work)
  - [Good briefs](#good-briefs)
- [Kickoff](#kickoff)
- [Reuse between media](#reuse-between-media)
- [Pipeline and folder map](#pipeline-and-folder-map)
- [Engine and project files](#engine-and-project-files)
- [Code that needs your product](#code-that-needs-your-product)
- [Outputs](#outputs)
- [Brand](#brand)
  - [`BRAND.md` and `brand/`](#brandmd-and-brand)
  - [The brand skill](#the-brand-skill)
  - [The checker](#the-checker)
- [Design system](#design-system)
  - [`design.json`](#designjson)
  - [Fonts by family](#fonts-by-family)
  - [Who reads what](#who-reads-what)
  - [Legibility](#legibility)
- [Editorial rules](#editorial-rules)
- [Project records](#project-records)
  - [`NOTES.md`: the decision log](#notesmd-the-decision-log)
  - [`HANDBOOK.md`: the project's own handbook](#handbookmd-the-projects-own-handbook)
  - [Rejected styles](#rejected-styles)
  - [`claims.md` and `scenarios.md`](#claimsmd-and-scenariosmd)
- [Mistakes and pitfalls](#mistakes-and-pitfalls)
- [Licences and credits](#licences-and-credits)

## What you make

**A video** of two to three minutes at 1920x1080 and the project's frame rate (30 fps by default)
([guides/video.md](guides/video.md)):

- a narrator (Gemini TTS) reading a script the human and the lead agent write together;
- an original score composed as Python code and rendered from free sample libraries;
- motion graphics drawn with skia-python on the GPU, including the product's logo from its SVG or
  PNG;
- real captures of the product: its web UI (the real built frontend, driven by a mock server with
  fixture data or a running instance), its terminal UIs (the real binary in a pseudo-terminal) and
  real CLI output;
- b-roll generated with Gemini Omni;
- a GPU compositor in Python (moderngl) that places everything on 3D planes with window chrome,
  depth of field, motion blur and grading, mixes the audio, and writes subtitles and credits.

Narration, the score and b-roll are each optional, chosen at kickoff. With none of the three the
video is motion graphics and captures over sound design.

**A blog post**, by default 1,200 to 1,800 words, in plain GitHub-flavoured markdown
([guides/blog.md](guides/blog.md)):

- the post, with YAML front matter when the site that publishes it needs some;
- every image it links, by relative path: PNG stills of the product's web UI and terminal, and
  optional short clips (a GIF the post links, a WebM of the same clip beside it), each still
  cropped, outlined, numbered and framed as the post needs;
- optionally stills and clips taken from the video: motion graphics, b-roll, frames of the
  finished cut.

Both media are accurate because every claim is checked against the product's code, and their
images agree because every capture shows the same fixture story.

### The stack

What both media use; each medium guide lists its own tools.

| Need             | Tool                                                                                            |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| Team             | Claude Code: one lead session plus named teammates that message each other                      |
| Kickoff          | the `mediatime` skill: machine check, interview, brand, records                                 |
| Web UI capture   | Playwright (headless Chromium) with an aiohttp mock of the product's server, or a live URL      |
| Terminal capture | the real CLI in a pty (`ptyprocess`), `pyte` as the terminal emulator, skia to draw each screen |
| Clips            | deterministic frame stepping, then ffmpeg (H.264 for the video, VP9 WebM and GIF for the post)  |
| Brand            | the `brand` skill: `BRAND.md` and `brand/` to `design.json`, checked by `check.py`              |
| Environments     | one `uv` project per engine                                                                     |

## How the kit is used

One kit serves many projects. The kit folder holds the engine, the guides, `HUMAN.md`, the
project instructions (`claude-project.md`) and the Claude Code skills; nobody works inside it.
For each project:

1. The human runs `./install.sh <project-dir>` from the kit folder. It creates the project
   folder with the engine, the guides, `CLAUDE.md` (from `claude-project.md`), `project.json`
   and the skills in `.claude/skills/` ([Install into a project](#install-into-a-project)). It
   refuses a target inside the kit folder.
2. The human starts `claude` in the project folder and types `/mediatime`. The lead session
   checks the machine, asks which media to make and the rest ([Kickoff](#kickoff)).
3. All the work happens in the project folder: the brand files, the records, the script or the
   outline, the captures, the edit, the draft and every render and build.

**`project.json`** names the project, its media and the video's two saved choices:

```json
{"slug": "acme-launch", "media": ["video", "blog"], "fps": 30, "piano": "vsco"}
```

`install.sh` writes it once, when absent, with `slug` and an empty `media`. The slug comes from
the folder's name: lowercased, every run of other characters turned into one hyphen, `project`
when nothing is left (`My_Post` gives `my-post`); the install prints a note when it differs from
the name. The slug names every deliverable ([Outputs](#outputs)). `media` is an ordered subset of
`video` and `blog`, filled by `/mediatime`; the capture engines and `setup.sh` read it for their
defaults. `fps` (a whole number from 1 to 120) and `piano` (`vsco` or `salamander`) are the
video's frame rate and piano library, saved by `./configure.sh --fps N --piano vsco|salamander`,
which keeps the other keys ([Kickoff](#kickoff)). A reader that finds no `fps` uses 30, no `piano`
VSCO. The lead owns the file; an edit keeps every key.

**A project is a copy.** Later kit updates do not reach existing projects. To take an update, run
the updated kit's `./install.sh <project-dir> --force`: it overwrites the engine files that have
the same name and deletes nothing. It never overwrites `project.json`, `.gitignore`,
`music/CREDITS.md`, `broll/CREDITS.md` or `.claude/settings.json`, and it leaves the project's own
files alone (`BRAND.md`, `brand/`, `design.json`, the records, `product.py`, the script, the
draft, `captures/`, `outputs/`), because the kit has no files of those names. It does overwrite
any engine file the project patched. Every such patch is recorded in the project's `NOTES.md`;
read it before the update and re-apply the patches after it. If a `--force` install is
interrupted, rerun the same command to finish it.

**Each project has its own environments and samples.** `setup.sh` creates the project's Python
environments and, for a video with music, downloads its own sample libraries into
`music/samples/`: VSCO-2 CE (about 2.2 GB download), plus the Salamander grand piano (1.2 GB) only
when `project.json` selects it.

## Requirements

- **A Linux machine or a Mac.** Debian, Ubuntu and Fedora are supported by `system-deps.sh`; on
  another Linux it prints the package list for an administrator.
- **For the video, OpenGL.** Motion graphics and the edit render through OpenGL (3.3 for motion
  graphics, 4.1 for the edit). On Linux that is headless EGL with any driver (NVIDIA, AMD,
  Intel) or Mesa's llvmpipe, which renders on the CPU on a machine without a GPU
  ([guides/video.md](guides/video.md), "CPU-only machines"). On a Mac it is the OpenGL 4.1 that
  macOS ships. A GPU makes renders fast but is not required. The blog needs no GPU.
- **Disk**: for the video about 25 GB free (up to 5 GB of sample libraries plus up to 3.4 GB of
  archives while `setup.sh` unpacks them, and room for renders), about 17 GB without the samples;
  for the blog alone about 2 GB.
- **Optional: a Gemini API key with billing enabled**, only for a narrated voice (Gemini TTS),
  generated b-roll and the listening judge. The free tier allows only 10 TTS requests a day,
  which runs out during the first voice auditions. The blog needs no key and no paid service.
- **Claude Code**, with access to Opus. Fable helps where taste is the product (music, motion
  design); Sonnet does simple jobs.
- **Command-line tools**: `uv`, `curl` and `tar` always. For the video: `ffmpeg` and `ffprobe`
  with the `libx264`, `prores_ks` and `aac` encoders, `unzip`, and on Linux `xz` (the macOS `tar`
  unpacks `.tar.xz` itself). For the blog, `ffmpeg` built with `libvpx-vp9` is optional and needed
  only for clips (on Fedora the package is `ffmpeg-free`). Optional for both: `tmux` (terminal
  captures inside tmux), `rg` (ripgrep, used by the search commands in these guides).
- **Fonts**: the system fonts used where `design.json` names none (DejaVu Sans and DejaVu Sans
  Mono on Linux; Helvetica and Menlo, which ship with macOS), and the fallback fonts for terminal
  glyphs the mono font lacks (on Linux the families DejaVu Sans Mono, Noto Sans Symbols2, Noto
  Sans Symbols, Noto Sans Math and Noto Color Emoji, found by family through fontconfig, so
  `fc-list` must be installed; on macOS Menlo, Apple Symbols and Apple Color Emoji).
- **Network**: PyPI, the Playwright download host (Chromium), and for the video the sample
  libraries and the Whisper model, during setup.
- **Your product**: its repository or docs, for a post the PRD of the feature, and for captures
  either its built web frontend (a folder with `index.html`) or the URL of a running instance,
  plus its CLI binary.

## Setup

1. The human installs the kit into a new project folder ([Install into a
   project](#install-into-a-project)). That also runs `system-deps.sh`, the only step that needs
   administrator rights ([System packages](#system-packages)). The human then starts `claude`
   there and types `/mediatime`. The steps below run in the project.

2. The lead sees what is missing, then fetches it. `setup.sh` needs no administrator rights:

   ```bash
   ./setup.sh --check                  # report only; changes nothing
   ./setup.sh                          # install and fetch everything missing
   ./setup.sh --for blog               # only what the blog needs
   ./setup.sh --no-samples             # without the music sample libraries
   ```

   `--for video|blog|both` sets the scope; without it `setup.sh` reads `media` in `project.json`
   and checks everything when that is empty. `setup.sh` never uses sudo and an agent never runs
   anything that needs it. A missing system package shows as MISSING or WARN with the hint to run
   `./system-deps.sh` in a terminal outside Claude Code, or to ask an administrator. It runs
   under the bash 3.2 that macOS ships. It prints one line per item, in sections:

   | Section             | Scope | What it checks or does                                                                                                                                                                                                            |
   | ------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | Commands            | both  | `uv`, `curl`, `tar` (MISSING); `rg`, `tmux`, `claude` (WARN); ffmpeg and ffprobe: MISSING for the video with `libx264`, `prores_ks`, `aac` and a test encode through the hardware H.264 encoder, WARN for the blog ("clips only"); `libvpx-vp9` WARN; video also `unzip` and, on Linux, `xz` |
   | Python environments | both  | `uv sync --frozen` in `fixtures/web/` and `fixtures/tui/`; video also `edit/`, `motion/`, `music/`; blog also `post/`                                                                                                              |
   | GPU (OpenGL)        | video | opens the edit's and the motion renderer's GL contexts and reports their renderer                                                                                                                                                 |
   | Fonts               | both  | `design.json` and the families it names (through `tools/fonts.py`), the system fonts, the terminal fallback fonts                                                                                                                 |
   | Claude Code skills  | both  | `brand`, `narration` and `mediatime` in `.claude/skills/`; a missing one means: rerun `install.sh` from the kit                                                                                                                  |
   | Brand               | both  | `BRAND.md` (WARN when absent: optional), `design.json` older than `BRAND.md` or a file in `brand/` (WARN), the logo (video)                                                                                                       |
   | Sample libraries    | video | downloads and unpacks VSCO-2 CE, and Salamander only when `project.json` `piano` is `salamander`, into `music/samples/` (resumable; `--no-samples` skips them)                                                                    |
   | Chromium            | both  | the browser Playwright drives, installed with `playwright install chromium`                                                                                                                                                       |
   | Whisper model       | video | the model `edit/words.py` names, for narration word timings                                                                                                                                                                       |
   | API key             | video | `GEMINI_API_KEY` (WARN when not set)                                                                                                                                                                                              |

   It exits 1 while anything required is MISSING. Rerun it until the summary shows `0 MISSING`.
   WARN lines are optional, and each affects one thing: the API key only a narrated voice,
   generated b-roll and the listening judge; the sample libraries only a score with sampled
   instruments; the Whisper model only narration word timings; ffmpeg and `libvpx-vp9` for the
   blog only clips; `tmux` only shots inside tmux; the fallback fonts only terminal glyphs the
   mono font lacks (they draw as empty boxes); Chromium only web captures; `rg` only the search
   commands; a software GL renderer (llvmpipe) renders on the CPU, much more slowly; without the
   hardware encoder edit previews fall back to libx264; a missing `BRAND.md` means neutral
   defaults ([Design system](#design-system)).

   The "Fonts" section prints one of these for `design.json`, then the system and fallback fonts:

   ```text
   ok        design.json            absent: system fonts and neutral colours in use
   ok        design.json            fonts and colours valid
   MISSING   design.json            <the loader's error: the key and the path, or the bad value>
   WARN      design.json            run ./setup.sh first to check it
   ok        system fonts           DejaVu Sans, DejaVu Sans Mono
   ok        fallback fonts
   ```

   When `design.json` names a font by family, a `font families` line comes first: `ok` with the
   number of roles resolved, `WARN` for a weight or style the family lacks, or `MISSING` with the
   family and where to put its files ([Fonts by family](#fonts-by-family)).

3. If the video uses a narrated voice, generated b-roll or the listening judge, the human puts
   the API key in their shell profile and restarts `claude` (`tts.py` also accepts
   `GOOGLE_API_KEY`). The key is never pasted into the chat:

   ```bash
   export GEMINI_API_KEY=<your key>   # https://aistudio.google.com/apikey
   ```

4. Claude Code settings. The lead works with named teammates that message each other, a feature
   called agent teams that is off by default, and visual work uses the `frontend-design` plugin.
   `install.sh` writes both into the project's `.claude/settings.json`, so they apply in the
   project folder only:

   ```json
   {
     "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
     "enabledPlugins": { "frontend-design@claude-plugins-official": true }
   }
   ```

   If the first session does not offer to install the plugin, install it:

   ```bash
   claude plugin install frontend-design@claude-plugins-official
   ```

   If that says the marketplace is unknown, run
   `/plugin install frontend-design@claude-plugins-official` inside the session. The project's
   skills in `.claude/skills/` (`brand`, `narration`, `mediatime`) are picked up automatically;
   in a session that was already running, run `/reload-skills`.

### Install into a project

```bash
./install.sh <project-dir> [--force] [--no-system] [--setup] [--fps N --piano vsco|salamander]
```

`install.sh` copies the kit into `<project-dir>` (created if missing; a relative path is fine, a
path inside the kit folder is refused):

- every top-level item of the kit except the development files (`install.sh`, `doc/`, `tests/`,
  `.claude/`, `.loom/`, `.worktrees/`, a kit-root `CLAUDE.md`) and the three items copied
  elsewhere below (`claude-project.md`, `claude-skills/`, `claude-settings.json`), with
  executable bits and dotfiles; environments (`.venv`), caches, `out/`, `build/`, `captures/`,
  `outputs/` and `music/samples/` are left out;
- `claude-project.md` as `CLAUDE.md`, the instructions every agent session in the project reads;
- every skill under `claude-skills/` to `.claude/skills/<name>/`: `brand`, `narration`,
  `mediatime`. A new skill added to the kit also goes into `KIT_SKILLS` in `setup.sh`, the list it
  checks;
- `claude-settings.json` as `.claude/settings.json` and `project.json`, each only when absent. If
  an existing settings file lacks the agent-teams entry, the install says so and names the line
  to add.

If the project already holds a file the install would write, it lists them and exits 1 without
writing anything; `--force` overwrites those files and deletes nothing, except `.gitignore`,
`music/CREDITS.md`, `broll/CREDITS.md`, `project.json` and `.claude/settings.json`, which are
written only when absent. After copying, the install runs the project's `./system-deps.sh` in the
human's terminal (it asks for the password itself); `--no-system` skips that for a machine where
the human has no administrator rights. `--setup` then runs `./setup.sh` in the project and
returns its exit code. It ends by printing the next steps: `cd` into the project, start `claude`,
type `/mediatime`.

The install asks nothing. `--fps N --piano vsco|salamander`, given together, pre-answers the
video's frame rate and piano library: the install saves them in `project.json` with
`./configure.sh`, and `/mediatime` then reuses them. Without them `/mediatime` asks.

### System packages

```bash
./system-deps.sh [--yes] [--dry-run] [--for video|blog|both]
```

`system-deps.sh` is the only script that needs administrator rights, and a person runs it in their
own terminal, outside Claude Code: an agent never runs it, never runs sudo, and asks the human to
run it when `./setup.sh --check` reports a MISSING system package. `install.sh` runs it after
copying; run it again at any time. It skips whatever is present, prints one list of what it will
install, and asks `Continue? [Y/n]` once (`--yes` skips the question; `--dry-run` prints the list
and changes nothing). It exits non-zero with a message on failure. `--for` defaults to `both`;
`--for blog` skips Mesa, `xz` and `unzip`. It installs:

- **macOS**: Homebrew first if `brew` is missing (its installer asks for the password), then
  `ffmpeg`, `ripgrep` and `tmux`. `curl`, `tar`, `unzip` and the fonts ship with macOS.
- **Debian and Ubuntu** (`apt-get`): `ffmpeg`, `curl`, `tar`, `xz-utils`, `unzip`, `ripgrep`,
  `tmux`, Mesa's `libegl1`, `libegl-mesa0` and `libgl1-mesa-dri` (headless EGL and CPU
  rendering), `fonts-dejavu-core`, `fonts-noto-core`, `fonts-noto-color-emoji`, and Chromium's OS
  libraries through `uvx playwright@<version in fixtures/web/uv.lock> install-deps chromium`,
  which uses sudo itself. It does not download the browser: `setup.sh` does.
- **Fedora** (`dnf`): the same tools and Mesa (`mesa-libEGL`, `mesa-dri-drivers`), the DejaVu
  fonts, the Noto fonts (`google-noto-sans-symbols-fonts`, `google-noto-sans-symbols-2-fonts`,
  `google-noto-sans-math-fonts`, Noto Color Emoji), and ffmpeg: for the video `ffmpeg` from the
  RPM Fusion free repository (Fedora's own build lacks `libx264`), for `--for blog`
  `ffmpeg-free` from the stock repositories (it has `libvpx-vp9` and GIF). Playwright's
  `install-deps` does not support Fedora, so Chromium's libraries are not installed there.
- **Any other Linux**: it prints the package list and exits 1.
- **Everywhere**: `uv`, with its official installer (no administrator rights), into
  `~/.local/bin`; a terminal opened before the install may need to be reopened to find it.

### Self-tests

Each engine has a self-test that needs no project file. Run them after setup, and again when a
render or a capture fails in a way that might be the machine. Each reads the project's
`design.json` when there is one, so it also shows the project's fonts and colours.

| Engine      | Medium | Self-test (run from its folder)                  | Output                                                                                                                                       |
| ----------- | ------ | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| web capture | both   | `uv run python -m webcap.capture --selftest`     | scenario `selftest` in `captures/web-selftest/`: still `page` (box `button`), and clip `clip` with its director still `typed` when ffmpeg has the profile's encoders |
| TUI capture | both   | `uv run tuicap --selftest`                       | scenario `selftest` in `captures/tui-selftest/`: still `screen` (box `prompt`) and clip `clip`; needs ffmpeg                                 |
| postkit     | blog   | `uv run postkit selftest`                        | builds and checks a made-up post in a temporary folder it deletes; ends with `selftest: ok`                                                  |
| motion      | video  | `uv run python render.py --selftest`             | prints `GL_RENDERER`; `out/selftest_01.50.png`, `out/selftest_contact.png` and `out/selftest.mp4` (2 s at 1920x1080, the logo if named)     |
| edit        | video  | `uv run bg_test.py [seconds]`                    | `out/bg_test.mp4` (default 6 s at 1920x1080, the project's frame rate): the background and one browser-chrome window around a placeholder   |
| music       | video  | `uv run render.py --selftest`                    | `out/selftest/soundtrack.wav` and stems, 17 s of synthesized C major at -16 LUFS                                                             |

```bash
(cd fixtures/web && uv run python -m webcap.capture --selftest)
(cd fixtures/tui && uv run tuicap --selftest)
(cd post && uv run postkit selftest)
```

The capture self-tests take `--for video|blog|both` like a real capture ([guides/capture.md,
"Profiles"](guides/capture.md#profiles)); without it they follow `project.json`. `.gitignore`
leaves `captures/*-selftest/` out of version control.

The kit was tested on Linux with an NVIDIA GPU and on a CPU-only Proxmox VM. The macOS support
was written from the documentation and source of moderngl, glcontext, skia and ffmpeg and checked
on Linux, but has not yet run on a Mac.

### Running on macOS

- **macOS version**: Apple Silicon needs macOS 14 or later for the video (the `av` package that
  `faster-whisper` pulls into `edit/` has no older wheel); on Intel Macs the Python packages
  install from macOS 12, and `edit/` installs `onnxruntime` 1.23.2, the last release with Intel
  Mac wheels.
- **Prerequisites**: Homebrew and `brew install ffmpeg` (its build includes `libx264`,
  `libvpx-vp9` and VideoToolbox), optionally `ripgrep` and `tmux`; `system-deps.sh` does all of
  it. `xz` and fontconfig are not needed.
- **GPU** (video): macOS has no EGL. moderngl opens a CGL context instead, which offers OpenGL
  4.1 core (on Apple Silicon it runs on Metal). The OS-specific choices for the edit live in
  `edit/editkit/hw.py`; motion graphics choose in `motion/lib/gfx.py`.
- **Speed** (video): there is no NVENC or CUDA. Previews and placeholder clips encode with
  `h264_videotoolbox` at 20 Mb/s and sources decode through VideoToolbox, scaled on the CPU. Full
  masters use libx264 on both systems.
- **Music**: worker processes start fresh on macOS (Python's `spawn`), which adds a few seconds
  to a render.
- **Terminal captures**: the fallback fonts are Menlo, Apple Symbols and Apple Color Emoji from
  `/System/Library/Fonts/`; a missing one is skipped, and a glyph no font has is drawn as the mono
  font's empty box. Where `design.json` names no font, the renderers use Helvetica and Menlo from
  the same folder. The captured programs run with `LANG=en_US.UTF-8`, since macOS may lack
  `C.UTF-8`. macOS has no `/proc`: a capture that reads process details there must use `ps`.
- **Web captures**: Playwright's Chromium needs nothing else on macOS; `playwright install-deps`
  is for Linux only.
- **Listening to a take**: `afplay out.wav` instead of `aplay`.

### Sharing a project

`export.sh` packs a project into one gzip-compressed tar archive; `inflate.sh` restores what it
left out on the recipient's machine. Run from the project folder, or from the kit with the
project's path:

```bash
./export.sh --output ../acme-launch.tar.gz
./export.sh /path/to/acme-launch --output /path/to/acme-launch.tar.gz
```

The archive holds one project folder: source, settings (`project.json` with its saved choices),
lockfiles, brand assets, the records, narration, b-roll, `captures/`, `outputs/` and every
workstream's media. Generated and paid-for media is kept, since it cannot be regenerated safely.
It omits what `inflate.sh` restores or a render rebuilds: Python environments, `node_modules`,
caches, `music/samples/`, `music/build/`, `edit/build/`, `post/build/`, `captures/*-selftest/`,
machine-specific font resolution (`brand/fonts/resolved.json`, `brand/fonts/.local/`), Git
history and local credentials (`.env`, `.env.*` except `.env.example` and `.env.template`,
`.aws/`). The archive path must lie outside the project and not exist yet. A symlink that points
outside the project or nowhere stops the export: copy that asset into the project first. A
project installed before `export.sh` existed takes the current kit with `./install.sh
<project-dir> --force` first. The scripts run on Python 3, or on `uv` when `python3` is absent.

The recipient extracts the archive and restores the dependencies:

```bash
tar -xzf acme-launch.tar.gz
cd acme-launch
./inflate.sh               # system-deps.sh, then setup.sh
./inflate.sh --no-system   # setup.sh only, when the system packages are installed
./inflate.sh --check       # report what is missing; change nothing
```

`inflate.sh` runs `./system-deps.sh` (it asks for the password) and then `./setup.sh`, which
scopes itself from `project.json` `media` and fetches the sample libraries `piano` selects,
Chromium and the Whisper model. `--no-samples` passes through to `setup.sh`. It needs network
access. API keys never travel in the archive: set `GEMINI_API_KEY` on the recipient's machine.

## The team

One **lead** session talks to the human, owns the records, the claims, the fixture story and
each medium's plan (the script and the timeline for the video, the outline and the draft for the
post), briefs the specialists, reviews every output, and decides. The specialists are agent-team
teammates (agent teams are on in `.claude/settings.json`), each with a name, so the lead and the
others can message it, and exclusive ownership of its files. The lead owns at the project root:
`project.json`, `NOTES.md`, `HANDBOOK.md`, `claims.md`, `scenarios.md`, `BRAND.md`, `brand/` and
`design.json` (through the brand skill), and for the video `rates.json` and `COSTS.md`.

Each medium guide has its roles table: [guides/video.md](guides/video.md) (composer, motion
designer, web and TUI capture, b-roll, editor) and [guides/blog.md](guides/blog.md) (web and TUI
capture, writer). The capture roles are shared: when a project makes both media, one web capture
and one TUI capture teammate serve both, from one `product.py` each. Only the roles the chosen
media and workstreams need exist.

Pick the tier per job: Sonnet for a search-and-cut task or plain CLI captures, Opus for
engineering-heavy capture and editing, Fable where taste is the product (motion design, music) or
where an attempt at the same thing already failed. Escalate one tier only after a failed attempt,
and hand the stronger agent the task, both attempts and their evidence. Later work on the same
piece goes to the tier that succeeded.

### Rules that make the team work

1. **One owner per file.** Two agents writing the same file lose work. Agents may import another's
   library or module but never modify it; a second designer brought in for one scene gets
   exactly that scene's file and its outputs.
2. **Files plus short messages.** Each workstream writes its outputs and a `manifest.json`;
   messages say what changed and where. Nobody asks when a dialog opens or where a box is; they
   read the manifest's marks and boxes.
3. **The records are the contract.** The video's clock is `narration/timeline.json`: every agent
   reads it, never a number from a message, and when it changes the lead sends absolute windows,
   not deltas. The post references an image only as `shot:<source>/<scenario>/<label>`, an id
   from a capture manifest, never by file path. Both media take claims from `claims.md` and
   fixture data from `scenarios.md`.
4. **Human decisions are written down first.** Every decision and correction goes into `NOTES.md`
   before anyone is briefed; every agent treats that file as binding. Then the lead tells the
   affected agents, with exact times or scenario and label names, file or symbol references and
   acceptance checks.
5. **The lead reviews before the human sees anything**, and purges rejected elements from every
   agent's work: an edit decision list can still reference a rejected animation after the motion
   designer dropped it, and a draft or `images.json` can still name a dropped scenario.
6. **Plans before production.** The human approves the script (video) or `post/outline.md`
   (post), and the scenarios in `scenarios.md`, before any capture starts. The editor renders
   previews for review and the master only after the lead's OK; a post is final only after
   `postkit check` passes.
7. **Messages cross.** An agent's report covers the brief it finished; newer messages may still be
   queued. Check whether the agent is running or idle and look at file timestamps before
   re-sending or re-spawning.
8. **Wait on files or explicit messages.** A watcher loop that searches for another agent's
   process (`pgrep` on its command line) can match its own command line and never end.
9. **Change only what was asked.** When the human asks to replace one beat or one image, leave
   the rest of the scene, the cut or the post unchanged and re-render or rebuild. A scene redesign
   keeps its story beats and its narration sync.
10. **Hands off the product.** No writes to the product's repository (it is the read-only source
    of truth for every claim; logo and font files are copied into `brand/`), no system installs,
    never `pip install` (use `uv`), no git inside the project unless the human wants it.
11. Visual work (scenes, fixture data that looks real, image treatment) uses the
    `frontend-design:frontend-design` skill for guidance.

### Good briefs

- the goal and the reference points: the agent's part of the HANDBOOK "Brand" section, plus the
  human's own references, with what each one means to the human;
- for a capture, the scenarios it captures from `scenarios.md`, with the medium each serves;
- what the agent owns and what it must never touch;
- exact deliverables: file, scenario and label names, sizes, codecs, the boxes each still needs,
  a manifest with named marks;
- how to check its own work without eyes or ears (Read each PNG, contact sheets, spectrograms,
  the judge, the boxes in the manifest);
- a final report format: paths, commands to re-render or recapture, known weaknesses.

During long renders a recurring five-minute status check (a scheduled prompt) keeps the human
informed; cancel it when the work settles.

## Kickoff

The human types `/mediatime` (or says "let's make a video", "write a blog post"). The `mediatime`
skill (`.claude/skills/mediatime/SKILL.md`) runs the kickoff:

1. Read `project.json` and `NOTES.md`; list the media and artefacts that exist.
2. Ask which media (video, blog post, both) and, for both, which comes first.
3. With a video, ask its frame rate (30 suggested), whether it has music and, with music, the
   piano library: VSCO (CC0, no attribution) unless the human explicitly picks the Salamander grand
   piano (CC BY 3.0: credited on screen and in the video description). Save both with
   `./configure.sh --fps N --piano vsco|salamander`; answers already in `project.json` are reused.
   A human who asks Claude to decide gets 30 fps and VSCO. Check the machine for the chosen media
   with `./setup.sh --check --for <media>`, then run `./setup.sh --for <media>` (`--no-samples`
   without music), and loop on `./system-deps.sh` for the human until `0 MISSING`.
4. Interview: one shared group (product, source and PRD, audience and goal, captures and theme,
   guidance, deliverables), then each medium's own group, skipping what is known.
5. The Gemini key, when narration, b-roll or the listening judge is wanted.
6. The brand skill.
7. Write `project.json` `media`, `NOTES.md` (the decisions, by medium), `rates.json` when billed
   calls are planned, and, when a medium joins a project that already has one, a reuse inventory
   in `NOTES.md` ([Reuse between media](#reuse-between-media)).
8. Start Phase 1 of [guides/video.md](guides/video.md) or [guides/blog.md](guides/blog.md).

Adding the other medium later is the same command: `/mediatime` sees the existing medium, asks
only what the new one needs, and appends it to `media`.

## Reuse between media

A project that makes both media builds the shared parts once. These are shared by construction:

- **`project.json`, `BRAND.md`, `brand/`, `design.json`** and the HANDBOOK "Brand" section, with a
  part per role of each chosen medium.
- **`claims.md`**: every claim, verified against the code once, with the places it is used. The
  script and the outline take claims from it ([`claims.md` and
  `scenarios.md`](#claimsmd-and-scenariosmd)).
- **`scenarios.md`**: one fixture story and one scenario table with a Media column. A scenario
  the video and the post both show is captured once.
- **The fixture world**: `fixtures/web/product.py` (with its `World`, `build_app` and fixture
  data) and `fixtures/tui/product.py`, written once, with `SHOTS` for stills and `CLIPS` for
  clips. One viewport serves both media: 1920x1080 when `media` includes the video, else
  1440x900; `VIEWPORT` in `product.py` wins.
- **`captures/`**: one manifest per source, merged by scenario and origin, so a run for one medium
  never drops what another run captured ([guides/capture.md, "Manifests"](guides/capture.md#manifests)).

**Capture once for both.** With both media in `project.json`, captures default to `--for both`:
one recording at the video's scale 2 and the project's frame rate gives `clip.mp4` for the edit,
and the post's 30 fps WebM and GIF are derived from it. `SHOTS` stills are scale 2 in every profile, so the same PNG
serves both. A project that captured for the video alone and then adds the post recaptures the
clips it needs with `--for both`; under the video profile a clip's manifest `file` is its poster
PNG and there is no GIF.

**Video to blog.**

- Web and TUI stills: the post links them as `shot:web/<scenario>/<label>`, including the stills a
  clip's director took with `still()` ([guides/capture.md, "Web capture"](guides/capture.md#web-capture)).
  Stills taken at 1920x1080 are 3840 px wide; `images.json` resizes them (default `width` 1600).
- Motion graphics, logo renders and b-roll: `postkit add` brings a PNG, a frame or a segment into
  `captures/motion/`, `captures/broll/` or `captures/video/` with a manifest entry, so the draft
  links it like any capture ([guides/blog.md, "`postkit add`"](guides/blog.md)):

  ```bash
  cd post
  uv run postkit add motion/endcard/logo ../motion/out/endcard.mp4 --at 3.5
  uv run postkit add broll/city/loop ../broll/candidates/03_city.mp4 --from 1.0 --to 4.0
  uv run postkit add video/intro/hero ../outputs/final-acme-launch-v2.mp4 --at 12.0
  ```

- The narration script (`narration/NN_*.txt`): the agreed pitch wording, the product terms and the
  order of the story. A post is written for reading, so reuse its terms and claims, never its
  sentences as spoken.
- `NOTES.md` rules about terms, the pitch line and rejected styles bind the post too.

**Blog to video.**

- `claims.md` and `scenarios.md`: the script uses the verified claims; a scenario the video also
  shows gets `both` in the Media column and, for a clip, the marks the edit syncs to.
- Captures: the edit references a capture clip as `web:<scenario>` or `tui:<scenario>`, which
  resolves `captures/<source>/<scenario>/clip.mp4`, else `clip.webm` with a printed warning; a
  still as `still:web/<scenario>/<label>`. A blog-only clip is a 30 fps WebM at scale 1: recapture
  with `--for both` for the cut.
- The viewport: a blog-only project captured at 1440x900. Adding the video changes the default to
  1920x1080, which changes every capture's size. Either recapture everything with `--for both`,
  or pin `VIEWPORT = (1440, 900)` in `product.py` and keep the post's stills; record the choice
  in `NOTES.md`.
- The fixture world: the mock server and the `SHOTS` scenarios stay; the video adds `CLIPS` with
  its choreography and key marks.

**The reuse inventory.** When `/mediatime` adds a medium to a project that has one, it writes a
"Reuse inventory" section into `NOTES.md`: each capture manifest (`captures/*/manifest.json`)
with its scenarios, labels and the profile that made its clips, `motion/out/manifest.json`, the
narration script, `claims.md`, `scenarios.md` and the b-roll picks, each marked reuse as is,
recapture, or not needed.

## Pipeline and folder map

```text
BRAND.md + brand/ ──brand skill──> design.json (fonts, colours, logo, grain) + HANDBOOK.md "Brand" (every brief)
product docs, PRD, source ──lead──> claims.md (verified claims) + scenarios.md (fixture story, scenarios, Media column)
fixtures/web/product.py (mock or live) ──webcap (Playwright)──> captures/web/<scenario>/<label>.png, clip.{mp4,webm,gif,png} + manifest.json
fixtures/tui/product.py (the CLI in a pty) ──tuicap (pyte + skia)──> captures/tui/<scenario>/<label>.png, clip.{mp4,webm,gif,png} + manifest.json

video
narration/NN_*.txt ──narration skill (Gemini TTS)──> narration/vN/*.wav ──process.sh──> narration/final/*.wav
                                                 └─build_timeline.py (sections.json)──> narration/timeline.json  (THE clock)
timeline.json ──> music/arrangement.py ──music/render.py──> music/out/soundtrack.wav + stems + manifest.json (bar grid)
timeline.json ──> motion/scenes/*.py ──motion/render.py──> motion/out/<scene>.mp4 / *_alpha.mov + manifest.json (marks)
broll/gen/shots.json ──tools/genvideo.py (Gemini Omni)──> broll/gen/omni/*.mp4 ──> broll/candidates/NN_*.mp4
all of the above ──> edit/words.py ──> edit/edl.py ──> edit/mix.py (edit/out/mix.wav) ──> edit/render.py (GPU compositor)
                 ──> outputs/draft-<slug>-vN.mp4 (--preview), outputs/final-<slug>-vN.mp4 (full)
                 ──> edit/subs.py, edit/credits.py ──> outputs/<stage>-<slug>-vN.srt, outputs/<stage>-<slug>-vN-credits.txt

blog
claims.md + scenarios.md ──lead──> post/outline.md ──lead or writer──> post/draft.md (shot: refs) + post/images.json
motion/out, broll/candidates, outputs/*.mp4 ──postkit add──> captures/{motion,broll,video}/ + manifest.json
post/draft.md + images.json + captures/*/manifest.json + design.json + project.json
                 ──postkit build──> outputs/blog/<stage>-<slug>-vN.md + outputs/blog/images/<source>-<scenario>-<label>.<png|gif|webm>
outputs/blog/ ──postkit check──> ERROR and WARN lines
```

**Rebuild order after a change.** Shared: brand (the brand skill after `BRAND.md` or `brand/`
changes, then every renderer that shows the change), claims, scenarios, captures (only the
scenarios the change touches). Video: narration, timeline, music (if timing moved), motion (if a
scene window or its content changed), edit. Blog: outline, draft, build, check.

Each engine is a folder with its own `uv` project (`pyproject.toml`, `uv.lock`,
`.python-version`). Run every command from inside its folder with `uv run ...`. `tools/*.py`,
`narration/build_timeline.py` and the skills' scripts are single-file `uv` scripts that declare
their own dependencies. Scripts find each other and the project root by relative path (`edit/`
reads `../narration/timeline.json`, the capture engines read `../../project.json`), so keep the
folder layout as it is.

## Engine and project files

The engine column ships with the kit and works for any product as it is. The project column is
what the team writes; each entry point that needs a project file stops with a message naming the
file.

| Folder                                       | Medium | Engine (in the kit)                                                                                                                                                                                                                                            | Files the project writes                                                                                                                                                                                                 |
| -------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| project root                                 | both   | `README.md`, `HUMAN.md`, `CLAUDE.md`, `guides/`, `setup.sh`, `system-deps.sh`, `configure.sh`, `export.sh`, `inflate.sh`, `LICENSE`, `.gitignore`; `project.json` (written once by `install.sh`)                                                               | `BRAND.md`, `brand/`, `design.json` ([Brand](#brand)); `NOTES.md`, `HANDBOOK.md`, `claims.md`, `scenarios.md` ([Project records](#project-records)); video: `rates.json`, `COSTS.md` (generated from `usage.jsonl`)       |
| `tools/`                                     | both   | `fonts.py` (finds the files for fonts `design.json` names by family), `project_settings.py` (`configure.sh`), `export_project.py` (`export.sh`); video: `setup-samples.sh` (sourced by `setup.sh`), `listen.py` (the listening judge), `genvideo.py` (Gemini Omni b-roll), `usage_log.py`, `costs.py` (writes `COSTS.md`) | none                                                                                                                                                                                                                     |
| `claude-skills/` (in a project `.claude/skills/`) | both   | `brand/` (`SKILL.md`, `BRAND.template.md`, `check.py`), `mediatime/` (`SKILL.md`); video: `narration/` (`SKILL.md`, `tts.py`)                                                                                                                                 | none                                                                                                                                                                                                                     |
| `fixtures/web/`                              | both   | `webcap/`: `capture` (the command), `project` (loads `product.py`, mock or live), `profiles`, `shots` (`Shooter`), `director` (frame stepping), `browser`, `boxes`, `encode`, `media`, `manifest`, `names`, `page_script`, `server`, `world` (scripted clock), `probe`, `verify`, `selftest`, `agent_session` and `ansi` (a scripted coding-agent terminal) | `product.py`: `SHOTS` and/or `CLIPS`, optional `CLIP_PATHS`, `VIEWPORT`, `THEME`, `LOCAL_STORAGE`, `FONT_PROBES`; mock mode `World` and `build_app`; live mode `BASE_URL`; plus fixture data ([guides/capture.md](guides/capture.md)) |
| `fixtures/tui/`                              | both   | `src/tuicap/`: `clips` (the `tuicap` command), `capture` (pty recording, typed-command shots), `render` (pyte and skia), `shots` (`Still`), `encode`, `fonts`, `manifest`, `design`, `palette`, `glyphs`, `tmux_clip`                                            | `product.py`: `SHOTS` and/or `CLIPS`, optional `prepare()`, `TRUECOLOR`, `NOTES`; plus fixture files ([guides/capture.md](guides/capture.md))                                                                             |
| `narration/`                                 | video  | `process.sh`, `build_timeline.py`                                                                                                                                                                                                                             | `NN_name.txt` scripts, `sections.json`, `sources.json`; generated: `vN/`, `final/`, `timeline.json`                                                                                                                      |
| `music/`                                     | video  | `scorekit/`, `render.py` with `--selftest`; `CREDITS.md` lists the sample libraries                                                                                                                                                                            | `arrangement.py`: `compose(seed) -> Score`                                                                                                                                                                              |
| `motion/`                                    | video  | `lib/` (`gfx`, `design`, `logo`, `ease`, `encode`, `scene`, `ui`, `selftest`), `render.py` with `--selftest`, `render_all.sh`                                                                                                                                  | `scenes/<name>.py` (one per scene, defining `SCENE`), `scenes.txt`                                                                                                                                                      |
| `edit/`                                      | video  | `editkit/` (`compositor`, `gpu`, `hw`, `decode`, `scene`, `ease`, `shaders/`, `cards`, `art`, `design`, `assets`, `shots`, `credit_data`, `outputs`, `project`); `render.py`, `mix.py`, `words.py`, `subs.py`, `credits.py`, `bg_test.py`                      | `edl.py`: `END`, `build()`, optional `BROLL_CLIPS`, `BUSY`, `FPS`; optional `credits.json`; `ISSUES.md`                                                                                                                  |
| `broll/`                                     | video  | `CREDITS.md` (the format for CC BY clips)                                                                                                                                                                                                                      | `gen/shots.json` (prompts), a `CREDITS.md` section per CC BY clip                                                                                                                                                       |
| `post/`                                      | blog   | `src/postkit/`: `cli` (the `postkit` command), `assemble` (build), `check`, `add`, `images` (treatment), `frames`, `config` (`images.json`), `manifest`, `outputs`, `design`, `common`, `selftest`                                                              | `outline.md`, `draft.md`, `images.json`                                                                                                                                                                                 |

The video's project files are described in [guides/video.md](guides/video.md), the post's in
[guides/blog.md](guides/blog.md).

Folders the project creates as it goes: `captures/<source>/` (stills, clips, manifests),
`outputs/` and `outputs/blog/` (the deliverables), the self-tests' `captures/*-selftest/`, and for
the video `narration/vN/`, `narration/final/`, `broll/gen/omni/`, `broll/candidates/`, every
workstream's `out/` and `edit/build/`; for the post `post/build/` (the image ledger).

**Not included**: brand files, claims, scenarios, a script, a score, scenes, capture modules, an
edit decision list, an outline, a draft, prompts, and any recorded, captured or rendered media.
`setup.sh` fetches the sample libraries and the Whisper model.

**Fonts and colours** come from the project's `design.json`, through one loader per renderer
(`motion/lib/design.py`, `edit/editkit/design.py`, `fixtures/tui/src/tuicap/design.py`,
`post/src/postkit/design.py`); nothing is installed system-wide ([Design system](#design-system)).

## Code that needs your product

Only the two capture harnesses talk to the product. Each loads one project module, `product.py`
in its folder, and keeps the rest (browser setup, frame stepping, pty recording, terminal
rendering, manifests) as engine. `product.py` reads where the product lives from environment
variables, never from hard-coded paths. Use these names, so every agent and `HANDBOOK.md` agree:

| Variable           | Meaning                                         | Typical use in `product.py`                              |
| ------------------ | ----------------------------------------------- | -------------------------------------------------------- |
| `PRODUCT_REPO`     | the product's repository checkout (read-only)   | CLI shots that run inside it; fixture data read from it  |
| `PRODUCT_WEB_DIST` | the product's built web frontend (`index.html`) | `serve_dist(app, ...)` in the mock server                |
| `PRODUCT_BIN`      | the product's CLI binary                        | the commands TUI shots run                               |
| `PRODUCT_URL`      | a running instance of the product's web UI      | live mode; it wins over `BASE_URL` in `product.py`       |

`webcap.server.require_env(name, what)` returns the path or stops with a message saying what to
set. Two rules hold for any product:

- Run the product read-only against its repository. Build fixture state (a workspace, a scratch
  `HOME` with config) inside `fixtures/` with the product's own init commands, never by
  hand-editing its files.
- Keep the operator's own settings out of captures: `tuicap.capture.clean_env(home, drop=(...))`
  removes the product's environment variables (pass its prefix, for example `"<PRODUCT>_"`) and
  points `HOME` at the scratch home. In live mode, log in as a fixture account, never the
  operator's own.

Narration, music, motion graphics, the edit, the draft, the build and the check run without the
product.

## Outputs

Every deliverable lands in `outputs/`, named by stage, slug and revision:

```text
outputs/draft-<slug>-v<N>.mp4                    edit/render.py --preview
outputs/final-<slug>-v<N>.mp4                    edit/render.py (full)
outputs/<stage>-<slug>-v<N>-range-<A>-<B>.mp4    edit/render.py --range A B
outputs/draft-<slug>-v<N>-contact-<NN>.png       edit/render.py --contact
outputs/<stage>-<slug>-v<N>.srt                  edit/subs.py [--final]
outputs/<stage>-<slug>-v<N>-credits.txt          edit/credits.py [--final]
outputs/final-<slug>-v<N>-share.mp4              edit/render.py --share
outputs/blog/<stage>-<slug>-v<N>.md              postkit build [--final]
outputs/blog/images/<source>-<scenario>-<label>.<png|gif|webm>
```

- **Stage**: `draft` for review, `final` for delivery. The slug comes from `project.json`.
  Names match `^(draft|final)-<slug>-v(\d+)(-[a-z0-9-]+)?\.<ext>$`; a range writes its decimal
  points as `p` (`range-0p5-1p5`).
- **Revisions** are found by scanning `outputs/`, never kept in a counter. Numbering is per medium
  and per stage: the video's primary file is an `outputs/*.mp4` without a suffix, the post's an
  `outputs/blog/*.md`. A tool rewrites the latest revision of its stage by default (v1 when there
  is none); `--next` writes the next one (latest + 1); `--revision vN` names one. Start a new
  revision when the human has seen the current one, so every version they reviewed stays.
- **Companions** (subtitles, credits, the share copy, contact sheets, ranges) attach to the latest
  primary of their stage unless `--revision vN` is given: `subs.py --final` after a full render
  writes the `.srt` beside that master. `--share` encodes the latest final and refuses to
  overwrite an existing share copy.
- **The post's images** live in one `outputs/blog/images/`, shared by every revision; a rebuild
  replaces an image in place. postkit records the images it wrote in `post/build/ledger.json`
  and deletes one only when no `.md` in `outputs/blog/` links it. The markdown links
  `images/<file>` relatively, so `outputs/blog/` moves as one folder.
- **`outputs/` is the deliverable** and is not in `.gitignore`.
- **Intermediates stay where they are made** and are rewritten freely: `edit/out/mix.wav`,
  `edit/build/frames/` (single frames from `render.py --frames`), `motion/out/`, `music/out/`,
  `captures/`.

`edit/editkit/outputs.py` and `post/src/postkit/outputs.py` implement these rules in two separate
`uv` projects; a kit test checks that both pick the same names.

## Brand

The brand decides how the video and the post look, speak and sound. A project keeps it at its
root, in two optional places: `BRAND.md`, the guidelines in prose, and `brand/`, the files.
`BRAND.md` is the source of truth. The brand skill turns it into `design.json`, which the
renderers read ([Design system](#design-system)), and into the "Brand" section of `HANDBOOK.md`,
which every brief points to. Without them both media use neutral defaults: system fonts, white
text on black for the video, no logo.

They go in the project folder that `install.sh` created, never in the kit, so each project has
its own brand:

```text
~/<product>-media/          # the project, made by ./install.sh
├── BRAND.md                # the guidelines (the brand skill writes it if you have none)
├── brand/
│   ├── logo/               # SVG, or PNG at least 2000 px wide; a dark- and a light-background variant
│   ├── fonts/              # font files plus their licence files, a folder per family
│   ├── palette/            # optional exported palette files
│   └── reference/          # images or videos of the brand in use
├── design.json             # generated by the brand skill; never edit by hand
└── ...                     # the engine and the project's own files
```

The human can copy existing brand files in before the first session; otherwise the lead runs the
brand skill with the human: it creates `BRAND.md` and the `brand/` folders and says which files to
add.

### `BRAND.md` and `brand/`

`BRAND.md` has these headings, in this order; the template ships at
`.claude/skills/brand/BRAND.template.md`:

| Heading                 | What it holds                                                                          |
| ----------------------- | -------------------------------------------------------------------------------------- |
| Identity                | the product name as written and as spoken, a one-line description                      |
| Voice and tone          | how the script and the prose read and the narrator sounds; words used and never used   |
| Colours                 | each colour as hex plus its role (background, text, secondary, accent, others)         |
| Typography              | the files in `brand/fonts/` and their roles: display, body, mono                       |
| Logo                    | files, variants, clear space, minimum size, do and don't                               |
| Imagery and motion feel | the visual mood, how things move, transitions liked or avoided, how screenshots look   |
| Music and sound feel    | genre, tempo, instruments, energy curve, what to avoid                                 |
| Things to avoid         | colours, effects, words, imagery neither medium may use                                |
| Legal                   | trademark lines, font licences, other notices                                          |

A heading that does not apply to the chosen media (music for a post) may stay empty.

### The brand skill

`claude-skills/brand/` in the kit, installed to `.claude/skills/brand/`. The lead runs it at
kickoff and again whenever `BRAND.md` or anything in `brand/` changes.

- **Without `BRAND.md`** it interviews the human, writes `BRAND.md` from the template and creates
  the `brand/` folders. The human then adds the logo and font files.
- **With `BRAND.md`** it maps `BRAND.md` and `brand/` to `design.json` (fonts by role, colours,
  logo, and for the video grain), resolves font families with `uv run tools/fonts.py`, runs the
  checker, writes a "Brand" section into `HANDBOOK.md` with a part for each role of each chosen
  medium (video: narration, music, motion, captures, edit; blog: writing, captures, images), and
  lists gaps and conflicts as questions for the human.

`design.json` is generated: never hand-edit it. To change the look, change `BRAND.md` or `brand/`
and rerun the skill; then re-render or recapture what shows the change (for the video delete
`edit/build/placeholders/` first; for the post recapture the TUI scenarios when the terminal's
colours or mono font changed) and rebuild. `setup.sh` and the checker warn when `design.json` is
older than `BRAND.md` or a file in `brand/`; `brand/fonts/resolved.json` and `brand/fonts/.local/`,
which `tools/fonts.py` writes, do not count.

### The checker

```bash
uv run .claude/skills/brand/check.py [project-root]
```

It prints one `ok`, `WARN` or `MISSING` line per check, then a summary with both counts, and
exits 1 on any MISSING:

| Check                                                                                        | Level when it fails |
| -------------------------------------------------------------------------------------------- | ------------------- |
| `BRAND.md`, `brand/` or `design.json` absent                                                 | MISSING             |
| `design.json` not valid (an unknown key, a bad colour, a negative grain)                     | MISSING             |
| `brand/logo`, `brand/fonts` or `brand/reference` empty or absent (an absent `palette` is ok) | WARN                |
| a font does not parse                                                                        | MISSING             |
| a font in `brand/` that `design.json` does not name (not checked when it names a family)     | WARN                |
| a font family `tools/fonts.py --check` cannot find                                           | MISSING             |
| a family that lacks the wanted weight or style, so another is used                           | WARN                |
| the mono font is not monospaced                                                              | MISSING             |
| the mono font lacks some ASCII characters                                                    | WARN                |
| a logo does not parse, or has the wrong extension                                            | MISSING             |
| a PNG logo under 2000 px wide                                                                | WARN                |
| WCAG contrast: text on background below 4.5:1, secondary below 3:1                           | WARN                |
| `design.json` older than `BRAND.md` or anything in `brand/`                                  | WARN                |

It is a single-file `uv` script with its own pinned dependencies (fonttools, pillow).

## Design system

The design system is the brand made concrete for the renderers: fonts, colours, logo, grain,
sizes and transitions. It lives in `design.json` and in `HANDBOOK.md`; the renderers read the
first, the agents the second.

1. The human approves `BRAND.md` and supplies `brand/` ([Brand](#brand)).
2. The brand skill generates `design.json` and the HANDBOOK "Brand" section; the checker passes.
3. The lead renders the self-tests and one still per renderer that matters (a terminal still, a
   built post image, a motion title, an edit frame with a window) and shows them to the human
   before production.
4. The lead writes the design system into `HANDBOOK.md` as data: the four colours and their
   roles, the fonts by role and the sizes in use, the logo variants with their minimum size, the
   rejected styles, and for the video the grain and the transitions in use
   ([guides/video.md](guides/video.md), "Transitions").
5. Every brief quotes the parts its workstream uses.

Rules that hold for any brand:

- The product's own UI keeps its own fonts and colours in captures; the product's state colours
  appear only where its UI shows them.
- Graph edges, connectors and text need strong contrast on any coloured ground.
- Draw only the files in `brand/logo/`: never redraw, recolour or distort the logo.

### `design.json`

At the project root, optional, generated by the brand skill. Every key is optional; an unknown
key is rejected. Paths are relative to the project root.

```json
{
  "fonts": {
    "family": "<Body family>",
    "regular": "brand/fonts/<Body>-Regular.otf",
    "bold": "brand/fonts/<Body>-Bold.otf",
    "italic": "brand/fonts/<Body>-Italic.otf",
    "bold_italic": "brand/fonts/<Body>-BoldItalic.otf",
    "mono": "brand/fonts/<Mono>-Regular.otf",
    "weights": { "700": "brand/fonts/<Display>-Bold.otf" }
  },
  "colors": {
    "background": "#rrggbb",
    "text": "#rrggbb",
    "secondary": "#rrggbb",
    "accent": "#rrggbb"
  },
  "grain": 0.022,
  "logo": {
    "on_dark": "brand/logo/<file>.svg",
    "on_light": "brand/logo/<file>.png"
  }
}
```

| Key      | Meaning                                                                       | Default                                    |
| -------- | ----------------------------------------------------------------------------- | ------------------------------------------ |
| `fonts`  | fonts by role (a file or a family name); `weights` maps a weight              | the system sans and monospace              |
| `colors` | `background`, `text`, `secondary`, `accent` as `#rrggbb`                      | `#000000`, `#ffffff`, `#a0a0a0`, `#ffffff` |
| `grain`  | film grain strength, a number >= 0; read only by the edit, the post ignores it | 0.022 (previews render with 0)             |
| `logo`   | `on_dark` (light ink, for dark grounds) and `on_light`, each `.svg` or `.png` | none                                       |

**Roles.** `design.json` has no display role: the brand skill puts the display face under
`fonts.weights` at the weights titles use, or under `bold`, and records which in `HANDBOOK.md`.
Body faces go under `regular`, `bold`, `italic` and `bold_italic`, the mono face under `mono`.

**Font lookup.** `font(weight, italic)` returns the file of the first role set among: for italic,
`bold_italic` (weight >= 600), then `italic`; then `weights["<weight>"]`; then `bold` (weight >=
600); then `regular`; then the system sans. `mono()` returns `fonts.mono`, else the system
monospace font.

**System fonts**: on Linux DejaVu Sans and DejaVu Sans Mono, found with `fc-match`, then under
`/usr/share/fonts/` (package `fonts-dejavu-core`, installed by `system-deps.sh`); on macOS
`/System/Library/Fonts/Helvetica.ttc` and `Menlo.ttc`.

**Errors.** A font or logo path that is set but missing raises an error naming the key and the
path; a family that `brand/fonts/resolved.json` does not resolve raises one telling you to run
`tools/fonts.py`. An invalid colour or grain raises an error naming this section. `setup.sh`
reports either as MISSING in its "Fonts" section.

**Loaders.** `edit/editkit/design.py`, `motion/lib/design.py` and
`fixtures/tui/src/tuicap/design.py` have the same API: `load()`, `color(name)`, `grain()`,
`font(weight=400, italic=False)`, `mono()`, `system(kind)`, `logo(variant=None)`.
`post/src/postkit/design.py` reads the accent colour and the bold font.

### Fonts by family

A font role (`regular`, `bold`, `italic`, `bold_italic`, `mono`, `weights."<n>"`) is written in
one of two ways:

- **A file**: a path relative to the project root that ends in `.ttf`, `.otf` or `.ttc`. It must
  exist.
- **A family name**: anything else, such as `"Inter"` or `"JetBrains Mono"`. A family under a
  role means that family at the role's weight and style: `mono` is 400 upright, and `"Inter"`
  under `weights."800"` is Inter at 800.

`fonts.family` names one family for the four body roles: it fills `regular` (400), `bold` (700),
`italic` (400 italic) and `bold_italic` (700 italic) for each of them the file does not set
itself. `{"fonts": {"family": "Inter", "mono": "JetBrains Mono"}}` is a complete font setup.

Rendering reads files, so a family has to be turned into files first. From the project root:

```bash
uv run tools/fonts.py          # resolve every family-named role, write brand/fonts/resolved.json
uv run tools/fonts.py --check  # resolve without writing; exit 1 if a family is missing
```

For each family-named role the script looks, in order, in `brand/fonts/` (recursively), then in
the fonts installed on this machine (on Linux `fc-list` and the usual font folders, on macOS
`/System/Library/Fonts`, `/System/Library/Fonts/Supplemental`, `/Library/Fonts` and
`~/Library/Fonts`). It never uses the network. It matches the family name (case-insensitive),
the weight and the italic flag read from the font file, and takes the exact weight and style,
else the nearest weight of that style with a printed `WARN` naming the role, the wanted and the
got weight. A variable font becomes a static instance at the wanted weight. A face inside a TTC
that is not face 0 is extracted to a single-face file, because every consumer (Skia, Pillow,
ffmpeg `drawtext`) needs one face per file.

Where files go, and why:

- A font already in `brand/fonts/` or installed as a single-face static file is used where it is;
  installed fonts are referenced by absolute path and never copied into the project, because
  commercial licences often forbid redistribution.
- Files the script derives from fonts in `brand/fonts/` (variable-font instances, extracted TTC
  faces) go next to them, in `brand/fonts/<Family>/`.
- Files it derives from installed fonts go to `brand/fonts/.local/`.
- The result is `brand/fonts/resolved.json`: each family-named role mapped to a path and the
  SHA-256 of the `design.json` it was built from.

`resolved.json` and `brand/fonts/.local/` hold machine-specific paths and are in `.gitignore`. The
loaders read `resolved.json`; if it is missing, lacks the role, was built from another
`design.json` or points at a file that is gone, they raise `FileNotFoundError` telling you to run
`uv run tools/fonts.py`. `setup.sh` runs the script, so a new machine resolves its own files with
`./setup.sh`.

When a family is found nowhere, the script exits 1 and names it. Either install the font on the
machine, or put its files and its licence file in `brand/fonts/<Family>/` and rerun the script. An
agent may fetch a font itself only when it has an open licence that allows use in video and on the
web (OFL, Apache); the GitHub repository `google/fonts` holds many under `ofl/`, `apache/` and
`ufl/`, with the licence file next to the fonts. For any other font, a human installs it or
provides the files; a commercial font is never fetched.

### Who reads what

| Renderer    | Medium | Reads                                     | Where it shows                                                                                                         |
| ----------- | ------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| web capture | both   | nothing                                   | the product's real frontend, in its own fonts and in the `THEME` `product.py` sets                                     |
| TUI capture | both   | mono, background, text                    | the terminal font and default colours; bold and italic synthesised, the cell size fitted to any monospace font        |
| postkit     | blog   | accent, bold; the other keys validated    | highlight outlines and callout circles (default accent `#2563eb`), callout numbers; window frames have fixed colours  |
| motion      | video  | fonts, all four colours, logo             | `gfx.BG`, `FG`, `FG2`, `ACCENT`; `gfx.typeface`, `gfx.font`; `logo.draw`                                               |
| edit        | video  | fonts, background, text, secondary, grain | the flat background and its grain; window titles, cards and placeholders; window chrome is a fixed neutral grey        |

A colour change for the terminal means a TUI recapture for both media. Placeholders in
`edit/build/placeholders/` are cached with the design they were drawn in: delete them after
changing `design.json`.

### Legibility

- **Contrast**: text on the background at least 4.5:1, secondary text at least 3:1 (WCAG; the
  checker warns below these). A light brand background can make yellow and cyan terminal text
  hard to read: check every terminal still.
- **Video, at 1080p**: body text at least 22 px, labels 26-34 px, hero names 52-62 px; every
  element inside 5 % title-safe (96 px from the left and right edges, 54 px from the top and
  bottom); text over b-roll or a capture needs the same contrast; cards sized from measured
  content; narrated UI shots fill at least 80 % of the frame width ([guides/video.md](guides/video.md)).
- **Post**: an image is shown at most `width` pixels wide (default 1600) and then often smaller
  on a page; crop to the part the prose names rather than shrink a full screen, and keep the
  first image readable at preview-card size ([guides/blog.md](guides/blog.md)).

## Editorial rules

Record the human's own rules in `NOTES.md` as they state them. These hold for both media and any
product; each medium guide adds its own.

- **Plain and accurate.** State what the product does and how to use it. No hype
  ("revolutionary", "game-changing"), no anthropomorphism ("watch it think", "it understands what
  you need"), no stock phrases. Read `BRAND.md`, "Voice and tone", before the first sentence. If
  a third-party tool appears (a coding agent's terminal, say), say what it is and what the
  product does with it.
- **Name things as the product does.** Use the UI's labels, the command's real flags, the
  setting's real name, written as the product writes them. Never call a component by the name of
  what it wraps or works with; never claim a setting the product does not have; word a setting's
  scope exactly as the product does ("for every project, or just the one you're working on",
  never "for yourself"). Record each term in `NOTES.md`.
- **Every claim checked.** A claim goes into the script or the draft only when `claims.md` marks
  it verified against the code. Version numbers, defaults and limits come from the code, never
  from memory. When the PRD and the code disagree, the code wins and the human decides the
  wording.
- **No LLM-isms.** No "delve", "seamless", "robust", "leverage", "unlock", "elevate", "in today's
  world", "it's worth noting", no "not just X, but Y" constructions, no closing line that
  repeats what came before. If a person would not say it, cut it.
- **Name a category, never other companies** (say "frontier labs" and list no names), unless the
  human asks for a comparison.
- **One fixture story.** The same names, ids and numbers in every capture, scene and sentence;
  numbers look plausible for what they depict.
- **Licence**: mention the product's licence only if the human wants it, and read it from the
  repository's LICENSE file.
- **Length**: decide it with the human at kickoff and record it; once the human says the length
  is fine, stop trimming.
- **Decisions**: once the human asks the lead to stop asking, the lead decides and reports what it
  decided.

## Project records

The project keeps these files at its root beside the pipeline. The kit ships none of them; the
lead creates and owns them. The video adds `edit/ISSUES.md` and `COSTS.md`
([guides/video.md](guides/video.md)); the post adds `post/outline.md`
([guides/blog.md](guides/blog.md)).

### `NOTES.md`: the decision log

Every human decision and correction, appended in order, written before anyone is briefed and
binding for every agent. One bullet per decision: what the human asked for (paraphrased, or the
exact wording when the words themselves are the decision, as for a script line or a title), the
rule that follows, and what changed. Group the kickoff decisions by medium; mark rejections so
nobody brings them back, and confirmations so nobody asks again. Prefix review notes with their
round and medium. Every patch to an engine file is recorded with the file and the reason, so a
kit update can re-apply it ([How the kit is used](#how-the-kit-is-used)).

```markdown
# Production notes

## Kickoff

- Media: video, then blog. Viewport 1920x1080 for both.
- Shared: audience platform engineers evaluating <product>; light theme; web and terminal
  captures. Term: the product says "workspace", never "project folder".
- Video: about 2 min, narration and music, no b-roll. Voice: <Voice>, style "warm and engaged,
  natural conversational pace". Pitch wording (fixed): "<exact approved line>".
- Blog: a how-to, 1,200-1,500 words, front matter `title`, `date`, `tags`.

## Decisions

- Video round 2: the first frame must not be black; end on a fade to black.
- REJECTED: the <motif> logo animation. Chosen: <the approved reveal>. Added to "Rejected styles".
- Blog round 1: crop the status table to the degraded row; keep everything else.
- Engine patch: fixtures/web/webcap/<file>.py, <what changed and why>. Re-apply after a kit update.

## Rejected styles

- From BRAND.md: <a colour, effect or motif the brand avoids>. All workstreams.
- Video round 1: <the element> ("<the human's words>"). Motion and edit.
```

### `HANDBOOK.md`: the project's own handbook

Lets the next agent pick the project up cold. Paths are relative to the project root. Sections:

- **Status**: per medium, which review round is done, what is open, which assets exist but are
  unused.
- **Target formats and output names**: the latest revision of each deliverable.
- **The product**: where it lives (the values of `PRODUCT_REPO`, `PRODUCT_WEB_DIST`,
  `PRODUCT_BIN`, `PRODUCT_URL`), mock or live mode, how its frontend was built.
- **The fixture story**: a pointer to `scenarios.md` and the rules it follows.
- **Brand**: written by the brand skill, one part per role. Rerun the skill rather than editing
  it by hand.
- **The design system** as data ([Design system](#design-system)), and the **editorial rules**
  the human has stated.
- **Captures**: one row per scenario: source, media, labels, boxes, clip length and key marks,
  the profile, the command to recapture it.
- **Per-medium tables**: for the video the timeline, motion scenes, b-roll picks and the score
  ([guides/video.md](guides/video.md)); for the post its sections and images.
- **Commands** that differ from these guides.
- **Review rounds**: one line per round and medium, what the human asked for and what changed.
  Decisions with their reasons stay in `NOTES.md`.

### Rejected styles

`NOTES.md` keeps one "Rejected styles" list for both media. Seed it from `BRAND.md`, "Things to
avoid", and add an entry every time the human rejects a look, a motif, a transition, a sound, a
delivery, an image treatment or a phrasing, before anyone is briefed. Each entry names what was
rejected, the round, the human's reason, and the workstreams it binds (see the example above).

Every brief quotes the entries for its workstream. The lead checks each preview and each build
against the list and purges a rejected element from every agent's work, the edit decision list,
the draft and `images.json` included. A look rejected in one medium is rejected in the other
unless the human says otherwise. Bring nothing back in a new form without asking. When a rejection
says something lasting about the brand, propose the change to `BRAND.md` too.

### `claims.md` and `scenarios.md`

**`claims.md`**: every claim either medium makes, in one table, before any script line or
paragraph is written. Read the docs or the PRD in full, then the parts of the product's code the
feature touches (commands, settings, UI routes, help text, defaults). The PRD says what was
intended; the code says what ships.

```markdown
| #   | Claim, as worded                                 | Source                                                     | Verified | Used in                    |
| --- | ------------------------------------------------ | ---------------------------------------------------------- | -------- | -------------------------- |
| 1   | `<product> init` writes `.<product>/config.toml` | `src/cli/init.rs:42`                                       | yes      | script 03, post "Set up"   |
| 2   | Projects can be renamed from Settings, Advanced  | PRD "Project settings"; `web/src/settings/Advanced.tsx:88` | yes      | post "Rename a project"    |
| 3   | Renaming keeps the project's history             | PRD "Project settings"                                     | no       |                            |
```

A claim is verified only when the code shows it. When the PRD and the code disagree, the code
wins and the lead asks the human how to treat it (a feature behind a flag, a renamed setting, a
default that changed). An unverified claim goes into neither medium.

**`scenarios.md`**: the one fixture story and the scenarios that show it. Every capture shows the
same imaginary project, account or dataset, so the web UI, the terminal, the motion graphics and
the prose agree. Write it once, as data, and let the web mock, the TUI fixtures and every scene
copy it from here:

```markdown
## Fixture story

| #   | Id         | Kind    | Shown as   | Related to | Changes during the clip              |
| --- | ---------- | ------- | ---------- | ---------- | ------------------------------------ |
| 1   | `acme-api` | project | `acme-api` | none       | `healthy` at the start               |
| 2   | `staging`  | env     | `staging`  | 1          | `healthy -> degraded` at clip second 4 |

## Scenarios

| Scenario    | Source | Media | User goal                          | Steps                                           | Shots and labels (boxes)                  | Fixture data                      |
| ----------- | ------ | ----- | ---------------------------------- | ----------------------------------------------- | ----------------------------------------- | --------------------------------- |
| `settings`  | web    | both  | rename a project                   | open Settings, then Advanced                    | `dialog` (boxes `dialog`, `name`, `save`) | project `acme-api`, 3 envs        |
| `first-run` | web    | video | create the first project           | type a name, press Create                       | `clip` (marks `name typed`, `created`)    | an empty account                  |
| `status`    | tui    | blog  | see which environments are healthy | run `<product> status` in the fixture workspace | `main` (box `table`)                      | `acme-api`, `staging` degraded    |
```

- Scenario, label and box names match `^[a-z0-9]+(-[a-z0-9]+)*$`; the label `clip` is reserved for
  a scenario's clip.
- Media is `video`, `blog` or `both`; it decides the capture profile a scenario needs.
- A graph in the story has no redundant (transitively implied) edges; check the data before
  capturing, because a fix afterwards costs a recapture and re-renders.
- One notation for the same data everywhere (a column of names, a unit, a version string).
- Keep it plausible and calm: things work, change and finish; no alarms unless the story is about
  one. Show only what the real product renders, named as the product names it.

The human approves `scenarios.md` (with the script or the outline) before any capture starts;
record the approval in `NOTES.md`.

## Mistakes and pitfalls

What went wrong in finished projects, for both media. Each medium guide and
[guides/capture.md](guides/capture.md) list their own.

| Area     | What went wrong                                                                                                    | Rule                                                                                                  |
| -------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Brief    | The lead misread a reference the human gave and steered the work toward the wrong genre or tone                   | Ask what a reference means to this person, or offer short excerpts early                              |
| Claims   | A script line or a paragraph described what the PRD planned, and the code shipped something else                  | Verify every claim against the code in `claims.md`; when they disagree, the human decides the wording |
| Terms    | A component was called by the name of something it wraps or works with                                            | Name things as the product's UI and help text do; record each term in `NOTES.md`                      |
| Fixtures | Two captures showed different project names or numbers                                                             | One fixture story in `scenarios.md`; every capture copies it                                          |
| Fixtures | A redundant dependency edge, or implausible fixture data, found after capture                                      | Review the fixture data for sense before capturing anything                                           |
| Reuse    | A post added to a video project linked clips captured under the video profile: the page showed their posters      | Recapture the clips the post needs with `--for both`; the reuse inventory lists them                  |
| Reuse    | Adding a video to a blog project changed the default viewport and every capture's size                             | Decide at `/mediatime`: recapture with `--for both`, or pin `VIEWPORT`; record it in `NOTES.md`       |
| Review   | A preview or a build containing an already-rejected element reached the human                                     | The lead reviews every output first; purge rejected elements from every agent's work                  |
| Review   | A teammate reported a still or a contact sheet as fine; it was not                                                 | The lead Reads every image and contact sheet itself                                                   |
| Team     | Messages crossed: agents reported on an old brief while a newer one sat in their inbox                             | Check whether the agent is running or idle and look at file timestamps before re-sending              |
| Team     | A watcher loop that searched for another agent's process matched its own command line and never ended              | Wait on files or explicit messages                                                                    |
| Files    | A capture overwritten in place was read half-written                                                               | Engines write to a temporary name and rename; read a capture only after its owner reports "final"     |
| Outputs  | A revision the human had reviewed was overwritten by the next render or build                                      | Pass `--next` for the first render or build after a review                                            |

## Licences and credits

- **Fonts**: the project's own, in `brand/fonts/` with their licences; `BRAND.md`, "Legal", says
  whether each allows use in video and on the web and asks for credit. Where `design.json` names
  none, the renderers use the system fonts (DejaVu Sans and DejaVu Sans Mono on Linux, Helvetica
  and Menlo on macOS); the kit ships no font.
- **Logo and brand assets**: the product owner's, in `brand/`; show trademark lines as
  `BRAND.md`, "Legal", asks.
- **Screenshots and clips**: images of the product, owned by the product's owner; the fixture
  story holds no real customer data.
- **Music samples** (video): VSCO 2 Community Edition (Versilian Studios, CC0 1.0, no
  attribution needed), the default, piano included; Salamander Grand Piano V3 (Alexander Holm, CC
  BY 3.0, credited on screen and in the video description) only when `project.json` `piano` is
  `salamander`, which takes the human's explicit consent. `setup.sh` downloads the selected
  libraries unless it runs with `--no-samples`. `music/CREDITS.md` records
  sources, files, licences and which instruments each library supplies; everything else in the
  score is synthesized.
- **B-roll** (video): generated with Gemini Omni; no attribution required. `broll/CREDITS.md`
  states this and holds a section for any CC BY clip added later. A b-roll still or clip reused in
  the post carries the same credit.
- **Narration** (video): Gemini TTS; no on-screen attribution.
- **Your product**: state its licence only if the human wants it, read from the repository's
  LICENSE file.

Credits on screen and in the video description are generated from these files
([guides/video.md](guides/video.md), "Subtitles and credits").
