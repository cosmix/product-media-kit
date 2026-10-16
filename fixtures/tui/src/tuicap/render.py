"""Replay a recorded byte stream through pyte and render stills and short clips with skia."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pyte
import skia
from wcwidth import wcwidth

from . import design, palette
from .encode import PROFILES, encoder, fps_for, gif_from_webm, uses_mp4, webm_from_mp4
from .fonts import emoji_font, fallback_fonts
from .glyphs import Procedural

CELL_W = 28  # px at 2x; the font size makes one advance fill a cell
CELL_H = 58
PAD = 48  # 24 px at 1x


class VtScreen(pyte.Screen):
    """pyte screen with the pieces a tmux client needs: SU/SD scrolling and the
    private DSR query (CSI ? 6 n), neither of which pyte 0.8 handles."""

    def report_device_status(self, *args, **kwargs) -> None:
        kwargs.pop("private", None)
        super().report_device_status(*args, **kwargs)

    def _scroll_region(self, count: int | None, insert: bool, **_: object) -> None:
        top = self.margins.top if self.margins else 0
        x, y = self.cursor.x, self.cursor.y
        self.cursor.y = top
        (self.insert_lines if insert else self.delete_lines)(count or 1)
        self.cursor.x, self.cursor.y = x, y

    def scroll_up(self, count: int | None = None, **kwargs: object) -> None:
        self._scroll_region(count, insert=False)

    def scroll_down(self, count: int | None = None, **kwargs: object) -> None:
        self._scroll_region(count, insert=True)


class VtStream(pyte.ByteStream):
    csi: ClassVar[dict[str, str]] = {**pyte.ByteStream.csi, "S": "scroll_up", "T": "scroll_down"}


@dataclass
class Geometry:
    cols: int
    rows: int

    @property
    def size(self) -> tuple[int, int]:
        w = self.cols * CELL_W + 2 * PAD
        h = self.rows * CELL_H + 2 * PAD
        return w + (w % 2), h + (h % 2)


class Fonts:
    def __init__(self) -> None:
        mono = design.mono()
        typeface = skia.Typeface.MakeFromFile(mono, 0)
        if typeface is None:
            raise RuntimeError(f"skia cannot read the terminal font {mono}")
        size = CELL_W / (skia.Font(typeface, 100).measureText("M") / 100)

        def load(path: str | Path, bold: bool = False, italic: bool = False) -> skia.Font:
            font = skia.Font(skia.Typeface.MakeFromFile(str(path), 0), size)
            font.setEdging(skia.Font.Edging.kAntiAlias)
            font.setSubpixel(True)
            font.setHinting(skia.FontHinting.kNone)
            font.setLinearMetrics(True)
            font.setEmbolden(bold)  # one font file: bold and italic are synthesised
            font.setSkewX(-0.2 if italic else 0.0)
            return font

        self.variants = {(b, i): load(mono, b, i) for b in (False, True) for i in (False, True)}
        self.fallbacks = [load(p) for p in fallback_fonts() if Path(p).is_file()]
        emoji = emoji_font()
        self.emoji = load(emoji) if emoji and Path(emoji).is_file() else None
        metrics = self.variants[(False, False)].getMetrics()
        self.baseline = (CELL_H - (metrics.fDescent - metrics.fAscent)) / 2 - metrics.fAscent
        self._choice: dict[tuple[str, bool, bool], tuple[skia.Font, bool]] = {}

    def pick(self, char: str, bold: bool, italic: bool) -> tuple[skia.Font, bool]:
        """(font, is_primary) for a character, walking the fallback chain."""
        key = (char, bold, italic)
        if key not in self._choice:
            primary = self.variants[(bold, italic)]
            cp = ord(char)
            if primary.unicharToGlyph(cp):
                self._choice[key] = (primary, True)
            else:
                chosen = next((f for f in self.fallbacks if f.unicharToGlyph(cp)), None)
                if chosen is None and self.emoji is not None and self.emoji.unicharToGlyph(cp):
                    chosen = self.emoji
                self._choice[key] = (chosen or primary, False)
        return self._choice[key]


class TerminalRenderer:
    def __init__(self, geometry: Geometry):
        self.geo = geometry
        self.width, self.height = geometry.size
        self.bg, self.fg = palette.bg(), palette.fg()  # design.json is read here, not at import
        self.fonts = Fonts()
        self.proc = Procedural(CELL_W, CELL_H)
        self.surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(self.width, self.height, skia.kRGBA_8888_ColorType,
                                skia.kPremul_AlphaType))
        self.base: skia.Image | None = None
        self._paints: dict[tuple[str, float], skia.Paint] = {}

    def paint(self, hexval: str, alpha: float = 1.0) -> skia.Paint:
        key = (hexval, alpha)
        if key not in self._paints:
            r, g, b = palette.rgb(hexval)
            p = skia.Paint(AntiAlias=True, Color=skia.Color(r, g, b, round(alpha * 255)))
            self._paints[key] = p
        return self._paints[key]

    def cell_origin(self, x: int, y: int) -> tuple[float, float]:
        return PAD + x * CELL_W, PAD + y * CELL_H

    def colors(self, char: pyte.screens.Char) -> tuple[str, str]:
        fg = palette.resolve(char.fg, self.fg)
        bg = palette.resolve(char.bg, self.bg)
        if char.reverse:
            fg, bg = bg, fg
        return fg, bg

    def draw_glyph(self, canvas: skia.Canvas, char: pyte.screens.Char, x: int, y: int,
                   fg: str, alpha: float = 1.0) -> None:
        data = char.data
        if not data or data == " ":
            return
        ox, oy = self.cell_origin(x, y)
        paint = self.paint(fg, alpha)
        glyph = data[0]
        if len(data) == 1 and self.proc.claims(glyph):
            self.proc.draw(canvas, glyph, ox, oy, paint)
            return
        span = 2 if wcwidth(glyph) == 2 else 1
        font, primary = self.fonts.pick(glyph, char.bold, char.italics)
        if primary:
            canvas.drawString(data, ox, oy + self.fonts.baseline, font, paint)
        else:
            self._draw_fallback(canvas, data, font, ox, oy, span * CELL_W, paint)
        if char.underscore:
            canvas.drawRect(skia.Rect.MakeXYWH(ox, oy + CELL_H - 8, CELL_W * span, 3), paint)
        if char.strikethrough:
            canvas.drawRect(skia.Rect.MakeXYWH(ox, oy + CELL_H / 2, CELL_W * span, 3), paint)

    def _draw_fallback(self, canvas, data, font, ox, oy, span_w, paint) -> None:
        bounds = skia.Rect()
        advance = font.measureText(data, bounds=bounds)
        scale = min(1.0, span_w * 0.96 / advance) if advance else 1.0
        # Symbol fonts draw some marks (e.g. U+27F3) far smaller than the terminal font's.
        target = font.getSize() * 0.62
        if 0 < bounds.height() < target * 0.85 and bounds.width() > 0:
            scale = min(target / bounds.height(), span_w * 0.9 / bounds.width())
        if font is self.fonts.emoji:
            scale = min(span_w * 0.92 / advance, CELL_H * 0.8 / font.getSize()) if advance else 1.0
        canvas.save()
        cx = ox + span_w / 2
        baseline = oy + self.fonts.baseline
        canvas.translate(cx, baseline)
        canvas.scale(scale, scale)
        canvas.drawString(data, -advance / 2, 0 if font is not self.fonts.emoji else -2, font, paint)
        canvas.restore()

    def render_base(self, buffer: list[list[pyte.screens.Char]]) -> None:
        canvas = self.surface.getCanvas()
        canvas.clear(skia.Color(*palette.rgb(self.bg)))
        for y, row in enumerate(buffer):
            x = 0
            while x < len(row):
                _, bg = self.colors(row[x])
                if bg == self.bg:
                    x += 1
                    continue
                start = x
                while x < len(row) and self.colors(row[x])[1] == bg:
                    x += 1
                ox, oy = self.cell_origin(start, y)
                canvas.drawRect(skia.Rect.MakeXYWH(ox, oy, (x - start) * CELL_W, CELL_H),
                                self.paint(bg))
        for y, row in enumerate(buffer):
            for x, char in enumerate(row):
                fg, _ = self.colors(char)
                self.draw_glyph(canvas, char, x, y, fg)
        self.base = self.surface.makeImageSnapshot()

    def draw_cursor(self, buffer, cursor: tuple[int, int], alpha: float) -> None:
        x, y = cursor
        if alpha > 0.01 and 0 <= x < self.geo.cols and 0 <= y < self.geo.rows:
            canvas = self.surface.getCanvas()
            char = buffer[y][x]
            _, bg = self.colors(char)
            ox, oy = self.cell_origin(x, y)
            canvas.drawRect(skia.Rect.MakeXYWH(ox, oy, CELL_W, CELL_H),
                            self.paint(self.fg, alpha * 0.92))
            self.draw_glyph(canvas, char, x, y, bg, alpha)

    def frame(self, buffer, cursor: tuple[int, int] | None, cursor_alpha: float) -> bytes:
        self.surface.getCanvas().drawImage(self.base, 0, 0)
        if cursor is not None:
            self.draw_cursor(buffer, cursor, cursor_alpha)
        return self.surface.makeImageSnapshot().tobytes()

    def still(self, path: Path) -> None:
        self.surface.makeImageSnapshot().save(str(path), skia.kPNG)


def cursor_alpha(since_input: float) -> float:
    """Solid while typing, then a soft blink: 0.55 s on, eased 0.12 s fades."""
    if since_input < 0.6:
        return 1.0
    phase = (since_input - 0.6) % 1.1
    def ease(u: float) -> float:
        return u * u * (3 - 2 * u)
    if phase < 0.55:
        return 1.0
    if phase < 0.67:
        return 1.0 - ease((phase - 0.55) / 0.12)
    if phase < 0.98:
        return 0.0
    return ease((phase - 0.98) / 0.12)


@dataclass
class Recording:
    """Output bytes with times (s) relative to video start; negative = pre-roll."""

    cols: int
    rows: int
    events: list[tuple[float, bytes]]
    duration: float
    inputs: list[float]  # times of keystrokes, for the cursor blink phase
    show_cursor: bool = True


def _snapshot(screen: VtScreen, rec: Recording) -> list[list[pyte.screens.Char]]:
    """A dense copy of pyte's sparse per-row buffer."""
    return [[screen.buffer[y][x] for x in range(rec.cols)] for y in range(rec.rows)]


def _atomic_png(renderer: TerminalRenderer, png: Path) -> None:
    png.parent.mkdir(parents=True, exist_ok=True)
    tmp = png.with_name(f"{png.stem}.tmp.png")
    renderer.still(tmp)
    tmp.replace(png)


def render_still(rec: Recording, png: Path, t: float) -> tuple[int, int]:
    """Render the terminal as it looks at time t to a PNG; returns (width, height)."""
    geo = Geometry(rec.cols, rec.rows)
    renderer = TerminalRenderer(geo)
    screen = VtScreen(rec.cols, rec.rows)
    stream = VtStream(screen)
    for when, data in sorted(rec.events, key=lambda e: e[0]):
        if when > t:
            break
        stream.feed(data)
    buffer = _snapshot(screen, rec)
    renderer.render_base(buffer)
    if rec.show_cursor and not screen.cursor.hidden:
        renderer.draw_cursor(buffer, (screen.cursor.x, screen.cursor.y), 1.0)
    _atomic_png(renderer, png)
    return geo.size


def cell_box(geometry: Geometry, row0: int, col0: int, row1: int, col1: int) -> list[int]:
    """[x, y, w, h] image pixels of the half-open cell range rows row0..row1, cols col0..col1."""
    if not (0 <= row0 < row1 <= geometry.rows and 0 <= col0 < col1 <= geometry.cols):
        raise ValueError(f"cell range rows {row0}..{row1}, cols {col0}..{col1} is empty or outside "
                         f"the {geometry.cols}x{geometry.rows} grid")
    return [PAD + col0 * CELL_W, PAD + row0 * CELL_H, (col1 - col0) * CELL_W, (row1 - row0) * CELL_H]




def _write_frames(rec: Recording, renderer: TerminalRenderer, sink, frames: int, fps: int) -> None:
    """Replay the recording and write `frames` raw frames to `sink`, re-rendering only on change."""
    screen = VtScreen(rec.cols, rec.rows)
    stream = VtStream(screen)
    events = sorted(rec.events, key=lambda e: e[0])
    idx, last, last_key, buffer = 0, b"", None, None
    for n in range(frames):
        t = n / fps
        changed = buffer is None
        while idx < len(events) and events[idx][0] <= t:
            stream.feed(events[idx][1])
            idx += 1
            changed = True
        if changed:
            buffer = _snapshot(screen, rec)
            renderer.render_base(buffer)
        visible = rec.show_cursor and not screen.cursor.hidden
        cursor = (screen.cursor.x, screen.cursor.y) if visible else None
        past = [i for i in rec.inputs if i <= t]
        alpha = cursor_alpha(t - past[-1] if past else t) if visible else 0.0
        key = (cursor, round(alpha, 3))
        if changed or key != last_key:
            last = renderer.frame(buffer, cursor, alpha)
        last_key = key
        sink.write(last)


def _encode(rec: Recording, renderer: TerminalRenderer, tmp: dict[str, Path], profile: str,
            draft: bool, frames: int, fps: int) -> None:
    """Write the profile's files under their temporary names (keys are the extensions)."""
    proc = encoder(tmp["mp4" if uses_mp4(profile) else "webm"], *renderer.geo.size, profile, fps, draft)
    try:
        _write_frames(rec, renderer, proc.stdin, frames, fps)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed while encoding the clip")
    except BaseException:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        raise
    if profile == "both":
        webm_from_mp4(tmp["mp4"], tmp["webm"], fps)
    if profile != "video":
        gif_from_webm(tmp["webm"], tmp["gif"])


def render_recording(rec: Recording, out_dir: Path, label: str, profile: str = "blog",
                     draft: bool = False) -> dict:
    """Write the profile's files for <label> into out_dir and return the clip manifest entry
    fields (paths relative to out_dir). blog: .webm (30 fps), .gif, .png poster (the last frame).
    video: .mp4 (project.json fps, default 30) and .png; `file` is then the poster. both: the mp4, plus the WebM
    and GIF derived from it. `draft` encodes the mp4 fast at crf 23. A failure leaves no partial files."""
    if profile not in PROFILES:
        raise ValueError(f"profile {profile!r}: expected one of {', '.join(PROFILES)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    geo = Geometry(rec.cols, rec.rows)
    renderer = TerminalRenderer(geo)
    exts = {"video": ("mp4",), "blog": ("webm", "gif"), "both": ("mp4", "webm", "gif")}[profile]
    tmp = {ext: out_dir / f"{label}.tmp.{ext}" for ext in exts}
    fps = fps_for(profile)
    frames = max(1, round(rec.duration * fps))
    try:
        _encode(rec, renderer, tmp, profile, draft, frames, fps)
        for ext, path in tmp.items():
            path.replace(out_dir / f"{label}.{ext}")
    except BaseException:
        for path in tmp.values():
            path.unlink(missing_ok=True)
        raise
    _atomic_png(renderer, out_dir / f"{label}.png")
    width, height = geo.size
    entry = {"kind": "clip", "file": f"{label}.gif" if "gif" in exts else f"{label}.png",
             "poster": f"{label}.png", "width": width, "height": height, "scale": 2.0,
             "duration": round(frames / fps, 3), "boxes": {}}
    if "webm" in exts:
        entry["webm"] = f"{label}.webm"
    if "mp4" in exts:
        entry.update({"video": f"{label}.mp4", "fps": fps, "grid": f"{rec.cols}x{rec.rows}",
                      "cell_px": [CELL_W, CELL_H], "padding_px": PAD})
    return entry
