"""Deterministic frame stepping: one virtual 1/fps s per captured frame.

Per frame: advance the mock server's clock, wait until the page has received
every frame the server sent, advance the page's faked clock (timers, rAF,
Date, performance.now), dispatch this frame's input, seek every CSS
animation and transition to the same virtual time, then screenshot. Nothing
depends on how long a screenshot takes, so motion is exactly the profile's
frame rate (30 fps blog; the project's fps, default 30, for video and both). In live mode (no World) the
first two steps are skipped: the page's own clock is still stepped, the live
server's data arrives in real time.

A clip is written into <out_dir>/<scenario>/ as the profile asks (webcap.profiles):
clip.mp4 (video, both), clip.webm and clip.gif (blog, both) and clip.png (the last
frame, the poster). `still(label)` writes the current frame as <label>.png.
"""

from __future__ import annotations

import asyncio
import base64
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page

from webcap import encode
from webcap.boxes import element_box, pixel_boxes
from webcap.manifest import still_entry
from webcap.media import png_size, temp_path, write_atomic
from webcap.names import LABEL, check_label, check_name
from webcap.profiles import Profile
from webcap.world import World


def ease_cubic(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return 4 * u**3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


@dataclass
class Clip:
    scenario: str
    folder: Path
    origin: int  # the director's frame index at the clip's first frame
    frames: int = 0
    marks: list[dict] = field(default_factory=list)
    cursor: list[dict] = field(default_factory=list)

    def file(self, ext: str) -> Path:
        return self.folder / f"{LABEL}.{ext}"

    def entry(self, profile: Profile, size: tuple[int, int], viewport: Mapping[str, int]) -> dict:
        """The clip's manifest entry; paths are relative to the manifest's folder."""
        base = f"{self.scenario}/{LABEL}"
        entry = {"id": base, "kind": "clip", "origin": "clip"}
        if profile.blog:
            entry |= {"file": f"{base}.gif", "webm": f"{base}.webm"}
        else:
            entry["file"] = f"{base}.png"  # the poster; "video" names the mp4
        entry["poster"] = f"{base}.png"
        if profile.video:
            entry["video"] = f"{base}.mp4"
        entry |= {"width": size[0], "height": size[1], "scale": profile.scale}
        if profile.video:
            entry["fps"] = profile.fps
        entry |= {"duration": round(self.frames / profile.fps, 3), "boxes": {}, "marks": self.marks}
        if profile.video:
            entry |= {"cursor": self.cursor,
                      "cursor_space": f"css-{viewport['width']}x{viewport['height']}"}
        return entry


class Director:
    def __init__(self, page: Page, world: World | None, out_dir: Path, profile: Profile) -> None:
        self.page = page
        self.profile = profile
        self.scale = profile.scale
        self.fps = profile.fps
        self.world = world
        self.out_dir = out_dir
        self.frame = 0  # virtual frame index; t = frame / fps
        viewport = page.viewport_size or {"width": 1440, "height": 900}
        self.x, self.y = viewport["width"] / 2, viewport["height"] / 2
        self.down = False
        self.clip: Clip | None = None
        self.stills: list[dict] = []  # the current clip's still entries (origin "clip")
        self._ffmpeg: asyncio.subprocess.Process | None = None
        self._cdp = None
        self._offset = 0
        self._last_png: bytes | None = None

    @property
    def t(self) -> float:
        return self.frame / self.fps

    def frames(self, seconds: float) -> int:
        """Whole frames in `seconds`, at least one."""
        return max(1, round(seconds * self.fps))

    # --- recording -------------------------------------------------------

    def _first_file(self) -> Path:
        """The file the frames are encoded into: the mp4, or the blog profile's WebM."""
        return self.clip.file("mp4" if self.profile.video else "webm")

    async def start(self, scenario: str) -> None:
        """Begin the scenario's clip; frames stepped from here are its frames."""
        check_name("scenario", scenario)
        encode.check_frame_size(scenario, self.page.viewport_size, self.scale)
        if self._cdp is None:
            self._cdp = await self.page.context.new_cdp_session(self.page)
        self.clip = Clip(scenario, self.out_dir / scenario, self.frame)
        self.stills = []
        self.clip.folder.mkdir(parents=True, exist_ok=True)
        partial = temp_path(self._first_file())
        if self.profile.video:
            command = encode.mp4_command(partial, self.fps, self.profile.draft)
        else:
            command = encode.webm_command(partial, self.fps)
        self._ffmpeg = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE)

    async def finish(self) -> dict:
        """Close the encoder, derive the profile's other files and the poster; the clip's
        manifest entry. The clip's still entries stay in `stills`."""
        clip, ffmpeg = self.clip, self._ffmpeg
        if clip is None or ffmpeg is None:
            raise RuntimeError("finish() without start()")
        if not clip.frames:
            await self.abort()
            raise RuntimeError(f"clip {clip.scenario}/{LABEL} recorded no frames")
        first = self._first_file()
        ffmpeg.stdin.close()
        code = await ffmpeg.wait()
        self.clip, self._ffmpeg = None, None
        if code != 0:
            temp_path(first).unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg failed encoding {first}")
        temp_path(first).replace(first)
        size = png_size(self._last_png)
        if self.profile.blog:
            if self.profile.video:
                webm = clip.file("webm")
                await encode.derive(webm, encode.derived_webm_command(first, temp_path(webm), self.fps))
            gif = clip.file("gif")
            await encode.derive(gif, encode.gif_command(first, temp_path(gif), size[0]))
        write_atomic(clip.file("png"), self._last_png)
        return clip.entry(self.profile, size, self.page.viewport_size)

    async def abort(self) -> None:
        """Drop an unfinished clip: stop its encoder and remove the partial file."""
        if self._ffmpeg is not None:
            if self._ffmpeg.returncode is None:
                self._ffmpeg.kill()
            await self._ffmpeg.wait()
            temp_path(self._first_file()).unlink(missing_ok=True)
        self.clip, self._ffmpeg = None, None

    def clip_t(self) -> float:
        return round((self.frame - self.clip.origin) / self.fps, 4)

    def mark(self, event: str, key: bool = False) -> None:
        """Log an event at the clip's current time; it goes into the clip's manifest entry.
        Key marks are the ones a video edit syncs narration to."""
        if self.clip:
            self.clip.marks.append({"t": self.clip_t(), "event": event, "key": key})

    async def still(self, label: str, boxes: Mapping[str, str] | None = None) -> dict:
        """Write the last recorded frame as <scenario>/<label>.png; its manifest entry.

        `boxes` maps a box name to a CSS selector, measured on the page as it is now.
        """
        if self.clip is None or self._last_png is None:
            raise RuntimeError("still() needs a recorded frame: call it after start() and a step")
        scenario = self.clip.scenario
        check_label(scenario, label)
        size = png_size(self._last_png)
        found = {name: await element_box(self.page, selector, scenario)
                 for name, selector in (boxes or {}).items()}
        measured = pixel_boxes(f"{scenario}/{label}", found, self.scale, (0.0, 0.0), size)
        write_atomic(self.clip.folder / f"{label}.png", self._last_png)
        entry = still_entry(scenario, label, size, self.scale, measured, "clip")
        self.stills = [e for e in self.stills if e["id"] != entry["id"]] + [entry]
        return entry

    # --- the frame step --------------------------------------------------

    async def _sync_messages(self) -> None:
        target = self.world.sent
        seen, stable = -1, 0
        for _ in range(80):
            rx = await self.page.evaluate("window.__rx")
            if rx + self._offset >= target:
                return
            stable = stable + 1 if rx == seen else 0
            seen = rx
            if stable >= 6:
                # A frame sent to a socket the page already closed never
                # arrives; rebase instead of waiting on it forever.
                self._offset = target - rx
                return
            await asyncio.sleep(0.003)

    async def _record(self) -> None:
        # A CDP session of our own does not inherit Playwright's device
        # metrics, so ask for the device scale explicitly.
        viewport = self.page.viewport_size
        clip = {"x": 0, "y": 0, "width": viewport["width"], "height": viewport["height"],
                "scale": self.scale}
        shot = await self._cdp.send(
            "Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True, "clip": clip}
        )
        self._last_png = base64.b64decode(shot["data"])
        self._ffmpeg.stdin.write(self._last_png)
        await self._ffmpeg.stdin.drain()
        self.clip.frames += 1
        if self.profile.video:
            self.clip.cursor.append(
                {"t": self.clip_t(), "x": round(self.x, 1), "y": round(self.y, 1), "down": self.down}
            )

    async def step(self, actions=None) -> None:
        """Render one frame at the current virtual time, then advance it."""
        if self.world is not None:
            await self.world.tick(self.t)
            await self._sync_messages()
        ms = round((self.frame + 1) * 1000 / self.fps) - round(self.frame * 1000 / self.fps)
        # run_for installs the fake clock on first use, so live mode (no world, no install
        # in open_page) still steps virtual time.
        await self.page.clock.run_for(ms)
        if actions:
            await actions()
        await self.page.evaluate("window.__frame()")
        if self.clip:
            await self._record()
        self.frame += 1
        # Let the loop deliver whatever the page sent back (keystrokes, resizes).
        await asyncio.sleep(0)

    # --- choreography ----------------------------------------------------

    async def hold(self, seconds: float) -> None:
        for _ in range(round(seconds * self.fps)):
            await self.step()

    async def glide(self, x: float, y: float, seconds: float, arc: float = 0.08) -> None:
        """Move the pointer along a gently bowed, eased path."""
        x0, y0 = self.x, self.y
        n = self.frames(seconds)
        dx, dy = x - x0, y - y0
        dist = math.hypot(dx, dy)
        nx, ny = (-dy / dist, dx / dist) if dist else (0.0, 0.0)
        for i in range(1, n + 1):
            u = ease_cubic(i / n)
            bow = math.sin(math.pi * u) * arc * dist
            px, py = x0 + dx * u + nx * bow, y0 + dy * u + ny * bow

            async def move(px=px, py=py):
                self.x, self.y = px, py
                await self.page.mouse.move(px, py)

            await self.step(move)

    async def click(self, count: int = 1, hold: float = 0.1, gap: float = 0.12) -> None:
        """Press and release `count` times: each press held `hold` seconds, presses `gap`
        seconds apart. Marks "click" (or "double-click")."""
        for n in range(1, count + 1):
            async def press(n=n):
                self.down = True
                await self.page.mouse.down(click_count=n)

            async def release(n=n):
                self.down = False
                await self.page.mouse.up(click_count=n)

            await self.step(press)
            for _ in range(self.frames(hold) - 1):
                await self.step()
            await self.step(release)
            if n < count:
                for _ in range(self.frames(gap)):
                    await self.step()
        self.mark("double-click" if count == 2 else "click")

    async def type(self, text: str, cps: float = 13.0, jitter: float = 0.35) -> None:
        """Type at a human pace: a steady rhythm with a deterministic wobble."""
        for i, ch in enumerate(text):
            async def key(ch=ch):
                await self.page.keyboard.type(ch)

            await self.step(key)
            wobble = 1 + jitter * math.sin(i * 2.3 + 0.7) * math.cos(i * 0.9)
            pause = (1 / cps) * wobble + (0.12 if ch == " " and i % 3 == 0 else 0)
            for _ in range(self.frames(pause) - 1):
                await self.step()

    async def press(self, key: str) -> None:
        async def action():
            await self.page.keyboard.press(key)

        await self.step(action)

    async def center(self, selector: str) -> tuple[float, float]:
        box = await self.page.locator(selector).first.bounding_box()
        if box is None:
            raise RuntimeError(f"not visible: {selector}")
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
