"""Unit tests for webcap's pure parts: names, manifest, boxes, PNG sizes, URLs and the CLI."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from webcap import manifest
from webcap.boxes import pixel_box, pixel_boxes
from webcap.browser import page_url
from webcap.capture import build_parser, choose, main
from webcap.director import Director
from webcap.encode import check_frame_size
from webcap.media import png_file_size, png_size
from webcap.profiles import profile
from webcap.project import ProjectError, check_names, mode
from webcap.shots import Shooter, check_name


def _still(scenario: str, label: str) -> dict:
    return {"id": f"{scenario}/{label}", "kind": "still", "origin": "shots",
            "file": f"{scenario}/{label}.png", "width": 10, "height": 10, "scale": 1.0, "boxes": {}}


# --- names -------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["a\n", "-a", "a-", "a_b", "a b", "é", ".."])
def test_check_name_rejects_non_slugs(bad):
    with pytest.raises(ValueError, match="scenario"):
        check_name("scenario", bad)


def test_check_names_rejects_bad_scenario_keys():
    good = SimpleNamespace(SHOTS={"settings": None, "a-1": None}, CLIPS={"tour": None})
    check_names(good)
    with pytest.raises(ProjectError, match="CLIPS scenario 'Tour'"):
        check_names(SimpleNamespace(SHOTS={"ok": None}, CLIPS={"Tour": None}))
    with pytest.raises(ProjectError, match="../x"):
        check_names(SimpleNamespace(SHOTS={"../x": None}))


def test_live_mode_needs_shots_or_clips(monkeypatch):
    monkeypatch.setenv("PRODUCT_URL", "http://b.test")
    with pytest.raises(ProjectError, match="missing SHOTS or CLIPS$"):
        mode(SimpleNamespace())
    assert mode(SimpleNamespace(SHOTS={})) == "live"
    assert mode(SimpleNamespace(CLIPS={})) == "live"


def test_mock_mode_names_every_missing_attribute(monkeypatch):
    monkeypatch.delenv("PRODUCT_URL", raising=False)
    with pytest.raises(ProjectError, match="missing SHOTS or CLIPS, World, build_app"):
        mode(SimpleNamespace())
    assert mode(SimpleNamespace(CLIPS={}, World=object, build_app=None)) == "mock"


# --- manifest ----------------------------------------------------------------


def test_update_starts_a_manifest_and_leaves_no_temp_file(tmp_path):
    out = tmp_path / "captures" / "web"
    path = manifest.update(out, "web", "a", [_still("a", "two"), _still("a", "one")])
    data = json.loads(path.read_text())
    assert data == {"source": "web", "shots": [_still("a", "one"), _still("a", "two")]}
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json"]


def test_update_with_no_entries_drops_the_scenario(tmp_path):
    manifest.update(tmp_path, "web", "a", [_still("a", "one")])
    manifest.update(tmp_path, "web", "b", [_still("b", "one")])
    data = json.loads(manifest.update(tmp_path, "web", "a", []).read_text())
    assert [s["id"] for s in data["shots"]] == ["b/one"]


def test_update_rejects_foreign_and_duplicate_ids(tmp_path):
    with pytest.raises(ValueError, match="b/one"):
        manifest.update(tmp_path, "web", "a", [_still("b", "one")])
    with pytest.raises(ValueError, match="duplicate"):
        manifest.update(tmp_path, "web", "a", [_still("a", "one"), _still("a", "one")])
    assert not (tmp_path / "manifest.json").exists()


def test_update_refuses_another_sources_manifest(tmp_path):
    manifest.update(tmp_path, "tui", "a", [_still("a", "one")])
    with pytest.raises(ValueError, match="tui"):
        manifest.update(tmp_path, "web", "a", [_still("a", "one")])


def test_annotate_survives_updates(tmp_path):
    assert manifest.read(tmp_path, "web") == {"source": "web", "shots": []}
    manifest.annotate(tmp_path, "web", "fonts", {"body": {"Inter": 12}})
    manifest.update(tmp_path, "web", "a", [_still("a", "one")])
    manifest.update(tmp_path, "web", "ab", [_still("ab", "one")])
    data = manifest.read(tmp_path, "web")
    assert data["fonts"] == {"body": {"Inter": 12}}
    assert [s["id"] for s in data["shots"]] == ["a/one", "ab/one"]
    with pytest.raises(ValueError):
        manifest.annotate(tmp_path, "web", "shots", [])


# --- boxes and images ---------------------------------------------------------


def test_pixel_box_scales_and_shifts_by_origin():
    box = {"x": 110.25, "y": 40.0, "width": 30.5, "height": 20.0}
    assert pixel_box(box, 1.0, (0.0, 0.0), (1440, 900)) == [110, 40, 31, 20]
    assert pixel_box(box, 2.0, (0.0, 0.0), (2880, 1800)) == [220, 80, 62, 40]
    assert pixel_box(box, 2.0, (100.0, 30.0), (400, 400)) == [20, 20, 62, 40]
    # A full-page shot of a page scrolled 500 px: the origin is (0, -500).
    assert pixel_box(box, 1.0, (0.0, -500.0), (1440, 3000)) == [110, 540, 31, 20]


def test_pixel_box_clips_to_the_image():
    box = {"x": -10.0, "y": 90.0, "width": 30.0, "height": 30.0}
    assert pixel_box(box, 1.0, (0.0, 0.0), (100, 100)) == [0, 90, 20, 10]
    with pytest.raises(ValueError, match="outside"):
        pixel_box({"x": 200.0, "y": 0.0, "width": 5.0, "height": 5.0}, 1.0, (0.0, 0.0), (100, 100))


def test_pixel_boxes_name_the_shot_and_the_box_off_the_image():
    inside = {"x": 10.0, "y": 10.0, "width": 20.0, "height": 20.0}
    outside = {"x": 200.0, "y": 0.0, "width": 5.0, "height": 5.0}
    args = (1.0, (0.0, 0.0), (100, 100))
    assert pixel_boxes("a/one", {"ok": inside}, *args) == {"ok": [10, 10, 20, 20]}
    with pytest.raises(ValueError, match=r"^a/one: box 'save': .*outside the 100x100 image$"):
        pixel_boxes("a/one", {"ok": inside, "save": outside}, *args)
    with pytest.raises(ValueError, match="box 'Bad'"):
        pixel_boxes("a/one", {"Bad": inside}, *args)


def test_shot_rejects_the_clip_label_before_writing_anything(tmp_path):
    shooter = Shooter(SimpleNamespace(), tmp_path, "tour", 2.0)
    with pytest.raises(ValueError, match="tour/clip"):
        asyncio.run(shooter.shot("clip"))
    assert list(tmp_path.iterdir()) == []
    assert shooter.entries == []


def test_png_size_reads_the_header(tmp_path, png):
    path = tmp_path / "x.png"
    path.write_bytes(png(7, 3))
    assert png_file_size(path) == (7, 3)
    with pytest.raises(ValueError):
        png_size(b"GIF89a" + b"\x00" * 18)


def test_page_url_joins_live_base_and_mock_port():
    assert page_url(None, "/settings") == "http://127.0.0.1:7373/settings"
    assert page_url("http://a.test", "/") == "http://a.test/"
    assert page_url("http://a.test/app/", "/settings") == "http://a.test/app/settings"


def test_page_url_adds_the_slash_a_path_lacks():
    assert page_url(None, "settings") == "http://127.0.0.1:7373/settings"
    assert page_url("http://a.test", "settings") == "http://a.test/settings"


# --- clip frame size ------------------------------------------------------------


@pytest.mark.parametrize(("width", "height", "scale", "frame"), [
    (1441, 900, 1.0, "1441x900"), (1440, 901, 1.0, "1440x901"), (1440, 900, 1.25, "1800x1125"),
])
def test_check_frame_size_rejects_an_odd_side(width, height, scale, frame):
    with pytest.raises(ValueError, match=f"^tour: clip frames {frame} need even sides for yuv420p video; change VIEWPORT$"):
        check_frame_size("tour", {"width": width, "height": height}, scale)


def test_check_frame_size_measures_the_scaled_frame():
    check_frame_size("tour", {"width": 1441, "height": 901}, 2.0)  # 2882x1802
    check_frame_size("tour", {"width": 1440, "height": 900}, 1.0)


def test_start_refuses_odd_frames_before_spawning_ffmpeg(tmp_path):
    page = SimpleNamespace(viewport_size={"width": 1441, "height": 900})
    director = Director(page, None, tmp_path, profile("blog"))
    with pytest.raises(ValueError, match="tour: clip frames 1441x900"):
        asyncio.run(director.start("tour"))
    assert director.clip is None
    assert list(tmp_path.iterdir()) == []


# --- CLI ----------------------------------------------------------------------


MODULE = SimpleNamespace(SHOTS={"settings": None, "home": None}, CLIPS={"home": None, "tour": None})


def _choose(argv: list[str]):
    parser = build_parser()
    return choose(parser, parser.parse_args(argv), MODULE)


def test_choose_defaults_to_every_shot_and_clips_on_request():
    assert _choose([]) == (["settings", "home"], [])
    assert _choose(["--clips"]) == (["settings", "home"], ["home", "tour"])
    assert _choose(["home", "--clips"]) == (["home"], ["home"])


def test_choose_rejects_unknown_scenarios_listing_valid_ones(capsys):
    with pytest.raises(SystemExit) as err:
        _choose(["nope"])
    assert err.value.code == 2
    message = capsys.readouterr().err
    assert "nope" in message
    assert "settings, home, tour" in message


def test_choose_rejects_a_clip_only_scenario_without_clips(capsys):
    with pytest.raises(SystemExit) as err:
        _choose(["tour"])
    assert err.value.code == 2
    assert "--clips" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["--selftest", "home"], ["--selftest", "--clips"], ["--bogus"],
                                  ["--for", "vhs"], ["--selftest", "--for", "blog", "--draft"]])
def test_main_rejects_bad_arguments(argv, capsys):
    with pytest.raises(SystemExit) as err:
        main(argv)
    assert err.value.code == 2
    assert capsys.readouterr().err


def _failing(error: Exception):
    async def run(*_args):
        raise error

    return run


@pytest.mark.parametrize("error", [ValueError("tour/clip: reserved"), ProjectError("missing World")])
def test_main_exits_with_one_line_on_a_value_error(monkeypatch, error):
    monkeypatch.setattr("webcap.capture.product", lambda: MODULE)
    monkeypatch.setattr("webcap.capture.run", _failing(error))
    with pytest.raises(SystemExit) as err:
        main(["home"])
    assert err.value.code == f"webcap: {error}"


def test_main_exits_with_one_line_on_a_selftest_value_error(monkeypatch):
    monkeypatch.setattr("webcap.capture.run_selftest", _failing(ValueError("THEME must be one of light, dark")))
    with pytest.raises(SystemExit) as err:
        main(["--selftest"])
    assert err.value.code == "webcap: THEME must be one of light, dark"


def test_main_keeps_the_selftest_exit_code(monkeypatch):
    async def run_selftest(_out, _profile):
        return 1

    monkeypatch.setattr("webcap.capture.run_selftest", run_selftest)
    with pytest.raises(SystemExit) as err:
        main(["--selftest"])
    assert err.value.code == 1
