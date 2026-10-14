# Startup choices

At the start of a new video project, ask the user for the frame rate (suggest 30 fps)
and whether they want VSCO only (CC0, no attribution) or Salamander Grand Piano
(CC BY 3.0, requires attribution on screen and in the description). Use VSCO unless
the user explicitly selects Salamander. Record their answers before rendering:

```bash
./configure.sh --fps 30 --piano vsco
```

`project.json` is the source of truth for these choices. Reuse saved answers when
resuming. Render captures, motion and the master at that frame rate. Omit `FPS` from
`edit/edl.py` so the master inherits the setting, and omit motion's `--fps` unless the
user requests an override. If other instructions suggest 60 fps, use the saved rate.
Never download or use Salamander without explicit consent. If the user asks you to
decide everything, save 30 fps and VSCO. Music is optional; `./setup.sh --no-samples`
skips downloads when no sampled instruments are needed.

To share the project, run `./export.sh --output ../project.tar.gz`. Keep original
project assets; the exporter omits restorable dependencies. The recipient extracts
the archive and runs `./inflate.sh` (or `./inflate.sh --no-system` when system
packages are already installed). API keys must be supplied on the recipient's machine.
