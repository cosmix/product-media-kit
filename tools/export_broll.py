"""Export a project's b-roll into a folder that can be uploaded and reused in other videos.

Usage (from the project root, through ./export-broll.sh):
    ./export-broll.sh <dest-dir> [--only <id>]... [--tar <file.tar.gz>] [--force]

Exported: EVERY rendered generated clip (broll/gen/omni/<id>.mp4), whether or not any video used it
and even without its <id>.json (the prompt then comes from broll/gen/shots.json and the sidecar says
so in "meta_source"; each such clip is reported as a note on stderr). Also every stock clip in
broll/candidates/ whose file stem, or stem without its NN_ prefix, equals a `## <name>` section of
broll/CREDITS.md; one sharing its stem with a generated clip is exported as stock-<stem>.
Temp files (.<id>.tmp.mp4) are never exported.

Layout under <dest-dir>:
    <slug>/<id>.mp4           the clip, copied unchanged
    <slug>/<id>-contact.png   12 evenly spaced frames tiled 4x3
    <slug>/<id>.json          sidecar: source, kind, prompt/model/mode or credit, probe data, sha256
    <slug>/INDEX.md           one section per clip, with the licence lines that must travel with it
    catalog.json, CATALOG.md  every project and clip in <dest-dir>; an export replaces its own
                              project's entries and keeps every other project's

Re-running is idempotent: a clip whose sha256 matches is not recopied. A clip that differs from
the one already in <dest-dir> is reported and left alone (exit 1) unless --force is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_NAME = re.compile(r"[A-Za-z0-9_-]+$")
GENERATED_LICENCE = "Generated, no attribution needed"
SHEET_FRAMES, SHEET_COLUMNS, SHEET_WIDTH = 12, 4, 480
NOTHING = "nothing to export: no rendered clip in broll/gen/omni/ and no credited clip in broll/candidates/"


def require_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise SystemExit(f"{' and '.join(missing)} not found: install ffmpeg")


def project_slug(root: Path) -> str:
    try:
        slug = json.loads((root / "project.json").read_text())["slug"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"project.json must hold a slug: {exc}") from exc
    if not isinstance(slug, str) or not SAFE_NAME.match(slug):
        raise SystemExit(f"project.json slug {slug!r} must be letters, digits, _ and -")
    return slug


def credit_sections(path: Path) -> dict[str, dict[str, str]]:
    """'## name' -> {"Key": "value"} from '- Key: value' lines (continuation lines folded in)."""
    out: dict[str, dict[str, str]] = {}
    name = last = None
    for line in (path.read_text().splitlines() if path.is_file() else []):
        if line.startswith("## "):
            name, last = line[3:].strip(), None
            out[name] = {}
        elif name and line.startswith("- ") and ":" in line:
            last, value = (part.strip() for part in line[2:].split(":", 1))
            out[name][last] = value
        elif name and last and line.startswith("  ") and not line.strip().startswith("-"):
            out[name][last] += " " + line.strip()
    return out


def note(message: str) -> None:
    print(f"note: {message}", file=sys.stderr)


def shot_table(path: Path) -> dict[str, dict]:
    """id -> shot from broll/gen/shots.json; empty when the file is missing or unreadable."""
    try:
        shots = json.loads(path.read_text()) if path.is_file() else []
    except ValueError as exc:
        note(f"{path} is not valid JSON ({exc}); generated clips without a sidecar get no prompt")
        return {}
    return {s["id"]: s for s in shots if isinstance(s, dict) and isinstance(s.get("id"), str)} \
        if isinstance(shots, list) else {}


def generated_meta(mp4: Path, shots: dict[str, dict]) -> dict:
    """The clip's <id>.json, or what shots.json knows when it is missing or unreadable (marked, with a note)."""
    meta_path = mp4.with_suffix(".json")
    try:
        meta = json.loads(meta_path.read_text())
        if isinstance(meta, dict):
            return meta
        problem = "is not a JSON object"
    except FileNotFoundError:
        problem = "is missing"
    except (OSError, ValueError) as exc:
        problem = f"is unreadable ({exc})"
    shot = shots.get(mp4.stem)
    source = "shots.json" if shot else "missing"
    note(f"{mp4.name}: {meta_path.name} {problem}; exported anyway with metadata from "
         f"{'broll/gen/shots.json' if shot else 'no source (no prompt known)'}")
    return {"meta_source": source, **{k: shot[k] for k in ("prompt", "mode", "images") if shot and k in shot}}


def find_clips(root: Path) -> list[dict]:
    """Every rendered generated clip, plus credited stock clips: {"id", "kind", "src", "meta"}, sorted by id.

    A generated clip is exported whether or not a sidecar exists; a stock clip whose stem equals a generated id
    is exported as stock-<stem> so that neither is lost.
    """
    clips = []
    shots = shot_table(root / "broll/gen/shots.json")
    for mp4 in sorted((root / "broll/gen/omni").glob("*.mp4")):
        if mp4.name.startswith("."):  # .<id>.tmp.mp4 is a partial render
            continue
        if not SAFE_NAME.match(mp4.stem):
            note(f"{mp4.name}: skipped, a clip id may only hold letters, digits, _ and -")
            continue
        clips.append({"id": mp4.stem, "kind": "generated", "src": mp4, "meta": generated_meta(mp4, shots)})
    taken = {c["id"] for c in clips}
    sections = credit_sections(root / "broll/CREDITS.md")
    for mp4 in sorted((root / "broll/candidates").glob("*.mp4")):
        credit = sections.get(mp4.stem) or sections.get(re.sub(r"^\d+_", "", mp4.stem))
        if mp4.name.startswith(".") or not credit or not SAFE_NAME.match(mp4.stem):
            continue
        clip_id = mp4.stem
        while clip_id in taken:
            clip_id = f"stock-{clip_id}"
        if clip_id != mp4.stem:
            note(f"{mp4.name}: shares its id with a generated clip; exported as {clip_id}")
        taken.add(clip_id)
        clips.append({"id": clip_id, "kind": "stock", "src": mp4, "meta": credit})
    return sorted(clips, key=lambda c: c["id"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    """Duration (s), width, height, fps and frame count of the first video stream."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(path)],
        check=False, capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
        stream, duration = data["streams"][0], float(data["format"]["duration"])
        num, _, den = stream["r_frame_rate"].partition("/")
        fps = float(num) / float(den or 1)
        frames = int(stream.get("nb_frames") or round(duration * fps))
        return {"duration": round(duration, 3), "width": stream["width"], "height": stream["height"],
                "fps": round(fps, 3), "frames": frames}
    except (ValueError, KeyError, IndexError, ZeroDivisionError) as exc:
        raise SystemExit(f"{path}: ffprobe could not read the video ({proc.stderr.strip() or exc})") from exc


def contact_sheet(src: Path, out: Path, frames: int) -> None:
    """One PNG of up to 12 evenly spaced frames tiled 4x3, written atomically."""
    step = max(1, math.ceil(frames / SHEET_FRAMES))
    rows = SHEET_FRAMES // SHEET_COLUMNS
    vf = f"select='not(mod(n,{step}))',scale={SHEET_WIDTH}:-2,tile={SHEET_COLUMNS}x{rows}:padding=4:margin=4"
    tmp = out.with_name(f".{out.stem}.tmp.png")
    proc = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-fps_mode", "passthrough",
                           "-frames:v", "1", str(tmp)], check=False, capture_output=True, text=True)
    if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:  # ffmpeg can exit 0 and write nothing
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"contact sheet for {src.name} failed: {proc.stderr.strip() or 'no output'}")
    os.replace(tmp, out)


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


def copy_atomic(src: Path, dest: Path) -> None:
    tmp = dest.with_name(f".{dest.stem}.tmp.mp4")
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def sidecar(slug: str, clip: dict, info: dict, digest: str) -> dict:
    data = {"project": slug, "id": clip["id"], "kind": clip["kind"]}
    if clip["kind"] == "generated":
        data.update({k: clip["meta"].get(k) for k in ("prompt", "model", "mode")})
        data.update({k: clip["meta"][k] for k in ("images", "meta_source") if k in clip["meta"]})
    else:
        data["credit"] = clip["meta"]
    data.update({"duration": info["duration"], "width": info["width"], "height": info["height"],
                 "fps": info["fps"], "sha256": digest})
    return data


def licence_lines(entry: dict) -> list[str]:
    if entry["kind"] == "generated":
        return [GENERATED_LICENCE]
    return [f"{key}: {value}" for key, value in entry["credit"].items()]


def render_index(slug: str, entries: list[dict]) -> str:
    out = [f"# B-roll from {slug}", ""]
    for e in entries:
        out += [f"## {e['id']}", "", f"![{e['id']} contact sheet]({e['id']}-contact.png)", "",
                f"[{e['id']}.mp4]({e['id']}.mp4)", ""]
        if e["kind"] == "generated":
            out += [*(f"> {line}" if line else ">" for line in (e.get("prompt") or "").splitlines()), ""]
        out += [f"- Duration: {e['duration']} s", f"- Resolution: {e['width']}x{e['height']} at {e['fps']} fps",
                f"- Kind: {e['kind']}", "- Licence:", *(f"  - {line}" for line in licence_lines(e)), ""]
    return "\n".join(out)


def render_catalog(projects: dict[str, list[dict]]) -> str:
    out = ["# B-roll library", ""]
    for slug in sorted(projects):
        out += [f"## {slug}", "", f"[Index]({slug}/INDEX.md)", ""]
        for e in projects[slug]:
            out += [f"### {slug}/{e['id']}", "", f"![{e['id']}]({e['contact']})", "",
                    f"[{e['id']}.mp4]({e['mp4']}): {e['kind']}, {e['duration']} s, {e['width']}x{e['height']}",
                    *(f"- {line}" for line in licence_lines(e)), ""]
    return "\n".join(out)


def read_catalog(path: Path) -> dict[str, list[dict]]:
    if not path.is_file():
        return {}
    try:
        projects = json.loads(path.read_text())["projects"]
        if not isinstance(projects, dict):
            raise TypeError("projects is not an object")
    except (ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"{path} is not a valid catalog ({exc}); fix or remove it, nothing was written") from exc
    return projects


def conflicts(folder: Path, clips: list[dict], digests: dict[str, str]) -> list[str]:
    return [c["id"] for c in clips
            if (folder / f"{c['id']}.mp4").is_file() and sha256(folder / f"{c['id']}.mp4") != digests[c["id"]]]


def export_clip(folder: Path, slug: str, clip: dict, digest: str, now: str) -> dict:
    """Copy one clip, its contact sheet and its sidecar; skip what is already current."""
    mp4, sheet, side = (folder / f"{clip['id']}{s}" for s in (".mp4", "-contact.png", ".json"))
    same = mp4.is_file() and sha256(mp4) == digest
    info = probe(clip["src"])
    if not same:
        copy_atomic(clip["src"], mp4)
    if not same or not sheet.is_file():
        contact_sheet(mp4, sheet, info["frames"])
    entry = sidecar(slug, clip, info, digest)
    try:
        old = json.loads(side.read_text()) if side.is_file() else {}
    except ValueError:
        old = {}
    if {k: v for k, v in old.items() if k != "exported_at"} == entry:
        return old
    entry["exported_at"] = now
    write_atomic(side, json.dumps(entry, indent=2) + "\n")
    return entry


def write_tar(output: Path, dest: Path, slug: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".export-", dir=output.parent)
    os.close(fd)
    try:
        with tarfile.open(tmp, "w:gz") as archive:
            for name in (slug, "catalog.json", "CATALOG.md"):
                archive.add(dest / name, arcname=name)
        os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, output)
    finally:
        Path(tmp).unlink(missing_ok=True)


def export(root: Path, dest: Path, only: list[str] | None = None, tar: Path | None = None,
           force: bool = False) -> list[str]:
    """Export the project's b-roll into dest; returns the ids exported."""
    root, dest = root.resolve(), dest.absolute()
    if dest.resolve().is_relative_to(root):
        raise SystemExit("write the export outside the project directory")
    if tar is not None and tar.exists():
        raise SystemExit(f"{tar} already exists; choose a new output path")
    require_tools()
    slug = project_slug(root)
    clips = find_clips(root)
    if not clips:
        raise SystemExit(NOTHING)
    unknown = sorted(set(only or []) - {c["id"] for c in clips})
    if unknown:
        raise SystemExit(f"unknown clip id: {', '.join(unknown)}; available: {', '.join(c['id'] for c in clips)}")
    clips = [c for c in clips if not only or c["id"] in only]
    folder = dest / slug
    digests = {c["id"]: sha256(c["src"]) for c in clips}
    differing = [] if force else conflicts(folder, clips, digests)
    if differing:
        raise SystemExit(f"{folder} already holds different clips for: {', '.join(differing)}; "
                         "nothing was written; rerun with --force to replace them")
    catalog = read_catalog(dest / "catalog.json")
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for clip in clips:
        export_clip(folder, slug, clip, digests[clip["id"]], now)
    publish(dest, slug, catalog)
    if tar is not None:
        tar.parent.mkdir(parents=True, exist_ok=True)
        write_tar(tar.absolute(), dest, slug)
    return [c["id"] for c in clips]


def publish(dest: Path, slug: str, catalog: dict[str, list[dict]]) -> None:
    """Rebuild INDEX.md and this slug's catalog entries from the folder's sidecars."""
    folder = dest / slug
    entries = []
    for side in sorted(folder.glob("*.json")):
        try:
            entries.append(json.loads(side.read_text()))
        except ValueError:
            continue  # a stray file, not one of our sidecars
    entries = [e for e in entries if isinstance(e, dict) and e.get("project") == slug and "sha256" in e]
    write_atomic(folder / "INDEX.md", render_index(slug, entries))
    catalog[slug] = [{**e, "mp4": f"{slug}/{e['id']}.mp4", "contact": f"{slug}/{e['id']}-contact.png"}
                     for e in entries]
    write_atomic(dest / "catalog.json", json.dumps({"projects": catalog}, indent=2, sort_keys=True) + "\n")
    write_atomic(dest / "CATALOG.md", render_catalog(catalog))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest", type=Path, help="folder to export into (created if missing)")
    ap.add_argument("--only", action="append", default=[], metavar="ID", help="export only this clip id (repeatable)")
    ap.add_argument("--tar", type=Path, metavar="FILE.tar.gz", help="also write a gzip tar of the export")
    ap.add_argument("--force", action="store_true", help="replace clips that differ from the ones already exported")
    args = ap.parse_args()
    try:
        ids = export(ROOT, args.dest, args.only, args.tar, args.force)
    except (OSError, tarfile.TarError) as exc:
        raise SystemExit(f"export failed: {exc}") from exc
    print(f"exported {len(ids)} clip(s) to {args.dest / project_slug(ROOT)}: {', '.join(ids)}")


if __name__ == "__main__":
    main()
