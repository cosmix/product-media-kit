"""Load the capture manifests captures/<source>/manifest.json into Shot records.

The format is pinned in the plan's "Shared interfaces": paths are relative to captures/<source>/
and must stay inside it; boxes are [x, y, w, h] integer pixels in the image file. Keys the build does
not use (origin, video, fps, marks, cursor, cursor_space, grid, cell_px, padding_px) are ignored.
"""

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from postkit.common import NAME_RE

SOURCES = ("web", "tui", "motion", "broll", "video")
KINDS = ("still", "clip")

type Box = tuple[int, int, int, int]


class ManifestError(ValueError):
    """A capture manifest is unreadable, or one of its entries is invalid or escapes its folder."""


@dataclass(frozen=True)
class Shot:
    ref: str  # "<source>/<scenario>/<label>"
    source: str
    kind: str  # "still" or "clip"
    path: Path  # absolute: the PNG of a still, the GIF of a clip
    width: int
    height: int
    scale: float
    boxes: dict[str, Box]
    webm: Path | None = None
    poster: Path | None = None
    duration: float | None = None

    @property
    def name(self) -> str:
        """`<source>-<scenario>-<label>`: the stem of the shot's files in outputs/blog/images/."""
        return self.ref.replace("/", "-")


def load_shots(root: Path) -> dict[str, Shot]:
    """Every shot of root/captures/<source> for each of SOURCES (each manifest optional), keyed by ref."""
    shots: dict[str, Shot] = {}
    errors: list[str] = []
    for source in SOURCES:
        path = root / "captures" / source / "manifest.json"
        if path.exists():
            errors += _load(path, source, shots)
    if errors:
        raise ManifestError("\n".join(errors))
    return shots


def _load(path: Path, source: str, shots: dict[str, Shot]) -> list[str]:
    try:
        entries = _entries(path, source)
    except ManifestError as e:
        return [str(e)]
    base = path.parent.resolve()
    errors = []
    for i, entry in enumerate(entries):
        try:
            shot = _shot(entry, source, base)
        except ManifestError as e:
            errors.append(f"{path}: shot {i}: {e}")
            continue
        if shot.ref in shots:
            errors.append(f"{path}: shot {i}: duplicate id {shot.ref.split('/', 1)[1]!r}")
        shots[shot.ref] = shot
    return errors


def _entries(path: Path, source: str) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ManifestError(f"{path}: cannot read: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
        raise ManifestError(f'{path}: expected an object with a "shots" list')
    if data.get("source", source) != source:
        raise ManifestError(f"{path}: source {data['source']!r} does not match its folder {source!r}")
    return data["shots"]


def _shot(entry: object, source: str, base: Path) -> Shot:
    if not isinstance(entry, dict):
        raise ManifestError("expected an object")
    shot_id = entry.get("id")
    parts = shot_id.split("/") if isinstance(shot_id, str) else []
    if len(parts) != 2 or not all(NAME_RE.fullmatch(p) for p in parts):
        raise ManifestError(f"id {shot_id!r}: expected <scenario>/<label>, each matching {NAME_RE.pattern}")
    where = f"{shot_id}: "
    try:
        return _fields(entry, f"{source}/{shot_id}", source, base)
    except ManifestError as e:
        raise ManifestError(where + str(e)) from None


def _fields(entry: dict, ref: str, source: str, base: Path) -> Shot:
    kind = entry.get("kind")
    if kind not in KINDS:
        raise ManifestError(f"kind {kind!r}: expected one of {', '.join(KINDS)}")
    scale = entry.get("scale", 1.0)
    if not _is_number(scale) or scale <= 0:
        raise ManifestError(f"scale {scale!r}: expected a number > 0")
    duration = entry.get("duration")
    if duration is not None and (not _is_number(duration) or duration < 0):
        raise ManifestError(f"duration {duration!r}: expected a number >= 0")
    return Shot(
        ref=ref,
        source=source,
        kind=kind,
        path=_inside(base, entry.get("file"), "file"),
        width=_positive_int(entry, "width"),
        height=_positive_int(entry, "height"),
        scale=float(scale),
        boxes=_boxes(entry.get("boxes", {})),
        webm=None if entry.get("webm") is None else _inside(base, entry["webm"], "webm"),
        poster=None if entry.get("poster") is None else _inside(base, entry["poster"], "poster"),
        duration=None if duration is None else float(duration),
    )


def _inside(base: Path, rel: object, key: str) -> Path:
    """`rel` resolved (symlinks too) under `base`; ManifestError when absolute or escaping."""
    if not isinstance(rel, str) or not rel:
        raise ManifestError(f"{key} {rel!r}: expected a path relative to {base}")
    if PurePosixPath(rel).is_absolute() or Path(rel).is_absolute():
        raise ManifestError(f"{key} {rel!r}: absolute paths are not allowed")
    full = (base / rel).resolve()
    if not full.is_relative_to(base):
        raise ManifestError(f"{key} {rel!r}: resolves outside {base}")
    return full


def _boxes(raw: object) -> dict[str, Box]:
    if not isinstance(raw, dict):
        raise ManifestError(f"boxes {raw!r}: expected an object of name -> [x, y, w, h]")
    boxes = {}
    for name, box in raw.items():
        if not isinstance(box, list) or len(box) != 4 or not all(_is_int(v) and v >= 0 for v in box):
            raise ManifestError(f"box {name!r} = {box!r}: expected four non-negative integers [x, y, w, h]")
        boxes[str(name)] = (box[0], box[1], box[2], box[3])
    return boxes


def _positive_int(entry: dict, key: str) -> int:
    value = entry.get(key)
    if not _is_int(value) or value <= 0:
        raise ManifestError(f"{key} {value!r}: expected an integer > 0")
    return value


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
