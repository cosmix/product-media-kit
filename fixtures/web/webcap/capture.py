"""Capture the project's web stills and clips (fixtures/web/product.py) and their manifest.

    uv run python -m webcap.capture                        # every SHOTS scenario, into captures/web/
    uv run python -m webcap.capture settings --clips       # one scenario, its clip too
    uv run python -m webcap.capture --clips --for video    # clips as mp4 at scale 2, project.json fps
    uv run python -m webcap.capture tour --clips --draft   # a quick scale-1 check of the choreography
    uv run python -m webcap.capture --selftest             # built-in page, into captures/web-selftest/

--for defaults to project.json's media: both for video and blog, video, else blog.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from webcap import manifest, selftest
from webcap.browser import launch, open_page, serving, session
from webcap.director import Director
from webcap.encode import ffmpeg_problem
from webcap.profiles import NAMES, STILL_SCALE, Profile, profile
from webcap.project import ROOT, default_profile, product
from webcap.shots import Shooter

SOURCE = "web"
OUT = ROOT / "captures/web"
SELFTEST_OUT = ROOT / "captures/web-selftest"


async def fonts_in_use(module, world, browser) -> dict:
    """Which font files the page actually rendered with, per FONT_PROBES selector."""
    probes = getattr(module, "FONT_PROBES", None)
    if not probes:
        return {}
    scene, path, selectors = probes
    page = await open_page(module, world, browser, scene, path, 1.0)
    try:
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("DOM.enable")
        await cdp.send("CSS.enable")
        root = (await cdp.send("DOM.getDocument", {"depth": -1}))["root"]["nodeId"]
        report = {}
        for label, selector in selectors.items():
            found = await cdp.send("DOM.querySelector", {"nodeId": root, "selector": selector})
            if not found["nodeId"]:
                report[label] = "not found"
                continue
            fonts = await cdp.send("CSS.getPlatformFontsForNode", {"nodeId": found["nodeId"]})
            report[label] = {f["familyName"]: f["glyphCount"] for f in fonts["fonts"]}
        return report
    finally:
        await page.context.close()


async def capture_shots(module, world, browser, scenario: str, out: Path) -> list[dict]:
    """Run SHOTS[scenario] on a fresh page; its still entries."""
    page = await open_page(module, world, browser, scenario, "/", STILL_SCALE)
    try:
        shooter = Shooter(page, out, scenario, STILL_SCALE, world)
        await module.SHOTS[scenario](shooter)
    finally:
        # A page left open keeps its sockets, and the world keeps sending to them.
        await page.context.close()
    return shooter.entries


async def capture_clip(module, world, browser, scenario: str, out: Path,
                       prof: Profile) -> list[dict]:
    """Record CLIPS[scenario] from CLIP_PATHS (default "/"); the clip's entry, then the entries
    of the stills its director took."""
    path = getattr(module, "CLIP_PATHS", {}).get(scenario, "/")
    page = await open_page(module, world, browser, scenario, path, prof.scale)
    director = Director(page, world, out, prof)
    try:
        await director.start(scenario)
        await module.CLIPS[scenario](director)
        return [await director.finish(), *director.stills]
    finally:
        await director.abort()
        await page.context.close()


async def run(module, shots: list[str], clips: list[str], out: Path, prof: Profile) -> None:
    async with session(module) as (world, browser):
        fonts = await fonts_in_use(module, world, browser)
        if fonts:
            manifest.annotate(out, SOURCE, "fonts", fonts)
            print("fonts:", fonts)
        for scenario in dict.fromkeys([*shots, *clips]):
            fresh, origins = [], []
            if scenario in shots:
                fresh += await capture_shots(module, world, browser, scenario, out)
                origins.append("shots")
            if scenario in clips:
                fresh += await capture_clip(module, world, browser, scenario, out, prof)
                origins.append("clip")
            # Entries of the origin this run did not capture stay (a clip and its stills when
            # only SHOTS ran, and the other way round).
            manifest.update(out, SOURCE, scenario, fresh, origins)
            print(f"{scenario}: " + ", ".join(e["file"] for e in fresh), flush=True)


async def run_selftest(out: Path, prof: Profile) -> int:
    module, scenario = selftest.MODULE, selftest.SCENARIO
    world = selftest.world()
    origins = ["shots"]
    async with serving(selftest.app()), launch() as browser:
        entries = await capture_shots(module, world, browser, scenario, out)
        problem = selftest.check(entries, out, prof)
        missing = ffmpeg_problem(prof)
        if problem is None and missing is None:
            entries += await capture_clip(module, world, browser, scenario, out, prof)
            origins.append("clip")
            problem = selftest.check(entries, out, prof)
        elif problem is None:
            print(f"{missing}: no clip", file=sys.stderr)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    path = manifest.update(out, SOURCE, scenario, entries, origins)
    for entry in entries:
        image = out / entry.get("video", entry["file"])  # the file the entry's size describes
        print(f"{image}: {entry['width']}x{entry['height']}, boxes {entry['boxes']}")
    print(f"selftest ok ({prof.name} profile): {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m webcap.capture", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenarios", nargs="*", help="SHOTS / CLIPS scenario names (default: all)")
    parser.add_argument("--clips", action="store_true", help="also record the CLIPS scenarios")
    parser.add_argument("--for", dest="profile", choices=NAMES,
                        help="capture profile (default from project.json's media; blog without it)")
    parser.add_argument("--draft", action="store_true",
                        help="video and both: clips at scale 1 with a fast, lower-quality encode")
    parser.add_argument("--out", type=Path, help=f"output folder (default {OUT})")
    parser.add_argument("--selftest", action="store_true",
                        help=f"capture a built-in page; no product.py needed (default out {SELFTEST_OUT})")
    return parser


def choose(parser: argparse.ArgumentParser, args: argparse.Namespace, module) -> tuple[list[str], list[str]]:
    """(SHOTS scenarios, CLIPS scenarios) to run; exits 2 on an unknown or clip-only name."""
    shots, clips = list(getattr(module, "SHOTS", {})), list(getattr(module, "CLIPS", {}))
    valid = list(dict.fromkeys([*shots, *clips]))
    unknown = [name for name in args.scenarios if name not in valid]
    if unknown:
        parser.error(f"unknown scenario(s) {', '.join(unknown)}; valid: {', '.join(valid) or 'none'}")
    chosen = args.scenarios or valid
    shots = [name for name in shots if name in chosen]
    clips = [name for name in clips if name in chosen] if args.clips else []
    if not shots and not clips:
        parser.error(f"nothing to capture in {', '.join(chosen) or 'SHOTS'} (clips need --clips)")
    return shots, clips


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        name = args.profile or default_profile()
        if args.draft and name == "blog":
            parser.error("--draft applies to the video and both profiles (see --for)")
        prof = profile(name, args.draft)
        if args.selftest:
            if args.scenarios or args.clips:
                parser.error("--selftest takes only --out, --for and --draft")
            sys.exit(asyncio.run(run_selftest(args.out or SELFTEST_OUT, prof)))
        module = product()
        shots, clips = choose(parser, args, module)
        problem = ffmpeg_problem(prof) if clips else None
        if problem:
            sys.exit(f"--clips needs ffmpeg with {', '.join(prof.encoders)}: {problem}")
        asyncio.run(run(module, shots, clips, args.out or OUT, prof))
    except ValueError as err:  # a bad product.py or project.json (ProjectError), a rejected shot or clip
        sys.exit(f"webcap: {err}")


if __name__ == "__main__":
    main()
