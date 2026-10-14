"""Saved startup choices, shared by setup and every video workstream."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {"fps": 30, "piano": "vsco"}


def read(root=ROOT):
    path = Path(root) / "project.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    settings = DEFAULTS | data
    fps = settings["fps"]
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError(f"{path}: fps must be an integer from 1 to 120")
    if settings["piano"] not in ("vsco", "salamander"):
        raise ValueError(f"{path}: piano must be vsco or salamander")
    return settings


def ask(prompt, default, valid):
    while True:
        value = input(f"{prompt} [{default}]: ").strip() or default
        if valid(value):
            return value
        print("Please choose one of the listed values.")


def configure(root, fps=None, piano=None):
    path = root / "project.json"
    settings = read(root)
    if path.exists() and fps is None and piano is None:
        return settings
    if fps is None or piano is None:
        if not sys.stdin.isatty():
            raise ValueError("Ask the user for frame rate and piano choice, then run "
                             "./configure.sh --fps 30 --piano vsco (or salamander).")
        if fps is None:
            fps = int(ask("Frame rate (24, 25, 30, 50, 60, or another integer 1–120)",
                          str(settings["fps"]), lambda s: s.isdigit() and 1 <= int(s) <= 120))
        if piano is None:
            piano = ask("Piano: vsco (CC0, no attribution) or salamander "
                        "(grand piano, requires on-screen CC BY 3.0 attribution)",
                        settings["piano"], lambda s: s in ("vsco", "salamander"))
    settings.update(fps=fps, piano=piano)
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return settings


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
