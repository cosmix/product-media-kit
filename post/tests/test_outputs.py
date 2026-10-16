"""outputs.py naming: regex, latest revision, primary and companion paths."""

from pathlib import Path

import pytest

from postkit.outputs import NAME_RE, latest_revision, output_path

SLUG = "acme"


def touch(directory: Path, *names: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / name).write_bytes(b"x")


def test_name_re_groups_and_rejections() -> None:
    pattern = NAME_RE(SLUG, "md")

    m = pattern.match("draft-acme-v12.md")
    assert m and (m[1], m[2], m[3]) == ("draft", "12", None)
    m = NAME_RE(SLUG, "mp4").match("final-acme-v2-range-1-5.mp4")
    assert m and m[3] == "-range-1-5"
    for bad in ("draft-acme.md", "other-acme-v1.md", "draft-acme-v1.mp4", "draft-acme-vx.md", "draft-acme-v1-.md"):
        assert not pattern.match(bad)


def test_latest_revision_counts_primaries_of_the_stage_and_ext(tmp_path: Path) -> None:
    touch(tmp_path, "draft-acme-v1.md", "draft-acme-v3.md", "draft-acme-v9-extra.md", "final-acme-v5.md",
          "draft-acme-v7.srt", "draft-other-v8.md")

    assert latest_revision(tmp_path, SLUG, "draft", "md") == 3
    assert latest_revision(tmp_path, SLUG, "final", "md") == 5
    assert latest_revision(tmp_path, SLUG, "final", "srt") is None
    assert latest_revision(tmp_path / "missing", SLUG, "draft", "md") is None


def test_latest_revision_is_not_recursive(tmp_path: Path) -> None:
    touch(tmp_path / "sub", "draft-acme-v4.md")

    assert latest_revision(tmp_path, SLUG, "draft", "md") is None


def test_primary_rewrites_latest_or_starts_at_one(tmp_path: Path) -> None:
    def path(**kw: object) -> str:
        return output_path(tmp_path, SLUG, "draft", "md", primary_ext="md", **kw).name  # type: ignore[arg-type]

    assert path() == "draft-acme-v1.md"
    assert path(next_rev=True) == "draft-acme-v1.md"
    touch(tmp_path, "draft-acme-v2.md")
    assert path() == "draft-acme-v2.md"
    assert path(next_rev=True) == "draft-acme-v3.md"
    assert path(revision=7) == "draft-acme-v7.md"
    assert path(revision=7, next_rev=True) == "draft-acme-v7.md"


def test_companion_attaches_to_the_latest_primary(tmp_path: Path) -> None:
    def path(**kw: object) -> str:
        return output_path(tmp_path, SLUG, "final", "srt", primary_ext="mp4", suffix="share", **kw).name  # type: ignore[arg-type]

    assert path() == "final-acme-v1-share.srt"
    touch(tmp_path, "final-acme-v4.mp4", "final-acme-v6-share.mp4", "draft-acme-v9.mp4")
    assert path() == "final-acme-v4-share.srt"
    assert path(revision=2) == "final-acme-v2-share.srt"


@pytest.mark.parametrize(("stage", "suffix", "revision"), [("beta", None, None), ("draft", "Bad", None),
                                                          ("draft", "a_b", None), ("draft", None, 0)])
def test_output_path_validates(tmp_path: Path, stage: str, suffix: str | None, revision: int | None) -> None:
    with pytest.raises(ValueError):
        output_path(tmp_path, SLUG, stage, "md", primary_ext="md", suffix=suffix, revision=revision)
