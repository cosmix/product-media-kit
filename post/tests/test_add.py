"""postkit add: PNG copy, frame and segment grabs, manifest updates, name safety."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from postkit.add import AddError, add
from postkit.assemble import build
from postkit.check import check
from postkit.cli import main
from postkit.manifest import load_shots

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


def png(path: Path, size: tuple[int, int] = (64, 48)) -> Path:
    Image.new("RGB", size, (10, 120, 200)).save(path)
    return path


def video(path: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=15",
                    "-t", "2", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def shots(root: Path, source: str) -> list[dict]:
    return json.loads((root / "captures" / source / "manifest.json").read_text())["shots"]


def test_add_png_copies_and_writes_the_manifest(tmp_path: Path) -> None:
    src = png(tmp_path / "in.png")

    written = add(tmp_path, "motion/intro/title", src)

    assert written == [tmp_path / "captures" / "motion" / "intro" / "title.png"]
    assert written[0].read_bytes() == src.read_bytes()
    assert shots(tmp_path, "motion") == [{"id": "intro/title", "kind": "still", "origin": "shots",
                                          "file": "intro/title.png", "width": 64, "height": 48,
                                          "scale": 1.0, "boxes": {}}]
    assert "motion/intro/title" in load_shots(tmp_path)


def test_add_replaces_the_same_id_and_keeps_others(tmp_path: Path) -> None:
    add(tmp_path, "broll/x/a", png(tmp_path / "a.png", (10, 10)))
    add(tmp_path, "broll/x/b", png(tmp_path / "b.png"))
    add(tmp_path, "broll/x/a", png(tmp_path / "a2.png", (20, 20)))

    entries = {e["id"]: e for e in shots(tmp_path, "broll")}
    assert sorted(entries) == ["x/a", "x/b"]
    assert entries["x/a"]["width"] == 20


@pytest.mark.parametrize("ref", ["web/a/b", "motion/a", "motion/a/b/c", "motion/../b", "motion/A/b", "motion/a/b.png",
                                 "video//b"])
def test_add_rejects_bad_refs(tmp_path: Path, ref: str) -> None:
    with pytest.raises(AddError):
        add(tmp_path, ref, png(tmp_path / "in.png"))
    assert not (tmp_path / "captures").exists()


def test_add_rejects_bad_inputs(tmp_path: Path) -> None:
    src = png(tmp_path / "in.png")
    (tmp_path / "clip.mp4").write_bytes(b"x")
    for kwargs, file in (({}, tmp_path / "missing.png"), ({"start": 1.0}, src), ({"start": 2.0, "end": 1.0}, src),
                         ({"start": 0.0, "end": 1.0, "at": 0.5}, src), ({"at": -1.0}, src), ({}, tmp_path / "clip.mp4")):
        with pytest.raises(AddError):
            add(tmp_path, "video/a/b", file, **kwargs)  # type: ignore[arg-type]


def test_cli_add_reports_errors_on_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["add", "web/a/b", str(png(tmp_path / "in.png")), "--root", str(tmp_path)])

    assert code == 1
    assert "postkit add:" in capsys.readouterr().err


def test_added_png_builds_with_no_frame(make_project: Path, tmp_path: Path) -> None:
    assert main(["add", "motion/intro/title", str(png(tmp_path / "in.png")), "--root", str(make_project)]) == 0
    (make_project / "post" / "draft.md").write_text("![Title card](shot:motion/intro/title)\n")

    result = build(make_project)

    with Image.open(make_project / "outputs" / "blog" / "images" / "motion-intro-title.png") as img:
        assert img.size == (64, 48)  # a browser frame would have grown it
    assert result.md.name == "draft-demo-post-v1.md"
    assert check(make_project) == []


@needs_ffmpeg
def test_add_frame_from_video(tmp_path: Path) -> None:
    add(tmp_path, "video/demo/open", video(tmp_path / "v.mp4"), at=1.0)

    with Image.open(tmp_path / "captures" / "video" / "demo" / "open.png") as img:
        assert img.size == (320, 180)
    assert shots(tmp_path, "video")[0]["kind"] == "still"


@needs_ffmpeg
def test_add_segment_from_video(tmp_path: Path) -> None:
    written = add(tmp_path, "video/demo/tour", video(tmp_path / "v.mp4"), start=0.5, end=1.5)

    folder = tmp_path / "captures" / "video" / "demo"
    assert sorted(p.name for p in written) == ["tour.gif", "tour.png", "tour.webm"]
    assert all((folder / p.name).stat().st_size > 0 for p in written)
    entry = shots(tmp_path, "video")[0]
    assert (entry["kind"], entry["origin"], entry["file"], entry["webm"], entry["poster"]) == (
        "clip", "clip", "demo/tour.gif", "demo/tour.webm", "demo/tour.png")
    assert entry["duration"] == 1.0
    assert not list(folder.glob(".*.part"))
    with Image.open(folder / "tour.gif") as gif:
        assert gif.format == "GIF"
    assert load_shots(tmp_path)["video/demo/tour"].webm == (folder / "tour.webm").resolve()
