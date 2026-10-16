"""Quick look: screenshots of a scenario at a few clip times, at scale 1, to check choreography.

The page steps on the virtual clock as a clip does (no input is played), so `probe tour 0.5 3`
shows the mock's state at clip seconds 0.5 and 3.

    uv run python -m webcap.probe <scenario> --out /tmp/p 0.5 3 8
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from webcap.browser import open_page, session
from webcap.director import Director
from webcap.profiles import profile
from webcap.project import default_profile, product


async def run(scenario: str, path: str, times: list[float], out: Path) -> None:
    module = product()
    out.mkdir(parents=True, exist_ok=True)
    async with session(module) as (world, browser):
        page = await open_page(module, world, browser, scenario, path, 1.0)
        try:
            stepper = Director(page, world, out, profile(default_profile()))
            for t in sorted(times):
                await stepper.hold(max(0.0, t - stepper.t))
                shot = out / f"{scenario}-{t:05.1f}.png"
                await page.screenshot(path=str(shot))
                print(shot)
        finally:
            await page.context.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m webcap.probe", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", help="a World scene (mock) or any name (live)")
    parser.add_argument("--path", default="/", help="page path (default /)")
    parser.add_argument("--out", type=Path, required=True, help="folder for the screenshots")
    parser.add_argument("times", type=float, nargs="+", help="clip seconds")
    args = parser.parse_args()
    asyncio.run(run(args.scenario, args.path, args.times, args.out))


if __name__ == "__main__":
    main()
