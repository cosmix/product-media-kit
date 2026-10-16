"""The ffmpeg commands a clip goes through, and a check that ffmpeg can run them.

Frames arrive as PNGs on stdin and become an H.264 mp4 (video, both) or a VP9 WebM (blog). The
both profile derives its WebM (30 fps, half size) and every profile its GIF from that first file.
All video is BT.709 limited range, yuv420p.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from webcap.media import temp_path
from webcap.profiles import Profile

GIF_FPS = 15
GIF_MAX_WIDTH = 960
DERIVED_FPS = 30  # the both profile's WebM
BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-color_range", "tv"]
# setparams tags the frames: ffmpeg 9 lets frame properties override -color_trc and
# -color_primaries, so the output options alone leave both "unknown".
TO_BT709 = ("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
            "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")
VP9 = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-b:v", "0", "-crf", "32", "-row-mt", "1"]
FROM_STDIN = ["-f", "image2pipe", "-c:v", "png", "-i", "-"]


def check_frame_size(scenario: str, viewport: Mapping[str, int], scale: float) -> None:
    """Raise ValueError when a clip's frames (viewport x scale) have an odd side: yuv420p
    needs even ones."""
    width, height = round(viewport["width"] * scale), round(viewport["height"] * scale)
    if width % 2 or height % 2:
        raise ValueError(f"{scenario}: clip frames {width}x{height} need even sides for "
                         f"yuv420p video; change VIEWPORT")


def mp4_command(dest: Path, fps: int, draft: bool) -> list[str]:
    """PNG frames on stdin to an H.264 mp4: crf 10, preset slow; a draft is crf 23, ultrafast."""
    return [
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), *FROM_STDIN,
        "-vf", TO_BT709, "-c:v", "libx264", "-preset", "ultrafast" if draft else "slow",
        "-crf", "23" if draft else "10", "-pix_fmt", "yuv420p", *BT709,
        "-r", str(fps), "-movflags", "+faststart", str(dest),
    ]


def webm_command(dest: Path, fps: int) -> list[str]:
    """PNG frames on stdin to a VP9 WebM."""
    return ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), *FROM_STDIN,
            "-vf", TO_BT709, *VP9, *BT709, "-r", str(fps), str(dest)]


def derived_webm_command(src: Path, dest: Path) -> list[str]:
    """The mp4 at DERIVED_FPS and half size (even sides) as a VP9 WebM."""
    graph = f"fps={DERIVED_FPS},scale=trunc(iw/4)*2:trunc(ih/4)*2:flags=lanczos,{TO_BT709}"
    return ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", graph, *VP9, *BT709,
            str(dest)]


def gif_command(src: Path, dest: Path, width: int) -> list[str]:
    """A palette-optimised GIF at GIF_FPS, at most GIF_MAX_WIDTH wide, from `src` (`width` px)."""
    graph = (
        f"fps={GIF_FPS},scale={min(width, GIF_MAX_WIDTH)}:-1:flags=lanczos,"
        "split[a][b];[a]palettegen[p];[b][p]paletteuse"
    )
    return ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", graph, str(dest)]


async def derive(dest: Path, command: list[str]) -> None:
    """Run `command`, which writes temp_path(dest), then rename it onto `dest`."""
    encoder = await asyncio.create_subprocess_exec(*command)
    if await encoder.wait() != 0:
        temp_path(dest).unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed encoding {dest}")
    temp_path(dest).replace(dest)


def ffmpeg_problem(profile: Profile) -> str | None:
    """Why ffmpeg cannot encode the profile's clips (absent, or an encoder missing), else None."""
    if not shutil.which("ffmpeg"):
        return "ffmpeg is not on PATH"
    listing = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                             text=True, check=False).stdout
    have = {line.split()[1] for line in listing.splitlines() if len(line.split()) > 1}
    missing = [name for name in profile.encoders if name not in have]
    if missing:
        return f"ffmpeg lacks {', '.join(missing)} (the {profile.name} profile needs it)"
    return None
