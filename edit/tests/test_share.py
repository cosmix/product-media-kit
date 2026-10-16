"""render.share: the 30 fps share copy of a master with and without audio, and failures leaving nothing."""

import shutil
import subprocess
from pathlib import Path

import pytest

import render

HAS_X264 = shutil.which("ffmpeg") is not None and "libx264" in subprocess.run(
    ["ffmpeg", "-hide_banner", "-encoders"], check=False, capture_output=True, text=True).stdout
pytestmark = pytest.mark.skipif(not HAS_X264, reason="ffmpeg with libx264 is not installed")


def master(path: Path, audio: bool) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=60"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440"]
    cmd += ["-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac"]
    subprocess.run([*cmd, str(path)], check=True)


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUTPUTS", tmp_path)
    return tmp_path


@pytest.mark.parametrize("audio", [False, True])
def test_share_handles_a_master_with_and_without_audio(outputs: Path, audio: bool) -> None:
    master(outputs / "final-demo-v1.mp4", audio)

    render.share("demo", None)

    dst = outputs / "final-demo-v1-share.mp4"
    assert dst.is_file() and render.has_audio(dst) is audio
    assert sorted(p.name for p in outputs.iterdir()) == ["final-demo-v1-share.mp4", "final-demo-v1.mp4"]


def test_a_failed_transcode_leaves_no_file(outputs: Path) -> None:
    (outputs / "final-demo-v1.mp4").write_bytes(b"not a video")

    with pytest.raises(subprocess.CalledProcessError):
        render.share("demo", 1)

    assert [p.name for p in outputs.iterdir()] == ["final-demo-v1.mp4"]


def test_no_master_error_never_names_v_none(outputs: Path) -> None:
    with pytest.raises(SystemExit) as e:
        render.share("demo", None)

    assert "vNone" not in str(e.value)


@pytest.mark.parametrize(("t", "slug"), [(12.5, "12p5"), (1e-05, "0"), (20.0, "20"), (1234567.0, "1234567")])
def test_time_slug_has_no_exponent(t: float, slug: str) -> None:
    assert render._t(t) == slug
