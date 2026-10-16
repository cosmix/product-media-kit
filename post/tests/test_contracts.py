"""Contract tests for postkit: slug and manifest path safety, rebuild ledger, relative links."""

import json
import re
from pathlib import Path

import pytest
from PIL import Image
from postkit.assemble import BuildError, build
from postkit.manifest import ManifestError, load_shots

DIALOG = "![Settings dialog](shot:web/settings/dialog)"
MENU = "![Settings menu](shot:web/settings/menu)"


def write_draft(root: Path, *lines: str) -> None:
    (root / "post" / "draft.md").write_text("# Demo\n\n" + "\n\n".join(lines) + "\n")


def test_build_rejects_traversal_slug(make_project: Path) -> None:
    root = make_project
    (root / "project.json").write_text(json.dumps({"slug": "../evil"}))
    write_draft(root, DIALOG)

    with pytest.raises(BuildError):
        build(root)

    assert not (root / "evil.md").exists()
    assert not list(root.parent.rglob("evil.md"))
    out = root / "outputs"
    assert not out.exists() or not any(out.rglob("*"))


def test_load_shots_rejects_escaping_file(make_project: Path) -> None:
    root = make_project
    Image.new("RGB", (16, 16), (255, 0, 0)).save(root / "secret.png")
    assert (root / "captures" / "web" / "../../secret.png").resolve().is_file()
    escaping = {
        "id": "settings/secret",
        "kind": "still",
        "file": "../../secret.png",
        "width": 16,
        "height": 16,
        "scale": 1.0,
        "boxes": {},
    }
    manifest = root / "captures" / "web" / "manifest.json"
    manifest.write_text(json.dumps({"source": "web", "shots": [escaping]}))

    with pytest.raises(ManifestError):
        load_shots(root)


def test_rebuild_removes_only_own_stale_images(make_project: Path) -> None:
    root = make_project
    images = root / "outputs" / "blog" / "images"
    images.mkdir(parents=True)
    keep = images / "keep.png"
    Image.new("RGB", (8, 8), (0, 255, 0)).save(keep)
    keep_bytes = keep.read_bytes()

    write_draft(root, DIALOG, MENU)
    build(root)
    dialog = images / "web-settings-dialog.png"
    menu = images / "web-settings-menu.png"
    assert dialog.is_file()
    assert menu.is_file()

    write_draft(root, DIALOG)
    result = build(root)

    assert dialog.is_file()
    assert not menu.exists()
    assert [p.name for p in result.removed] == ["web-settings-menu.png"]
    assert keep.is_file()
    assert keep.read_bytes() == keep_bytes


def test_build_embeds_relative_image_links(make_project: Path) -> None:
    root = make_project
    write_draft(root, DIALOG)

    result = build(root)

    md = root / "outputs" / "blog" / "draft-demo-post-v1.md"
    assert Path(result.md).resolve() == md.resolve()
    text = md.read_text()
    assert "shot:" not in text
    links = re.findall(r"!\[Settings dialog\]\(([^)\s]+)", text)
    assert links == ["images/web-settings-dialog.png"]
    target = links[0]
    assert not Path(target).is_absolute()
    linked = (md.parent / target).resolve()
    assert linked.is_relative_to((root / "outputs" / "blog").resolve())
    assert linked.is_file()
    with Image.open(linked) as img:
        assert img.format == "PNG"
