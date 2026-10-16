"""Saved video choices (configure.sh), install pre-answers, and the export/inflate round trip
(no downloads)."""

import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest
from tools.export_project import export
from tools.project_settings import configure, read

KIT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "/bin/bash"
SHARE_SCRIPTS = ("inflate.sh", "configure.sh", "system-deps.sh", "setup.sh",
                 "tools/project_settings.py", "tools/setup-samples.sh")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "video with spaces"
    path.mkdir()
    return path


def write(root: Path, name: str, content: str = "asset") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def copy_from_kit(root: Path, *names: str) -> None:
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(KIT / name, target)


def test_choices_require_answers_and_persist(project: Path) -> None:
    assert read(project) == {"fps": 30, "piano": "vsco"}
    with patch("sys.stdin.isatty", return_value=False), pytest.raises(ValueError, match="Ask the user"):
        configure(project)
    configure(project, 24, "vsco")
    with patch("builtins.input", side_effect=AssertionError("asked twice")):
        assert configure(project)["fps"] == 24
    configure(project, 60, "salamander")
    assert read(project)["piano"] == "salamander"
    write(project, "project.json", '{"fps": true}')
    with pytest.raises(ValueError):
        read(project)


def test_configure_keeps_slug_and_media(project: Path) -> None:
    write(project, "project.json", '{"slug": "launch", "media": ["video", "blog"]}\n')
    with patch("sys.stdin.isatty", return_value=False), pytest.raises(ValueError, match="Ask the user"):
        configure(project)
    configure(project, 60, "vsco")
    configure(project, fps=25)
    assert json.loads((project / "project.json").read_text()) == {
        "slug": "launch", "media": ["video", "blog"], "fps": 25, "piano": "vsco"}


def test_interactive_startup(project: Path) -> None:
    with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["", ""]):
        assert configure(project) == {"fps": 30, "piano": "vsco"}


def test_archive_roundtrip_and_inflation(project: Path, tmp_path: Path) -> None:
    for name in SHARE_SCRIPTS:
        content = (KIT / name).read_text() if name == "inflate.sh" else "#!/bin/bash\necho restored >> calls\n"
        write(project, name, content).chmod(0o755)
    configure(project, 25, "vsco")
    keep = ("narration/final/voice.wav", "broll/source.mp4", "music/out/soundtrack.wav",
            "motion/out/scene.mov", "brand/fonts/font.ttf", "fixtures/web/uv.lock", ".env.example",
            "outputs/final-video-v1.mp4", "outputs/blog/draft-video-v1.md",
            "captures/web/settings/clip.mp4", "captures/web/manifest.json")
    omit = ("music/samples/piano.wav", "music/.venv/bin/python", "fixtures/web/node_modules/bin",
            ".env", ".env.production", ".aws/credentials", "music/build/fine_tune.json",
            "edit/build/words.json", "post/build/ledger.json", "captures/web-selftest/clip.mp4",
            "captures/tui-selftest/manifest.json", "edit/__pycache__/render.cpython-313.pyc")
    for name in keep + omit:
        write(project, name)
    (project / "voice-link.wav").symlink_to(project / keep[0])
    output = export(project, tmp_path / "share.tar.gz")
    recipient = tmp_path / "recipient"
    recipient.mkdir()
    with tarfile.open(output) as archive:
        names = archive.getnames()
        for name in keep:
            assert f"{project.name}/{name}" in names
        for name in omit:
            assert f"{project.name}/{name}" not in names
        archive.extractall(recipient, filter="data")
    restored = recipient / project.name
    assert (restored / "voice-link.wav").read_text() == "asset"
    assert read(restored)["fps"] == 25
    subprocess.run(["./inflate.sh", "--no-system"], cwd=restored, check=True)
    assert (restored / "calls").read_text().splitlines() == ["restored"]
    with pytest.raises(ValueError, match="already exists"):
        export(project, output)


def test_external_symlink_rejected(project: Path, tmp_path: Path) -> None:
    for name in SHARE_SCRIPTS:
        write(project, name)
    external = tmp_path / "external.wav"
    external.write_text("audio")
    (project / "external.wav").symlink_to(external)
    output = tmp_path / "share.tar.gz"
    with pytest.raises(ValueError, match="outside"):
        export(project, output)
    assert not output.exists()


def install(kit: Path, dest: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, str(kit / "install.sh"), str(dest), "--no-system", *flags],
                          check=False, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=120)


def test_install_saves_choices_only_when_given(fake_kit: Path, project: Path, tmp_path: Path) -> None:
    copy_from_kit(fake_kit, "configure.sh", "tools/project_settings.py")
    plain = tmp_path / "plain"
    assert install(fake_kit, plain).returncode == 0
    assert json.loads((plain / "project.json").read_text()) == {"slug": "plain", "media": []}

    proc = install(fake_kit, project, "--fps", "24", "--piano", "vsco")
    assert proc.returncode == 0, proc.stderr
    assert json.loads((project / "project.json").read_text()) == {
        "slug": "video-with-spaces", "media": [], "fps": 24, "piano": "vsco"}
    assert install(fake_kit, project, "--force").returncode == 0
    assert read(project)["fps"] == 24


@pytest.mark.parametrize("flags", [("--fps", "60"), ("--piano", "vsco"), ("--fps", "0", "--piano", "vsco"),
                                   ("--fps", "30", "--piano", "grand")])
def test_install_rejects_incomplete_or_bad_choices(fake_kit: Path, project: Path, flags) -> None:
    proc = install(fake_kit, project, *flags)
    assert proc.returncode == 2
    assert not (project / "project.json").exists()


@pytest.mark.parametrize(("args", "choice", "expected"), [
    ("--check --for video", "vsco", ["VSCO-2 CE"]),
    ("--check --for video", "salamander", ["Salamander piano", "VSCO-2 CE"]),
    ("--check --for blog", "salamander", []),
])
def test_setup_fetches_only_selected_libraries(project: Path, args, choice, expected) -> None:
    copy_from_kit(project, "setup.sh", "configure.sh", "tools/project_settings.py", "tools/setup-samples.sh")
    configure(project, 30, choice)
    script = f'source ./setup.sh {args}; sample_set() {{ echo "LIBRARY:$1"; }}; fetch_samples'
    result = subprocess.run([BASH, "-c", script, "setup.sh"], cwd=project, check=True,
                            capture_output=True, text=True)
    assert [line[8:] for line in result.stdout.splitlines() if line.startswith("LIBRARY:")] == expected
