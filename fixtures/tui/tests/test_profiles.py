"""The capture profiles: video and both render an MP4 at project.json's fps (default 30), blog a
WebM at 30 fps; every entry reports scale 2.0 and an origin; project.json picks the default profile."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import types

import pytest

from tuicap import clips, encode
from tuicap.capture import prompt, synth_cli
from tuicap.encode import encoder, fps_for
from tuicap.render import render_recording

ENCODERS = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], check=False,
                          capture_output=True, text=True).stdout if shutil.which("ffmpeg") else ""
needs_h264 = pytest.mark.skipif("libx264" not in ENCODERS, reason="ffmpeg without libx264")
needs_all = pytest.mark.skipif(not all(c in ENCODERS for c in ("libx264", "libvpx-vp9")),
                               reason="ffmpeg without libx264 or libvpx-vp9")


def _short_rec():
    rec, marks = synth_cli(prompt("~/t"), "echo", b"hello\n", 20, 5, seed=1, lead=0.1, tail=0.2)
    return rec, marks


def _probe(path, entries="stream=r_frame_rate,codec_name"):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries,
                          "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    return json.loads(out)["streams"][0]


@pytest.fixture
def project_fps(tmp_path_factory, monkeypatch):
    """Set the project root's project.json fps (None: no project.json) for the encoders."""
    def set_fps(rate):
        root = tmp_path_factory.mktemp("project")
        if rate is not None:
            (root / "project.json").write_text(json.dumps({"slug": "x", "media": ["video"], "fps": rate}))
        monkeypatch.setattr(encode, "ROOT", root)
    return set_fps


@pytest.mark.parametrize(("rate", "video"), [(None, 30), (30, 30), (60, 60)])
@pytest.mark.parametrize("profile", ["blog", "video", "both"])
def test_fps_per_profile(project_fps, profile, rate, video):
    project_fps(rate)
    assert fps_for(profile) == (30 if profile == "blog" else video)


def test_encoder_draft_is_fast_and_low_quality(monkeypatch):
    seen = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: seen.append(cmd))
    encoder("o.mp4", 10, 10, "video", 60, draft=True)
    encoder("o.mp4", 10, 10, "video", 60)
    assert seen[0][seen[0].index("-preset") + 1] == "ultrafast"
    assert seen[0][seen[0].index("-crf") + 1] == "23"
    assert (seen[1][seen[1].index("-preset") + 1], seen[1][seen[1].index("-crf") + 1]) == ("slow", "10")


def test_render_recording_rejects_an_unknown_profile(tmp_path):
    with pytest.raises(ValueError, match="profile 'web'"):
        render_recording(_short_rec()[0], tmp_path, "clip", "web")
    assert not list(tmp_path.iterdir())


@needs_h264
@pytest.mark.parametrize("rate", [30, 60])
def test_video_profile_writes_an_mp4_at_the_project_fps_and_a_poster(tmp_path, project_fps, rate):
    project_fps(rate)
    rec, _ = _short_rec()
    entry = render_recording(rec, tmp_path, "clip", "video")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.mp4", "clip.png"]
    stream = _probe(tmp_path / "clip.mp4")
    assert (stream["codec_name"], stream["r_frame_rate"]) == ("h264", f"{rate}/1")
    assert entry["video"] == "clip.mp4" and entry["fps"] == rate and entry["scale"] == 2.0
    assert entry["grid"] == "20x5" and entry["padding_px"] > 0 and len(entry["cell_px"]) == 2
    assert "webm" not in entry


@needs_all
@pytest.mark.parametrize("rate", [30, 60])
def test_both_profile_derives_the_webm_and_gif_from_the_mp4(tmp_path, project_fps, rate):
    project_fps(rate)
    rec, _ = _short_rec()
    entry = render_recording(rec, tmp_path, "clip", "both")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.gif", "clip.mp4", "clip.png", "clip.webm"]
    mp4, webm = _probe(tmp_path / "clip.mp4", "stream=r_frame_rate,width"), _probe(
        tmp_path / "clip.webm", "stream=r_frame_rate,width")
    assert (mp4["r_frame_rate"], webm["r_frame_rate"]) == (f"{rate}/1", "30/1")
    assert webm["width"] == mp4["width"] // 2
    assert (entry["file"], entry["webm"], entry["poster"], entry["video"]) == (
        "clip.gif", "clip.webm", "clip.png", "clip.mp4")


@needs_all
def test_blog_profile_writes_webm_gif_and_poster_at_30_fps(tmp_path):
    entry = render_recording(_short_rec()[0], tmp_path, "clip", "blog")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.gif", "clip.png", "clip.webm"]
    assert _probe(tmp_path / "clip.webm")["r_frame_rate"] == "30/1"
    assert entry["scale"] == 2.0 and "video" not in entry and "fps" not in entry


def test_render_stills_report_scale_2_and_the_shots_origin(tmp_path, monkeypatch):
    monkeypatch.setattr(clips, "render_still", lambda rec, png, t: (7, 5))
    rec = types.SimpleNamespace(cols=10, rows=4)
    (entry,) = clips.render_stills("s", rec, [clips.Still("a", 1.0)], tmp_path)
    assert (entry["scale"], entry["origin"]) == (2.0, "shots")


def test_clip_entries_carry_the_clip_origin_marks_and_scenario_paths(tmp_path, monkeypatch):
    info = {"kind": "clip", "file": "clip.gif", "poster": "clip.png", "webm": "clip.webm",
            "video": "clip.mp4", "width": 1, "height": 1, "scale": 2.0}
    monkeypatch.setattr(clips, "render_recording", lambda *a: dict(info))
    job = clips.Job("s", "clip", None, None, [{"t": 0.0, "event": "x"}], tmp_path, {}, "both", False, {})
    entry = clips.render_clip(job)
    assert entry["origin"] == "clip" and entry["id"] == "s/clip"
    assert (entry["file"], entry["video"], entry["webm"], entry["poster"]) == (
        "s/clip.gif", "s/clip.mp4", "s/clip.webm", "s/clip.png")
    assert entry["marks"] == [{"t": 0.0, "event": "x", "key": False}]


def test_marks_accept_tuples_and_dicts_and_default_key_to_false():
    marks = clips.normalize_marks([(0.5, "a"), (1.0, "b", True), {"t": 2.0, "event": "c"},
                                   {"t": 3.0, "event": "d", "key": True}])
    assert marks == [{"t": 0.5, "event": "a", "key": False}, {"t": 1.0, "event": "b", "key": True},
                     {"t": 2.0, "event": "c", "key": False}, {"t": 3.0, "event": "d", "key": True}]
    with pytest.raises(ValueError, match="mark"):
        clips.normalize_marks([(1.0,)])


def test_annotate_prefers_the_entry_note_over_the_scenario_note():
    entries = [{"id": "s/a"}, {"id": "s/b"}, {"id": "t/c"}]
    clips.annotate(entries, {"s": "scenario", "s/b": "entry"})
    assert [e.get("notes") for e in entries] == ["scenario", "entry", None]


@pytest.mark.parametrize(("project", "profile"), [
    ({"slug": "x", "media": ["video", "blog"]}, "both"),
    ({"slug": "x", "media": ["blog", "video"]}, "both"),
    ({"slug": "x", "media": ["video"]}, "video"),
    ({"slug": "x", "media": ["blog"]}, "blog"),
    ({"slug": "x", "media": []}, "blog"),
    ({"slug": "x"}, "blog"),
    ([], "blog"),
])
def test_default_profile_follows_project_json(tmp_path, project, profile):
    (tmp_path / "project.json").write_text(json.dumps(project))
    assert clips.default_profile(tmp_path) == profile


def test_default_profile_is_blog_without_a_readable_project_json(tmp_path):
    assert clips.default_profile(tmp_path) == "blog"
    (tmp_path / "project.json").write_text("{not json")
    assert clips.default_profile(tmp_path) == "blog"


def test_main_passes_the_profile_and_draft_flag(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "argv", ["tuicap", "--clips", "--for", "video", "--draft"])
    monkeypatch.setattr(clips.shutil, "which", lambda name: "/bin/ffmpeg")
    monkeypatch.setattr(clips.design, "mono", lambda: "font.ttf")
    monkeypatch.setattr(clips, "capture", lambda *args: seen.append(args))
    clips.main()
    assert seen == [([], True, clips.OUT, "video", True)]


def test_capture_dedupes_scenario_names_and_needs_only_clips_or_shots(tmp_path, monkeypatch):
    seen = []
    mod = types.SimpleNamespace(CLIPS={"c": lambda: ("rec", [])})
    monkeypatch.setattr(clips, "product", lambda: mod)
    monkeypatch.setattr(clips, "run", lambda jobs, out: seen.extend(j.scenario for j in jobs))
    clips.capture(["c", "c"], True, tmp_path)
    assert seen == ["c"]
    with pytest.raises(SystemExit, match="only CLIPS: pass --clips"):
        clips.capture([], False, tmp_path)


def test_manifest_update_rejects_an_entry_of_another_origin(tmp_path):
    from tuicap import manifest
    with pytest.raises(ValueError, match="origin 'clip'"):
        manifest.update(tmp_path, "tui", "a", "clip", [{"id": "a/clip", "origin": "shots"}])
    assert not (tmp_path / "manifest.json").exists()
