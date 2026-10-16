# Stack & Dependencies

> Project technology stack, frameworks, and key dependencies.
> A summary of the current tree: correct a section in place with `replace-section`.

## Python packages

Each folder is its own uv project with a committed `uv.lock` (run with `uv run --frozen`); dev group pytest>=9.1.1 and ruff.
- `fixtures/web` (`web-capture`, python >=3.13): aiohttp>=3.14.3, numpy>=2.5.3, playwright>=1.63.0.
- `fixtures/tui` (`tui-capture`, python >=3.12, build `uv_build>=0.12.22,<0.13.0`): ptyprocess, pyte, skia-python, wcwidth.
- `post` (`postkit`, python >=3.13, same build bound): pillow>=12.3.0; per-file ignore of `I001` for the frozen `tests/test_contracts.py`.
- `edit` (`editkit`, python >=3.12): moderngl, glcontext, numpy, pillow, scipy, soundfile, pyloudnorm, faster-whisper, onnxruntime (macOS Intel keeps older moderngl, glcontext and onnxruntime through platform markers).
- `motion` (python >=3.12): skia-python, moderngl, glcontext, numpy, pillow.
- `music` (`scorekit`, python >=3.12): numpy, scipy, soundfile, soxr, pyloudnorm, matplotlib, pedalboard.
- `tests` (`kit-tests`, python >=3.13): no runtime deps.
- PEP 723 scripts: `tools/fonts.py` (fonttools), `tools/listen.py` and `tools/genvideo.py` (google-genai), `tools/costs.py`; `claude-skills/brand/check.py` (fonttools, pillow), `claude-skills/narration/tts.py` (google-genai).
- Every package's `uv_build` bound stays in step with the uv the kit locks with (0.12.x); a stale bound makes every build print a warning.

## System tools

- ffmpeg: video needs libx264, prores_ks and aac (MISSING otherwise); blog clips need libvpx-vp9 (WARN). Hardware encoders `h264_nvenc` and `h264_videotoolbox` are optional.
- Playwright's Chromium (`setup.sh` installs it), tmux (`tmux_clip.py`), `fc-list` and `fc-match` (`tuicap/fonts.py`, `tools/fonts.py`, `postkit/design.py`), `xz` and `unzip` (sample archives), Mesa EGL on machines without a GPU driver.
- tuicap fallback fonts are looked up by family through fontconfig (DejaVu Sans Mono, Noto Sans Symbols2, Noto Sans Symbols, Noto Sans Math, Noto Color Emoji on Linux; Menlo, Apple Symbols, Apple Color Emoji on macOS).
- External services: Gemini (`GEMINI_API_KEY`) for narration (TTS), generated b-roll (Omni) and the listening judge; billed per request and estimated in `<project>/COSTS.md`.
- Sample libraries are fetched by `setup.sh` into `music/samples/`: VSCO-2 CE always, Salamander Grand Piano only when `project.json` `piano` is `salamander`.

## Kit scripts

Scripts are bash with `set -euo pipefail` (`tests/smoke.sh` is POSIX sh with `set -eu`). `setup.sh` runs `uv sync --frozen` per package. `system-deps.sh` reads the Playwright version from `fixtures/web/uv.lock`. `claude-settings.json` sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and enables the `frontend-design@claude-plugins-official` plugin. Supported hosts: apt, dnf, Homebrew; any other package manager (Arch's pacman included) prints the package list and exits 1. Platforms: Linux and macOS (`doc/mac_port_testing.md` lists the macOS checks).
