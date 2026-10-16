"""Ledger deletions, every way a post names an image, part-file cleanup, add's PNG validation."""

import json
from pathlib import Path

import pytest
from PIL import Image

from postkit.add import AddError, add
from postkit.assemble import build, ledger_path
from postkit.check import check
from postkit.common import referenced_images, remove_part_files


def blog_with(tmp_path: Path, text: str) -> Path:
    blog = tmp_path / "blog"
    (blog / "images").mkdir(parents=True)
    (blog / "post.md").write_text(text, encoding="utf-8")
    return blog


@pytest.mark.parametrize("text", [
    "![a](<images/a.png>)\n",
    '<p><img alt="a" src="images/a.png"></p>\n',
    "<img src='images/a.png'>\n",
    "![a][ref]\n\n[ref]: images/a.png\n",
    "![a][ref]\n\n[ref]: <images/a.png> \"title\"\n",
    "---\nhero: images/a.png\n---\ntext\n",
    "---\nimages:\n  - 'images/a.png'\n---\ntext\n",
])
def test_every_way_of_naming_an_image_counts(tmp_path: Path, text: str) -> None:
    blog = blog_with(tmp_path, text)

    assert (blog / "images" / "a.png").resolve() in referenced_images(blog)


def test_a_fenced_example_does_not_count(tmp_path: Path) -> None:
    blog = blog_with(tmp_path, "```html\n<img src=\"images/a.png\">\n```\n")

    assert referenced_images(blog) == set()


def test_ledger_deletes_only_inside_images(make_project: Path) -> None:
    blog = make_project / "outputs" / "blog"
    (make_project / "post" / "draft.md").write_text("# Demo\n\n![Dialog](shot:web/settings/dialog)\n")
    build(make_project)
    (blog / "notes.txt").write_text("keep")
    (make_project.parent / "outside.txt").write_text("keep")
    ledger_path(make_project).write_text(json.dumps({"files": ["notes.txt", "../../outside.txt"]}))

    result = build(make_project)

    assert result.removed == []
    assert (blog / "notes.txt").exists() and (make_project.parent / "outside.txt").exists()


def test_check_accepts_angle_bracket_image_targets(make_project: Path) -> None:
    (make_project / "post" / "draft.md").write_text("# Demo\n\n![Dialog](shot:web/settings/dialog)\n")
    md = build(make_project).md
    md.write_text(md.read_text().replace("(images/", "(<images/").replace(".png)", ".png>)"))

    assert check(make_project) == []


def test_remove_part_files_only_removes_what_postkit_writes(tmp_path: Path) -> None:
    blog = blog_with(tmp_path, "x")
    mine = [blog / ".draft-demo-v1.md.part", blog / "images" / ".a.png.part"]
    theirs = [blog / ".keep.part", blog / "extra" / ".a.png.part"]
    theirs[1].parent.mkdir()
    for p in [*mine, *theirs]:
        p.write_text("x")

    remove_part_files(blog)

    assert not any(p.exists() for p in mine)
    assert all(p.exists() for p in theirs)


def test_add_rejects_a_fake_png_and_leaves_no_orphan(tmp_path: Path) -> None:
    fake = tmp_path / "fake.png"
    fake.write_text("not an image")
    jpeg = tmp_path / "photo.png"
    Image.new("RGB", (8, 8)).save(jpeg, format="JPEG")

    for bad in (fake, jpeg):
        with pytest.raises(AddError):
            add(tmp_path, "web/intro/title", bad)
        assert not (tmp_path / "captures" / "web" / "intro" / "title.png").exists()
