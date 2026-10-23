"""The Slack, Linear and GitHub windows (motion/lib/*_ui.py, github_pages.py) draw on a CPU raster
surface with the demo content and with empty content, reject malformed content, and report anchors
that do not depend on the window's opacity. The drawing runs in motion's own environment (skia is
only installed there), one `uv run --project motion` call per check (tests/motion_window_checks.py)."""

import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CHECKS = ("errors", "imports", "demos", "empty_slack", "empty_linear", "empty_github", "anchors", "linear_title",
          "linear_feed", "merge_box")

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")


@pytest.mark.parametrize("check", CHECKS)
def test_window_check(check: str) -> None:
    run = subprocess.run(
        ["uv", "run", "--frozen", "--project", str(KIT / "motion"), "python", str(KIT / "tests" / "motion_window_checks.py"), check],
        check=False, capture_output=True, text=True, timeout=300, cwd=KIT / "motion",
    )
    assert run.returncode == 0 and run.stdout.strip().endswith("ok"), run.stdout + run.stderr
