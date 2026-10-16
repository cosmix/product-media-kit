# Concerns & Technical Debt

> Technical debt, warnings, issues, and improvements needed.
> A summary of the current tree: correct a section in place with `replace-section`.

## Open reviewer suggestions and known gaps

Unimplemented suggestions (postkit, webcap, kit scripts, tests) are recorded with their file and the change they ask for in [concerns/open-suggestions](concerns/open-suggestions.md).

## Known gaps

- `music/render.py` cannot be verified on CPUs where the `pedalboard` wheel raises SIGILL on import (it needs instruction-set extensions some CPUs lack); the soundtrack render and its tests there are unproven until run on another machine.
- postkit has no macOS fallback font for callout numbers: `design._fc_match` uses `fc-match`, then Pillow's built-in font. `doc/mac_port_testing.md` lists the postkit check.
- A clip captured with `--for video` shows as a still in a post (its manifest `file` is the poster PNG and no GIF exists) until it is recaptured with `--for both`.

## Unverified claims

- `system-deps.sh` names the Fedora package `google-noto-sans-symbols-2-fonts`; the real name may be `google-noto-sans-symbols2-fonts`. A wrong name aborts the whole dnf transaction, and README.md repeats it. Check with `dnf provides '*/NotoSansSymbols2-Regular.ttf'` on Fedora. The `ffmpeg-free` choice rests on stock Fedora shipping it, and `ffmpeg` only in RPM Fusion.
- The macOS code paths (`edit/editkit/hw.py`, `motion/lib/gfx.py`, fallback fonts) have not run on a Mac; `doc/mac_port_testing.md` is the checklist.
- `shellcheck` is not installed here, so the shell scripts were never linted.

## Proposed loom checks

A `loom plan verify` check that rejects a contract whose `cwd` is the repository root while the contract file sits under a directory with its own `pyproject.toml`, since that contract runs on the system python (see [mistakes/loom-gates](mistakes/loom-gates.md)).
