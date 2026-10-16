"""A still the project's SHOTS function asks for: a label, a time and named cell boxes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Still:
    label: str
    t: float  # seconds into the recording; events with time <= t are on screen
    boxes: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)  # name -> (row0, col0, row1, col1), half-open
