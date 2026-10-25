# Narration

> timeline.json the only clock, tts skill, listening judge, costs.py and usage.jsonl

## timeline.json is the only clock

`narration/build_timeline.py` rebuilds `narration/timeline.json` from `narration/sections.json` and the processed takes in `narration/final/`, with or without a voice. Sections play in list order from `first_start`; each later one starts after `gap` seconds of silence (default 0.5); `pin` fixes a section start, `scene_start` a scene start, `insert` places a line at a fixed time without adding a scene. A section's length is its take in `final/`, else its `duration`, else the reading time of its on-screen `text` (about 15 characters per second, minimum hold 2.5 s). With no takes at all the timeline has an empty `narration` list and the scene starts. A scene's key is `key`, else the name after its first `_`. `uv run build_timeline.py --sources` prints the take list that `process.sh` reads.

`process.sh` rebuilds `final/` from the chosen takes in `sources.json` (trims ends, caps pauses at 0.45 s, tempo +4%, 48 kHz). The lead owns `sections.json` and `timeline.json`; the edit (`editkit/shots.py`), the music (`scorekit/timing.py`) and the motion scenes read the timeline and never take a time from a message. When it changes, send absolute windows.

## TTS skill and the listening judge

`claude-skills/narration/` (installed as `.claude/skills/narration/`): `tts.py` sends a script to Gemini TTS (`gemini-3.8-flash-tts`, prebuilt voice, optional style direction) and writes a 24 kHz mono WAV; needs `GEMINI_API_KEY`; one narrator per file; each call logs token counts. The human chooses the tone and the voice; the agent renders variants in the stated tone and never picks alone unless told, recorded in `<project>/NOTES.md`.

`tools/listen.py "question" file... [--model NAME]` uploads audio or video to Gemini and prints the answer (the guide says to pass `--model gemini-3.5-flash`). Scores drift between identical calls, so it screens takes for misreads and compares variants; it never picks the tone or voice. Without a key the lead measures with ffmpeg (`ebur128`, `silencedetect`).

## Cost records

`tools/usage_log.py` appends one JSON line per paid Gemini call to `usage.jsonl` at the project root (`tts.py`, `tools/listen.py`, `tools/genvideo.py` and `music/lyria.py` call it; b-roll: [architecture/broll](broll.md), Lyria: [architecture/music](music.md)); its `slim()` strips base64 blobs from a response dump for the metadata files. `uv run tools/costs.py` prices the log with the lead's `rates.json` and rewrites `<project>/COSTS.md`, which is never hand-edited; script `lyria` is grouped as the `music` workstream. Token rates are USD per 1M tokens, one number or a table per modality, thinking priced as text output; a model with `per_call` (Lyria: $0.08 for `lyria-3.5`, $0.04 for `lyria-3-clip-preview`, read 2026-10-25) is priced at that rate per line with `ok` true, so a failed or refused call adds $0; a model with `per_second` (Gemini Omni) is priced as that rate times the logged clip seconds, so its input tokens, images included, are counted in `<project>/COSTS.md` but never priced, and a failed attempt (no clip) adds $0. A `null` or absent rate counts $0 and is listed as unpriced. Rejected and failed calls are logged too; the lead runs `costs.py` after every batch and reports the total. `tests/test_costs.py` covers the pricing.
