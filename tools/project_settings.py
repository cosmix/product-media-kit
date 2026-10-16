"""The video's saved choices in project.json: frame rate (`fps`) and piano library (`piano`).

Read by setup (sample libraries), the captures, motion, music and the edit; written by
./configure.sh, which keeps every other key (`slug`, `media`).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {"fps": 30, "piano": "vsco"}


def _saved(path):
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")  # noqa: TRY004 - main and configure report a bad project.json as ValueError
    return data


def _validated(path, settings):
    """`settings` when its fps and piano are valid; ValueError naming `path` otherwise."""
    fps = settings["fps"]
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError(f"{path}: fps must be an integer from 1 to 120")
    if settings["piano"] not in ("vsco", "salamander"):
        raise ValueError(f"{path}: piano must be vsco or salamander")
    return settings


def read(root=ROOT):
    """project.json under `root` with DEFAULTS for absent keys; ValueError for a bad fps or piano."""
    path = Path(root) / "project.json"
    return _validated(path, DEFAULTS | _saved(path))


def ask(prompt, default, valid):
    while True:
        value = input(f"{prompt} [{default}]: ").strip() or default
        if valid(value):
            return value
        print("Please choose one of the listed values.")


def configure(root, fps=None, piano=None):
    """Save `fps` and `piano` in root/project.json, keeping its other keys. A choice not given
    keeps the saved one; one neither given nor saved is asked on a terminal, else ValueError.
    The merged result is validated before it is written, so a new value repairs a bad saved one."""
    path = root / "project.json"
    saved = _saved(path)
    if fps is None and piano is None and DEFAULTS.keys() <= saved.keys():
        return read(root)
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
    merged = _validated(path, DEFAULTS | saved | {"fps": fps, "piano": piano})
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(saved | {"fps": merged["fps"], "piano": merged["piano"]}, indent=2) + "\n")
    return read(root)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--fps", type=int, choices=range(1, 121), metavar="1–120")
    ap.add_argument("--piano", choices=("vsco", "salamander"))
    ap.add_argument("--get", choices=("fps", "piano"))
    args = ap.parse_args()
    try:
        if args.get:
            print(read(args.root)[args.get])
        else:
            print(json.dumps(configure(args.root, args.fps, args.piano)))
    except (ValueError, EOFError) as exc:
        ap.exit(2, f"{exc}\n")


if __name__ == "__main__":
    main()
