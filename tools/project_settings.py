"""The video's saved choices in project.json: frame rate (`fps`), piano library (`piano`) and the
music source (`music`).

Read by setup (sample libraries), the captures, motion, music and the edit; written by
./configure.sh, which keeps every other key (`slug`, `media`). `fps` and `piano` are asked for
together; `music` is optional (scorekit's sample score when absent) and set on its own.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {"fps": 30, "piano": "vsco", "music": "score"}
ASKED = ("fps", "piano")  # configure() asks for these when neither given nor saved
MUSIC = ("score", "lyria-3.5", "lyria-3-clip-preview", "none")


def _saved(path):
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")  # noqa: TRY004 - main and configure report a bad project.json as ValueError
    return data


def _validated(path, settings):
    """`settings` when its fps, piano and music are valid; ValueError naming `path` otherwise."""
    fps = settings["fps"]
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError(f"{path}: fps must be an integer from 1 to 120")
    if settings["piano"] not in ("vsco", "salamander"):
        raise ValueError(f"{path}: piano must be vsco or salamander")
    if settings["music"] not in MUSIC:
        raise ValueError(f"{path}: music must be one of {', '.join(MUSIC)}")
    return settings


def read(root=ROOT):
    """project.json under `root` with DEFAULTS for absent keys; ValueError for a bad fps, piano or music."""
    path = Path(root) / "project.json"
    return _validated(path, DEFAULTS | _saved(path))


def ask(prompt, default, valid):
    while True:
        value = input(f"{prompt} [{default}]: ").strip() or default
        if valid(value):
            return value
        print("Please choose one of the listed values.")


def _fps_and_piano(saved, fps, piano):
    """{"fps", "piano"}: each the given value, else the saved one, else asked on a terminal."""
    fps = fps if fps is not None else saved.get("fps")
    piano = piano or saved.get("piano")
    if fps is None or piano is None:
        if not sys.stdin.isatty():
            raise ValueError("Ask the user for frame rate and piano choice, then run "
                             "./configure.sh --fps 30 --piano vsco (or salamander).")
        if fps is None:
            fps = int(ask("Frame rate (24, 25, 30, 50, 60, or another integer 1–120)",
                          str(DEFAULTS["fps"]), lambda s: re.fullmatch(r"[0-9]+", s) and 1 <= int(s) <= 120))
        if piano is None:
            piano = ask("Piano: vsco (CC0, no attribution) or salamander "
                        "(grand piano, requires on-screen CC BY 3.0 attribution)",
                        DEFAULTS["piano"], lambda s: s in ("vsco", "salamander"))
    return {"fps": fps, "piano": piano}


def configure(root, fps=None, piano=None, music=None):
    """Save the given choices in root/project.json, keeping its other keys. `music` alone is saved
    as is. Otherwise a choice of fps or piano not given keeps the saved one; one neither given nor
    saved is asked on a terminal, else ValueError. The merged result is validated before it is
    written, so a new value repairs a bad saved one."""
    path = root / "project.json"
    saved = _saved(path)
    new = {}
    if fps is not None or piano is not None or (music is None and not set(ASKED) <= saved.keys()):
        new = _fps_and_piano(saved, fps, piano)
    if music is not None:
        new["music"] = music
    if not new:
        return read(root)
    _validated(path, DEFAULTS | saved | new)
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(saved | new, indent=2) + "\n")
    return read(root)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--fps", type=int, choices=range(1, 121), metavar="1–120")
    ap.add_argument("--piano", choices=("vsco", "salamander"))
    ap.add_argument("--music", choices=MUSIC)
    ap.add_argument("--get", choices=tuple(DEFAULTS))
    args = ap.parse_args()
    try:
        if args.get:
            print(read(args.root)[args.get])
        else:
            print(json.dumps(configure(args.root, args.fps, args.piano, args.music)))
    except (ValueError, EOFError) as exc:
        ap.exit(2, f"{exc}\n")


if __name__ == "__main__":
    main()
