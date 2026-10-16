import argparse
import json

import pytest

from editkit.outputs import (
    latest_revision,
    name_re,
    output_path,
    read_slug,
    revision_arg,
)


def touch(d, *names):
    d.mkdir(exist_ok=True)
    for n in names:
        (d / n).write_bytes(b"")


def test_name_re_groups():
    m = name_re("demo", "mp4").match("final-demo-v12-range-1p5-4.mp4")
    assert m and m.group(1) == "final" and m.group(2) == "12" and m.group(3) == "-range-1p5-4"
    assert name_re("demo", "mp4").match("final-demo-v1.mp4").group(3) is None
    assert not name_re("demo", "mp4").match("preview-demo-v1.mp4")
    assert not name_re("demo", "mp4").match("final-other-v1.mp4")
    assert not name_re("demo", "mp4").match("final-demo-v1.srt")


def test_latest_ignores_companions_other_stages_and_exts(tmp_path):
    touch(tmp_path, "final-demo-v1.mp4", "final-demo-v3.mp4", "final-demo-v7-share.mp4",
          "draft-demo-v9.mp4", "final-demo-v8.srt")
    assert latest_revision(tmp_path, "demo", "final", "mp4") == 3
    assert latest_revision(tmp_path, "demo", "draft", "mp4") == 9
    assert latest_revision(tmp_path, "demo", "final", "srt") == 8
    assert latest_revision(tmp_path / "missing", "demo", "final", "mp4") is None


def test_primary_latest_next_and_revision(tmp_path):
    out = tmp_path / "outputs"
    assert output_path(out, "demo", "final", "mp4", primary_ext="mp4").name == "final-demo-v1.mp4"
    assert out.is_dir()
    touch(out, "final-demo-v2.mp4")
    assert output_path(out, "demo", "final", "mp4", primary_ext="mp4").name == "final-demo-v2.mp4"
    assert output_path(out, "demo", "final", "mp4", primary_ext="mp4", next_rev=True).name == "final-demo-v3.mp4"
    assert output_path(out, "demo", "final", "mp4", primary_ext="mp4", revision=5).name == "final-demo-v5.mp4"
    assert output_path(out, "demo", "draft", "mp4", primary_ext="mp4", next_rev=True).name == "draft-demo-v1.mp4"


def test_companions_follow_latest_primary(tmp_path):
    touch(tmp_path, "draft-demo-v1.mp4", "draft-demo-v4.mp4", "final-demo-v2.mp4", "draft-demo-v6.srt")
    p = output_path(tmp_path, "demo", "draft", "png", primary_ext="mp4", suffix="contact-00")
    assert p.name == "draft-demo-v4-contact-00.png"
    p = output_path(tmp_path, "demo", "final", "mp4", primary_ext="mp4", suffix="share")
    assert p.name == "final-demo-v2-share.mp4"
    p = output_path(tmp_path, "demo", "draft", "txt", primary_ext="mp4", suffix="credits", revision=1)
    assert p.name == "draft-demo-v1-credits.txt"
    assert output_path(tmp_path, "demo", "final", "srt", primary_ext="mp4", suffix="x").name == "final-demo-v2-x.srt"


def test_companion_without_primary_is_v1(tmp_path):
    p = output_path(tmp_path, "demo", "final", "mp4", primary_ext="mp4", suffix="share")
    assert p.name == "final-demo-v1-share.mp4"


@pytest.mark.parametrize("suffix", ["Range", "a_b", "-a", "a--b", "a b", "", "../x"])
def test_invalid_suffix(tmp_path, suffix):
    with pytest.raises(ValueError):
        output_path(tmp_path, "demo", "final", "mp4", primary_ext="mp4", suffix=suffix)


def test_invalid_stage_and_revision(tmp_path):
    with pytest.raises(ValueError):
        output_path(tmp_path, "demo", "preview", "mp4", primary_ext="mp4")
    with pytest.raises(ValueError):
        output_path(tmp_path, "demo", "final", "mp4", primary_ext="mp4", revision=0)


def test_read_slug(tmp_path):
    (tmp_path / "project.json").write_text(json.dumps({"slug": "acme-launch", "media": ["video"]}))
    assert read_slug(tmp_path) == "acme-launch"


@pytest.mark.parametrize("content", [None, "not json", "[]", "{}", '{"slug": "Bad_Slug"}', '{"slug": 3}',
                                     '{"slug": "-x"}'])
def test_read_slug_errors(tmp_path, content):
    if content is not None:
        (tmp_path / "project.json").write_text(content)
    with pytest.raises(SystemExit):
        read_slug(tmp_path)


@pytest.mark.parametrize("text,n", [("v1", 1), ("v12", 12)])
def test_revision_arg_accepts_vn(text, n):
    assert revision_arg(text) == n


@pytest.mark.parametrize("text", ["2", "v0", "v01", "V2", "v", "v2x", ""])
def test_revision_arg_rejects_other_forms(text):
    with pytest.raises(argparse.ArgumentTypeError, match="expected vN"):
        revision_arg(text)
