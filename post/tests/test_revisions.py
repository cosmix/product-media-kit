"""Revisions, stages, the shared-image ledger and check's default targets."""

import json
from pathlib import Path

import pytest

from postkit.assemble import build, ledger_path
from postkit.check import check
from postkit.cli import main

DIALOG = "![Settings dialog](shot:web/settings/dialog)"
MENU = "![Settings menu](shot:web/settings/menu)"


def write_draft(root: Path, *lines: str) -> None:
    (root / "post" / "draft.md").write_text("# Demo\n\n" + "\n\n".join(lines) + "\n")


def names(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "outputs" / "blog").glob("*.md"))


def test_default_build_rewrites_the_latest_draft_revision(make_project: Path) -> None:
    write_draft(make_project, DIALOG)

    assert build(make_project).md.name == "draft-demo-post-v1.md"
    assert build(make_project).md.name == "draft-demo-post-v1.md"
    assert names(make_project) == ["draft-demo-post-v1.md"]


def test_next_and_revision_flags(make_project: Path) -> None:
    write_draft(make_project, DIALOG)
    build(make_project)

    assert build(make_project, next_rev=True).md.name == "draft-demo-post-v2.md"
    assert build(make_project).md.name == "draft-demo-post-v2.md"
    assert build(make_project, revision=5).md.name == "draft-demo-post-v5.md"
    assert build(make_project).md.name == "draft-demo-post-v5.md"
    assert main(["build", "--root", str(make_project), "--next"]) == 0
    assert names(make_project)[-1] == "draft-demo-post-v6.md"
    assert main(["build", "--root", str(make_project), "--revision", "v1"]) == 0


def test_final_has_its_own_numbering(make_project: Path) -> None:
    write_draft(make_project, DIALOG)
    build(make_project, next_rev=True)
    build(make_project, next_rev=True)

    assert build(make_project, final=True).md.name == "final-demo-post-v1.md"
    assert names(make_project) == ["draft-demo-post-v1.md", "draft-demo-post-v2.md", "final-demo-post-v1.md"]


def test_cli_rejects_next_with_revision_and_bad_revision(make_project: Path) -> None:
    for argv in (["--next", "--revision", "v2"], ["--revision", "2"], ["--revision", "v0"]):
        with pytest.raises(SystemExit):
            main(["build", "--root", str(make_project), *argv])


def test_ledger_lives_under_post_build(make_project: Path) -> None:
    write_draft(make_project, DIALOG)
    build(make_project)

    data = json.loads(ledger_path(make_project).read_text())
    assert ledger_path(make_project) == make_project / "post" / "build" / "ledger.json"
    assert data == {"files": ["images/web-settings-dialog.png"]}
    assert not (make_project / "outputs" / "blog" / ".postkit.json").exists()


def test_image_survives_while_another_revision_references_it(make_project: Path) -> None:
    root = make_project
    images = root / "outputs" / "blog" / "images"
    write_draft(root, DIALOG, MENU)
    build(root)  # v1 links dialog and menu
    write_draft(root, DIALOG)
    build(root, next_rev=True)  # v2 drops menu, v1 still links it

    assert (images / "web-settings-menu.png").is_file()
    assert "images/web-settings-menu.png" in json.loads(ledger_path(root).read_text())["files"]

    (root / "outputs" / "blog" / "draft-demo-post-v1.md").unlink()
    result = build(root)  # the last reference is gone

    assert not (images / "web-settings-menu.png").exists()
    assert [p.name for p in result.removed] == ["web-settings-menu.png"]


def test_losing_the_ledger_deletes_nothing(make_project: Path) -> None:
    root = make_project
    write_draft(root, DIALOG, MENU)
    build(root)
    ledger_path(root).unlink()
    write_draft(root, DIALOG)

    result = build(root)

    assert result.removed == []
    assert (root / "outputs" / "blog" / "images" / "web-settings-menu.png").is_file()


def test_check_defaults_to_latest_draft_and_final(make_project: Path) -> None:
    root = make_project
    blog = root / "outputs" / "blog"
    write_draft(root, DIALOG)
    build(root)
    build(root, next_rev=True)
    build(root, final=True)
    (blog / "draft-demo-post-v1.md").write_text("![](images/old-broken.png)\n")  # not the latest draft
    (blog / "final-demo-post-v1.md").write_text((blog / "final-demo-post-v1.md").read_text() + "![](x.png)\n")

    messages = [p.message for p in check(root) if p.level == "ERROR"]

    assert len(messages) == 2  # the final's empty alt and missing x.png; the old draft is not checked
    assert all(m.startswith("final-demo-post-v1.md") for m in messages)
    picked = check(root, blog / "draft-demo-post-v1.md")
    assert any("old-broken.png" in p.message for p in picked)
    assert check(root, Path("draft-demo-post-v2.md")) == []


def test_unreferenced_warning_scans_every_post(make_project: Path) -> None:
    root = make_project
    images = root / "outputs" / "blog" / "images"
    write_draft(root, DIALOG)
    build(root)
    write_draft(root, MENU)
    build(root, next_rev=True)

    assert check(root) == []  # v2 is the latest; v1 still references the dialog
    (images / "orphan.png").write_bytes((images / "web-settings-dialog.png").read_bytes())
    warns = [p.message for p in check(root) if p.level == "WARN"]
    assert len(warns) == 1
    assert "orphan.png" in warns[0]
