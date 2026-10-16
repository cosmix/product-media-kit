import json
from pathlib import Path

import pytest

from editkit import assets, shots
from editkit.decode import Probe

MANIFEST = {"source": "web", "shots": [
    {"id": "settings/dialog", "kind": "still", "file": "settings/dialog.png",
     "width": 2880, "height": 1800, "scale": 2.0},
    {"id": "settings/clip", "kind": "clip", "file": "settings/clip.gif", "video": "settings/clip.mp4",
     "width": 3840, "height": 2160, "scale": 2.0,
     "marks": [{"t": 1.2, "event": "open", "key": True}],
     "cursor": [{"t": 0.0, "x": 100, "y": 200, "down": True}], "cursor_space": "css-1920x1080"},
    {"id": "billing/clip", "kind": "clip", "file": "billing/clip.gif", "width": 1920, "height": 1080,
     "scale": 1.0, "marks": [{"t": 3.0, "event": "pay", "key": False}]},
]}


@pytest.fixture
def captures(tmp_path, monkeypatch):
    web = tmp_path / "captures" / "web"
    for scenario in ("settings", "billing"):
        (web / scenario).mkdir(parents=True)
    (web / "manifest.json").write_text(json.dumps(MANIFEST))
    (web / "settings" / "dialog.png").write_bytes(b"")
    monkeypatch.setattr(assets, "ROOT", tmp_path)
    monkeypatch.setitem(assets.DIRS, "web", web)
    monkeypatch.setitem(assets.MANIFESTS, "web", web / "manifest.json")
    monkeypatch.setattr(assets, "_readable", lambda path: True)
    monkeypatch.setattr(assets, "probe", lambda path: Probe(3840, 2160, 60.0, 4.5, "yuv420p", "bt709", False))
    assets.manifest.cache_clear()
    assets._SEEN.clear()
    yield web
    assets.manifest.cache_clear()
    assets._SEEN.clear()


def test_manifest_indexed_by_id(captures):
    m = assets.manifest("web")
    assert {"settings/dialog", "settings/clip", "billing/clip"} <= set(m)
    assert m["billing/clip"]["marks"][0]["event"] == "pay"
    assert m["settings/clip"]["scale"] == 2.0


def test_clip_resolves_mp4_with_marks_and_cursor(captures):
    (captures / "settings" / "clip.mp4").write_bytes(b"")
    (captures / "settings" / "clip.webm").write_bytes(b"")
    a = assets.resolve("web:settings")
    assert a.path == captures / "settings" / "clip.mp4" and not a.placeholder
    assert a.marks == {"open": 1.2}
    assert a.cursor == [(0.0, 100, 200, 1.0)] and a.cursor_space == "css-1920x1080"
    assert assets.resolve("web:settings").scale == 2.0


def test_each_scenario_gets_its_own_clip_entry(captures):
    (captures / "settings" / "clip.mp4").write_bytes(b"")
    (captures / "billing" / "clip.mp4").write_bytes(b"")
    assert assets.resolve("web:billing").marks == {"pay": 3.0}
    assert assets.resolve("web:settings").marks == {"open": 1.2}


def test_clip_falls_back_to_webm_with_warning(captures, capsys):
    (captures / "billing" / "clip.webm").write_bytes(b"")
    a = assets.resolve("web:billing")
    assert a.path == captures / "billing" / "clip.webm"
    assert "clip.webm" in capsys.readouterr().err


def test_still_reference(captures):
    a = assets.resolve("still:web/settings/dialog")
    assert a.still and a.path == captures / "settings" / "dialog.png" and a.scale == 2.0


def test_content_size_from_scale(captures):
    (captures / "settings" / "clip.mp4").write_bytes(b"")
    assert shots.content_size("web:settings") == (1920.0, 1080.0)
    assert shots.content_size("still:web/settings/dialog") == (1440.0, 900.0)


def test_content_size_unscaled_capture_is_pixel_size(captures, monkeypatch):
    (captures / "billing" / "clip.mp4").write_bytes(b"")
    monkeypatch.setattr(assets, "probe", lambda path: Probe(3840, 2160, 30.0, 4.5, "yuv420p", "bt709", False))
    monkeypatch.setitem(assets.manifest("web"), "billing/clip", {"scale": 1.0})
    assert shots.content_size("web:billing") == (3840.0, 2160.0)


def test_layer_source_content_size_divides_by_asset_scale():
    from editkit.compositor import LayerSource

    for scale, native, want in [(2.0, (3840, 2160), (1920.0, 1080.0)), (1.0, (3840, 2160), (3840.0, 2160.0)),
                                (2.0, (2000, 1000), (1000.0, 500.0))]:
        src = object.__new__(LayerSource)  # no GPU: only the size arithmetic is under test
        src.asset = assets.Asset("k", Path("x"), None, scale=scale)
        src.native = native
        assert src.content_size() == want
