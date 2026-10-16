"""Output names `<stage>-<slug>-v<N>[-<suffix>].<ext>` and their revisions.

The twin of edit/editkit/outputs.py (separate uv projects); the kit test compares the two, so
change them together. A primary file has no suffix; companions (suffix given) attach to the latest
primary of their stage unless a revision is named.
"""

import re
from pathlib import Path

STAGES = ("draft", "final")
SUFFIX_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def NAME_RE(slug: str, ext: str | None = None) -> re.Pattern[str]:
    """`^(draft|final)-<slug>-v([1-9][0-9]*)(-[a-z0-9-]+)?\\.<ext>$`; groups: stage, revision, suffix.

    `ext` defaults to any lowercase alphanumeric extension.
    """
    tail = "[a-z0-9]+" if ext is None else re.escape(ext)
    return re.compile(rf"^({'|'.join(STAGES)})-{re.escape(slug)}-v([1-9][0-9]*)(-[a-z0-9-]+)?\.{tail}$")


def latest_revision(directory: Path, slug: str, stage: str, ext: str) -> int | None:
    """The highest N over the primary files (no suffix) of `stage` and `ext` in `directory`."""
    pattern = NAME_RE(slug, ext)
    found = []
    if directory.is_dir():
        for path in directory.iterdir():
            m = pattern.match(path.name)
            if m and m[1] == stage and m[3] is None and path.is_file():
                found.append(int(m[2]))
    return max(found, default=None)


def output_path(directory: Path, slug: str, stage: str, ext: str, *, primary_ext: str,
                suffix: str | None = None, revision: int | None = None,
                next_rev: bool = False) -> Path:
    """The path of the next write, creating `directory`.

    ValueError for an unknown stage, a bad suffix or revision.

    A revision given is used as is. A primary file (no suffix) rewrites the latest revision of its
    stage and ext (1 when none), or the one after it with `next_rev`. A companion takes the latest
    primary revision of its stage with `primary_ext`, or 1.
    """
    if stage not in STAGES:
        raise ValueError(f"stage {stage!r}: expected one of {', '.join(STAGES)}")
    if suffix is not None and not SUFFIX_RE.fullmatch(suffix):
        raise ValueError(f"suffix {suffix!r}: must match {SUFFIX_RE.pattern}")
    if revision is not None and revision < 1:
        raise ValueError(f"revision {revision}: expected a number >= 1")
    if revision is None:
        if suffix is None:
            latest = latest_revision(directory, slug, stage, ext)
            revision = (latest or 0) + 1 if next_rev else latest or 1
        else:
            revision = latest_revision(directory, slug, stage, primary_ext) or 1
    directory.mkdir(parents=True, exist_ok=True)
    tag = f"-{suffix}" if suffix else ""
    return directory / f"{stage}-{slug}-v{revision}{tag}.{ext}"
