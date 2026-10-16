"""Render the edit. Deliverables go to outputs/ at the project root as <stage>-<slug>-v<N>[-suffix].<ext>
(slug from project.json; stage final for a full render, draft for --preview).

  uv run render.py                          full quality -> outputs/final-<slug>-vN.mp4 (muxes out/mix.wav)
  uv run render.py --preview                540p at min(30, FPS), no grain/DOF/motion blur -> outputs/draft-<slug>-vN.mp4
  uv run render.py --range 20 34            any mode, a time range -> outputs/<stage>-<slug>-vN-range-20-34.mp4
                                            (a decimal point is written p: 12.5 -> 12p5)
  uv run render.py --contact [--every 2]    contact sheets -> outputs/draft-<slug>-vN-contact-<NN>.png
  uv run render.py --share [--revision vN]   30 fps share copy of the latest final -> outputs/final-<slug>-vN-share.mp4
  uv run render.py --frames 12.5 40         single frames -> build/frames/*.png

N is the latest revision of the stage's mp4 (1 when none); --next starts the following one for a new
full render or preview, --revision vN picks one. Range, contact and share attach to the latest mp4.
The frame rate is edl.py's FPS, else project.json's fps (default 30).
"""


import argparse
import dataclasses
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from editkit import assets
from editkit.art import font
from editkit.compositor import PREVIEW, Compositor, Quality, project_fps
from editkit.decode import probe
from editkit.hw import fast_h264
from editkit.outputs import latest_revision, output_path, read_slug, revision_arg
from editkit.project import edl

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUTPUTS = assets.ROOT / "outputs"


def encoder(path: Path, q: Quality, start: float, dur: float, audio: Path | None, fast: bool):
    w, h = q.res
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(q.fps), "-i", "-"]
    if audio is not None:
        cmd += ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(audio)]
    cmd += ["-vf", ("scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
                   "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")]
    if fast:
        cmd += [*fast_h264("p5", 20), "-profile:v", "high"]
    else:
        cmd += ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "14",
                "-x264-params", "aq-mode=3"]
    cmd += ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    if audio is not None:
        cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest"]
    cmd += ["-movflags", "+faststart", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def render_video(q: Quality, start: float, end: float, out: Path, audio: Path | None, fast: bool) -> None:
    tl = edl().build()
    comp = Compositor(tl, q)
    n = round((end - start) * q.fps)
    enc = encoder(out, q, start, end - start, audio, fast)
    t0 = time.time()
    for i in range(n):
        t = start + i / q.fps
        enc.stdin.write(comp.render(t))
        if i % q.fps == 0:
            comp.retire(t)
        if i and i % (q.fps * 5) == 0:
            el = time.time() - t0
            print(f"  t={t:6.2f}s  {i}/{n}  {i / el:5.1f} fps", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    comp.close()
    print(f"wrote {out} ({n} frames in {time.time() - t0:.0f}s)")


def render_frames(q: Quality, times: list[float]) -> list[Image.Image]:
    tl = edl().build()
    comp = Compositor(tl, q)
    w, h = q.res
    imgs = []
    for t in times:
        buf = comp.render(t)
        imgs.append(Image.frombytes("RGB", (w, h), buf))
        comp.close()  # isolated frames: reopen decoders at the next seek point
    return imgs


def contact(q: Quality, start: float, end: float, every: float, sheet_path, cols: int = 4) -> list[Path]:
    """Contact sheets of one frame every `every` s; `sheet_path(n)` names sheet number n."""
    times = list(np.arange(start, end, every))
    imgs = render_frames(q, times)
    tw = 480
    th = int(tw * 9 / 16)
    rows_per_sheet = 6
    per = cols * rows_per_sheet
    paths = []
    f = font(16, 500)
    for s in range(0, len(imgs), per):
        chunk = imgs[s:s + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * 6, rows * (th + 26) + 6), (40, 40, 40))
        d = ImageDraw.Draw(sheet)
        for i, im in enumerate(chunk):
            x, y = 6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 26)
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x + 4, y + th + 3), f"{times[s + i]:6.2f}s", font=f, fill=(230, 230, 230))
        p = sheet_path(s // per)
        sheet.save(p)
        paths.append(p)
    return paths


def require_real_assets() -> None:
    """Refuse to render a video while any shot resolves to a placeholder."""
    for seg in edl().build().segments:
        for plane in seg.layers:
            if isinstance(plane.source, str):
                assets.resolve(plane.source)
    missing = [key for key, state in assets.status() if state != "real"]
    if missing:
        sys.exit("refusing to render, placeholders in use: " + ", ".join(missing)
                 + " (wait for the asset, or pass --allow-placeholders for a draft)")


def _t(x: float) -> str:
    """A time as a slug part: 12.5 -> 12p5."""
    return f"{x:g}".replace(".", "p")


def share(slug: str, revision: int | None) -> None:
    """Transcode a final master to the share copy (guides/video.md, "The share copy")."""
    rev = revision or latest_revision(OUTPUTS, slug, "final", "mp4")
    src = OUTPUTS / f"final-{slug}-v{rev}.mp4"
    if rev is None or not src.exists():
        sys.exit(f"no final master {src} to transcode: render one with `uv run render.py`")
    dst = output_path(OUTPUTS, slug, "final", "mp4", primary_ext="mp4", suffix="share", revision=rev)
    if dst.exists():
        sys.exit(f"{dst} exists: remove it to regenerate")
    vf = ["-vf", "fps=30"] if probe(str(src)).fps > 30.5 else []
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-nostdin", "-n", "-i", str(src),
                    "-map", "0:v:0", "-map", "0:a:0", "-map_metadata", "0", *vf,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                    "-profile:v", "high", "-level:v", "4.1", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)], check=True)
    print(f"wrote {dst}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--range", nargs=2, type=float, metavar=("START", "END"))
    ap.add_argument("--out", type=Path, help="write the video here instead of outputs/")
    ap.add_argument("--contact", action="store_true")
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--frames", nargs="+", type=float)
    ap.add_argument("--full-frames", action="store_true", help="--frames at full quality")
    ap.add_argument("--share", action="store_true", help="30 fps share copy of the latest final master")
    ap.add_argument("--next", action="store_true", help="start the next revision of a full render or preview")
    ap.add_argument("--revision", type=revision_arg, metavar="vN", help="write to (or, for --share, read) this revision")
    ap.add_argument("--fast", "--nvenc", dest="fast", action="store_true",
                    help="fast encode instead of x264 at crf 14 (NVENC or VideoToolbox when they work, else x264 veryfast)")
    ap.add_argument("--allow-placeholders", action="store_true", help="render even if an asset is missing")
    a = ap.parse_args()

    slug = read_slug(assets.ROOT)
    if a.share:
        return share(slug, a.revision)
    OUT.mkdir(exist_ok=True)
    if not (a.frames or a.contact or a.allow_placeholders):
        require_real_assets()
    fps = int(getattr(edl(), "FPS", project_fps()))
    q = dataclasses.replace(PREVIEW, fps=min(30, fps)) if a.preview else Quality(fps=fps)
    total = edl().END
    start, end = a.range if a.range else (0.0, total)
    stage = "draft" if a.preview else "final"

    if a.frames:
        fq = Quality(fps=fps) if a.full_frames else Quality(res=(1920, 1080), fps=fps, grain=0.0, dof=True,
                                                            motion_blur=False, decode_scale=0.5)
        d = HERE / "build" / "frames"
        d.mkdir(parents=True, exist_ok=True)
        for t, im in zip(a.frames, render_frames(fq, a.frames)):
            p = d / f"f_{t:07.3f}.png"
            im.save(p)
            print(p)
    elif a.contact:
        cq = Quality(res=(960, 540), fps=fps, grain=0.0, dof=True, motion_blur=False, decode_scale=0.5)

        def sheet(n: int) -> Path:
            return output_path(OUTPUTS, slug, "draft", "png", primary_ext="mp4",
                               suffix=f"contact-{n:02d}", revision=a.revision)

        for p in contact(cq, start, end, a.every, sheet):
            print(p)
    else:
        mix = OUT / "mix.wav"
        audio = mix if mix.exists() else None
        suffix = f"range-{_t(start)}-{_t(end)}" if a.range else None
        out = a.out or output_path(OUTPUTS, slug, stage, "mp4", primary_ext="mp4", suffix=suffix,
                                   revision=a.revision, next_rev=a.next)
        render_video(q, start, end, out, audio, fast=a.fast or a.preview)
    for key, state in assets.status():
        if state != "real":
            print(f"  {state}: {key}")


if __name__ == "__main__":
    main()
