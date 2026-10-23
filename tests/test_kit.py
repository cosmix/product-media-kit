"""Kit plumbing tests: reinstall keeps project.json, a half-built kit fails early, setup and system-deps scoping."""

import json
import os
import re
import shutil
import subprocess
import sys
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
    (fake_kit / "CLAUDE-project.md").unlink()
    dest = tmp_path / "launch-week"

    proc = run_install(fake_kit, dest)

    assert proc.returncode == 1
    assert "CLAUDE-project.md missing" in proc.stderr
    assert not dest.exists()


def git(cwd: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


def push_new_file(origin: Path, tmp_path: Path, name: str) -> None:
    """Commit `name` to origin through a second clone."""
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(origin), str(other))
    (other / name).write_text("new\n")
    git(other, "add", name)
    git(other, "commit", "-q", "-m", f"add {name}")
    git(other, "push", "-q")


@pytest.fixture
def git_kit(fake_kit: Path, tmp_path: Path) -> tuple[Path, Path]:
    """(origin, kit): the fake kit as a clone of a bare origin, with an upstream."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(fake_kit, "init", "-q", "-b", "main")
    git(fake_kit, "add", "-A")
    git(fake_kit, "commit", "-q", "-m", "kit")
    git(fake_kit, "remote", "add", "origin", str(origin))
    git(fake_kit, "push", "-q", "-u", "origin", "main")
    return origin, fake_kit


def test_install_pulls_the_kit_and_restarts_once(
    git_kit: tuple[Path, Path], tmp_path: Path
) -> None:
    origin, kit = git_kit
    push_new_file(origin, tmp_path, "newtool.py")
    dest = tmp_path / "launch-week"

    proc = run_install(kit, dest)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (dest / "newtool.py").read_text() == "new\n"
    assert proc.stdout.count("Updating the kit from origin/main") == 1
    assert proc.stdout.count("restarting the install") == 1


def test_install_up_to_date_kit_does_not_restart(
    git_kit: tuple[Path, Path], tmp_path: Path
) -> None:
    _, kit = git_kit

    proc = run_install(kit, tmp_path / "launch-week")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "The kit is up to date." in proc.stdout
    assert "restarting" not in proc.stdout


def test_no_pull_skips_the_update(git_kit: tuple[Path, Path], tmp_path: Path) -> None:
    origin, kit = git_kit
    push_new_file(origin, tmp_path, "newtool.py")
    dest = tmp_path / "launch-week"

    proc = run_install(kit, dest, "--no-pull")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (dest / "newtool.py").exists()
    assert "Updating the kit" not in proc.stdout


def test_failed_pull_exits_1_and_writes_nothing(
    git_kit: tuple[Path, Path], tmp_path: Path
) -> None:
    origin, kit = git_kit
    shutil.rmtree(origin)
    dest = tmp_path / "launch-week"

    proc = run_install(kit, dest)

    assert proc.returncode == 1
    assert "--no-pull" in proc.stderr
    assert not dest.exists()


def test_bad_arguments_exit_2_before_any_pull(
    git_kit: tuple[Path, Path], tmp_path: Path
) -> None:
    origin, kit = git_kit
    shutil.rmtree(origin)

    proc = run_install(kit, tmp_path / "launch-week", "--bogus")

    assert proc.returncode == 2
    assert "unknown option" in proc.stderr


def test_kit_without_git_checkout_notes_and_continues(
    fake_kit: Path, tmp_path: Path
) -> None:
    proc = run_install(fake_kit, tmp_path / "launch-week")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "the kit was not updated" in proc.stderr
    assert "not a git checkout" in proc.stderr


def test_kit_without_upstream_notes_and_continues(
    git_kit: tuple[Path, Path], tmp_path: Path
) -> None:
    _, kit = git_kit
    git(kit, "branch", "--unset-upstream")

    proc = run_install(kit, tmp_path / "launch-week")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "the kit was not updated: the current branch has no upstream" in proc.stderr


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


def dnf_machine(tmp_path: Path, encoders: str) -> dict[str, str]:
    """An environment with dnf and no apt-get whose ffmpeg lists ENCODERS, and every other tool present."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("dirname", "uname", "sed", "awk", "cat"):
        (bin_dir / tool).symlink_to(shutil.which(tool) or tool)
    for tool in ("dnf", "curl", "tar", "rg", "tmux", "xz", "unzip", "uv"):
        (bin_dir / tool).write_text("#!/bin/sh\n")
    (bin_dir / "ffmpeg").write_text(f"#!/bin/sh\necho '{encoders}'\n")
    for tool in ("dnf", "curl", "tar", "rg", "tmux", "xz", "unzip", "uv", "ffmpeg"):
        (bin_dir / tool).chmod(0o755)
    return {"PATH": str(bin_dir), "HOME": str(tmp_path)}


@pytest.mark.skipif(sys.platform != "linux", reason="the dnf path is detected on Linux")
@pytest.mark.parametrize(("encoders", "fusion"), [(" V..... libopenh264", True), (" V..... libx264", False)])
def test_system_deps_dnf_swaps_an_ffmpeg_without_libx264(tmp_path: Path, encoders: str, fusion: bool) -> None:
    proc = subprocess.run(
        [BASH, str(KIT / "system-deps.sh"), "--dry-run", "--for", "video"],
        check=False, capture_output=True, text=True, timeout=60, env=dnf_machine(tmp_path, encoders),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ("RPM Fusion" in proc.stdout) is fusion, proc.stdout


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


def aged_brand_project(tmp_path: Path) -> Path:
    """A project whose design.json names brand/mark.svg and is newer than BRAND.md."""
    root = tmp_path / "project"
    (root / "brand").mkdir(parents=True)
    copy_setup(root)
    (root / "BRAND.md").write_text("brand\n")
    (root / "design.json").write_text('{"logo": {"on_dark": "brand/mark.svg"}}\n')
    past = time.time() - 120
    os.utime(root / "design.json", (past, past))
    os.utime(root / "BRAND.md", (past - 60, past - 60))
    return root


def test_setup_brand_newer_ignores_photos_and_reference(tmp_path: Path) -> None:
    root = aged_brand_project(tmp_path)
    for rel in ("brand/hero.png", "brand/shots/dashboard.png", "brand/reference/in-use.png"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"png")

    assert setup_brand_newer(root) == []


@pytest.mark.parametrize(
    "rel", ["brand/palette/brand.css", "brand/fonts/Body/Body-Regular.ttf", "brand/logo/logo.svg", "brand/mark.svg"]
)
def test_setup_brand_newer_reports_design_sources(tmp_path: Path, rel: str) -> None:
    root = aged_brand_project(tmp_path)
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text("changed\n")

    assert setup_brand_newer(root) == [rel]


def test_scripts_expand_arrays_in_a_form_bash_3_2_accepts() -> None:
    """macOS bash 3.2 fails "${ARR[@]}" on an empty array under set -u; ${ARR[@]+"${ARR[@]}"} is safe."""
    bare = re.compile(r'(?<!\+)"\$\{\w+\[@\]\}"')
    scripts = [*KIT.glob("*.sh"), *(KIT / "tools").glob("*.sh")]
    assert scripts
    offenders = [f"{s.name}:{n}" for s in scripts for n, line in enumerate(s.read_text().splitlines(), 1)
                 if bare.search(line)]

    assert offenders == []


def test_setup_samples_reports_a_malformed_project_json_instead_of_aborting(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    for name in ("configure.sh", "tools/project_settings.py"):
        shutil.copy2(KIT / name, tmp_path / name)
    (tmp_path / "project.json").write_text("{not json")

    proc = source_setup(tmp_path, "--for video --no-samples", "set -e; fetch_samples; echo reached-the-end")

    assert "reached-the-end" in proc.stdout, proc.stdout + proc.stderr
    assert "MISSING   project.json" in proc.stdout, proc.stdout
