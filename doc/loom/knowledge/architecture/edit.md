# Edit

> compositor, EDL asset refs, outputs naming, render, subs, credits and share copy

## Modules (edit/)

The edit is one uv project (`editkit`; Python >= 3.12, numpy, moderngl, faster-whisper, pyloudnorm). Entry scripts run from `edit/` with `uv run`:
- `render.py`: the master and previews. `uv run render.py` full quality to `outputs/final-<slug>-v<N>.mp4` (muxes `edit/out/mix.wav` when present); `--preview` 540p at up to 30 fps with no grain, DOF or motion blur to `outputs/draft-...`; `--range A B`; `--contact [--every S]`; `--frames t...` to `edit/build/frames/`; `--fast`; `--share`; `--next`, `--revision vN`, `--out`. The frame rate is `<project>/edit/edl.py`'s `FPS`, else `compositor.project_fps()` (`project.json` `fps`, default 30). A placeholder guard (`require_real_assets`) stops a full render while any asset is a generated placeholder.
- `subs.py [--final] [--revision vN]` writes the `.srt` from the narration scripts timed by the Whisper words; `credits.py [--final] [--revision vN]` writes the description credits; `words.py` writes `edit/build/words.json`; `mix.py` writes `edit/out/mix.wav` (voice chain, music ducked under speech, sound design, -14 LUFS); `bg_test.py` is the self-test.
- `editkit/project.py` loads the project's `<project>/edit/edl.py`, which defines `END`, `build() -> Timeline` and optionally `BROLL_CLIPS`, `BUSY`, `FPS` (an override; without it the master renders at `project.json` `fps`, default 30).

## Scene model and compositor

`editkit/scene.py`: `Camera`, `Cursor`, `Plane` (a layer: source, start, end, placement), `Transition` (kind `cut`, `dissolve`, `push`, `zoom`), `Segment` (a scene; its optional `end` lets one segment span the scenes after it), `group_state`. `editkit/shots.py` has the EDL's helpers: narration word times from `narration/timeline.json` and `build/words.json` (`word`, `word_end`, `scene_starts`), `sync`/`anchor` to a clip's marks, and plane builders `fullframe`, `browser`, `terminal`, `cursor_for`.

`editkit/compositor.py`: `Quality` (res, fps defaulting to `project_fps()`, grain from `design.grain()`, dof, motion_blur, bloom, decode_scale; `PREVIEW` is the preview preset) and `Compositor`: GPU render targets, background, scene groups with transitions, per-layer depth of field, shutter-sampled motion blur (180 degree), bloom, grain. `gpu.py` is the OpenGL plumbing (EGL on Linux, CGL on macOS), `decode.py` streams video through ffmpeg pipes with a prefetch thread, `hw.py` decides the GL context, fast H.264 encoder (`h264_nvenc`, `h264_videotoolbox`, else libx264) and decode acceleration, `art.py` and `cards.py` draw title bars, the cursor sprite and the credit card (`credit_line(name, lines, size=22)`), `credit_data.py` reads the credit files of b-roll and music samples.

## Asset references (editkit/assets.py)

A key is `<kind>:<name>`: `web:<scenario>` or `tui:<scenario>` resolves `captures/<kind>/<scenario>/clip.mp4`, else `clip.webm` with a printed warning; `still:<source>/<scenario>/<label>` resolves `captures/<source>/<scenario>/<label>.png`; `motion:<scene>` and `motion_alpha:<scene>` resolve from `motion/out`; `broll:<clip>` from `broll/candidates`; `image:<card>` from `edit/build/art/`. Manifest entries are keyed by id (`<scenario>/<label>`) and the capture size is pixels divided by the entry's `scale`. Under `--for video` alone a clip entry's `file` is the poster PNG and the mp4 is its `video` field. A missing asset becomes a generated placeholder of the right shape, so the cut can be built and timed first.

## Outputs, share copy and colour

Deliverable names and revision rules: [architecture/outputs-and-reuse](outputs-and-reuse.md). `render.py --share` encodes the latest final as H.264 30 fps AAC to `outputs/final-<slug>-v<N>-share.mp4` and refuses to overwrite one. The encoder tags frames with a `setparams` bt709 filter ([mistakes/media-kit-merge](../mistakes/media-kit-merge.md)). Intermediates stay put: `edit/out/mix.wav`, `edit/build/`.
