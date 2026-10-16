# Capture And Postkit

> Pipefail grep, Pillow errors, guides ahead of code

## `grep -q` into a pipe under `pipefail` reported a missing encoder

**What happened**: `ffmpeg -encoders | grep -qw libvpx-vp9` in `setup.sh` returned 141 (SIGPIPE on ffmpeg once `grep -q` exited), so the `!` test warned that libvpx-vp9 was missing on an ffmpeg that has it.
**Why**: `set -o pipefail` makes the pipeline's status the first failing command's.
**Prevention**: never pipe into `grep -q` under `pipefail`; capture the output first and test it with a here-string.
**Fix**: `check_ffmpeg` captures `ffmpeg -hide_banner -encoders` into a variable.

## Pillow `verify()` and `open()` did not catch every bad capture

**What happened**: three ways a capture escaped `BuildError`: `Image.verify()` raises `SyntaxError` (not `OSError`) on a PNG chunk CRC error; `verify()` never decodes pixels, so a valid CRC with a broken zlib stream passed and failed later in `load()`; `Image.DecompressionBombError` (images over about 179 million pixels) subclasses `Exception`, so it escaped as a traceback.
**Why**: Pillow's exceptions are not under one base class.
**Prevention**: validate a capture with `Image.open` plus `img.load()` and catch `(OSError, ValueError, SyntaxError, Image.DecompressionBombError)`, in `build` and in `check`.
**Fix**: `assemble._unreadable_images` and `check._size_problems` catch all four; tests `test_build_rejects_a_decompression_bomb_capture` and `test_check_reports_a_decompression_bomb_image` in `post/tests/test_postkit.py`.

## Guides described engine behaviour the code does not have

**What happened**: the brand `SKILL.md` said postkit reads the background and text colours for frames (frames use fixed `CHROMES` colours; only tuicap reads `colors.background` and `colors.text`); `setup.sh` called ffmpeg "clips only; stills work without it" while `--clips` and `--selftest` spawned ffmpeg unguarded and ended in a `FileNotFoundError` traceback.
**Why**: guides were written from the plan's interfaces before the engines settled.
**Prevention**: before documenting a key, flag or optional dependency, find its consumer in the code; run each command's `--help` and quote flags from it.
**Fix**: `SKILL.md` corrected; `clips.require_ffmpeg` exits with `tuicap: --clips needs ffmpeg on PATH`; `webcap.capture` exits with `--clips needs ffmpeg with <encoders>: <problem>`.
