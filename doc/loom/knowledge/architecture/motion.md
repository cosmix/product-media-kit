# Motion

> motion graphics renderer: scene modules, lib, encode, logo, manifest

## Renderer and scenes (motion/)

One uv project (Python >= 3.12; skia-python, moderngl, numpy, Pillow). `uv run render.py <scene> [--duration s] [--alpha] [--variants] [--contact] [--fps n] [--still t]` (`--fps` defaults to `project.json` `fps`, 30 when absent) renders the project's `motion/scenes/<scene>.py`, a module defining `SCENE`, a `lib.scene.Scene` subclass authored in nominal seconds and retimed uniformly by `--duration`. Output: `motion/out/<scene>.mp4` (H.264) or a transparent `motion/out/<scene>_alpha.mov` (ProRes 4444), and `motion/out/manifest.json` with the retimed marks the edit reads. `uv run render.py --selftest` renders the kit's own scene (a still, a contact sheet, a 2 s clip) to check the GPU and encoder; `render_all.sh` renders every scene.

## lib

- `gfx.py`: Skia GPU context (EGL on Linux, CGL on macOS), the design-system palette, typography and drawing primitives (glow strokes, cards, rules). Everything is authored in 1920x1080 logical units and scaled at render time.
- `design.py`: design.json loader with the same schema as the other loaders ([architecture/brand-and-design](brand-and-design.md)).
- `logo.py`: `logo.draw(canvas, x, y, width)` draws design.json `logo` (`on_dark` or `on_light` per the background) with Skia's SVG module or as a PNG; `logo.size`.
- `ui.py`: perspective panes, status glyphs, connectors, typed code. `ease.py`: easing. `scene.py`: the Scene base. `selftest.py`: the self-test scene.
- `encode.py`: `Writer` (ffmpeg raw frames to H.264 or ProRes), `contact_sheet`, `save_png`. The H.264 path tags frames with a `setparams` bt709 filter and converts with the BT.709 matrix ([mistakes/media-kit-merge](../mistakes/media-kit-merge.md)).

Reuse: a still or segment of a motion scene reaches a post through `postkit add motion/<scene>/<label> motion/out/<scene>.mp4 --at T` ([architecture/outputs-and-reuse](outputs-and-reuse.md)).
