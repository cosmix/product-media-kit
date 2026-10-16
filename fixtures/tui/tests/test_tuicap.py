"""Unit tests for tuicap's cell boxes, manifest, name checks, design validation and font lookup."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import types

import pytest

from tuicap import clips, design, fonts, manifest, palette
from tuicap.render import CELL_H, CELL_W, PAD, Geometry
from tuicap.render import cell_box as box
from tuicap.shots import Still


@pytest.mark.parametrize("cells", [(0, 0, 0, 5), (0, 3, 1, 3), (-1, 0, 1, 1), (0, 0, 1, 11), (0, 0, 5, 1), (2, 0, 1, 1)])
def test_cell_box_rejects_empty_or_outside(cells):
    with pytest.raises(ValueError, match="grid"):
        box(Geometry(10, 4), *cells)


def test_cell_box_full_grid():
    assert box(Geometry(10, 4), 0, 0, 4, 10) == [PAD, PAD, 10 * CELL_W, 4 * CELL_H]


def test_still_boxes_default_is_not_shared():
    a, b = Still("a", 1.0), Still("b", 2.0)
    a.boxes["x"] = (0, 0, 1, 1)
    assert b.boxes == {}


def test_manifest_update_replaces_scenario_and_sorts(tmp_path):
    entry = lambda i: {"id": i, "kind": "still", "origin": "shots", "file": f"{i}.png"}
    manifest.update(tmp_path, "tui", "b", "shots", [entry("b/two"), entry("b/one")])
    path = manifest.update(tmp_path, "tui", "a", "shots", [entry("a/x")])
    manifest.update(tmp_path, "tui", "b", "shots", [entry("b/three")])
    data = json.loads(path.read_text())
    assert data["source"] == "tui"
    assert [s["id"] for s in data["shots"]] == ["a/x", "b/three"]
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("name", ["a", "a-b", "a1-b2-c3"])
def test_check_name_accepts(name):
    assert clips.check_name("label", name) == name


@pytest.mark.parametrize("name", ["", "A", "a_b", "a--b", "-a", "a-", "a b", "../x"])
def test_check_name_rejects(name):
    with pytest.raises(ValueError, match="label"):
        clips.check_name("label", name)


def test_validate_good_and_bad():
    assert design.validate({}) == []
    assert design.validate({"fonts": {"mono": "Fira Code"}, "colors": {"text": "#ffffff"},
                            "logo": {"on_dark": "logo.svg"}}) == []
    assert design.validate({"grain": 0.1}) == []
    assert design.validate({"grain": 0}) == []
    for grain in (-1, "x", True, None):
        assert design.validate({"grain": grain}) == [f"grain = {grain!r}: expected a number >= 0"]
    bad = design.validate({"colors": {"text": "white"}, "logo": {"on_dark": "logo.jpg"}})
    assert any(b.startswith("colors.text") for b in bad)
    assert any(b.startswith("logo.on_dark") for b in bad)


def test_manifest_update_rejects_other_source(tmp_path):
    manifest.update(tmp_path, "tui", "a", "shots", [])
    with pytest.raises(ValueError, match="source"):
        manifest.update(tmp_path, "web", "a", "shots", [])


def test_run_keeps_the_origin_it_did_not_recapture(tmp_path, monkeypatch):
    still = {"id": "a/x", "kind": "still", "origin": "shots", "file": "a/x.png", "width": 1, "height": 1}
    clip = {"id": "a/clip", "kind": "clip", "origin": "clip", "file": "a/clip.gif", "width": 1, "height": 1}
    manifest.update(tmp_path, "tui", "a", "shots", [still])
    manifest.update(tmp_path, "tui", "a", "clip", [clip])
    fresh = {**still, "width": 2}
    monkeypatch.setattr(clips, "ProcessPoolExecutor", _Inline)
    monkeypatch.setattr(clips, "_job", lambda job: ("a", "shots", [fresh]))
    clips.run([None], tmp_path)
    shots = {s["id"]: s for s in json.loads((tmp_path / "manifest.json").read_text())["shots"]}
    assert shots["a/x"]["width"] == 2
    assert shots["a/clip"] == clip


def test_capture_accepts_clips_only_scenario_with_clips(tmp_path, monkeypatch):
    seen = []
    mod = types.SimpleNamespace(SHOTS={"s": lambda: (None, [])}, CLIPS={"c": lambda: ("rec", [])})
    monkeypatch.setattr(clips, "product", lambda: mod)
    monkeypatch.setattr(clips, "run", lambda jobs, out: seen.extend((j.scenario, j.kind) for j in jobs))
    clips.capture(["c"], True, tmp_path)
    assert seen == [("c", "clip")]
    with pytest.raises(SystemExit, match="unknown scenario"):
        clips.capture(["c"], False, tmp_path)


def test_selftest_prompt_box_is_the_closing_prompt_row(tmp_path, monkeypatch):
    jobs = []
    monkeypatch.setattr(clips, "run", lambda j, out: jobs.extend(j))
    clips.selftest(tmp_path, "blog", False)
    rec, (still,) = jobs[0].rec, jobs[0].stills
    row = 1 + clips.SELFTEST_LINES
    assert still.boxes["prompt"] == (row, 0, row + 1, rec.cols)
    assert box(Geometry(rec.cols, rec.rows), *still.boxes["prompt"])[3] == CELL_H


class _Inline:
    """A ProcessPoolExecutor stand-in that maps in-process."""

    def __init__(self, max_workers=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def map(self, fn, items):
        return map(fn, items)


def _rec(cols=10, rows=4):
    return types.SimpleNamespace(cols=cols, rows=rows)


def _forbidden(*args, **kwargs):
    raise AssertionError("must not run")


@pytest.fixture
def rendered(monkeypatch):
    """The PNG paths render_still was asked for; the renderer itself is a stub."""
    paths = []
    monkeypatch.setattr(clips, "render_still", lambda rec, png, t: paths.append(png) or (7, 5))
    return paths


def test_render_stills_rejects_a_repeated_label_before_rendering(tmp_path, rendered):
    stills = [Still("a", 1.0), Still("b", 1.0), Still("a", 2.0)]
    with pytest.raises(ValueError, match="s/a"):
        clips.render_stills("s", _rec(), stills, tmp_path)
    assert rendered == []


def test_render_stills_rejects_the_clip_label_before_rendering(tmp_path, rendered):
    with pytest.raises(ValueError, match="s/clip"):
        clips.render_stills("s", _rec(), [Still("a", 1.0), Still("clip", 2.0)], tmp_path)
    assert rendered == []


@pytest.mark.parametrize("name", ["Status Table", "a_b", "", "a--b"])
def test_render_stills_rejects_a_bad_box_name_before_rendering(tmp_path, rendered, name):
    stills = [Still("a", 1.0), Still("main", 1.0, {name: (0, 0, 1, 1)})]
    with pytest.raises(ValueError, match="s/main box"):
        clips.render_stills("s", _rec(), stills, tmp_path)
    assert rendered == []


def test_render_stills_returns_one_entry_per_still(tmp_path, rendered):
    stills = [Still("a", 1.0, {"status-table": (0, 0, 1, 10)}), Still("b", 2.0)]
    entries = clips.render_stills("s", _rec(), stills, tmp_path)
    assert [e["id"] for e in entries] == ["s/a", "s/b"]
    assert entries[0]["boxes"] == {"status-table": box(Geometry(10, 4), 0, 0, 1, 10)}
    assert entries[1]["boxes"] == {}
    assert rendered == [tmp_path / "s" / "a.png", tmp_path / "s" / "b.png"]


@pytest.mark.parametrize("stray", ["b/x", "ab/x", "a"])
def test_manifest_update_rejects_an_id_outside_the_scenario(tmp_path, stray):
    with pytest.raises(ValueError, match="must have ids starting 'a/'"):
        manifest.update(tmp_path, "tui", "a", "shots", [{"id": "a/ok"}, {"id": stray}])
    assert not (tmp_path / "manifest.json").exists()


def test_manifest_update_rejects_duplicate_ids(tmp_path):
    with pytest.raises(ValueError, match="duplicate ids in scenario 'a'"):
        manifest.update(tmp_path, "tui", "a", "shots", [{"id": "a/x", "origin": "shots"}] * 2)
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize(("argv", "message"), [
    (["--clips"], "--clips needs ffmpeg on PATH"),
    (["--selftest"], "--selftest renders a clip and needs ffmpeg on PATH"),
])
def test_main_exits_with_a_message_when_a_clip_needs_ffmpeg(monkeypatch, argv, message):
    monkeypatch.setattr(sys, "argv", ["tuicap", *argv])
    monkeypatch.setattr(clips.shutil, "which", lambda name: None)
    monkeypatch.setattr(clips, "selftest", _forbidden)
    monkeypatch.setattr(clips, "capture", _forbidden)
    with pytest.raises(SystemExit, match=f"^tuicap: {message}$"):
        clips.main()


def test_main_renders_stills_without_ffmpeg(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "argv", ["tuicap", "settings", "settings", "--for", "blog"])
    monkeypatch.setattr(clips.shutil, "which", lambda name: None)
    monkeypatch.setattr(clips.design, "mono", lambda: "font.ttf")
    monkeypatch.setattr(clips, "capture", lambda names, with_clips, out, profile, draft: seen.append(
        (names, with_clips, profile, draft)))
    clips.main()
    assert seen == [(["settings", "settings"], False, "blog", False)]


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project root; the test writes its design.json through the yielded function."""
    monkeypatch.setattr(design, "ROOT", tmp_path)
    monkeypatch.setattr(design, "DESIGN_JSON", tmp_path / "design.json")
    design.load.cache_clear()
    yield lambda data: (tmp_path / "design.json").write_text(json.dumps(data))
    design.load.cache_clear()


def test_palette_reads_design_json_when_asked_not_at_import(project):
    project({"colors": {"background": "red"}})
    importlib.reload(palette)
    with pytest.raises(ValueError, match="colors.background"):
        palette.bg()
    project({"colors": {"background": "#102030", "text": "#AABBCC"}})
    design.load.cache_clear()
    assert (palette.bg(), palette.fg()) == ("102030", "aabbcc")


def test_palette_bright_white_follows_the_text_colour(project):
    project({"colors": {"text": "#AABBCC"}})
    assert palette.resolve("brightwhite", "dflt") == "aabbcc"
    assert palette.resolve("default", "dflt") == "dflt"
    assert palette.resolve("red", "dflt") == palette.ANSI[1]


@pytest.mark.parametrize(("data", "message"), [
    ({"colors": {"background": "red"}}, "colors.background"),
    ({"logo": {"on_dark": "missing.svg"}}, "logo.on_dark .* does not exist"),
    ({"fonts": {"mono": "missing.ttf"}}, "fonts.mono .* does not exist"),
])
def test_main_exits_with_a_message_for_a_bad_design(project, monkeypatch, data, message):
    project(data)
    monkeypatch.setattr(sys, "argv", ["tuicap"])
    monkeypatch.setattr(clips, "capture", _forbidden)
    with pytest.raises(SystemExit, match=f"^tuicap: .*{message}"):
        clips.main()


@pytest.mark.parametrize(("data", "key"), [
    ({"fonts": "x"}, "fonts"),
    ({"colors": []}, "colors"),
    ({"logo": 3}, "logo"),
    ({"fonts": {"weights": "x"}}, "fonts.weights"),
])
def test_validate_names_the_key_that_is_not_an_object(data, key):
    with pytest.raises(ValueError, match=f"^{key} = .*expected an object"):
        design.validate(data)


def test_read_prefixes_the_object_error_with_the_file(project):
    project({"fonts": "x"})
    with pytest.raises(ValueError, match=r"design\.json.*fonts = 'x': expected an object"):
        design.read()


@pytest.mark.parametrize(("jobs", "cpus", "workers"), [(5, 2, 2), (2, 8, 2), (3, None, 1), (0, 4, 1)])
def test_run_caps_the_pool_at_the_cpu_count(tmp_path, monkeypatch, jobs, cpus, workers):
    seen = []

    class Pool(_Inline):
        def __init__(self, max_workers=None):
            seen.append(max_workers)

    monkeypatch.setattr(clips, "ProcessPoolExecutor", Pool)
    monkeypatch.setattr(clips.os, "cpu_count", lambda: cpus)
    monkeypatch.setattr(clips, "_job", lambda job: ("a", "shots", []))
    clips.run([None] * jobs, tmp_path)
    assert seen == [workers]


DEJAVU = "/f/DejaVuSansMono-Bold.ttf|Bold\n/f/DejaVuSansMono.ttf|Book,Regular\n/f/DejaVuSansMono-Oblique.ttf|Oblique,Italic\n"
SYMBOLS = "/f/NotoSansSymbols-Light.ttf|Light,Regular\n/f/NotoSansSymbols-Regular.ttf|Regular\n/f/NotoSansSymbols-Bold.ttf|Bold\n"


@pytest.fixture
def fontconfig(monkeypatch):
    """A fc-list stand-in: the test fills {family: stdout}; every call is recorded."""
    listing, calls = {}, []

    def run(argv, **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] == fonts.FC_TIMEOUT
        return types.SimpleNamespace(stdout=listing.get(argv[-1], ""))

    monkeypatch.setattr(fonts, "subprocess", types.SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired))
    monkeypatch.setattr(fonts, "MACOS", False)
    fonts.fallback_fonts.cache_clear()
    fonts.emoji_font.cache_clear()
    yield listing, calls
    fonts.fallback_fonts.cache_clear()
    fonts.emoji_font.cache_clear()


def test_fallback_fonts_come_by_family_in_order_regular_style_first(fontconfig):
    listing, calls = fontconfig
    listing.update({"Noto Sans Math": "/f/NotoSansMath-Regular.ttf|Regular\n", "DejaVu Sans Mono": DEJAVU,
                    "Noto Sans Symbols2": "/f/NotoSansSymbols2-Regular.ttf|Regular\n", "Noto Sans Symbols": SYMBOLS})
    assert fonts.fallback_fonts() == ("/f/DejaVuSansMono.ttf", "/f/NotoSansSymbols2-Regular.ttf",
                                      "/f/NotoSansSymbols-Regular.ttf", "/f/NotoSansMath-Regular.ttf")
    assert [argv[-1] for argv in calls] == ["DejaVu Sans Mono", "Noto Sans Symbols2", "Noto Sans Symbols", "Noto Sans Math"]
    assert all(argv[0] == "fc-list" for argv in calls)


def test_fallback_fonts_skip_a_family_that_is_not_installed(fontconfig):
    listing, _ = fontconfig
    listing.update({"Noto Sans Symbols2": "/f/Symbols2.ttf|Regular\n", "Noto Sans Math": "/f/Math.ttf|Regular\n"})
    assert fonts.fallback_fonts() == ("/f/Symbols2.ttf", "/f/Math.ttf")


def test_font_lookup_survives_a_missing_fc_list(fontconfig, monkeypatch):
    def missing(argv, **kwargs):
        raise FileNotFoundError("fc-list")

    monkeypatch.setattr(fonts, "subprocess", types.SimpleNamespace(run=missing, TimeoutExpired=subprocess.TimeoutExpired))
    assert fonts.fallback_fonts() == ()
    assert fonts.emoji_font() is None


def test_font_lookup_survives_an_fc_list_timeout(fontconfig, monkeypatch):
    def hung(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(fonts, "subprocess", types.SimpleNamespace(run=hung, TimeoutExpired=subprocess.TimeoutExpired))
    assert fonts.fallback_fonts() == ()
    assert fonts.emoji_font() is None


def test_emoji_font_is_the_noto_color_emoji_file(fontconfig):
    listing, calls = fontconfig
    listing["Noto Color Emoji"] = "/f/NotoColorEmoji.ttf|Regular\n"
    assert fonts.emoji_font() == "/f/NotoColorEmoji.ttf"
    assert calls[-1][-1] == "Noto Color Emoji"


def test_emoji_font_is_none_when_the_family_is_not_installed(fontconfig):
    assert fonts.emoji_font() is None


def test_macos_fonts_are_the_fixed_system_files(fontconfig, monkeypatch):
    _, calls = fontconfig
    monkeypatch.setattr(fonts, "MACOS", True)
    assert fonts.fallback_fonts() == ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Apple Symbols.ttf")
    assert fonts.emoji_font() == "/System/Library/Fonts/Apple Color Emoji.ttc"
    assert calls == []
