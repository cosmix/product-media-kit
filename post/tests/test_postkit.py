"""Unit tests for postkit: images.json defaults, crop translation, clips, check(), draft errors."""

import json
import zlib
from pathlib import Path

import pytest
from PIL import Image

from postkit.assemble import BuildError, build
from postkit.check import check
from postkit.cli import main
from postkit.common import part_path
from postkit.config import treatment_for
from postkit.design import Design
from postkit.images import Treatment, treat
from postkit.manifest import load_shots

ACCENT = (37, 99, 235)  # Design().accent, #2563eb
DIALOG_COLOR = (40, 90, 160)  # conftest's settings/dialog fill


def write_draft(root: Path, *lines: str) -> None:
    (root / "post" / "draft.md").write_text("# Demo\n\n" + "\n\n".join(lines) + "\n")


def test_images_json_defaults_merge_under_entries(make_project: Path) -> None:
    shots = load_shots(make_project)
    config = {"defaults": {"width": 800, "pad": 8}, "web/settings/dialog": {"width": 1000, "frame": "none"}}

    dialog, dialog_errors = treatment_for(shots["web/settings/dialog"], config)
    menu, menu_errors = treatment_for(shots["web/settings/menu"], config)
    plain, _ = treatment_for(shots["web/settings/menu"], {})

    assert dialog_errors == menu_errors == []
    assert (dialog.width, dialog.pad, dialog.frame) == (1000, 8, "none")
    assert (menu.width, menu.pad, menu.frame) == (800, 8, "browser")
    assert plain == Treatment(frame="browser")


def test_images_json_rejects_unknown_boxes_and_keys(make_project: Path) -> None:
    shot = load_shots(make_project)["web/settings/dialog"]

    _, errors = treatment_for(shot, {shot.ref: {"crop": "nope", "callouts": ["save", "gone"], "zoom": 2}})

    assert len(errors) == 3
    assert any("unknown key 'zoom'" in e for e in errors)
    assert any("crop 'nope'" in e for e in errors)
    assert any("callouts 'gone'" in e for e in errors)


def test_crop_translates_highlight_boxes(make_project: Path, tmp_path: Path) -> None:
    shot = load_shots(make_project)["web/settings/dialog"]  # 320x200, save = [200, 150, 80, 30]
    dest = tmp_path / "dialog.png"

    treat(shot, Treatment(crop="save", pad=10, highlight=["save"]), Design(), dest)

    with Image.open(dest) as img:
        rgb = img.convert("RGB")
    assert rgb.size == (100, 50)  # x 190..290, y 140..190 (clamped to the image bottom)
    assert rgb.getpixel((7, 25)) == ACCENT  # the outline sits just left of the moved box at x=10
    assert rgb.getpixel((50, 25)) == DIALOG_COLOR


def test_wide_still_is_resized_never_upscaled(make_project: Path, tmp_path: Path) -> None:
    shot = load_shots(make_project)["web/settings/dialog"]

    treat(shot, Treatment(width=160), Design(), tmp_path / "small.png")
    treat(shot, Treatment(width=5000), Design(), tmp_path / "same.png")

    with Image.open(tmp_path / "small.png") as small, Image.open(tmp_path / "same.png") as same:
        assert small.size == (160, 100)
        assert same.size == (320, 200)


def test_build_copies_clip_and_webm(make_project: Path) -> None:
    root = make_project
    scene = root / "captures" / "web" / "demo"
    scene.mkdir()
    frames = [Image.new("P", (40, 30), i) for i in (1, 2)]
    frames[0].save(scene / "clip.gif", save_all=True, append_images=frames[1:], duration=100)
    (scene / "clip.webm").write_bytes(b"\x1aE\xdf\xa3webm")
    clip = {"id": "demo/clip", "kind": "clip", "file": "demo/clip.gif", "webm": "demo/clip.webm",
            "width": 40, "height": 30, "scale": 1.0, "duration": 0.2, "boxes": {}}
    manifest = root / "captures" / "web" / "manifest.json"
    data = json.loads(manifest.read_text())
    data["shots"].append(clip)
    manifest.write_text(json.dumps(data))
    write_draft(root, "![A short clip](shot:web/demo/clip)")

    result = build(root)

    images = root / "outputs" / "blog" / "images"
    assert (images / "web-demo-clip.gif").read_bytes() == (scene / "clip.gif").read_bytes()
    assert (images / "web-demo-clip.webm").read_bytes() == (scene / "clip.webm").read_bytes()
    assert "![A short clip](images/web-demo-clip.gif)" in result.md.read_text()
    assert check(root) == []


def test_build_rejects_unknown_shot_and_empty_alt(make_project: Path) -> None:
    root = make_project
    write_draft(root, "![](shot:web/settings/dialog)", "![Gone](shot:web/settings/gone)")

    with pytest.raises(BuildError) as err:
        build(root)

    message = str(err.value)
    assert "empty alt text" in message
    assert "unknown shot 'web/settings/gone'" in message
    assert not (root / "outputs").exists()


def test_build_keeps_front_matter_and_titles(make_project: Path) -> None:
    root = make_project
    (root / "post" / "draft.md").write_text(
        '---\nimage: shot:web/settings/dialog\n---\n\n![Dialog](shot:web/settings/dialog "The dialog")\n'
    )

    text = build(root).md.read_text()

    assert text.startswith("---\nimage: shot:web/settings/dialog\n---\n")
    assert '![Dialog](images/web-settings-dialog.png "The dialog")' in text


def test_check_reports_link_problems(make_project: Path) -> None:
    root = make_project
    write_draft(root, "![Dialog](shot:web/settings/dialog)")
    md = build(root).md
    images = root / "outputs" / "blog" / "images"
    Image.new("RGB", (2500, 10)).save(images / "wide.png")
    Image.new("RGB", (8, 8)).save(images / "orphan.png")
    links = ["![](images/web-settings-dialog.png)", "![Abs](/etc/x.png)", "![Up](../secret.png)",
             "![Gone](images/missing.png)", "![Left](shot:web/settings/menu)", "![Wide](images/wide.png)",
             "![Remote](https://example.com/a.png)"]
    md.write_text(md.read_text() + "\n".join(links) + "\n")

    problems = [(p.level, p.message) for p in check(root)]

    def has(level: str, text: str) -> bool:
        return any(lv == level and text in msg for lv, msg in problems)

    assert has("ERROR", "![](images/web-settings-dialog.png): empty alt text")
    assert has("ERROR", "![Abs](/etc/x.png): absolute image path")
    assert has("ERROR", "![Up](../secret.png): image path escapes outputs/blog/")
    assert has("ERROR", "missing.png is missing")
    assert has("ERROR", "![Left](shot:web/settings/menu): leftover shot: link")
    assert has("WARN", "![Wide](images/wide.png): 2500 px wide")
    assert has("WARN", "orphan.png is not referenced")
    assert not has("WARN", "wide.png is not referenced")
    assert sum(lv == "ERROR" for lv, _ in problems) == 5
    assert not any("example.com" in msg for _, msg in problems)


def test_check_reports_missing_post(make_project: Path) -> None:
    problems = check(make_project)

    assert [p.level for p in problems] == ["ERROR"]
    assert "no built post" in problems[0].message


def add_dialog_copies(root: Path, ids: list[str]) -> None:
    """Add stills with the given ids that all point at the dialog capture."""
    manifest = root / "captures" / "web" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["shots"] += [{"id": i, "kind": "still", "file": "settings/dialog.png", "width": 320, "height": 200,
                       "scale": 1.0, "boxes": {}} for i in ids]
    manifest.write_text(json.dumps(data), encoding="utf-8")


def test_build_rejects_refs_that_share_an_output_file(make_project: Path) -> None:
    root = make_project
    add_dialog_copies(root, ["a-b/c", "a/b-c"])
    write_draft(root, "![One](shot:web/a-b/c)", "![Two](shot:web/a/b-c)")

    with pytest.raises(BuildError) as err:
        build(root)

    message = str(err.value)
    assert "web/a-b/c" in message and "web/a/b-c" in message
    assert "both write images/web-a-b-c.png" in message
    assert not (root / "outputs").exists()


def _corrupt_idat(png: bytes, fix_crc: bool) -> bytes:
    """Overwrite IDAT data; with fix_crc the chunk CRC stays valid so only zlib breaks."""
    at = png.index(b"IDAT")
    length = int.from_bytes(png[at - 4 : at], "big")
    data = b"\xff" * length
    if fix_crc:
        crc = zlib.crc32(b"IDAT" + data).to_bytes(4, "big")
    else:
        crc = png[at + 4 + length : at + 8 + length]
    return png[: at + 4] + data + crc + png[at + 8 + length :]


@pytest.mark.parametrize("corrupt", ["garbage", "bad-crc", "bad-zlib"])
def test_build_rejects_unreadable_capture_before_writing(make_project: Path, corrupt: str) -> None:
    root = make_project
    menu = root / "captures" / "web" / "settings" / "menu.png"
    if corrupt == "garbage":
        menu.write_bytes(b"not an image")
    else:
        menu.write_bytes(_corrupt_idat(menu.read_bytes(), fix_crc=corrupt == "bad-zlib"))
    write_draft(root, "![Dialog](shot:web/settings/dialog)", "![Menu](shot:web/settings/menu)")

    with pytest.raises(BuildError) as err:
        build(root)

    assert "web/settings/menu: capture file" in str(err.value)
    assert "not a readable image" in str(err.value)
    assert not (root / "outputs").exists()


def test_check_skips_front_matter(make_project: Path) -> None:
    root = make_project
    write_draft(root, "![Dialog](shot:web/settings/dialog)")
    md = build(root).md
    md.write_text("---\nimage: ![](shot:web/x)\n---\n" + md.read_text(encoding="utf-8"), encoding="utf-8")

    assert check(root) == []


def test_bold_font_falls_back_when_named_file_is_missing(make_project: Path) -> None:
    from postkit.design import load

    (make_project / "design.json").write_text(json.dumps({"fonts": {"bold": "nope.ttf"}}), encoding="utf-8")

    assert load(make_project).bold_font != make_project / "nope.ttf"


def test_cli_selftest_passes() -> None:
    assert main(["selftest"]) == 0


def test_cli_build_fails_on_a_bad_project(tmp_path: Path) -> None:
    assert main(["build", "--root", str(tmp_path)]) == 1


def test_cli_check_fails_on_an_error(make_project: Path) -> None:
    write_draft(make_project, "![Dialog](shot:web/settings/dialog)")
    md = build(make_project).md
    md.write_text(md.read_text(encoding="utf-8") + "![](images/web-settings-dialog.png)\n", encoding="utf-8")

    assert main(["check", "--root", str(make_project)]) == 1
    assert main(["check", "--root", str(make_project / "nowhere")]) == 1


BRACKET_ALT = "![Press [Enter] to save](shot:web/settings/dialog)"
SINGLE_TITLE = "![Status](shot:web/settings/dialog 'Status table')"
UNREWRITABLE = ["[Dialog](shot:web/settings/dialog)", "![Dialog](<shot:web/settings/dialog>)",
                "![Dialog]( shot:web/settings/dialog)"]


def built_md(root: Path, *extra: str) -> Path:
    """Build a draft with the dialog, append `extra` lines to outputs/blog/draft-<slug>-v1.md and return its path."""
    write_draft(root, "![Dialog](shot:web/settings/dialog)")
    md = build(root).md
    md.write_text(md.read_text(encoding="utf-8") + "".join(f"{line}\n" for line in extra), encoding="utf-8")
    return md


@pytest.mark.parametrize(("link", "built"), [
    (BRACKET_ALT, "![Press [Enter] to save](images/web-settings-dialog.png)"),
    (SINGLE_TITLE, "![Status](images/web-settings-dialog.png 'Status table')"),
])
def test_build_rewrites_bracketed_alt_and_single_quoted_title(make_project: Path, link: str, built: str) -> None:
    write_draft(make_project, link)

    text = build(make_project).md.read_text(encoding="utf-8")

    assert built in text
    assert "shot:" not in text
    assert check(make_project) == []


@pytest.mark.parametrize("link", UNREWRITABLE)
def test_build_refuses_a_shot_link_it_cannot_rewrite(make_project: Path, link: str) -> None:
    write_draft(make_project, link, "![Dialog](shot:web/settings/dialog)", link)

    with pytest.raises(BuildError) as err:
        build(make_project)

    lines = str(err.value).splitlines()
    assert [line.split(":")[1] for line in lines] == ["3", "7"]
    assert all("a shot: link that is not an image" in line for line in lines)
    assert not (make_project / "outputs").exists()


@pytest.mark.parametrize("link", [BRACKET_ALT, SINGLE_TITLE, *UNREWRITABLE])
def test_check_reports_every_leftover_shot_link(make_project: Path, link: str) -> None:
    md = built_md(make_project, link)
    line = md.read_text(encoding="utf-8").count("\n")  # the link is the last line

    errors = [p.message for p in check(make_project) if p.level == "ERROR"]

    assert len(errors) == 1
    assert errors[0].startswith(f"draft-demo-post-v1.md:{line}:")
    assert "leftover shot: link" in errors[0]


@pytest.mark.parametrize("fence", ["```", "~~~", "````"])
def test_fenced_code_is_left_alone_by_build_and_check(make_project: Path, fence: str) -> None:
    code = f"{fence}markdown\n![Alt](shot:web/settings/gone)\n![](missing.png)\n[a](shot:x)\n{fence}"
    write_draft(make_project, "![Dialog](shot:web/settings/dialog)", code, "![Menu](shot:web/settings/menu)")

    text = build(make_project).md.read_text(encoding="utf-8")

    assert code in text
    assert "![Dialog](images/web-settings-dialog.png)" in text
    assert "![Menu](images/web-settings-menu.png)" in text
    assert check(make_project) == []


def test_check_ignores_fragment_and_query_and_accepts_external_images(make_project: Path) -> None:
    built_md(make_project, "![Frag](images/web-settings-dialog.png#top)",
             "![Query](images/web-settings-dialog.png?v=2#top)", "![Data](data:image/png;base64,AAAA)",
             "![Upper](HTTPS://example.com/a.png)", "![Proto](//example.com/a.png)")

    assert check(make_project) == []


def test_check_strips_the_fragment_before_looking_for_the_file(make_project: Path) -> None:
    built_md(make_project, "![Gone](images/missing.png?v=1#top)")

    errors = [p.message for p in check(make_project) if p.level == "ERROR"]

    assert len(errors) == 1
    assert errors[0].endswith("missing.png is missing")


def test_check_reports_a_markdown_file_that_is_not_utf8(make_project: Path) -> None:
    md = built_md(make_project)
    md.write_bytes(b"\xff\xfe# not utf-8\n")

    problems = [p for p in check(make_project) if p.level == "ERROR"]

    assert len(problems) == 1
    assert "cannot read" in problems[0].message


def test_build_deletes_part_files_a_killed_run_left(make_project: Path) -> None:
    write_draft(make_project, "![Dialog](shot:web/settings/dialog)")
    out = make_project / "outputs" / "blog"
    stale = [part_path(out / "draft-demo-post-v1.md"), part_path(out / "images" / "web-settings-dialog.png")]
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"half")

    build(make_project)

    assert not any(path.exists() for path in stale)
    assert check(make_project) == []


def huge_png(source: bytes) -> bytes:
    """`source` with its IHDR claiming 20000 x 20000 pixels, which Pillow refuses as a decompression bomb."""
    at = source.index(b"IHDR")
    header = (20000).to_bytes(4, "big") * 2 + source[at + 12 : at + 17]
    crc = zlib.crc32(b"IHDR" + header).to_bytes(4, "big")
    return source[: at + 4] + header + crc + source[at + 21 :]


def test_build_rejects_a_decompression_bomb_capture(make_project: Path) -> None:
    menu = make_project / "captures" / "web" / "settings" / "menu.png"
    menu.write_bytes(huge_png(menu.read_bytes()))
    write_draft(make_project, "![Menu](shot:web/settings/menu)")

    with pytest.raises(BuildError, match="not a readable image"):
        build(make_project)

    assert not (make_project / "outputs").exists()


def test_check_reports_a_decompression_bomb_image(make_project: Path) -> None:
    built = make_project / "outputs" / "blog" / "images" / "web-settings-dialog.png"
    built_md(make_project, "![Huge](images/huge.png)")
    (built.parent / "huge.png").write_bytes(huge_png(built.read_bytes()))

    errors = [p.message for p in check(make_project) if p.level == "ERROR"]

    assert len(errors) == 1
    assert "![Huge](images/huge.png): not a readable image" in errors[0]
