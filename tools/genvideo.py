# /// script
# dependencies = ["google-genai"]
# ///
"""Generate b-roll clips with Gemini Omni from broll/gen/shots.json.

usage: uv run tools/genvideo.py [--only <id>]
A shot is {"id", "prompt"} and may carry "images" (paths inside the project) and a "mode":
first_frame (1 image), first_last (2: first, last) or reference (1-6, the prompt names each as
<IMAGE_REF_0>, ...). An image may instead be a frame of another shot's clip: frame:<id> or
frame:<id>@last (its last frame) or frame:<id>@<seconds>, extracted with ffmpeg to broll/gen/frames/
just before the call (tools/broll_frames.py); such a shot renders after the shot it names.
Every shot not yet rendered is checked before the first paid call, and all errors are listed.
Outputs broll/gen/omni/<id>.mp4 and <id>.json (skips ids already rendered).
Logs every attempt's token counts and clip length to usage.jsonl (tools/usage_log.py).
"""
import argparse
import base64
import contextlib
import graphlib
import hashlib
import json
import os
import re
import subprocess
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import broll_frames
import usage_log
from google import genai

try:
    from metrics import timed
except ImportError:  # loaded without tools/ on sys.path (the tests do): timing is a no-op

    def timed(*_args, **_kwargs):
        return contextlib.nullcontext()

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / "broll" / "gen"
MODEL = "gemini-omni-1.1-flash"
OMNI_FMT = {"type": "video", "aspect_ratio": "16:9", "resolution": "1080p", "delivery": "inline"}
# Image limits are the kit's own caps: the Omni docs state none (Interactions inline requests stay small).
MODES = {"first_frame": (1, 1, "image_to_video"), "first_last": (2, 2, "image_to_video"),
         "reference": (1, 6, "reference_to_video")}
IMAGE_MIME = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}
MAX_IMAGE_BYTES = 7 * 1024 * 1024
MAX_SHOT_BYTES = 20 * 1024 * 1024
SHOT_ID = re.compile(broll_frames.ID)
IMAGE_REF = re.compile(r"<IMAGE_REF_(\d+)>")


def sniff_mime(data):
    """Image type from the file's magic bytes (the extension is not trusted), or None."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return IMAGE_MIME["png"]
    if data.startswith(b"\xff\xd8\xff"):
        return IMAGE_MIME["jpeg"]
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return IMAGE_MIME["webp"]
    return None


def mb(n):
    return f"{n / 2**20:.1f} MB"


def load_image(sid, name, budget):
    """{path, mime, sha256, data} for one image inside the project, at most `budget` bytes."""
    try:
        path = (PROJECT / name).resolve()  # follows symlinks, so a link out of the project is caught
        inside = path.is_relative_to(PROJECT) and path.is_file()
        size = path.stat().st_size if inside else 0
    except (OSError, RuntimeError, ValueError):  # a symlink loop, an embedded NUL byte
        inside = False
    if not inside:
        raise ValueError(f"[{sid}] image not found inside the project: {name}")
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"[{sid}] {name} is {mb(size)}; the limit is {mb(MAX_IMAGE_BYTES)} per image")
    if size > budget:
        raise ValueError(f"[{sid}] {name} takes the shot's images past {mb(MAX_SHOT_BYTES)} in total")
    limit = min(MAX_IMAGE_BYTES, budget)
    try:
        with path.open("rb") as f:
            data = f.read(limit + 1)  # never more than the caps, even if the file grew since stat
    except OSError as e:
        raise ValueError(f"[{sid}] cannot read {name}: {e}") from e
    if len(data) > limit:
        raise ValueError(f"[{sid}] {name} grew past the size cap while being read")
    mime = sniff_mime(data)
    if mime is None:
        raise ValueError(f"[{sid}] {name} is not a png, jpeg or webp image")
    return {"path": name, "mime": mime, "sha256": hashlib.sha256(data).hexdigest(), "data": data}


def check_refs(sid, prompt, mode, count):
    """reference prompts name <IMAGE_REF_0> to <IMAGE_REF_{count-1}> exactly; other prompts name none."""
    found = set(IMAGE_REF.findall(prompt))
    if mode != "reference":
        if found:
            raise ValueError(f"[{sid}] <IMAGE_REF_n> belongs in reference mode only; this shot is "
                             f"{mode or 'text-only'}")
        return
    wanted = {str(n) for n in range(count)}
    if wanted - found:
        missing = ", ".join(f"<IMAGE_REF_{n}>" for n in sorted(wanted - found, key=int))
        raise ValueError(f"[{sid}] the prompt must name every reference, missing {missing}")
    if found - wanted:
        extra = ", ".join(f"<IMAGE_REF_{n}>" for n in sorted(found - wanted, key=int))
        raise ValueError(f"[{sid}] the prompt names {extra}, but the shot has {count} image(s)")


def load_frame(sid, ref, ids, pending, budget):
    """load_image() for a frame: entry, extracted now; None when its shot is in `pending` (renders first)."""
    parent, at = ref
    entry = f"frame:{parent}@{at}"
    if parent not in ids:
        raise ValueError(f"[{sid}] {entry}: there is no shot {parent} in shots.json")
    if parent == sid:
        raise ValueError(f"[{sid}] {entry}: a shot cannot use a frame of its own clip")
    if parent in pending:
        return None
    clip = ROOT / "omni" / f"{parent}.mp4"
    if not clip.is_file():
        raise ValueError(f"[{sid}] needs {parent} rendered first: run --only {parent}, or run without --only")
    out = broll_frames.extract(sid, clip, at, ROOT / "frames", seconds)
    return load_image(sid, out.relative_to(PROJECT).as_posix(), budget) | {"source": entry}


def validate(shot, ids, pending=()):
    """Check one shot (`ids`: every id in shots.json); return its images [{path, mime, sha256, data}],
    a frame: entry's with its "source". Frames of the `pending` ids, rendered later in this run, are left out.

    Raises ValueError naming the shot id, so a bad entry never reaches the paid API.
    """
    if not isinstance(shot, dict):
        raise ValueError(f"[{str(shot)[:40]}] a shot must be an object with 'id' and 'prompt'")  # noqa: TRY004 - main collects every shot error as ValueError
    sid = shot.get("id")
    if not isinstance(sid, str) or not SHOT_ID.fullmatch(sid):
        raise ValueError(f"[{sid!r}] 'id' must be a non-empty string of letters, digits, '_' and '-'")
    if ids.count(sid) > 1:
        raise ValueError(f"[{sid}] the id appears {ids.count(sid)} times in shots.json")
    prompt, names, mode = shot.get("prompt"), shot.get("images"), shot.get("mode")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"[{sid}] 'prompt' must be a non-empty string")
    if "images" not in shot:
        if "mode" in shot:
            raise ValueError(f"[{sid}] mode {mode!r} needs an 'images' list")
        check_refs(sid, prompt, None, 0)
        return []
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError(f"[{sid}] 'images' must be a list of paths or frame: entries, got {names!r}")
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError(f"[{sid}] 'images' needs a 'mode': one of {', '.join(MODES)} (got {mode!r})")
    low, high, _ = MODES[mode]
    if not low <= len(names) <= high:
        want = str(low) if low == high else f"{low} to {high}"
        raise ValueError(f"[{sid}] mode {mode} takes {want} image(s), got {len(names)}")
    check_refs(sid, prompt, mode, len(names))
    images, budget = [], MAX_SHOT_BYTES
    for name in names:
        ref = broll_frames.parse(sid, name)
        image = load_image(sid, name, budget) if ref is None else load_frame(sid, ref, ids, pending, budget)
        if image is not None:
            images.append(image)
            budget -= len(image["data"])
    return images


def request(shot, images):
    """Keyword arguments for interactions.create: text-only unchanged, images become input parts."""
    kw = {"model": MODEL, "input": shot["prompt"], "response_modalities": ["video"],
          "response_format": OMNI_FMT}
    if images:
        parts = [{"type": "image", "data": base64.b64encode(i["data"]).decode(), "mime_type": i["mime"]}
                 for i in images]
        kw["input"] = parts + [{"type": "text", "text": shot["prompt"]}]
        kw["generation_config"] = {"video_config": {"task": MODES[shot["mode"]][2]}}
    return kw


def slim(obj):
    """Drop large blobs (base64 video) so metadata stays readable."""
    if isinstance(obj, dict):
        return {k: slim(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [slim(v) for v in obj]
    return "<blob>" if isinstance(obj, str) and len(obj) > 2000 else obj


def seconds(path):
    """Clip length from ffprobe, or None when it cannot be read (or ffprobe is missing)."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(path)], check=False, capture_output=True, text=True)
        return round(float(r.stdout), 2)
    except (OSError, ValueError):
        return None


def generate(client, shot, images, tmp):
    """The paid call and the decoding of its response into `tmp`; returns the interaction."""
    r = client.interactions.create(**request(shot, images))
    vid = r.output_video
    if vid is None or not vid.data:
        usage_log.log("genvideo", MODEL, usage_log.from_interaction(r.usage), shot=shot["id"], ok=False)
        why = f"uri delivery not handled: {vid.uri}" if vid is not None and vid.uri else \
            f"no video returned: {slim(r.model_dump(mode='json', exclude_none=True))}"
        raise RuntimeError(why)
    tmp.write_bytes(vid.data if isinstance(vid.data, bytes) else base64.b64decode(vid.data))
    return r


def finish(shot, images, r, tmp, attempt, t0):
    """Log the call, write <id>.json atomically, then move the clip into place (the skip check keys on it)."""
    sid, d = shot["id"], tmp.parent
    secs = seconds(tmp)
    usage_log.log("genvideo", MODEL, usage_log.from_interaction(r.usage), shot=sid, ok=True, seconds=secs)
    info = {"model": MODEL, "prompt": shot["prompt"], "config": OMNI_FMT,
            "task": MODES[shot["mode"]][2] if images else None, "seconds": secs,
            "seconds_taken": round(time.time() - t0, 1), "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "attempts": attempt, "interaction": slim(r.model_dump(mode="json", exclude_none=True))}
    if images:
        info["mode"] = shot["mode"]
        info["images"] = [{k: i[k] for k in ("path", "sha256", "source") if k in i} for i in images]
    meta_tmp = d / f".{sid}.tmp.json"
    meta_tmp.write_text(json.dumps(info, indent=1, default=str))
    os.replace(meta_tmp, d / f"{sid}.json")
    os.replace(tmp, d / f"{sid}.mp4")


def run(client, shot, images):
    """Render one validated shot: the paid call is retried once; the work after it never is."""
    sid = shot["id"]
    d = ROOT / "omni"
    d.mkdir(parents=True, exist_ok=True)
    tmp, t0 = d / f".{sid}.tmp.mp4", time.time()
    for attempt in (1, 2):
        try:
            with timed("broll", f"shot {sid}", attempt=attempt, mode=shot.get("mode") or "text"):
                r = generate(client, shot, images, tmp)
            break
        except Exception as e:  # noqa: BLE001 - any API or decoding failure is retried once, then reported
            tmp.unlink(missing_ok=True)
            print(f"[{sid}] attempt {attempt} failed: {str(e)[:500]}", flush=True)
    else:
        return sid, "FAILED"
    try:
        finish(shot, images, r, tmp, attempt, t0)
    except Exception as e:  # noqa: BLE001 - the clip is paid for: keep it, report it, let the other shots go on
        return sid, f"FAILED after the paid call, clip kept at {keep(sid, tmp)}: {e}"
    return sid, f"ok (attempt {attempt})"


def keep(sid, tmp):
    """Move a paid clip that failed after the call to .<id>.<time>.kept.mp4, a name no later run writes;
    return where the clip is (still `tmp` when the move fails)."""
    stamp, n = time.strftime("%Y%m%d-%H%M%S"), 0
    kept = tmp.with_name(f".{sid}.{stamp}.kept.mp4")
    while kept.exists():
        n += 1
        kept = tmp.with_name(f".{sid}.{stamp}-{n}.kept.mp4")
    try:
        os.replace(tmp, kept)
    except OSError:
        return tmp
    return kept


def job(client, shot, images, ids, fresh):
    """run() in a worker, after validate() again when `fresh` (its frame parents rendered in this run, so
    their frames are extracted now); always returns (id, status), so one shot never stops the others."""
    try:
        return run(client, shot, validate(shot, ids) if fresh else images)
    except Exception as e:  # noqa: BLE001 - run() reports every failure from the paid call on: this is before it
        return shot["id"], f"FAILED before the paid call: {e}"


def schedule(ex, client, jobs, ids):
    """Run `jobs` (parents first) on `ex`, each submitted once every frame parent it has in the run has ended,
    so no worker waits on another; print each status as it ends. A child of a failed parent never starts."""
    todo = {s["id"]: (s, images) for s, images in jobs}
    needs = {sid: [p for p in broll_frames.parents(s) if p in todo] for sid, (s, _) in todo.items()}
    ended, running = {}, set()
    while todo or running:
        for sid in list(todo):  # parents first, so a skip reaches the whole chain in one pass
            if any(p not in ended for p in needs[sid]):
                continue
            shot, images = todo.pop(sid)
            failed = next((p for p in needs[sid] if not ended[p].startswith("ok")), None)
            if failed is None:
                running.add(ex.submit(job, client, shot, images, ids, bool(needs[sid])))
                continue
            ended[sid] = f"skipped: needs {failed}, which did not render"
            print(f"{sid}: {ended[sid]}", flush=True)
        done, running = wait(running, return_when=FIRST_COMPLETED)
        for future in done:
            sid, status = future.result()
            ended[sid] = status
            print(f"{sid}: {status}", flush=True)


def rendered(shot):
    sid = shot.get("id") if isinstance(shot, dict) else None
    return isinstance(sid, str) and bool(SHOT_ID.fullmatch(sid)) and (ROOT / "omni" / f"{sid}.mp4").exists()


def skip_rendered(picked, pending, shots):
    """The picked shots not yet rendered; prints the others, and warns of every rendered shot in `shots`
    (picked or not, so `--only <parent>` warns too) whose frame parent renders again now."""
    for s in filter(rendered, picked):
        print(f"{s['id']}: skipped (already rendered)", flush=True)
    for s in filter(rendered, shots):
        for parent in broll_frames.parents(s):
            if parent in pending:
                print(f"{s['id']}: rendered from an earlier {parent}; delete broll/gen/omni/{s['id']}.mp4 to "
                      "render it again from the new clip", flush=True)
    return [s for s in picked if not rendered(s)]


def plan(picked, ids, shots):
    """(jobs [(shot, images)] with every parent before its children, errors): all checks before a paid call."""
    pending = {s["id"] for s in picked if isinstance(s, dict) and isinstance(s.get("id"), str) and not rendered(s)}
    jobs, errors = {}, []
    for s in skip_rendered(picked, pending, shots):
        try:  # validate every shot first: a bad one must not cost a paid call
            job = (s, validate(s, ids, pending))
        except ValueError as e:
            errors.append(str(e))
            continue
        jobs[s["id"]] = job
    graph = {sid: [p for p in broll_frames.parents(s) if p in pending] for sid, (s, _) in jobs.items()}
    errors += [f"[{sid}] needs {p}, whose entry in shots.json has errors" for sid, needs in graph.items()
               for p in needs if p not in jobs]
    try:
        order = list(graphlib.TopologicalSorter(graph).static_order())
    except graphlib.CycleError as e:  # args[1] lists each parent before its child
        cycle = e.args[1][::-1]
        errors.append(f"[{cycle[0]}] frame: entries form a cycle, each shot using a frame of the next: "
                      + " -> ".join(cycle))
        order = []
    return [jobs[sid] for sid in order if sid in jobs], errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    path = ROOT / "shots.json"
    if not path.exists():
        raise SystemExit(f"no shot list: create {path}, a list of {{\"id\", \"prompt\"}} with an optional "
                         "\"mode\" and \"images\" (paths, or frame:<id>[@<seconds>] for a frame of another "
                         "shot's clip) (guides/video.md, \"B-roll\")")
    try:
        shots = json.loads(path.read_text())
    except ValueError as e:
        raise SystemExit(f"{path} is not valid JSON: {e}") from e
    if not isinstance(shots, list):
        raise SystemExit(f"{path} must hold a JSON list of shots")
    ids = [s.get("id") if isinstance(s, dict) else None for s in shots]
    picked = [s for s, sid in zip(shots, ids) if a.only in (None, sid)]
    if a.only is not None and not picked:
        raise SystemExit(f"no shot {a.only} in {path}")
    jobs, errors = plan(picked, ids, shots)
    if errors:
        raise SystemExit("invalid shot list:\n" + "\n".join(errors))
    if not jobs:
        return
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    with ThreadPoolExecutor(max_workers=3) as ex, timed("broll", "run", shots=len(jobs)):
        try:
            schedule(ex, client, jobs, ids)
        except KeyboardInterrupt:  # queued paid calls never start; the running ones end and keep their clips
            ex.shutdown(cancel_futures=True)
            raise


if __name__ == "__main__":
    main()
