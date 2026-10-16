# Entry Points

> Key files agents should read first to understand the codebase.
> A summary of the current tree: correct a section in place with `replace-section`.

## Capture CLIs

- `uv run python -m webcap.capture [scenarios...] [--clips] [--for video|blog|both] [--draft] [--out DIR] [--selftest]` from `fixtures/web` (`fixtures/web/webcap/capture.py`, `main`); also `webcap.server --scene NAME` (mock preview), `webcap.probe` (choreography stills), `webcap.verify` (clip smoothness). The project module contract: [architecture/webcap](architecture/webcap.md).
- `uv run tuicap [scenarios...] [--clips] [--for ...] [--out DIR] [--draft] [--selftest]` from `fixtures/tui` (`fixtures/tui/src/tuicap/clips.py`, `main`). Contract: [architecture/tuicap](architecture/tuicap.md).
Both read `<project>/project.json` for the default profile and exit with a message when the project's product module is missing or breaks its contract.

## Blog

`uv run postkit build [--final] [--next | --revision vN] | check [--file PATH] | add <source>/<scenario>/<label> <file> [--at T | --from T --to T] | selftest [--root DIR]` from `post/` (`post/src/postkit/cli.py`). See [architecture/postkit](architecture/postkit.md).

## Video

From each folder with `uv run`: `edit/render.py` (master, `--preview`, `--range`, `--contact`, `--share`, `--frames`), `edit/subs.py`, `edit/credits.py`, `edit/words.py`, `edit/mix.py`, `edit/bg_test.py`; `motion/render.py <scene>`; `music/render.py`; `narration/build_timeline.py` and `narration/process.sh`. Project-owned inputs: `<project>/edit/edl.py`, `motion/scenes/<scene>.py`, `<project>/music/arrangement.py`, `narration/sections.json`. See [architecture/edit](architecture/edit.md), [architecture/motion](architecture/motion.md), [architecture/music](architecture/music.md), [architecture/narration](architecture/narration.md).

## Project-root tools

PEP 723 scripts run with `uv run` from the project root: `tools/fonts.py [--check]` (font resolution), `tools/listen.py` (listening judge), `tools/genvideo.py` (b-roll with Gemini Omni), `tools/costs.py` (prices `usage.jsonl` into `<project>/COSTS.md`), `tools/usage_log.py` (library). `claude-skills/brand/check.py [PROJECT_ROOT]` (install.sh copies it to `<project>/.claude/skills/brand/check.py`) prints `ok`, `WARN`, `MISSING` and exits 1 on any `MISSING`; `claude-skills/narration/tts.py` renders speech; `claude-skills/mediatime/SKILL.md` is the kickoff.

## Kit scripts

- `./install.sh <project-dir> [--force] [--no-system] [--setup]`: copies the kit into a project; exit 2 on bad usage, 1 on conflicts or an incomplete kit.
- `./setup.sh [--check] [--for video|blog|both] [--no-samples]`: the lead runs it in the project; `--check` changes nothing; exit 1 when any item is MISSING.
- `./system-deps.sh [--yes] [--dry-run] [--for video|blog|both]`: the only script needing administrator rights; a human runs it in their own terminal, never an agent.
- `sh tests/smoke.sh <kit-dir>`: end-to-end install and selftests in a scratch project.
Details: [architecture/kit-plumbing](architecture/kit-plumbing.md). The guides to read for a role: `README.md`, `guides/capture.md`, `guides/video.md`, `guides/blog.md`.
