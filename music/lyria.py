"""Music from Lyria, Google's music model, through the Gemini API, finished into the soundtrack.

    uv run lyria.py gen [--takes 1] [--prompt lyria/prompt.md] [--model ID] [--sections]
    uv run lyria.py finish <take> [--end SECONDS] [--fade 3] [--start SECONDS]
    uv run lyria.py --selftest

gen sends the composer's prompt (lyria/prompt.md) to the model named by project.json `music`
(or --model) and writes out/lyria/take-NN.{wav,mp3,json}: the song as delivered (MP3 from
lyria-3-clip-preview, WAV from lyria-3.5), the other format beside it, and the model, prompt,
date, length, measured tempo and the response without its audio. Takes are numbered and never
overwritten. --sections appends timestamped sections built from narration/timeline.json. Every
attempt logs one usage.jsonl line (tools/usage_log.py) and one metrics line. Needs GEMINI_API_KEY
with billing (Lyria is not on the free tier).

finish turns one take (take-03, or 3) into out/soundtrack.wav and manifest.json: 48 kHz, the
beat and bar grid measured from the audio, cut at --end (default: the timeline's total) snapped to
the nearest bar accent, faded over --fade seconds, -16 LUFS with a -1 dBTP ceiling, no stems; the
take is recorded in CREDITS.md (guides/video.md, "Lyria").

--selftest finishes a synthesized click track of known tempo in out/selftest-lyria/, offline.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the project root, for tools/
from tools import usage_log
from tools.metrics import timed
from tools.project_settings import MUSIC
from tools.project_settings import read as project_settings

from scorekit import finish as finishing
from scorekit.beatgrid import measure
from scorekit.timing import TIMELINE

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "lyria"
PROMPT = HERE / "lyria" / "prompt.md"
MODELS = tuple(m for m in MUSIC if m.startswith("lyria"))
TAKE = re.compile(r"take-(\d+)")
REFUSED = ("The model refused the prompt (HTTP 400). Prompts that name bands, artists or songs are "
           "refused: describe the sound in words instead (genre, era, instruments, production, feel).")


def audio_bytes(interaction) -> bytes:
    """The song's bytes: the SDK returns base64 text, or raw MP3 or WAV bytes."""
    audio = getattr(interaction, "output_audio", None)
    if audio is None or not getattr(audio, "data", None):
        raise RuntimeError(f"no output_audio in the response: {interaction!r}"[:800])
    data = audio.data
    if isinstance(data, str):
        return base64.b64decode(data, validate=True)
    if data[:3] == b"ID3" or data[:4] == b"RIFF" or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0):  # MP3 frame sync
        return bytes(data)
    return base64.b64decode(data, validate=True)


def store_audio(folder: Path, name: str, raw: bytes) -> tuple[Path, float]:
    """Write the song as delivered and its other format: name.wav (PCM) and name.mp3. Never overwrites:
    the call is paid, so when a take-NN name is taken (an overlapping run) the song moves to the next
    free number, and the returned path's stem is the name used."""
    folder.mkdir(parents=True, exist_ok=True)
    kind, other = ("wav", "mp3") if raw[:4] == b"RIFF" else ("mp3", "wav")
    match = TAKE.fullmatch(name)
    n = int(match[1]) if match else 0
    while True:
        stem = f"take-{n:02d}" if match else name
        delivered, beside = folder / f"{stem}.{kind}", folder / f"{stem}.{other}"
        try:
            if beside.exists():
                raise FileExistsError(beside)
            with delivered.open("xb") as f:
                f.write(raw)
            break
        except FileExistsError:
            if not match:
                raise
            n += 1
    x, rate = sf.read(delivered, always_2d=True)
    with beside.open("xb") as f:
        sf.write(f, x, rate, format=other.upper(), subtype="PCM_16" if other == "wav" else None)
    return folder / f"{stem}.wav", len(x) / rate


def sections_text(timeline: dict) -> str:
    """The timeline's scenes as Lyria's timestamped sections, `[m:ss - m:ss] key`. Times are rounded to
    whole seconds and a section shorter than 1 s is left out."""
    def clock(t: float) -> str:
        t = round(t)
        return f"{t // 60}:{t % 60:02d}"

    scenes = timeline["scenes"]
    ends = [s["start"] for s in scenes[1:]] + [timeline["total"]]
    rows = [f"[{clock(s['start'])} - {clock(end)}] {s['key']}" for s, end in zip(scenes, ends)
            if round(end) - round(s["start"]) >= 1]
    return ("\n\nThe song lasts " + clock(timeline["total"]) + ", in these timed sections:\n" + "\n".join(rows))


def request(model: str, prompt: str) -> dict:
    kw = {"model": model, "input": prompt}
    if model == "lyria-3.5":
        kw["response_format"] = {"type": "audio"}  # WAV instead of the default MP3
    return kw


def status_code(error: Exception) -> int | None:
    """The HTTP status of an SDK error (the Interactions client and genai.errors name it differently)."""
    return getattr(error, "status_code", None) or getattr(error, "code", None)


def call(client, model: str, prompt: str, name: str, attempt: int):
    """One paid call; a failure is logged (usage.jsonl, metrics) and raised. Returns (interaction, bytes)."""
    r = None
    try:
        with timed("music", f"lyria {name}", model=model, attempt=attempt):
            r = client.interactions.create(**request(model, prompt))
            return r, audio_bytes(r)
    except Exception as e:
        usage = usage_log.from_interaction(getattr(r, "usage", None))
        usage_log.log("lyria", model, usage, ok=False, take=name, error=str(e)[:500])
        raise


def save(name: str, model: str, prompt: str, prompt_file: str, r, raw: bytes, attempt: int) -> str:
    """Store a delivered song, log the billed call, write name.json, then measure its tempo into it."""
    usage = usage_log.from_interaction(getattr(r, "usage", None))
    used = name
    try:
        wav, seconds = store_audio(OUT, name, raw)
        used = wav.stem
    finally:  # billed even when the audio cannot be decoded
        usage_log.log("lyria", model, usage, ok=True, take=used, prompt_file=prompt_file)
    info = {"model": model, "prompt_file": prompt_file, "prompt": prompt, "seconds": round(seconds, 3),
            "measured_bpm": None, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "attempts": attempt,
            "interaction": usage_log.slim(r.model_dump(mode="json", exclude_none=True))}
    meta = OUT / f"{used}.json"
    meta.write_text(json.dumps(info, indent=1, default=str) + "\n")  # before measuring: the song is paid for
    try:
        info["measured_bpm"] = round(measure(finishing.load(wav)[0]).bpm, 1)
    except Exception as e:  # noqa: BLE001 - the take is kept without a tempo
        print(f"{used}: tempo not measured: {str(e)[:300]}", flush=True)
    else:
        meta.write_text(json.dumps(info, indent=1, default=str) + "\n")
    tempo = f"measured {info['measured_bpm']:.0f} BPM" if info["measured_bpm"] else "tempo not measured"
    moved = f" [{name} was taken: stored as {used}]" if used != name else ""
    return f"ok{moved}, {seconds:.1f} s, {tempo} ({wav.relative_to(HERE)}), {usage_log.summary(usage)}"


def take(client, model: str, prompt: str, prompt_file: str, name: str) -> tuple[str, str]:
    """One take: the paid call is retried once unless refused (400); the work after it never is."""
    for attempt in (1, 2):
        try:
            r, raw = call(client, model, prompt, name, attempt)
            break
        except Exception as e:  # noqa: BLE001 - any API or decoding failure is reported, then retried once
            print(f"{name}: attempt {attempt} failed: {str(e)[:500]}", flush=True)
            if status_code(e) == 400:
                return name, "refused. " + REFUSED
    else:
        return name, "FAILED"
    try:
        return name, save(name, model, prompt, prompt_file, r, raw, attempt)
    except Exception as e:  # noqa: BLE001 - the song is paid for: say where it is
        return name, f"FAILED after the paid call (audio in {OUT.relative_to(HERE)}/{name}.*): {e}"


def next_names(count: int) -> list[str]:
    """take-NN names after the highest take in out/lyria/."""
    used = [int(m[1]) for p in OUT.glob("take-*") if (m := TAKE.fullmatch(p.name.split(".")[0]))]
    start = max(used, default=0) + 1
    return [f"take-{n:02d}" for n in range(start, start + count)]


def pick_model(model: str | None) -> str:
    if model:
        return model
    music = project_settings()["music"]
    if music not in MODELS:
        sys.exit(f"project.json music is {music}: pass --model ({' or '.join(MODELS)}) or save one with "
                 "./configure.sh --music lyria-3.5")
    return music


def gen(a: argparse.Namespace) -> None:
    from google import genai

    model = pick_model(a.model)
    if not a.prompt.is_file():
        sys.exit(f"no prompt: write {a.prompt} (guides/video.md, \"Lyria\")")
    prompt = a.prompt.read_text().strip()
    if a.sections:
        if not TIMELINE.exists():
            sys.exit(f"--sections needs {TIMELINE}: build the timeline first")
        timeline = json.loads(TIMELINE.read_text())
        if model == "lyria-3-clip-preview" and timeline["total"] > 30:
            print(f"note: {model} always makes 30 s; the timeline is {timeline['total']:.1f} s", flush=True)
        if model == "lyria-3.5" and timeline["total"] > 120:
            print(f"note: {model} songs run about 120 s; the timeline is {timeline['total']:.1f} s", flush=True)
        prompt += sections_text(timeline)
    prompt_file = str(a.prompt.resolve().relative_to(HERE)) if a.prompt.resolve().is_relative_to(HERE) else str(a.prompt)
    names = next_names(a.takes)
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    with ThreadPoolExecutor(max_workers=min(3, a.takes)) as ex, timed("music", "lyria gen", takes=a.takes):
        jobs = [ex.submit(take, client, model, prompt, prompt_file, n) for n in names]
        for job in as_completed(jobs):
            name, result = job.result()
            print(f"{name}: {result}", flush=True)


def take_path(arg: str) -> Path:
    name = f"take-{int(arg):02d}" if arg.isdigit() else Path(arg).name.split(".")[0]
    path = OUT / f"{name}.wav"
    if not path.is_file():
        have = sorted(p.stem for p in OUT.glob("take-*.wav"))
        sys.exit(f"no take {path.relative_to(HERE)}; takes: {', '.join(have) or 'none (run gen first)'}")
    return path


def timeline_total() -> float | None:
    return json.loads(TIMELINE.read_text())["total"] if TIMELINE.exists() else None


def finish(a: argparse.Namespace) -> None:
    wav = take_path(a.take)
    meta_path = wav.with_suffix(".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    source = {"generator": "lyria", "model": meta.get("model"), "take": str(wav.relative_to(HERE)),
              "prompt_file": meta.get("prompt_file"), "generated_at": meta.get("generated_at")}
    end = a.end if a.end is not None else timeline_total()
    try:
        man, notes = finishing.finish(wav, HERE / "out", a.start, end, a.fade, source)
    except ValueError as e:
        sys.exit(str(e))
    (HERE / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    finishing.write_credit(HERE / "CREDITS.md", [
        f"- Model: {source['model'] or 'unknown'} (Google Lyria, through the Gemini API)",
        f"- Take: {source['take']}, generated {source['generated_at'] or 'unknown'}",
        f"- Prompt: {source['prompt_file'] or 'unknown'} (the text sent is in {meta_path.relative_to(HERE)})",
        (f"- Finished: {time.strftime('%Y-%m-%d')}, {man['source']['start']:.2f}-{man['source']['end']:.2f} s "
         f"of the take, {a.fade:g} s fade"),
        "- Credit: none on screen; the audio carries Google's SynthID watermark",
    ])
    for note in notes:
        print(f"note: {note}")
    print(json.dumps({k: man[k] for k in ("duration", "bpm", "bar_0_at", "loudness")}, indent=1))


def click_track(bpm: float, first: float, seconds: float, rate: int = 44100) -> np.ndarray:
    """Stereo 4/4 test music: a kick on every downbeat (from `first`), a hi-hat on the other beats."""
    rng = np.random.default_rng(3)
    t = np.arange(int(0.3 * rate)) / rate
    kick = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 12) + rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
    hat = np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t * 60) * 0.15
    x = rng.standard_normal(int(seconds * rate)) * 0.002
    for k, at in enumerate(np.arange(first, seconds - 0.3, 60 / bpm)):
        i = round(at * rate)
        x[i:i + len(t)] += kick if k % 4 == 0 else hat
    return np.stack([x, x], axis=1) * 0.5


def selftest() -> None:
    """A click track at 117 BPM, first downbeat 0.31 s, through the MP3 response path and finish."""
    out = HERE / "out" / "selftest-lyria"
    for old in out.glob("lyria/take-01.*"):
        old.unlink()
    bpm, first, bar = 117.0, 0.31, 4 * 60 / 117.0
    mp3 = io.BytesIO()
    sf.write(mp3, click_track(bpm, first, 30.4), 44100, format="MP3")
    response = SimpleNamespace(output_audio=SimpleNamespace(data=base64.b64encode(mp3.getvalue()).decode()))
    wav, _ = store_audio(out / "lyria", "take-01", audio_bytes(response))
    man, notes = finishing.finish(wav, out, 5.0, 12.0, 0.5, {"generator": "selftest"})
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    start = first + bar * 2  # --start 5.0 snaps to the third downbeat (4.41 s)
    expect = {"bpm": (man["bpm"], bpm, 0.2), "start": (man["source"]["start"], start, 0.02),
              "duration": (man["duration"], round(12.0 / bar) * bar, 0.02),
              "bar_0_at": (man["bar_0_at"], 0.0, 0.02),
              "lufs": (man["loudness"]["lufs_integrated"], finishing.TARGET_LUFS, 0.5)}
    failed = [f"{k} {got} (want {want} +- {tol})" for k, (got, want, tol) in expect.items() if abs(got - want) > tol]
    if man["loudness"]["true_peak_dbtp"] > finishing.CEILING_DBTP + 0.05:
        failed.append(f"true peak {man['loudness']['true_peak_dbtp']} dBTP over the ceiling")
    if sf.info(out / "soundtrack.wav").samplerate != 48000 or man["stems"] or man["sample_libraries"]:
        failed.append("soundtrack not 48 kHz, or stems or sample libraries listed")
    print(json.dumps({k: v[0] for k, v in expect.items()} | {"notes": notes}, indent=1))
    if failed:
        sys.exit("selftest FAILED: " + "; ".join(failed))
    print(f"selftest ok: {out.relative_to(HERE)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="finish a synthesized click track, offline")
    sub = ap.add_subparsers(dest="command")
    g = sub.add_parser("gen", help="generate takes (paid calls)")
    g.add_argument("--takes", type=int, choices=range(1, 11), default=1, metavar="1-10")
    g.add_argument("--prompt", type=Path, default=PROMPT)
    g.add_argument("--model", choices=MODELS)
    g.add_argument("--sections", action="store_true", help="append timed sections from narration/timeline.json")
    f = sub.add_parser("finish", help="make a take the soundtrack")
    f.add_argument("take", help="take-03, or 3")
    f.add_argument("--end", type=float, help="soundtrack length in seconds (default: the timeline's total)")
    f.add_argument("--fade", type=float, default=3.0, help="fade-out to the end, seconds (default 3)")
    f.add_argument("--start", type=float, default=0.0, help="skip the take's first seconds (snapped to a bar)")
    a = ap.parse_args()
    if a.selftest:
        with timed("music", "lyria selftest"):
            selftest()
    elif a.command == "gen":
        gen(a)
    elif a.command == "finish":
        with timed("music", "lyria finish", take=a.take):
            finish(a)
    else:
        ap.error("name a command (gen or finish) or --selftest")


if __name__ == "__main__":
    main()
