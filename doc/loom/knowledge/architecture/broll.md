# Broll

> genvideo.py: Omni b-roll, image modes, frame: continuity, validation, retry

## tools/genvideo.py

PEP 723 script run from the project root (`uv run tools/genvideo.py [--only <id>]`, google-genai, needs `GEMINI_API_KEY`). Gemini Omni only (`gemini-omni-1.1-flash`, Interactions API, inline delivery, 16:9 1080p); Veo is never used. Reads `broll/gen/shots.json`, a list of `{"id", "prompt"}` with optional `images` (paths inside the project, kept in `<project>/brand/` with the other brand assets) and `mode`; writes `broll/gen/omni/<id>.mp4` and `<id>.json`.

- `MODES`: `first_frame` (1 image, task `image_to_video`), `first_last` (2: `images[0]` first frame, `images[1]` last, `image_to_video`), `reference` (1-6, `reference_to_video`, the prompt names `<IMAGE_REF_0>`..`<IMAGE_REF_{n-1}>`). Image parts go before the text part in `input`; `generation_config.video_config.task` carries the task. A text-only shot sends the prompt string unchanged.
- `validate(shot, ids)` is the single check, returning the loaded images (`path`, `mime`, `sha256`, `data`): id unique and `[A-Za-z0-9_-]+`, prompt a non-empty string, `images` a list of strings with a `mode` (and `mode` only with `images`), image count per mode, each path resolved (symlinks followed) and `is_relative_to` the project, `st_size` against the 7 MB per-image cap before reading, 20 MB raw total per shot, mime from magic bytes (png, jpeg, webp), `<IMAGE_REF_n>` exactly 0..n-1 in `reference` and none elsewhere. Every error is a `ValueError` starting `[<id>]`. The caps are the kit's; the Omni docs state none.
- `main()` skips shots whose mp4 exists without validating them, validates every other selected shot, exits listing all errors before `genai.Client()` exists, and exits `no shot <id>` when `--only` matches nothing. Three workers render, parents before children ("frame: entries and tools/broll_frames.py" below).
- `run(client, shot, images)`: the retry (two attempts) wraps only `generate`, the paid call plus decoding into `.<id>.tmp.mp4`; a failed attempt deletes the tmp file. `finish` runs once after it: `seconds()` (ffprobe, None when missing), the usage log line, `<id>.json` written atomically (model, prompt, config, `task` or null, `seconds`, timing, attempts, interaction, and `mode` plus `images` with sha256), then the mp4 moved into place last, because the skip check keys on the mp4. An OSError there reports `FAILED after the paid call` and keeps the tmp clip.

Costs: `tools/costs.py` prices Omni by `per_second` in `rates.json` times the logged clip seconds; image input tokens are logged and counted in `<project>/COSTS.md` but not priced, and a failed attempt costs 0 ([architecture/narration](narration.md), "Cost records").

## frame: entries and tools/broll_frames.py

An `images` entry `frame:<shot id>`, `frame:<shot id>@last` or `frame:<shot id>@<seconds>` names a frame of another shot's clip, in any mode (continuation with `first_frame`, a bridge with `first_last`, consistency with `reference`). `tools/broll_frames.py` holds the grammar (`FRAME`, `parse`, `parents`) and the extraction (`extract`, `ffmpeg_png`): `-sseof -1 ... -update 1` for the last frame, `-ss <t> ... -frames:v 1` for a time, into a per-call `mkstemp` file then `os.replace` to `broll/gen/frames/<parent>@<at>.png` (two children may extract the same frame at once). ffmpeg exits 0 and writes nothing for a time past the end, so an empty file counts as failure.

- `genvideo.load_frame` checks the parent is in shots.json and is not the shot itself; a parent in `pending` (rendered later this run) is left out of up-front validation; an unrendered parent outside the run (`--only`) is an error. A rendered parent's frame is extracted and loaded through `load_image` during validation, so errors cost nothing.
- `plan()` validates, then orders jobs with `graphlib` (a cycle is reported before any call). `main()` submits them parents-first to the FIFO 3-worker pool; `run_after` waits on the parents' futures, skips the child when one did not end `ok`, and otherwise re-runs `validate()` to extract fresh frames before the paid call.
- `skip_rendered` warns of every rendered shot in shots.json (picked or not, so `--only <parent>` warns too) whose frame parent renders again this run; there is no other stale detection.
- `<id>.json` records a frame image as `{path, sha256, source}`.

## Exporting b-roll for reuse

`export-broll.sh <dest-dir>` runs `tools/export_broll.py`. It exports every rendered clip in `broll/gen/omni/`, whether or not any video used it, because the user treats generated b-roll as expensive and valuable. A clip missing its `<id>.json` is still exported, with its metadata rebuilt from `broll/gen/shots.json`. Credited stock clips from `broll/candidates/` are exported as well. Each clip gets `<dest>/<slug>/<id>.mp4`, `<id>-contact.png` (12 frames, 4x3) and a `<id>.json` sidecar, and the folder gets an `INDEX.md`. `<dest>/catalog.json` and `CATALOG.md` are merged: an export replaces only its own slug's entries.
