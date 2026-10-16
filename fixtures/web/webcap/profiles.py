"""Capture profiles: what a clip is recorded at and which files it becomes.

    blog   scale 1, 30 fps: clip.webm (VP9), clip.gif, clip.png poster
    video  scale 2, the project's frame rate (project.json fps, default 30): clip.mp4 (H.264),
           clip.png poster, a per-frame cursor track
    both   recorded once as video, then clip.webm (30 fps) and clip.gif derived from the mp4

`--draft` (video and both) records at scale 1 with a fast, lower-quality H.264 encode.
"""

from __future__ import annotations

from dataclasses import dataclass

from webcap.project import fps as project_fps

NAMES = ("video", "blog", "both")
STILL_SCALE = 2.0  # SHOTS stills, whatever the profile


@dataclass(frozen=True)
class Profile:
    name: str
    scale: float
    fps: int
    draft: bool = False

    @property
    def video(self) -> bool:
        """Records an mp4 and a cursor track."""
        return self.name != "blog"

    @property
    def blog(self) -> bool:
        """Writes the WebM and GIF a post embeds."""
        return self.name != "video"

    @property
    def encoders(self) -> tuple[str, ...]:
        """The ffmpeg encoders a clip in this profile needs."""
        return ("libx264",) * self.video + ("libvpx-vp9",) * self.blog


def profile(name: str, draft: bool = False, fps: int | None = None) -> Profile:
    """The profile called `name`. Video and both record at `fps`, by default the project's frame
    rate (webcap.project.fps). ValueError for an unknown name or a blog draft."""
    if name not in NAMES:
        raise ValueError(f"profile {name!r} must be one of {', '.join(NAMES)}")
    if name == "blog":
        if draft:
            raise ValueError("--draft applies to the video and both profiles")
        return Profile("blog", 1.0, 30)
    return Profile(name, 1.0 if draft else 2.0, fps or project_fps(), draft)
