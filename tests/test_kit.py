"""Kit plumbing tests: reinstall keeps project.json, a half-built kit fails early, setup and system-deps scoping."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "/bin/bash"


def run_install(kit: Path, dest: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(kit / "install.sh"), str(dest), "--no-system", *flags],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_force_reinstall_keeps_edited_project_json(
    fake_kit: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "launch-week"
    assert run_install(fake_kit, dest).returncode == 0
    (dest / "project.json").write_text('{"slug": "launch-week", "media": ["blog"]}\n')

    proc = run_install(fake_kit, dest, "--force")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads((dest / "project.json").read_text())["media"] == ["blog"]
    assert "project.json: kept" in proc.stdout


def test_force_reinstall_keeps_project_gitignore(
    fake_kit: Path, tmp_path: Path
) -> None:
    (fake_kit / ".gitignore").write_text("kit-only\n")
    dest = tmp_path / "launch-week"
    assert run_install(fake_kit, dest).returncode == 0
    assert (dest / ".gitignore").read_text() == "kit-only\n"
    (dest / ".gitignore").write_text("project-owned\n")

    proc = run_install(fake_kit, dest, "--force")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (dest / ".gitignore").read_text() == "project-owned\n"
    assert "never overwritten): .gitignore" in proc.stdout


def test_reinstall_without_force_lists_conflicts(
    fake_kit: Path, tmp_path: Path
) -> None:
    dest = tmp_path / "launch-week"
    assert run_install(fake_kit, dest).returncode == 0

    proc = run_install(fake_kit, dest)

    assert proc.returncode == 1
    assert "CLAUDE.md" in proc.stderr
    assert "project.json" not in proc.stderr


def test_missing_claude_project_fails_before_writing(
    fake_kit: Path, tmp_path: Path
) -> None:
    (fake_kit / "claude-project.md").unlink()
    dest = tmp_path / "launch-week"

    proc = run_install(fake_kit, dest)

    assert proc.returncode == 1
    assert "claude-project.md missing" in proc.stderr
    assert not dest.exists()


def test_help_names_slug_and_project_json() -> None:
    proc = subprocess.run(
        [BASH, str(KIT / "install.sh"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0
    assert "slug" in proc.stdout
    assert "project.json" in proc.stdout


def test_setup_help_lists_for_check_and_no_samples() -> None:
    proc = subprocess.run(
        [BASH, str(KIT / "setup.sh"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0
    for flag in ("--for", "--check", "--no-samples"):
        assert flag in proc.stdout


def system_deps_dry_run(*flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(KIT / "system-deps.sh"), "--dry-run", *flags],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_system_deps_for_blog_has_no_mesa_xz_unzip() -> None:
    proc = system_deps_dry_run("--for", "blog")

    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    for absent in ("libegl", "mesa", "xz", "unzip"):
        assert absent not in out.lower(), out


def test_system_deps_default_lists_video_packages_when_apt() -> None:
    if shutil.which("apt-get") is None:
        pytest.skip("apt is not the detected package manager")

    proc = system_deps_dry_run()

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "System dependencies to install (apt):" in proc.stdout
    assert "Chromium's OS libraries" in proc.stdout


def test_system_deps_rejects_unknown_medium() -> None:
    assert system_deps_dry_run("--for", "audio").returncode == 2


def copy_setup(root: Path) -> None:
    """setup.sh and the sample code it sources, into root."""
    (root / "tools").mkdir(parents=True, exist_ok=True)
    for name in ("setup.sh", "tools/setup-samples.sh"):
        shutil.copy2(KIT / name, root / name)


def source_setup(root: Path, args: str, call: str) -> subprocess.CompletedProcess:
    """Source a copy of setup.sh in root with ARGS, run CALL; sourcing keeps main from running."""
    copy_setup(root)
    return subprocess.run(
        # $0 is "setup.sh", so the script's ROOT (the folder of $0) is cwd
        [BASH, "-c", f"source ./setup.sh {args}; set +e; {call}", "setup.sh"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    ("media", "scope"),
    [
        ('["video"]', "1 0"),
        ('["blog"]', "0 1"),
        ('["blog", "video"]', "1 1"),
        ("[]", "1 1"),
    ],
)
def test_setup_scope_from_project_json(tmp_path: Path, media: str, scope: str) -> None:
    (tmp_path / "project.json").write_text(f'{{"slug": "x", "media": {media}}}\n')

    proc = source_setup(tmp_path, "", 'echo "$WANT_VIDEO $WANT_BLOG"')

    assert proc.stdout.strip() == scope, proc.stderr


def test_setup_for_flag_wins_over_project_json(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text('{"slug": "x", "media": ["video"]}\n')

    proc = source_setup(tmp_path, "--for blog", 'echo "$WANT_VIDEO $WANT_BLOG"')

    assert proc.stdout.strip() == "0 1", proc.stderr


def test_setup_rejects_unknown_medium() -> None:
    proc = subprocess.run(
        [BASH, str(KIT / "setup.sh"), "--check", "--for", "audio"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 2
    assert "--for takes" in proc.stderr


def test_setup_gpu_probe_only_for_video(tmp_path: Path) -> None:
    blog = source_setup(tmp_path, "--for blog", "check_gpu")
    video = source_setup(tmp_path, "--for video", "check_gpu")

    assert "GPU" not in blog.stdout, blog.stderr
    assert "GPU (OpenGL)" in video.stdout, video.stderr


def setup_brand_newer(root: Path) -> list[str]:
    """The files setup.sh's brand_newer reports, sourced from a copy of the script in root."""
    proc = subprocess.run(
        # $0 is "setup.sh", so the script's ROOT (the folder of $0) is cwd; sourcing keeps main from running
        [BASH, "-c", "source ./setup.sh && brand_newer", "setup.sh"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.split()


def test_setup_brand_newer_ignores_tools_fonts_output(tmp_path: Path) -> None:
    root = tmp_path / "project"
    fonts = root / "brand" / "fonts"
    (fonts / ".local").mkdir(parents=True)
    copy_setup(root)
    asset = fonts / "Body-Regular.ttf"
    for path in (root / "BRAND.md", asset):
        path.write_text("brand\n")
    (root / "design.json").write_text("{}\n")
    past = time.time() - 120
    for path in (root / "BRAND.md", asset):
        os.utime(path, (past, past))
    os.utime(root / "design.json", (past + 60, past + 60))
    (fonts / "resolved.json").write_text("{}\n")
    (fonts / ".local" / "Copy-Regular.ttf").write_text("copy\n")

    assert setup_brand_newer(root) == []

    asset.write_text("changed\n")
    assert setup_brand_newer(root) == ["brand/fonts/Body-Regular.ttf"]
