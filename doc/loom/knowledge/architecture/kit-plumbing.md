# Kit Plumbing

> install.sh, setup.sh, system-deps.sh, settings, installed folder map

## install.sh behavior

Usage `./install.sh <project-dir> [--force] [--no-system] [--setup]`. An unknown option, a second folder or none exits 2. The target must not be inside the kit (exit 2) or a non-directory. `abspath` resolves a not-yet-existing path without `realpath -m` (macOS has none).

The slug is derived from the folder basename: lowercase, other characters become single hyphens, `project` when nothing is left; a note on stderr says so when it differs from the folder name. It never fails on a name.

Copy set: every file and symlink under the kit (tar copy preserving exec bits and dotfiles), minus `.venv`, caches, `out`, `build`, `.git`, and the kit's own paths: `install.sh`, `claude-skills`, `claude-settings.json`, `claude-project.md`, the kit root CLAUDE.md, `doc`, `tests`, `.claude`, `.loom`, `.worktrees`, `captures`, `outputs`, `music/samples`. The project owns `.gitignore`, `music/CREDITS.md` and `broll/CREDITS.md`: copied when absent, never overwritten, even with `--force`.

`claude-project.md` becomes `<project>/CLAUDE.md` (a conflict without `--force`; a kit without it exits 1 "kit is incomplete" before writing). Every `claude-skills/<name>/` with a `SKILL.md` goes to `<project>/.claude/skills/<name>/` (brand, narration, mediatime); a folder missing `SKILL.md`, or no skills, exits 1 before writing. `project.json` is written as `{"slug": "<slug>", "media": []}` only when absent and is never a conflict; `/mediatime` fills `media`. `claude-settings.json` becomes `<project>/.claude/settings.json` only when absent; an existing one lacking the agent-teams env gets a note.

Without `--force`, any existing destination is listed (up to 40) and the script exits 1 with nothing written. `--force` overwrites and deletes nothing. After copying: `system-deps.sh` unless `--no-system`; `--setup` then `exec ./setup.sh`; otherwise the next steps end with `claude` and `/mediatime`.

## setup.sh behavior

Run by the lead inside the project, never with sudo. Flags: `--check` (change nothing), `--for video|blog|both`, `--no-samples`, `--help`; an unknown flag or medium exits 2. Without `--for`, scope comes from `<project>/project.json` `media` (parsed with grep and sed), and everything is checked when it is empty or absent. One `LEVEL ITEM HINT` line per item through `status`; any MISSING makes exit status 1, WARN is only counted. `main` order: commands, Python environments, GPU probe (video only), fonts, brand, skills, sample libraries, Chromium, Whisper, Gemini key, then `Summary: N MISSING, M WARN`. A sourcing guard lets tests call single functions.
- Video only: `xz`, `unzip`; ffmpeg MISSING unless it has libx264, prores_ks and aac (a WARN for `h264_nvenc` or `h264_videotoolbox`); the `edit`, `motion` and `music` environments; the GPU probe; design and logo checks; samples; Whisper model; Gemini key WARN.
- Blog only: the `post` environment; ffmpeg is WARN ("clips only").
- Shared: `uv`, `curl`, `tar` MISSING; `rg`, `tmux`, `claude` WARN; `fixtures/web` and `fixtures/tui` environments; fonts (system fonts, `tools/fonts.py` when `design.json` names families, terminal fallback fonts as WARN); brand freshness (`design.json` older than `<project>/BRAND.md` or a `brand/` file is WARN, ignoring `resolved.json` and `.local/*`); skills (`KIT_SKILLS` lists brand, narration, mediatime where `claude-skills/` is absent); Chromium (`playwright install chromium` in `fixtures/web`); libvpx-vp9, tested on captured `ffmpeg -encoders` output because `grep -q` under pipefail SIGPIPEs ffmpeg.

## system-deps.sh behavior

Never run by an agent; the human runs it outside Claude Code (`./system-deps.sh [--yes] [--dry-run] [--for video|blog|both]`). Default scope is both. Detects `brew` (Darwin), `apt-get` or `dnf` (Linux); any other manager prints the package list and exits 1. One `TABLE` of `command|apt|dnf|brew` rows: ffmpeg (`ffmpeg-free` on Fedora), curl, tar, ripgrep, tmux, DejaVu fonts, the Noto fonts (symbols, symbols 2, math as three Fedora packages), Noto Color Emoji; the video adds xz, unzip and Mesa (`--for blog` skips them). Extras: Homebrew and `uv` through their installers when missing; on apt, `uvx playwright@<version from fixtures/web/uv.lock> install-deps chromium`. Prints one list and asks `Continue? [Y/n]` once (`--yes` skips; `--dry-run` changes nothing). Uses `sudo` unless root or brew.

## claude-settings.json and .gitignore

`claude-settings.json`: `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"` and `enabledPlugins["frontend-design@claude-plugins-official"] = true`; no permissions or hooks. `.gitignore` covers `.venv/`, caches, `out/`, `build/`, `music/samples/`, `captures/*-selftest/`, `.env`, editor files, `brand/fonts/resolved.json`, `brand/fonts/.local/`, `.loom/work/`, `.worktrees/`. `outputs/` is not ignored: it is the deliverable and is committed.

## Installed project folder map

The project root holds `<project>/CLAUDE.md` (from `claude-project.md`), `README.md`, `HUMAN.md`, `guides/` (`capture.md`, `video.md`, `blog.md`), `project.json`, `setup.sh`, `system-deps.sh`, `tools/`, the engine folders `fixtures/web`, `fixtures/tui`, `post`, `edit`, `motion`, `music`, `narration`, `broll`, and `.claude/skills/` (brand, narration, mediatime) and `.claude/settings.json`. The lead adds `<project>/NOTES.md`, `<project>/HANDBOOK.md`, `<project>/BRAND.md`, `brand/`, `design.json`, `<project>/claims.md`, `<project>/scenarios.md`, `rates.json`; captures land in `captures/<source>/`; deliverables in `outputs/` and `outputs/blog/`. Each Python package is its own uv project with a `pyproject.toml`, `uv.lock` and venv; commands run from inside the package with `uv run --frozen`. A project is a copy: a kit update reaches it only through `install.sh <project-dir> --force`.
