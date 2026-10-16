"""Check built posts: links resolve inside outputs/blog/, alt text present, sizes sensible.

Default targets: the latest draft and the latest final in outputs/blog/; `file` picks one.
ERROR: no built post; a post outside outputs/blog/; an image link whose target is missing,
absolute or escapes outputs/blog/; empty alt text; a leftover `shot:` link; an unreadable post.
WARN: an image wider than 2400 px; a GIF over 10 MB; a file in outputs/blog/images/ that no post
in outputs/blog/ references. Remote (http, https, protocol-relative) and data: images pass;
`#fragment` and `?query` are ignored on local links. Front matter and fenced code blocks are not
checked.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

from postkit.common import (
    EXTERNAL,
    IMAGE_RE,
    LEFTOVER_RE,
    SHOT,
    blog_dir,
    body_matches,
    line_of,
    read_slug,
    referenced_images,
)
from postkit.outputs import STAGES, latest_revision

MAX_WIDTH = 2400
MAX_GIF_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Problem:
    level: str  # "ERROR" or "WARN"
    message: str


def check(root: Path, file: Path | None = None) -> list[Problem]:
    """Every problem with the built posts of the project at `root`, or with the post `file`."""
    try:
        slug = read_slug(root)
    except ValueError as e:
        return [Problem("ERROR", str(e))]
    blog = blog_dir(root)
    targets = [_pick(blog, file)] if file else _latest(blog, slug)
    if not targets:
        return [Problem("ERROR", f"no built post in {blog}: run `postkit build`")]
    problems: list[Problem] = []
    for md in targets:
        problems += _check_post(md, blog)
    return problems + _unreferenced(blog / "images", referenced_images(blog))


def _pick(blog: Path, file: Path) -> Path:
    """`file` as given, else a name inside outputs/blog/."""
    return file if file.exists() or file.is_absolute() else blog / file


def _latest(blog: Path, slug: str) -> list[Path]:
    """The latest draft and the latest final post that exist."""
    found = []
    for stage in STAGES:
        revision = latest_revision(blog, slug, stage, "md")
        if revision is not None:
            found.append(blog / f"{stage}-{slug}-v{revision}.md")
    return found


def _check_post(md: Path, blog: Path) -> list[Problem]:
    if not md.is_file():
        return [Problem("ERROR", f"{md} is missing: run `postkit build`")]
    if not md.resolve().is_relative_to(blog.resolve()):
        return [Problem("ERROR", f"{md} is outside {blog}")]
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, ValueError) as e:  # a file that is not UTF-8 raises UnicodeDecodeError, a ValueError
        return [Problem("ERROR", f"{md}: cannot read: {e}")]
    problems: list[Problem] = []
    shot_lines: set[int] = set()
    for m in body_matches(IMAGE_RE, text):
        line = line_of(text, m.start())
        if _is_shot(m["url"]):
            shot_lines.add(line)
        problems += _link_problems(m, f"{md.name}:{line}: {m[0]}", md.parent, blog.resolve())
    return problems + _leftovers(text, md.name, shot_lines)


def report(problems: list[Problem]) -> int:
    """Print `LEVEL message` lines and a summary; return the number of ERRORs."""
    for p in problems:
        print(f"{p.level} {p.message}")
    errors = sum(p.level == "ERROR" for p in problems)
    print(f"{errors} error(s), {len(problems) - errors} warning(s)")
    return errors


def _is_shot(url: str) -> bool:
    return url.removeprefix("<").startswith(SHOT)  # `<shot:...>` is the angle-bracket form of the target


def _leftovers(text: str, name: str, reported: set[int]) -> list[Problem]:
    """An ERROR per line with a `shot:` link target that the image pass did not already report."""
    lines = {line_of(text, m.start()) for m in body_matches(LEFTOVER_RE, text)} - reported
    return [Problem("ERROR", f"{name}:{line}: leftover shot: link (run `postkit build`)") for line in sorted(lines)]


def _link_problems(m: re.Match[str], where: str, base: Path, blog: Path) -> list[Problem]:
    url = m["url"]
    problems = [] if m["alt"].strip() else [Problem("ERROR", f"{where}: empty alt text")]
    if url.lower().startswith(EXTERNAL):
        return problems
    if _is_shot(url):
        return [*problems, Problem("ERROR", f"{where}: leftover shot: link (run `postkit build`)")]
    rel = unquote(url.partition("#")[0].partition("?")[0])
    if rel.startswith("/") or Path(rel).is_absolute():
        return [*problems, Problem("ERROR", f"{where}: absolute image path; links must be relative")]
    target = (base / rel).resolve()
    if not target.is_relative_to(blog):
        return [*problems, Problem("ERROR", f"{where}: image path escapes outputs/blog/")]
    if not target.is_file():
        return [*problems, Problem("ERROR", f"{where}: image {target} is missing")]
    return problems + _size_problems(target, where)


def _size_problems(target: Path, where: str) -> list[Problem]:
    try:
        with Image.open(target) as img:
            width, fmt = img.width, img.format
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        return [Problem("ERROR", f"{where}: not a readable image: {e}")]
    problems = []
    if width > MAX_WIDTH:
        problems.append(Problem("WARN", f"{where}: {width} px wide, over {MAX_WIDTH} px"))
    size = target.stat().st_size
    if fmt == "GIF" and size > MAX_GIF_BYTES:
        problems.append(Problem("WARN", f"{where}: GIF of {size / 1024 / 1024:.1f} MB, over 10 MB"))
    return problems


def _unreferenced(images: Path, linked: set[Path]) -> list[Problem]:
    """A WARN per file in outputs/blog/images/ that no post in outputs/blog/ references."""
    if not images.is_dir():
        return []
    return [Problem("WARN", f"{path} is not referenced by any post in {images.parent}")
            for path in sorted(p for p in images.rglob("*") if p.is_file()) if path.resolve() not in linked]
