"""ruff over tools/ and claude-skills/, which have no test package of their own to lint them."""

import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def test_tools_and_skills_pass_ruff() -> None:
    ruff = Path(sys.executable).parent / "ruff"  # the tests venv's own ruff (uv.lock pins it)
    assert ruff.is_file(), f"{ruff} not found: run uv sync in tests/"
    run = subprocess.run(
        [str(ruff), "check", "--no-cache", str(KIT / "tools"), str(KIT / "claude-skills")],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert run.returncode == 0, run.stdout + run.stderr
