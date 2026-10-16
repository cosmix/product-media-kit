"""Build outputs/blog/<stage>-<slug>-v<N>.md from post/draft.md and the captures.

Every input is read and validated first and all problems are raised as one BuildError before
anything is written; a `shot:` link that is not a well-formed image counts as one. Then each
referenced shot is treated into outputs/blog/images/, the markdown is written with relative
`images/<file>` links, and the ledger post/build/ledger.json is updated: images postkit wrote
last time and not this time are deleted once no post in outputs/blog/ references them; nothing
else ever is. Revisions share images/, so a rebuild replaces images in place.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from postkit.common import (
    IMAGE_RE,
    LEFTOVER_RE,
    SHOT,
    blog_dir,
    body_matches,
    line_of,
    read_slug,
    referenced_images,
    remove_part_files,
    write_atomic,
)
from postkit.config import read_images_json, treatment_for
from postkit.design import Design
from postkit.design import load as load_design
from postkit.images import Treatment, output_name, treat
from postkit.manifest import Shot, load_shots
from postkit.outputs import output_path


class BuildError(ValueError):
    """The post cannot be built; the message lists every problem, one per line."""


@dataclass(frozen=True)
class BuildResult:
    md: Path  # outputs/blog/<stage>-<slug>-v<N>.md
    written: list[Path]  # every file written, the markdown last
    removed: list[Path]  # images of the previous build that this build no longer produces


@dataclass(frozen=True)
class _Plan:
    slug: str
    draft: str
    jobs: dict[str, tuple[Shot, Treatment]]
    design: Design


def build(root: Path, *, final: bool = False, revision: int | None = None,
          next_rev: bool = False) -> BuildResult:
    """Assemble the post of the project at `root`; BuildError (nothing written) when inputs are wrong.

    The stage is `draft`, or `final` with `final`. The latest revision of the stage is rewritten
    (v1 when none); `next_rev` writes the one after it, `revision` names one.
    """
    plan = _prepare(root)
    text = _rewrite(plan)
    blog = blog_dir(root)
    stage = "final" if final else "draft"
    md = output_path(blog, plan.slug, stage, "md", primary_ext="md", revision=revision, next_rev=next_rev)
    remove_part_files(blog)  # a killed run leaves them; check would report them as unreferenced
    written: list[Path] = []
    for shot, treatment in plan.jobs.values():
        written += treat(shot, treatment, plan.design, blog / "images" / output_name(shot))
    write_atomic(md, text.encode("utf-8"))
    removed = _update_ledger(root, written)
    return BuildResult(md=md, written=[*written, md], removed=removed)


def _prepare(root: Path) -> _Plan:
    errors: list[str] = []
    slug = _attempt(errors, read_slug, root)
    draft = _attempt(errors, _read_draft, root)
    config = _attempt(errors, read_images_json, root)
    shots = _attempt(errors, load_shots, root)
    design = _attempt(errors, load_design, root)
    jobs: dict[str, tuple[Shot, Treatment]] = {}
    if draft is not None and shots is not None:
        jobs = _resolve(draft, shots, config or {}, errors)
    if errors or slug is None or draft is None or design is None:
        raise BuildError("\n".join(errors))
    return _Plan(slug=slug, draft=draft, jobs=jobs, design=design)


def _rewrite(plan: _Plan) -> str:
    """The draft with each `shot:` image pointing at its treated file; BuildError when a shot: link is left."""
    draft, parts, pos = plan.draft, [], 0
    for m in body_matches(IMAGE_RE, draft):
        parts += [draft[pos : m.start()], _link(m, plan.jobs)]
        pos = m.end()
    text = "".join([*parts, draft[pos:]])  # the substitution keeps every newline, so line numbers hold
    lines = sorted({line_of(text, m.start()) for m in body_matches(LEFTOVER_RE, text)})
    if lines:
        raise BuildError("\n".join(
            f"draft.md:{line}: a shot: link that is not an image; write ![alt text](shot:<source>/<scenario>/<label>)"
            for line in lines))
    return text


def _attempt[T](errors: list[str], fn: Callable[[Path], T], root: Path) -> T | None:
    try:
        return fn(root)
    except ValueError as e:
        errors.append(str(e))
        return None


def _read_draft(root: Path) -> str:
    path = root / "post" / "draft.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"{path}: missing; write the post there") from None
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: cannot read: {e}") from e


def _resolve(draft: str, shots: dict[str, Shot], config: dict[str, dict],
             errors: list[str]) -> dict[str, tuple[Shot, Treatment]]:
    """A job per shot the draft links; appends every problem with the links and their treatment."""
    jobs: dict[str, tuple[Shot, Treatment]] = {}
    for m in body_matches(IMAGE_RE, draft):
        if not m["url"].startswith(SHOT):
            continue
        where = f"draft.md:{line_of(draft, m.start())}: {m[0]}"
        ref = m["url"].removeprefix(SHOT)
        if not m["alt"].strip():
            errors.append(f"{where}: empty alt text")
        shot = shots.get(ref)
        if shot is None:
            errors.append(f"{where}: unknown shot {ref!r} (known: {', '.join(sorted(shots)) or 'none'})")
        elif ref not in jobs:
            errors += _missing_files(shot) or _unreadable_images(shot)
            errors += _collision(shot, jobs)
            treatment, problems = treatment_for(shot, config)
            errors += problems
            jobs[ref] = (shot, treatment)
    errors += [f"images.json: {key!r} names no shot in the capture manifests"
               for key in config if key != "defaults" and key not in shots]
    return jobs


def _missing_files(shot: Shot) -> list[str]:
    files = [shot.path] + ([shot.webm] if shot.webm is not None else [])
    return [f"{shot.ref}: capture file {path} is missing" for path in files if not path.is_file()]


def _unreadable_images(shot: Shot) -> list[str]:
    """Pillow must decode the capture, or treating it would fail mid-build."""
    try:
        with Image.open(shot.path) as img:
            img.load()  # verify() skips pixel data, so a broken zlib stream would pass
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as e:  # a bad PNG chunk CRC raises SyntaxError
        return [f"{shot.ref}: capture file {shot.path} is not a readable image: {e}"]
    return []


def _collision(shot: Shot, jobs: dict[str, tuple[Shot, Treatment]]) -> list[str]:
    """An error when another shot of the draft is written to the same output file."""
    name = output_name(shot)
    return [f"{shot.ref} and {other.ref} both write images/{name}; rename a scenario or label"
            for other, _ in jobs.values() if output_name(other) == name]


def _link(m: re.Match[str], jobs: dict[str, tuple[Shot, Treatment]]) -> str:
    if not m["url"].startswith(SHOT):
        return m[0]
    shot, _ = jobs[m["url"].removeprefix(SHOT)]
    return f"![{m['alt']}](images/{output_name(shot)}{m['title'] or ''})"


def ledger_path(root: Path) -> Path:
    return root / "post" / "build" / "ledger.json"


def _update_ledger(root: Path, written: list[Path]) -> list[Path]:
    """Delete last build's images that no post references any more, then record the ledger.

    The ledger lists images (relative to outputs/blog/) postkit wrote; one still referenced by
    another revision stays listed. Losing the ledger only means nothing is ever deleted.
    """
    blog = blog_dir(root)
    inside = (blog / "images").resolve()  # the ledger can only ever delete images
    now = {path.relative_to(blog).as_posix() for path in written}
    linked = referenced_images(blog)
    kept, removed = set(now), []
    for rel in _ledger_files(ledger_path(root)):
        path = blog / rel
        if rel in now or not path.resolve().is_relative_to(inside) or not path.is_file():
            continue
        if path.resolve() in linked:
            kept.add(rel)
            continue
        path.unlink()
        removed.append(path)
    write_atomic(ledger_path(root), (json.dumps({"files": sorted(kept)}, indent=2) + "\n").encode("utf-8"))
    return removed


def _ledger_files(path: Path) -> list[str]:
    try:
        files = json.loads(path.read_text(encoding="utf-8")).get("files", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [f for f in files if isinstance(f, str)] if isinstance(files, list) else []
