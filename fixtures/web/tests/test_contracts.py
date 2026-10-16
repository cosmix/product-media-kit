"""Contract tests for the webcap capture surface."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


def test_check_name_rejects_traversal():
    from webcap.shots import check_name

    for bad in ("../x", "a/b", "", "Upper", "a--b"):
        with pytest.raises(ValueError) as err:
            check_name("label", bad)
        message = str(err.value)
        assert "label" in message
        assert bad in message
    assert check_name("label", "ok-1") == "ok-1"


def test_product_url_env_overrides_base_url(monkeypatch):
    from webcap.project import base_url

    module = SimpleNamespace(BASE_URL="http://a.test", SHOTS={})
    monkeypatch.setenv("PRODUCT_URL", "http://b.test")
    assert base_url(module) == "http://b.test"
    assert base_url(SimpleNamespace(SHOTS={})) == "http://b.test"

    monkeypatch.setenv("PRODUCT_URL", "")
    assert base_url(module) == "http://a.test"

    monkeypatch.delenv("PRODUCT_URL")
    assert base_url(module) == "http://a.test"
    assert base_url(SimpleNamespace(SHOTS={})) is None


def test_live_mode_needs_no_mock(monkeypatch):
    from webcap.project import ProjectError, mode

    monkeypatch.delenv("PRODUCT_URL", raising=False)
    assert issubclass(ProjectError, ValueError)
    assert mode(SimpleNamespace(BASE_URL="http://a.test", SHOTS={})) == "live"
    mock = SimpleNamespace(SHOTS={}, World=object, build_app=lambda world: None)
    assert mode(mock) == "mock"

    with pytest.raises(ProjectError) as err:
        mode(SimpleNamespace(SHOTS={}))
    assert "build_app" in str(err.value)
    assert "World" in str(err.value)


def test_context_options_honour_product(monkeypatch, tmp_path):
    from webcap.browser import context_options

    monkeypatch.setattr("webcap.project.ROOT", tmp_path)

    opts = context_options(SimpleNamespace(VIEWPORT=(1280, 720), THEME="dark"), 2.0)
    assert opts["viewport"] == {"width": 1280, "height": 720}
    assert opts["device_scale_factor"] == 2.0
    assert opts["color_scheme"] == "dark"
    assert opts["reduced_motion"] == "no-preference"

    default = context_options(SimpleNamespace(), 1.0)
    assert default["viewport"] == {"width": 1440, "height": 900}
    assert default["device_scale_factor"] == 1.0
    assert default["color_scheme"] == "light"

    with pytest.raises(ValueError):
        context_options(SimpleNamespace(THEME="sepia"), 1.0)


@pytest.mark.parametrize(("media", "size"), [
    (None, (1440, 900)), ([], (1440, 900)), (["blog"], (1440, 900)),
    (["video"], (1920, 1080)), (["blog", "video"], (1920, 1080)),
])
def test_default_viewport_follows_project_media(monkeypatch, tmp_path, media, size):
    from webcap.browser import context_options

    monkeypatch.setattr("webcap.project.ROOT", tmp_path)
    if media is not None:
        (tmp_path / "project.json").write_text(json.dumps({"slug": "x", "media": media}))
    opts = context_options(SimpleNamespace(), 1.0)
    assert opts["viewport"] == {"width": size[0], "height": size[1]}
    assert context_options(SimpleNamespace(VIEWPORT=(800, 600)), 1.0)["viewport"]["width"] == 800


def _still(scenario: str, label: str, width: int = 100) -> dict:
    return {
        "id": f"{scenario}/{label}",
        "kind": "still",
        "origin": "shots",
        "file": f"{scenario}/{label}.png",
        "width": width,
        "height": 50,
        "scale": 1.0,
        "boxes": {},
    }


def test_manifest_update_keeps_other_scenarios(tmp_path):
    from webcap.manifest import update

    update(tmp_path, "web", "a", [_still("a", "one"), _still("a", "three")])
    update(tmp_path, "web", "b", [_still("b", "two")])
    update(tmp_path, "web", "ab", [_still("ab", "four")])
    path = update(tmp_path, "web", "a", [_still("a", "one", width=200)])

    assert path == tmp_path / "manifest.json"
    data = json.loads(path.read_text())
    assert data["source"] == "web"
    assert [s["id"] for s in data["shots"]] == ["a/one", "ab/four", "b/two"]
    assert data["shots"][0]["width"] == 200
