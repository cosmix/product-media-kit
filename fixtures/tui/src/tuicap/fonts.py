"""Fallback fonts for the glyphs the terminal font lacks: symbols, maths and colour emoji.

macOS uses the fixed system files. Linux resolves each family through fontconfig, so the files
may sit wherever the distribution puts them. A family that is not installed, or a machine
without fc-list, simply contributes no font."""

from __future__ import annotations

import subprocess
import sys
from functools import cache

MACOS = sys.platform == "darwin"
MACOS_FALLBACKS = ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Apple Symbols.ttf")
MACOS_EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"
LINUX_FALLBACK_FAMILIES = ("DejaVu Sans Mono", "Noto Sans Symbols2", "Noto Sans Symbols", "Noto Sans Math")
LINUX_EMOJI_FAMILY = "Noto Color Emoji"
FC_TIMEOUT = 10  # seconds; a stuck fontconfig cache rebuild must not hang a capture
REGULAR_STYLES = ("Regular", "Book")  # DejaVu calls its regular style Book


def family_file(family: str) -> str | None:
    """The file of a family's regular style through fontconfig; None when the family is not
    installed, fc-list is missing or it times out."""
    try:
        listed = subprocess.run(["fc-list", "--format", "%{file}|%{style}\n", family],
                                check=False, capture_output=True, text=True,
                                timeout=FC_TIMEOUT).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    # A family lists every weight and slant; the style field's first name tells them apart.
    rows = [line.rpartition("|") for line in listed.splitlines()]
    files = [(path, style.split(",")[0]) for path, _, style in rows if path]
    files.sort(key=lambda item: item[1] not in REGULAR_STYLES)  # stable: listing order among equals
    return files[0][0] if files else None


@cache
def fallback_fonts() -> tuple[str, ...]:
    """Fallback font files in order of preference."""
    if MACOS:
        return MACOS_FALLBACKS
    return tuple(path for path in map(family_file, LINUX_FALLBACK_FAMILIES) if path)


@cache
def emoji_font() -> str | None:
    """The colour emoji font file, None when there is none."""
    return MACOS_EMOJI if MACOS else family_file(LINUX_EMOJI_FAMILY)
