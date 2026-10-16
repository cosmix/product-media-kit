"""Capture profiles, project.json, the director's stills and cursor track, and the origin merge."""

from __future__ import annotations

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from webcap import capture, encode, manifest
from webcap.director import Clip, Director
from webcap.profiles import profile
from webcap.project import ProjectError, default_profile, fps, media

# --- profiles and project.json --------------------------------------------------


def _project(tmp_path, data) -> None:
    (tmp_path / "project.json").write_text(json.dumps(data))


@pytest.mark.parametrize(("chosen", "name"), [
    ([], "blog"), (["blog"], "blog"), (["video"], "video"),
    (["video", "blog"], "both"), (["blog", "video"], "both"),
])
def test_default_profile_follows_project_media(tmp_path, chosen, name):
    _project(tmp_path, {"slug": "x", "media": chosen})
    assert default_profile(tmp_path / "project.json") == name


def test_default_profile_without_project_json_is_blog(tmp_path):
    assert default_profile(tmp_path / "project.json") == "blog"
    _project(tmp_path, {"slug": "x"})
    assert default_profile(tmp_path / "project.json") == "blog"


@pytest.mark.parametrize("data", [{"media": ["podcast"]}, {"media": "video"}, ["video"]])
def test_media_rejects_a_malformed_project_json(tmp_path, data):
    _project(tmp_path, data)
    with pytest.raises(ProjectError, match="project.json"):
        media(tmp_path / "project.json")


@pytest.mark.parametrize("rate", [30, 60])
def test_profiles_set_scale_fps_and_encoders(rate):
    blog, video, both = profile("blog", fps=rate), profile("video", fps=rate), profile("both", fps=rate)
    assert (blog.scale, blog.fps, blog.encoders) == (1.0, 30, ("libvpx-vp9",))
    assert (video.scale, video.fps, video.encoders) == (2.0, rate, ("libx264",))
    assert (both.scale, both.fps, both.encoders) == (2.0, rate, ("libx264", "libvpx-vp9"))
    draft = profile("both", draft=True, fps=rate)
    assert (draft.scale, draft.fps, draft.draft) == (1.0, rate, True)
    with pytest.raises(ValueError, match="--draft"):
        profile("blog", draft=True)
    with pytest.raises(ValueError, match="vhs"):
        profile("vhs")


@pytest.mark.parametrize(("data", "rate"), [({}, 30), ({"fps": 30}, 30), ({"fps": 60}, 60)])
def test_video_fps_follows_project_json(monkeypatch, tmp_path, data, rate):
    monkeypatch.setattr("webcap.project.ROOT", tmp_path)
    _project(tmp_path, {"slug": "x", "media": ["video"], **data})
    assert fps() == rate
    assert profile("video").fps == profile("both").fps == rate
    assert profile("blog").fps == 30


def test_fps_rejects_an_out_of_range_rate(tmp_path):
    _project(tmp_path, {"fps": 0})
    with pytest.raises(ProjectError, match="fps"):
        fps(tmp_path / "project.json")


@pytest.mark.parametrize(("rate", "resampled"), [(30, False), (60, True)])
def test_derived_webm_resamples_only_a_rate_other_than_30(rate, resampled):
    graph = encode.derived_webm_command(Path("clip.mp4"), Path("clip.webm"), rate)
    assert ("fps=30," in " ".join(graph)) == resampled


def test_main_takes_the_profile_from_project_json(monkeypatch, tmp_path):
    seen = []

    async def run_selftest(_out, prof):
        seen.append(prof)
        return 0

    monkeypatch.setattr("webcap.project.ROOT", tmp_path)
    monkeypatch.setattr("webcap.capture.run_selftest", run_selftest)
    _project(tmp_path, {"slug": "x", "media": ["video", "blog"]})
    for argv in (["--selftest"], ["--selftest", "--for", "video", "--draft"]):
        with pytest.raises(SystemExit):
            capture.main(argv)
    assert seen == [profile("both"), profile("video", draft=True)]


# --- the director ----------------------------------------------------------------


class _Locator:
    def __init__(self, box):
        self.box = box
        self.first = self

    async def count(self):
        return 1 if self.box else 0

    async def bounding_box(self):
        return self.box


async def _nothing(*_args, **_kwargs):
    return None


def _page(boxes=None):
    return SimpleNamespace(
        viewport_size={"width": 20, "height": 10},
        locator=lambda selector: _Locator((boxes or {}).get(selector)),
        clock=SimpleNamespace(run_for=_nothing), evaluate=_nothing,
        mouse=SimpleNamespace(down=_nothing, up=_nothing),
    )


@pytest.fixture
def recording(tmp_path, png):
    return lambda name, boxes=None, rate=60: _recording(tmp_path, png, name, boxes, rate)


def _recording(tmp_path, png, name: str, boxes=None, rate: int = 60) -> Director:
    """A director mid-clip with a fake page, screenshot and encoder; video and both at `rate`."""
    prof = profile(name, fps=rate)
    director = Director(_page(boxes), None, tmp_path, prof)
    director.clip = Clip("tour", tmp_path / "tour", 0)
    shot = base64.b64encode(png(round(20 * prof.scale), round(10 * prof.scale))).decode()

    async def send(*_args):
        return {"data": shot}

    director._cdp = SimpleNamespace(send=send)
    director._ffmpeg = SimpleNamespace(stdin=SimpleNamespace(write=lambda _data: None, drain=_nothing))
    return director


def test_still_writes_the_frame_with_an_origin_clip_entry(tmp_path, recording):
    box = {"x": 2.0, "y": 1.0, "width": 4.0, "height": 3.0}
    director = recording("video", {"button": box})
    with pytest.raises(RuntimeError, match="recorded frame"):
        asyncio.run(director.still("early"))
    asyncio.run(director.step())
    entry = asyncio.run(director.still("final", boxes={"save": "button"}))
    assert entry == {"id": "tour/final", "kind": "still", "origin": "clip", "file": "tour/final.png",
                     "width": 40, "height": 20, "scale": 2.0, "boxes": {"save": [4, 2, 8, 6]}}
    assert (tmp_path / "tour/final.png").read_bytes() == director._last_png
    assert director.stills == [entry]
    with pytest.raises(ValueError, match="reserved"):
        asyncio.run(director.still("clip"))


@pytest.mark.parametrize("rate", [30, 60])
@pytest.mark.parametrize(("name", "track"), [("video", True), ("both", True), ("blog", False)])
def test_cursor_track_and_video_fields_follow_the_profile(recording, name, track, rate):
    director = recording(name, rate=rate)
    asyncio.run(director.step())
    director.mark("open", key=True)
    asyncio.run(director.step())
    director.mark("moved")
    prof = director.profile
    entry = director.clip.entry(prof, (40, 20), director.page.viewport_size)
    assert entry["marks"] == [{"t": round(1 / prof.fps, 4), "event": "open", "key": True},
                              {"t": round(2 / prof.fps, 4), "event": "moved", "key": False}]
    assert entry["origin"] == "clip"
    assert entry["poster"] == "tour/clip.png"
    assert entry["file"] == ("tour/clip.gif" if prof.blog else "tour/clip.png")
    assert ("webm" in entry) == prof.blog
    video_keys = {"video", "fps", "cursor", "cursor_space"}
    assert video_keys <= entry.keys() if track else not video_keys & entry.keys()
    if track:
        assert entry["cursor"] == [{"t": 0.0, "x": 10.0, "y": 5.0, "down": False},
                                   {"t": round(1 / prof.fps, 4), "x": 10.0, "y": 5.0, "down": False}]
        assert entry["cursor_space"] == "css-20x10"
        assert entry["fps"] == rate


def test_click_holds_and_gaps_in_seconds(recording):
    # A press lasts hold frames plus the release frame; presses are gap frames apart.
    for name, rate, frames in (("blog", 60, 4 + 4 + 4), ("video", 30, 4 + 4 + 4), ("video", 60, 7 + 7 + 7)):
        director = recording(name, rate=rate)
        asyncio.run(director.click(count=2, hold=0.1, gap=0.12))
        assert director.clip.frames == frames
        assert director.clip.marks[-1]["event"] == "double-click"


# --- the origin merge --------------------------------------------------------------


def _entry(label: str, origin: str, kind: str = "still") -> dict:
    return {"id": f"tour/{label}", "kind": kind, "origin": origin, "file": f"tour/{label}.png",
            "width": 1, "height": 1, "scale": 1.0, "boxes": {}}


def _ids(tmp_path) -> list[str]:
    return [s["id"] for s in manifest.read(tmp_path, "web")["shots"]]


def test_update_merges_by_scenario_and_origin(tmp_path):
    manifest.update(tmp_path, "web", "tour", [_entry("page", "shots"), _entry("clip", "clip", "clip"),
                                              _entry("final", "clip")])
    manifest.update(tmp_path, "web", "tour", [_entry("dialog", "shots")], ["shots"])
    assert _ids(tmp_path) == ["tour/clip", "tour/dialog", "tour/final"]
    manifest.update(tmp_path, "web", "tour", [_entry("clip", "clip", "clip")], ["clip"])
    assert _ids(tmp_path) == ["tour/clip", "tour/dialog"]
    with pytest.raises(ValueError, match="origin"):
        manifest.update(tmp_path, "web", "tour", [_entry("x", "clip")], ["shots"])
    with pytest.raises(ValueError, match="duplicate"):
        manifest.update(tmp_path, "web", "tour", [_entry("clip", "shots")], ["shots"])


def test_run_keeps_the_origin_it_did_not_recapture(monkeypatch, tmp_path):
    @asynccontextmanager
    async def session(_module):
        yield None, None

    async def shots(*_args):
        return [_entry("page", "shots")]

    async def clip(*_args):
        return [_entry("clip", "clip", "clip"), _entry("final", "clip")]

    monkeypatch.setattr("webcap.capture.session", session)
    monkeypatch.setattr("webcap.capture.capture_shots", shots)
    monkeypatch.setattr("webcap.capture.capture_clip", clip)
    module, prof = SimpleNamespace(), profile("video")
    asyncio.run(capture.run(module, ["tour"], ["tour"], tmp_path, prof))
    manifest.update(tmp_path, "web", "tour", [_entry("old", "shots")], ["shots"])
    asyncio.run(capture.run(module, [], ["tour"], tmp_path, prof))
    assert _ids(tmp_path) == ["tour/clip", "tour/final", "tour/old"]
    asyncio.run(capture.run(module, ["tour"], [], tmp_path, prof))
    assert _ids(tmp_path) == ["tour/clip", "tour/final", "tour/page"]
