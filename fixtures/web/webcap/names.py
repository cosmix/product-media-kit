"""Scenario and label names: they become folder and file names, so only a safe slug passes."""

from __future__ import annotations

import re

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LABEL = "clip"  # a scenario's clip files are <scenario>/clip.*


def check_name(kind: str, value: str) -> str:
    """`value` when it is a slug (lower-case words joined by single hyphens); else ValueError."""
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise ValueError(f"{kind} {value!r} must match {NAME_RE.pattern}")
    return value


def check_label(scenario: str, label: str) -> str:
    """`label` when it is a slug other than LABEL, the name reserved for the scenario's clip."""
    check_name("label", label)
    if label == LABEL:
        raise ValueError(f"{scenario}/{LABEL}: the label {LABEL!r} is reserved for the "
                         f"scenario's clip; name the still something else")
    return label
