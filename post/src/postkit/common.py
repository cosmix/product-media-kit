"""Names, the markdown image syntax, project.json and atomic writes shared by build and check."""

import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote

SHOT = "shot:"  # the url prefix of a draft image that names a capture
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")  # slugs, scenarios and labels; use fullmatch
# Alt text may hold one level of balanced brackets; the title is "..." or '...'.
IMAGE_RE = re.compile(
    r"!\[(?P<alt>(?:[^\[\]]|\[[^\]]*\])*)\]\((?P<url>[^)\s]+)(?P<title>\s+(?:\"[^\"]*\"|'[^']*'))?\)"
)
# Other ways a post names a file: an <img src>, a reference definition `[id]: target`, and front matter values.
IMG_TAG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)')", re.IGNORECASE)
REF_DEF_RE = re.compile(r"^ {0,3}\[[^\]]+\]:[ \t]*(?P<url><[^>\s]+>|\S+)", re.MULTILINE)
FRONT_IMAGE_RE = re.compile(r"(?<![\w/.-])images/[^\s\"'<>,\]}]+")
LEFTOVER_RE = re.compile(r"\]\(\s*<?shot:")  # a shot: link target, whatever the text around it looks like
EXTERNAL = ("http://", "https://", "//", "data:")  # link targets that are not files of outputs/blog/
FRONT_MATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
FENCE_RE = re.compile(r" {0,3}(?P<mark>`{3,}|~{3,})(?P<rest>.*)")


def front_matter_end(text: str) -> int:
    """Offset where the body starts: after a leading YAML front matter block, else 0."""
    m = FRONT_MATTER_RE.match(text)
    return m.end() if m else 0


def line_of(text: str, pos: int) -> int:
    """The 1-based line number of offset `pos` in `text`."""
    return text.count("\n", 0, pos) + 1


def body_matches(pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
    """Matches of `pattern` that start after the front matter and outside fenced code blocks."""
    start = front_matter_end(text)
    fenced = _fenced_spans(text, start)
    return [m for m in pattern.finditer(text, start) if not any(a <= m.start() < b for a, b in fenced)]


def _fenced_spans(text: str, start: int) -> list[tuple[int, int]]:
    """Offsets (begin, end) of the ``` and ~~~ blocks from `start`; an unclosed fence runs to the end."""
    spans: list[tuple[int, int]] = []
    pos, opened = start, None  # opened: (offset, mark) of the fence being skipped
    for line in text[start:].splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if opened is None:
            if m and not (m["mark"][0] == "`" and "`" in m["rest"]):  # a backtick fence's info has no backtick
                opened = (pos, m["mark"])
        elif m and m["mark"][0] == opened[1][0] and len(m["mark"]) >= len(opened[1]) and not m["rest"].strip():
            spans.append((opened[0], pos + len(line)))
            opened = None
        pos += len(line)
    if opened is not None:
        spans.append((opened[0], len(text)))
    return spans


def blog_dir(root: Path) -> Path:
    """Where the built posts and their images live."""
    return root / "outputs" / "blog"


def read_slug(root: Path) -> str:
    """The slug from root/project.json; ValueError when the file is missing, malformed or unsafe."""
    path = root / "project.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{path}: missing (install.sh writes it)") from None
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: cannot read: {e}") from e
    slug = data.get("slug") if isinstance(data, dict) else None
    if not isinstance(slug, str) or not NAME_RE.fullmatch(slug):
        raise ValueError(f"{path}: slug {slug!r} must match {NAME_RE.pattern}")
    return slug


def link_target(url: str) -> str:
    """A markdown link target without the angle brackets that may wrap it."""
    return url.removeprefix("<").removesuffix(">")


def _post_urls(text: str) -> list[str]:
    """Every local-file candidate a post names: image links, <img src>, reference definitions, front matter."""
    urls = [link_target(m["url"]) for m in body_matches(IMAGE_RE, text)]
    urls += [m["dq"] if m["dq"] is not None else m["sq"] for m in body_matches(IMG_TAG_RE, text)]
    urls += [link_target(m["url"]) for m in body_matches(REF_DEF_RE, text)]
    urls += FRONT_IMAGE_RE.findall(text[: front_matter_end(text)])
    return urls


def referenced_images(blog: Path) -> set[Path]:
    """The resolved local files every .md in `blog` names; a linked GIF counts its WebM sibling too."""
    linked: set[Path] = set()
    for md in sorted(blog.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue  # an unreadable post is reported by check; it references nothing we can tell
        for url in _post_urls(text):
            if url.lower().startswith(EXTERNAL) or url.startswith("/"):
                continue
            path = (md.parent / unquote(url.partition("#")[0].partition("?")[0])).resolve()
            linked.add(path)
            if path.suffix == ".gif":
                linked.add(path.with_suffix(".webm"))
    return linked


def part_path(target: Path) -> Path:
    """The temporary name a file is written under before it replaces `target`."""
    return target.with_name(f".{target.name}.part")


def remove_part_files(directory: Path) -> None:
    """Delete the part files (see `part_path`) a killed run left where postkit writes: the posts in
    `directory` and the images in its images/ folder. Other hidden .part files are the user's."""
    candidates = [*directory.glob(".*.md.part"), *(directory / "images").glob(".*.part")]
    for part in candidates:
        if part.is_file():
            part.unlink()


def write_atomic(target: Path, data: bytes) -> None:
    _publish(target, lambda part: part.write_bytes(data))


def copy_atomic(source: Path, target: Path) -> None:
    _publish(target, lambda part: shutil.copyfile(source, part))


def _publish(target: Path, fill: Callable[[Path], object]) -> None:
    """Fill the part file, then replace `target` with it; the part file never outlives a failure."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = part_path(target)
    try:
        fill(part)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)  # already gone after a successful replace
