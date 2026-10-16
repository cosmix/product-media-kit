"""Unit tests for postkit internals: fenced-code scanning, atomic writes, the resolved font."""

import hashlib
import json
from pathlib import Path

import pytest

from postkit.common import IMAGE_RE, body_matches, copy_atomic, part_path, write_atomic


def test_body_matches_skips_front_matter_and_fenced_blocks() -> None:
    text = ("---\nk: ![a](x)\n---\n![b](x)\n````\n![c](x)\n```\n![d](x)\n````\n![e](x)\n"
            "~~~ md\n![f](x)\n\n![g](x)\n")  # the 3-backtick line does not close the 4-backtick fence

    assert [m["alt"] for m in body_matches(IMAGE_RE, text)] == ["b", "e"]  # the ~~~ fence is never closed


def test_atomic_writes_remove_the_part_file_when_the_replace_fails(tmp_path: Path) -> None:
    target = tmp_path / "taken"
    target.mkdir()  # os.replace cannot put a file over a directory
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    with pytest.raises(OSError):
        write_atomic(target, b"x")
    assert not part_path(target).exists()
    with pytest.raises(OSError):
        copy_atomic(source, target)
    assert not part_path(target).exists()


def bold_font_from_resolved(root: Path, font: Path, sha256: str | None) -> Path | None:
    """The bold font load() picks when brand/fonts/resolved.json names `font` for a design.json hashing to `sha256`."""
    from postkit.design import load

    design = root / "design.json"
    design.write_text('{"colors": {}}', encoding="utf-8")
    font.parent.mkdir(parents=True, exist_ok=True)
    font.write_bytes(b"not parsed, only looked up")
    resolved = root / "brand" / "fonts" / "resolved.json"
    resolved.parent.mkdir(parents=True, exist_ok=True)
    value = str(font.relative_to(root)) if font.is_relative_to(root) else str(font)  # tools/fonts.py shown()
    sha = hashlib.sha256(design.read_bytes()).hexdigest() if sha256 is None else sha256
    resolved.write_text(json.dumps({"fonts.bold": value, "design_json_sha256": sha}), encoding="utf-8")
    return load(root).bold_font


@pytest.mark.parametrize("absolute", [False, True])
def test_bold_font_uses_resolved_json_built_from_this_design(make_project: Path, tmp_path: Path, absolute: bool) -> None:
    font = tmp_path / "system" / "Bold.ttf" if absolute else make_project / "brand" / "fonts" / "Bold.ttf"

    assert bold_font_from_resolved(make_project, font, None) == font


def test_bold_font_ignores_resolved_json_built_from_another_design(make_project: Path) -> None:
    font = make_project / "brand" / "fonts" / "Bold.ttf"

    assert bold_font_from_resolved(make_project, font, "0" * 64) != font
