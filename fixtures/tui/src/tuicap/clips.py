"""The `tuicap` command: capture the project's terminal stills and clips into captures/tui/.

    uv run tuicap                       # every scenario in fixtures/tui/product.py SHOTS
    uv run tuicap settings other        # just those, keeping the rest of manifest.json
                                        # (a scenario's clip entry survives a stills-only run)
    uv run tuicap --clips               # also render each CLIPS scenario as <scenario>/clip
    uv run tuicap --clips --for video   # clip.mp4 at 60 fps and the poster (blog: WebM + GIF + poster;
                                        # both: the mp4, then the WebM and GIF derived from it)
    uv run tuicap --clips --draft       # a fast, lower quality mp4 for previews
    uv run tuicap --selftest            # render a canned terminal; needs no product

--for defaults from project.json at the project root: media with video and blog is both, only
video is video, anything else blog.

The project's fixtures/tui/product.py (guides/capture.md, "TUI capture") defines SHOTS,
{scenario: function() -> (Recording, [tuicap.shots.Still])}, and/or CLIPS,
{scenario: function() -> (Recording, marks)}; at least one. Optional: prepare() (build the
fixture workspace; runs before capturing), TRUECOLOR ({hex: palette hex}, see palette.py) and
NOTES ({scenario or "scenario/label": text}, written to the manifest entry as `notes`).
Scenario and label names match ^[a-z0-9]+(-[a-z0-9]+)*$.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from . import design, manifest, palette
from .capture import prompt, synth_cli
from .encode import PROFILES
from .render import Geometry, Recording, cell_box, render_recording, render_still
from .shots import Still

FIXTURE = Path(__file__).resolve().parents[2]
ROOT = FIXTURE.parent.parent
OUT = ROOT / "captures" / "tui"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SOURCE = "tui"
CLIP_LABEL = "clip"  # a still of that name would race the clip's poster on clip.tmp.png and share its id
SELFTEST_LINES = 8
GUIDE = 'guides/capture.md, "TUI capture"'


class Job(NamedTuple):
    scenario: str
    kind: str  # "still" or "clip"
    rec: Recording
    stills: list[Still] | None
    marks: list[dict]
    out: Path
    truecolor: dict
    profile: str
    draft: bool
    notes: dict


def check_name(kind: str, value: str) -> str:
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise ValueError(f"{kind} {value!r}: expected lowercase words joined by hyphens ({NAME_RE.pattern})")
    return value


def default_profile(root: Path = ROOT) -> str:
    """The capture profile project.json asks for: both for video and blog media, video for
    video alone, blog otherwise (also when the file is absent or unreadable)."""
    try:
        media = json.loads((root / "project.json").read_text()).get("media", [])
    except (OSError, ValueError, AttributeError):
        return "blog"
    if not isinstance(media, list):
        return "blog"
    return "both" if {"video", "blog"} <= set(media) else "video" if "video" in media else "blog"


@lru_cache(maxsize=1)
def product():
    if not (FIXTURE / "product.py").exists():
        sys.exit(f"no capture module: create {FIXTURE / 'product.py'} defining SHOTS and/or CLIPS ({GUIDE})")
    if str(FIXTURE) not in sys.path:
        sys.path.insert(0, str(FIXTURE))
    module = importlib.import_module("product")
    if not (hasattr(module, "SHOTS") or hasattr(module, "CLIPS")):
        sys.exit(f"{FIXTURE / 'product.py'} defines neither SHOTS nor CLIPS ({GUIDE})")
    return module


def check_stills(scenario: str, stills: list[Still]) -> None:
    """ValueError for a bad or repeated label, the reserved `clip`, or a bad box name."""
    seen: set[str] = set()
    for still in stills:
        label = check_name("label", still.label)
        where = f"{scenario}/{label}"
        if label == CLIP_LABEL:
            raise ValueError(f"{where}: the label {CLIP_LABEL!r} is reserved for the scenario's clip")
        if label in seen:
            raise ValueError(f"{where}: label repeated within scenario {scenario!r}")
        seen.add(label)
        for name in still.boxes:
            check_name(f"{where} box", name)


def render_stills(scenario: str, rec: Recording, stills: list[Still], out: Path) -> list[dict]:
    """Render every still of a scenario into <out>/<scenario>/<label>.png; the manifest entries.
    The labels and box names are checked before anything is rendered."""
    check_stills(scenario, stills)
    geo, entries = Geometry(rec.cols, rec.rows), []
    for still in stills:
        width, height = render_still(rec, out / scenario / f"{still.label}.png", still.t)
        entries.append({"id": f"{scenario}/{still.label}", "kind": "still", "origin": "shots",
                        "file": f"{scenario}/{still.label}.png", "width": width, "height": height,
                        "scale": 2.0,
                        "boxes": {name: cell_box(geo, *cells) for name, cells in still.boxes.items()}})
    return entries


def render_clip(job: Job) -> dict:
    """Render a clip scenario in the job's profile; the manifest entry, paths relative to out."""
    info = render_recording(job.rec, job.out / job.scenario, "clip", job.profile, job.draft)
    entry = {"id": f"{job.scenario}/clip", "origin": "clip", **info}
    for key in ("file", "webm", "poster", "video"):
        if key in entry:
            entry[key] = f"{job.scenario}/{entry[key]}"
    if "video" in entry:
        entry["marks"] = job.marks
    return entry


def annotate(entries: list[dict], notes: dict) -> None:
    """Add `notes` to each entry: the text for its id, else the one for its scenario."""
    for entry in entries:
        text = notes.get(entry["id"], notes.get(entry["id"].split("/")[0]))
        if text:
            entry["notes"] = text


def _job(job: Job) -> tuple[str, str, list[dict]]:
    palette.TRUECOLOR.update(job.truecolor)  # workers may start fresh (spawn on macOS)
    if job.kind == "still":
        entries = render_stills(job.scenario, job.rec, job.stills or [], job.out)
        origin = "shots"
    else:
        entries, origin = [render_clip(job)], "clip"
    annotate(entries, job.notes)
    return job.scenario, origin, entries


def run(jobs: list[Job], out: Path) -> None:
    """Render the jobs in parallel, then merge each scenario's entries into the manifest."""
    workers = max(1, min(len(jobs), os.cpu_count() or 1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_job, jobs))
    for scenario, origin in dict.fromkeys((s, o) for s, o, _ in results):
        entries = [e for s, o, es in results if (s, o) == (scenario, origin) for e in es]
        path = manifest.update(out, SOURCE, scenario, origin, entries)
        for entry in entries:
            print(f"{path.parent / entry.get('video', entry['file'])}: {entry['width']}x{entry['height']}")


def selftest(out: Path, profile: str, draft: bool) -> None:
    output = "".join(f"\x1b[3{1 + i % 6}mline {i + 1}: box ─│┌┐└┘ block ▁▂▃▄▅▆▇█ braille ⣿⡇\x1b[0m\n"
                     for i in range(SELFTEST_LINES)).encode()
    rec, marks = synth_cli(prompt("~/selftest"), "print-test-pattern", output, 80, 14, seed=1)
    # Row 0 holds prompt and command, the output follows, the closing prompt is the next row.
    prompt_row = 1 + SELFTEST_LINES
    still = Still("screen", rec.duration - 0.05, {"prompt": (prompt_row, 0, prompt_row + 1, rec.cols)})
    run([Job("selftest", "still", rec, [still], [], out, {}, profile, draft, {}),
         Job("selftest", "clip", rec, None, marks, out, {}, profile, draft, {})], out)


def capture(names: list[str], clips: bool, out: Path, profile: str = "blog", draft: bool = False) -> None:
    mod = product()
    shots, available = getattr(mod, "SHOTS", {}), getattr(mod, "CLIPS", {})
    names = list(dict.fromkeys(names))
    for name in [*names, *shots, *available]:
        check_name("scenario", name)
    known = {**shots, **(available if clips else {})}
    unknown = set(names) - set(known)
    if unknown:
        sys.exit(f"unknown scenario(s): {', '.join(sorted(unknown))} (have {', '.join(known)})")
    if hasattr(mod, "prepare"):
        mod.prepare()
    common = {"out": out, "truecolor": getattr(mod, "TRUECOLOR", {}), "profile": profile, "draft": draft,
              "notes": getattr(mod, "NOTES", {})}
    jobs = []
    for name in [n for n in names or shots if n in shots]:
        rec, stills = shots[name]()
        jobs.append(Job(name, "still", rec, stills, [], **common))
    for name in [n for n in names or available if n in available] if clips else []:
        rec, marks = available[name]()
        jobs.append(Job(name, "clip", rec, None, marks, **common))
    if not jobs:
        sys.exit("tuicap: nothing to capture" + ("" if clips or not available else
                                               " (product.py defines only CLIPS: pass --clips)"))
    run(jobs, out)


def require_ffmpeg(args: argparse.Namespace) -> None:
    """Exit with a message when the run renders a clip and ffmpeg is not on PATH; without this
    the encoder's FileNotFoundError comes out of a pool worker, before the manifest merge."""
    if shutil.which("ffmpeg") or not (args.selftest or args.clips):
        return
    sys.exit("tuicap: --selftest renders a clip and needs ffmpeg on PATH" if args.selftest
             else "tuicap: --clips needs ffmpeg on PATH")


def check_design() -> None:
    """Load design.json and resolve the terminal font before rendering: a bad file or a missing
    font or logo exits with a message instead of raising out of a pool worker."""
    try:
        design.mono()
    except (ValueError, FileNotFoundError) as e:
        sys.exit(f"tuicap: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tuicap", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenarios", nargs="*", metavar="SCENARIO")
    parser.add_argument("--clips", action="store_true", help="also render each CLIPS scenario as <scenario>/clip")
    parser.add_argument("--for", dest="profile", choices=PROFILES,
                        help="capture profile (default: from project.json media)")
    parser.add_argument("--out", type=Path, help=f"output directory (default {OUT})")
    parser.add_argument("--draft", action="store_true", help="fast, lower quality mp4 (video and both)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    require_ffmpeg(args)
    check_design()
    profile = args.profile or default_profile()
    try:
        if args.selftest:
            selftest(args.out or OUT.parent / "tui-selftest", profile, args.draft)
        else:
            capture(args.scenarios, args.clips, args.out or OUT, profile, args.draft)
    except ValueError as e:
        sys.exit(f"tuicap: {e}")


if __name__ == "__main__":
    main()
