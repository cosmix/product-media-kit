"""edit/editkit/outputs.py and post/src/postkit/outputs.py live in separate uv projects and must
pick the same output names (README "Outputs"). Both are loaded by path and run on the same trees."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

KIT = Path(__file__).resolve().parents[1]
SLUG = "acme-launch"


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EDIT = load("edit_outputs", KIT / "edit/editkit/outputs.py")
POST = load("post_outputs", KIT / "post/src/postkit/outputs.py")
VIDEO_TREE = (
    "draft-acme-launch-v1.mp4",
    "draft-acme-launch-v3.mp4",
    "draft-acme-launch-v9-contact-00.png",
    "draft-acme-launch-v7-range-0p5-1p5.mp4",
    "final-acme-launch-v2.mp4",
    "final-acme-launch-v2.srt",
    "final-acme-launch-v5-share.mp4",
    "draft-other-v8.mp4",
    "draft-acme-launch-v04.mp4",
    "Draft-acme-launch-v6.mp4",
    "draft-acme-launch-v6.mp4.part",
    "notes.txt",
)
BLOG_TREE = (
    "draft-acme-launch-v1.md",
    "draft-acme-launch-v2.md",
    "final-acme-launch-v1.md",
    "draft-acme-launch-v11-notes.md",
    "draft-acme-launch-v3.markdown",
)
CASES = [
    # (stage, ext, primary_ext, suffix, revision, next_rev)
    ("draft", "mp4", "mp4", None, None, False),
    ("draft", "mp4", "mp4", None, None, True),
    ("final", "mp4", "mp4", None, None, False),
    ("final", "mp4", "mp4", None, None, True),
    ("draft", "mp4", "mp4", None, 12, False),
    ("draft", "srt", "mp4", None, None, False),
    ("final", "srt", "mp4", None, None, False),
    ("draft", "srt", "mp4", None, None, True),
    ("draft", "png", "mp4", "contact-00", None, False),
    ("final", "txt", "mp4", "credits", None, False),
    ("final", "mp4", "mp4", "share", None, False),
    ("final", "mp4", "mp4", "share", 1, False),
    ("draft", "mp4", "mp4", "range-0p5-1p5", None, True),
    ("draft", "md", "md", None, None, False),
    ("draft", "md", "md", None, None, True),
    ("final", "md", "md", None, None, False),
    ("final", "md", "md", None, 4, False),
]


def tree(root: Path, names: tuple[str, ...]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).write_text("x")
    return root


@pytest.fixture(params=["empty", "video", "blog", "missing"])
def directory(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    if request.param == "missing":
        return tmp_path / "outputs"
    names = {"empty": (), "video": VIDEO_TREE, "blog": BLOG_TREE}[request.param]
    return tree(tmp_path / "outputs", names)


@pytest.mark.parametrize("ext", ["mp4", "md", "srt"])
@pytest.mark.parametrize("stage", ["draft", "final"])
def test_latest_revision_agrees(directory: Path, stage: str, ext: str) -> None:
    assert EDIT.latest_revision(directory, SLUG, stage, ext) == POST.latest_revision(directory, SLUG, stage, ext)


@pytest.mark.parametrize(("stage", "ext", "primary_ext", "suffix", "revision", "next_rev"), CASES)
def test_output_path_agrees(directory: Path, stage, ext, primary_ext, suffix, revision, next_rev) -> None:
    kwargs = {"primary_ext": primary_ext, "suffix": suffix, "revision": revision, "next_rev": next_rev}
    edit = EDIT.output_path(directory, SLUG, stage, ext, **kwargs)
    post = POST.output_path(directory, SLUG, stage, ext, **kwargs)
    assert edit == post


@pytest.mark.parametrize(("stage", "ext", "primary_ext", "suffix", "revision", "next_rev", "expected"), [
    ("draft", "mp4", "mp4", None, None, False, "draft-acme-launch-v3.mp4"),  # v04 is no revision
    ("draft", "mp4", "mp4", None, None, True, "draft-acme-launch-v4.mp4"),
    ("final", "srt", "mp4", None, None, False, "final-acme-launch-v2.srt"),
    ("draft", "png", "mp4", "contact-00", None, False, "draft-acme-launch-v3-contact-00.png"),
    ("final", "mp4", "mp4", "share", None, False, "final-acme-launch-v2-share.mp4"),
    ("draft", "md", "md", None, None, True, "draft-acme-launch-v1.md"),
])
def test_video_tree_names(tmp_path: Path, stage, ext, primary_ext, suffix, revision, next_rev, expected) -> None:
    """The names README "Outputs" documents, from both modules."""
    directory = tree(tmp_path / "outputs", VIDEO_TREE)
    kwargs = {"primary_ext": primary_ext, "suffix": suffix, "revision": revision, "next_rev": next_rev}
    for module in (EDIT, POST):
        assert module.output_path(directory, SLUG, stage, ext, **kwargs).name == expected, module.__name__


@pytest.mark.parametrize("name", VIDEO_TREE + BLOG_TREE + ("final-acme-launch-v2-a-b.srt", "draft-acme-launch-v1.MP4"))
@pytest.mark.parametrize("ext", ["mp4", "md", "srt", "png"])
def test_name_patterns_agree(name: str, ext: str) -> None:
    edit = EDIT.name_re(SLUG, ext).match(name)
    post = POST.NAME_RE(SLUG, ext).match(name)
    assert (edit and edit.groups()) == (post and post.groups())


@pytest.mark.parametrize("kwargs", [
    {"stage": "preview"},
    {"stage": "Final"},
    {"suffix": "Share"},
    {"suffix": "-share"},
    {"suffix": "share-"},
    {"suffix": "a_b"},
    {"suffix": ""},
    {"suffix": "share\n"},
    {"revision": 0},
    {"revision": -1},
])
def test_both_reject_the_same_input(tmp_path: Path, kwargs: dict) -> None:
    args = {"stage": "draft", "suffix": None, "revision": None} | kwargs
    for module in (EDIT, POST):
        with pytest.raises(ValueError):
            module.output_path(tmp_path, SLUG, args["stage"], "mp4", primary_ext="mp4",
                               suffix=args["suffix"], revision=args["revision"])


def test_directory_named_like_a_primary_is_not_a_revision(tmp_path: Path) -> None:
    directory = tree(tmp_path / "outputs", ("draft-acme-launch-v1.mp4",))
    (directory / "draft-acme-launch-v7.mp4").mkdir()
    for module in (EDIT, POST):
        assert module.latest_revision(directory, SLUG, "draft", "mp4") == 1, module.__name__


@pytest.mark.parametrize("name", ["draft-acme-launch-v04.mp4", "draft-acme-launch-v0.mp4"])
def test_zero_padded_revision_is_no_primary(tmp_path: Path, name: str) -> None:
    directory = tree(tmp_path / "outputs", (name,))
    for module in (EDIT, POST):
        assert module.latest_revision(directory, SLUG, "draft", "mp4") is None, module.__name__


def test_output_path_creates_the_folder_in_both(tmp_path: Path) -> None:
    for module in (EDIT, POST):
        directory = tmp_path / module.__name__ / "outputs"
        module.output_path(directory, SLUG, "draft", "mp4", primary_ext="mp4")
        assert directory.is_dir(), module.__name__


def test_a_slug_with_a_trailing_newline_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text('{"slug": "acme\\n"}')
    with pytest.raises(SystemExit):
        EDIT.read_slug(tmp_path)
