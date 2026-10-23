"""Contract tests for the kit plumbing: slug derivation, the install copy set, ffmpeg per medium."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "/bin/bash"


def run_install(kit: Path, dest: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(kit / "install.sh"), str(dest), "--no-system"],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("folder", "slug"),
    [("My_Post", "my-post"), ("demo-post", "demo-post"), ("__", "project")],
)
def test_install_derives_slug_from_folder(
    fake_kit: Path, tmp_path: Path, folder: str, slug: str
) -> None:
    dest = tmp_path / folder

    proc = run_install(fake_kit, dest)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((dest / "project.json").read_text()) == {
        "slug": slug,
        "media": [],
    }
    assert ("is not a slug" in proc.stderr) == (folder != slug)


def test_install_excludes_dev_tree(fake_kit: Path, tmp_path: Path) -> None:
    dest = tmp_path / "demo-post"

    proc = run_install(fake_kit, dest)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    top = {p.name for p in dest.iterdir()}
    for absent in (
        "doc",
        "tests",
        ".loom",
        "install.sh",
        "claude-skills",
        "claude-settings.json",
        "CLAUDE-project.md",
        "captures",
        "outputs",
    ):
        assert absent not in top, f"{absent} was copied into the project"
    assert not (dest / "music" / "samples").exists()
    assert (dest / "CLAUDE.md").read_text() == "# Project instructions\n"
    for skill in ("brand", "narration"):
        assert (dest / ".claude" / "skills" / skill / "SKILL.md").is_file()
    assert (dest / ".claude" / "settings.json").is_file()
    assert (dest / "fixtures" / "web" / "a.py").read_text() == "A = 1\n"
    assert (dest / "README.md").is_file()
    assert (dest / "music" / "CREDITS.md").is_file()
    assert (dest / "broll" / "CREDITS.md").is_file()
    assert json.loads((dest / "project.json").read_text()) == {
        "slug": "demo-post",
        "media": [],
    }
    assert not (dest / ("post" + ".json")).exists()


def path_without_ffmpeg(tmp_path: Path) -> Path:
    """A folder of symlinks to every /usr/bin and /bin executable except ffmpeg and ffprobe."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for src in (Path("/usr/bin"), Path("/bin")):
        if not src.is_dir():
            continue
        for exe in src.iterdir():
            name = exe.name
            if name in ("ffmpeg", "ffprobe") or (bin_dir / name).exists():
                continue
            if exe.is_file() and os.access(exe, os.X_OK):
                (bin_dir / name).symlink_to(exe)
    return bin_dir


def check_commands_without_ffmpeg(tmp_path: Path, medium: str) -> list[str]:
    bin_dir = path_without_ffmpeg(tmp_path)
    env = {**os.environ, "PATH": str(bin_dir)}

    proc = subprocess.run(
        [BASH, "-c", f"source ./setup.sh --for {medium}; set +e; check_commands"],
        cwd=KIT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    return [ln for ln in proc.stdout.splitlines() if "ffmpeg" in ln or "ffprobe" in ln]


def test_setup_ffmpeg_is_optional_for_blog(tmp_path: Path) -> None:
    lines = check_commands_without_ffmpeg(tmp_path, "blog")

    assert lines
    assert not [ln for ln in lines if ln.startswith("MISSING")], lines
    assert [ln for ln in lines if ln.startswith("WARN")], lines


def test_setup_ffmpeg_is_required_for_video(tmp_path: Path) -> None:
    lines = check_commands_without_ffmpeg(tmp_path, "video")

    assert [ln for ln in lines if ln.startswith("MISSING")], lines
