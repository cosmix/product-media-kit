"""claude-skills/brand/check.py against small tmp projects: a good one, low contrast, a missing font."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
CHECK = KIT / "claude-skills" / "brand" / "check.py"
LOGO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'
GOOD = {
    "colors": {
        "background": "#ffffff",
        "text": "#111111",
        "secondary": "#555555",
        "accent": "#0b5fff",
    },
    "logo": {"on_light": "brand/logo/logo.svg"},
}


def make_project(root: Path, design: dict) -> Path:
    root.mkdir(parents=True)
    (root / "BRAND.md").write_text("# Brand\n\nPlain and calm.\n")
    for sub in ("logo", "fonts", "palette", "reference"):
        (root / "brand" / sub).mkdir(parents=True)
    (root / "brand" / "logo" / "logo.svg").write_text(LOGO)
    (root / "brand" / "reference" / "ref.txt").write_text("reference\n")
    (root / "brand" / "fonts" / "licence.txt").write_text("licence\n")
    (root / "design.json").write_text(json.dumps(design))
    return root


def run_check(root: Path) -> tuple[int, str]:
    uv = shutil.which("uv")
    assert uv, "uv not on PATH"
    run = subprocess.run(
        [uv, "run", "--script", str(CHECK), str(root)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=KIT,
    )
    return run.returncode, run.stdout + run.stderr


def test_good_project_passes(tmp_path: Path) -> None:
    code, out = run_check(make_project(tmp_path / "good", GOOD))

    assert code == 0, out
    assert "MISSING " not in out, out
    assert "ok        design.json" in out, out
    assert "Summary: 0 MISSING" in out, out


def test_low_contrast_text_warns(tmp_path: Path) -> None:
    design = {
        **GOOD,
        "colors": {**GOOD["colors"], "background": "#808080", "text": "#777777"},
    }

    code, out = run_check(make_project(tmp_path / "dim", design))

    assert code == 0, out
    assert any(
        line.startswith("WARN") and "contrast text" in line for line in out.splitlines()
    ), out


def test_missing_font_file_is_reported(tmp_path: Path) -> None:
    design = {**GOOD, "fonts": {"regular": "brand/fonts/Nope-Regular.ttf"}}

    code, out = run_check(make_project(tmp_path / "nofont", design))

    assert code == 1, out
    assert "Nope-Regular.ttf" in out and "does not exist" in out, out


def age_project(root: Path) -> None:
    """BRAND.md and brand/ two minutes old, design.json one minute newer, as after a brand skill run."""
    past = time.time() - 120
    for path in [root / "BRAND.md", *(root / "brand").rglob("*")]:
        os.utime(path, (past, past))
    os.utime(root / "design.json", (past + 60, past + 60))


def stale_warnings(out: str) -> list[str]:
    return [
        ln for ln in out.splitlines() if ln.startswith("WARN") and "older than" in ln
    ]


def test_tools_fonts_output_does_not_age_design_json(tmp_path: Path) -> None:
    root = make_project(tmp_path / "derived", GOOD)
    age_project(root)
    fonts = root / "brand" / "fonts"
    (fonts / "resolved.json").write_text("{}\n")
    (fonts / ".local").mkdir()
    (fonts / ".local" / "Copy-Regular.ttf").write_text("copy\n")

    code, out = run_check(root)

    assert code == 0, out
    assert not stale_warnings(out), out
    assert "newer than BRAND.md and the brand files it is built from" in out, out


def test_photos_and_reference_do_not_age_design_json(tmp_path: Path) -> None:
    """design.json is not built from photos, screenshots or brand/reference/, so they never age it."""
    root = make_project(tmp_path / "photos", GOOD)
    age_project(root)
    (root / "brand" / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (root / "brand" / "shots").mkdir()
    (root / "brand" / "shots" / "dashboard.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (root / "brand" / "reference" / "ref.txt").write_text("changed\n")

    code, out = run_check(root)

    assert code == 0, out
    assert not stale_warnings(out), out


@pytest.mark.parametrize("source", ["brand/palette/brand.css", "brand/fonts/Body/Body-Regular.ttf", "brand/logo/logo.svg"])
def test_newer_design_source_warns_that_design_json_is_old(tmp_path: Path, source: str) -> None:
    root = make_project(tmp_path / "stale", GOOD)
    age_project(root)
    path = root / source
    path.parent.mkdir(exist_ok=True)
    path.write_text(path.read_text() if path.exists() else "changed\n")

    _, out = run_check(root)  # the stand-in font does not parse (MISSING); only freshness is under test

    assert any(source in ln for ln in stale_warnings(out)), out


def test_grain_is_accepted(tmp_path: Path) -> None:
    code, out = run_check(make_project(tmp_path / "grain", {**GOOD, "grain": 0.03}))

    assert code == 0, out
    assert "unknown key" not in out, out


def test_negative_grain_is_rejected(tmp_path: Path) -> None:
    code, out = run_check(make_project(tmp_path / "badgrain", {**GOOD, "grain": -1}))

    assert code == 1, out
    assert "grain = -1" in out, out
