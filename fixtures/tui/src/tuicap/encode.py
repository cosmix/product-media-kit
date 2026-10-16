"""ffmpeg commands for the capture profiles (guides/capture.md, "TUI capture"): raw frames in, H.264 MP4
or VP9 WebM out, then the WebM and GIF derived for the blog."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # the project: fixtures/tui/src/tuicap/../../../..
sys.path.insert(0, str(ROOT))  # for tools/
from tools.project_settings import read as project_settings

PROFILES = ("blog", "video", "both")
BLOG_FPS = 30  # the blog profile's frame rate and the derived WebM's
GIF_FPS = 15
GIF_MAX_WIDTH = 960
DRAFT_CRF = "23"
FINAL_CRF = "10"
# setparams tags the frames: ffmpeg 9 lets frame properties override -color_trc and
# -color_primaries, so the output options alone leave both "unknown".
TO_BT709 = ("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
            "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")


def uses_mp4(profile: str) -> bool:
    """The video and both profiles render the MP4 first."""
    return profile != "blog"


def fps_for(profile: str, root: Path | None = None) -> int:
    """BLOG_FPS for blog; for video and both, project.json's fps under `root` (default ROOT; 30
    when absent, tools/project_settings.py)."""
    return project_settings(root or ROOT)["fps"] if uses_mp4(profile) else BLOG_FPS


def encoder(path: Path, width: int, height: int, profile: str, fps: int,
            draft: bool = False) -> subprocess.Popen:
    """ffmpeg reading raw RGBA frames at `fps` on stdin: a bt709 H.264 MP4 for video and both
    (slow crf 10, or ultrafast crf 23 as a draft), a VP9 WebM for blog."""
    fps = str(fps)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", fps,
        "-i", "-",
        "-vf", TO_BT709,
    ]
    if uses_mp4(profile):
        cmd += ["-c:v", "libx264", "-preset", "ultrafast" if draft else "slow",
                "-crf", DRAFT_CRF if draft else FINAL_CRF, "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-r", fps, "-fps_mode", "cfr", "-movflags", "+faststart"]
    else:
        cmd += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-pix_fmt", "yuv420p", "-r", fps]
    return subprocess.Popen([*cmd, str(path)], stdin=subprocess.PIPE)


def _ffmpeg(*args: str) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=False,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")


def webm_from_mp4(mp4: Path, webm: Path, fps: int) -> None:
    """The blog WebM from the video MP4 (recorded at `fps`): BLOG_FPS, resampled only when `fps`
    differs, at half the pixel size."""
    resample = "" if fps == BLOG_FPS else f"fps={BLOG_FPS},"
    _ffmpeg("-i", str(mp4), "-vf", f"{resample}scale=trunc(iw/4)*2:trunc(ih/4)*2:flags=lanczos",
            "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-pix_fmt", "yuv420p", str(webm))


def gif_from_webm(webm: Path, gif: Path) -> None:
    """GIF from the WebM: 15 fps, at most 960 px wide, one generated palette."""
    chain = f"fps={GIF_FPS},scale='min({GIF_MAX_WIDTH},iw)':-2:flags=lanczos"
    _ffmpeg("-i", str(webm), "-vf",
            f"{chain},split[a][b];[a]palettegen[p];[b][p]paletteuse", "-f", "gif", str(gif))
