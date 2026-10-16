"""Deliverable names: outputs/<stage>-<slug>-v<N>[-<suffix>].<ext> (guides/video.md, "Deliverable conventions").

Numbering is per medium and per stage. The primary file of a stage has no suffix; companions
(srt, credits, share, contact, range) attach to the latest primary of their stage unless a
revision is given. post/src/postkit/outputs.py implements the same rules; keep them identical.
"""

import argparse
import json
import re
from pathlib import Path

STAGES = ("draft", "final")
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_SLUG_RE = re.compile(rf"^{SLUG}$")
_REVISION_RE = re.compile(r"v([1-9][0-9]*)")


def revision_arg(text: str) -> int:
    """argparse type for --revision vN (the same form as postkit's); returns N."""
    m = _REVISION_RE.fullmatch(text)
    if not m:
        raise argparse.ArgumentTypeError(f"{text!r}: expected vN, for example v2")
    return int(m[1])


def name_re(slug: str, ext: str) -> re.Pattern:
    """Matches ^(draft|final)-<slug>-v([1-9][0-9]*)(-[a-z0-9-]+)?\\.<ext>$ ; groups: stage, N, suffix."""
    return re.compile(rf"^(draft|final)-{re.escape(slug)}-v([1-9][0-9]*)(-[a-z0-9-]+)?\.{re.escape(ext)}$")


def latest_revision(directory: Path, slug: str, stage: str, ext: str) -> int | None:
    """Highest N among the primary files (no suffix) of `stage` and `ext` in `directory`."""
    if not directory.is_dir():
        return None
    pattern = name_re(slug, ext)
    found = []
    for p in directory.iterdir():
        m = pattern.match(p.name)
        if m and m.group(1) == stage and m.group(3) is None and p.is_file():
            found.append(int(m.group(2)))
    return max(found, default=None)


def output_path(directory: Path, slug: str, stage: str, ext: str, *, primary_ext: str,
                suffix: str | None = None, revision: int | None = None,
                next_rev: bool = False) -> Path:
    """The path to write, creating `directory`.

    revision given: used as is. Primary (suffix None): the latest revision of `ext`, 1 when none,
    or latest + 1 with `next_rev`. Companion (suffix): the latest primary revision with
    `primary_ext`, 1 when none."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, not {stage!r}")
    if suffix is not None and not _SLUG_RE.match(suffix):
        raise ValueError(f"invalid suffix {suffix!r}: lowercase letters, digits and single hyphens")
    if revision is not None and revision < 1:
        raise ValueError(f"revision must be 1 or more, not {revision}")
    if revision is not None:
        n = revision
    elif suffix is None:
        latest = latest_revision(directory, slug, stage, ext)
        n = (latest or 0) + 1 if next_rev else latest or 1
    else:
        n = latest_revision(directory, slug, stage, primary_ext) or 1
    directory.mkdir(parents=True, exist_ok=True)
    tail = f"-{suffix}" if suffix else ""
    return directory / f"{stage}-{slug}-v{n}{tail}.{ext}"


def read_slug(project_root: Path) -> str:
    """The project's slug from project.json, with a clear error when missing or invalid."""
    path = project_root / "project.json"
    if not path.exists():
        raise SystemExit(f"no {path}: create it as {{\"slug\": \"my-product\", \"media\": [\"video\"]}}")
    try:
        slug = json.loads(path.read_text()).get("slug")
    except (json.JSONDecodeError, AttributeError) as e:
        raise SystemExit(f"{path} is not a JSON object: {e}") from e
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise SystemExit(f"{path}: \"slug\" must match {SLUG} (lowercase words joined by hyphens), got {slug!r}")
    return slug
