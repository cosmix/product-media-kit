# Open Suggestions

> Unimplemented reviewer suggestions and known gaps per package

## postkit

- Containment of the bold font: `design._bold_font` joins `root / fonts.bold` and `_resolved_bold` joins `root / <resolved.json value>` without containment (absolute or `..` accepted), although the README documents `fonts.bold` as relative to the project root. A fix must keep absolute paths working: `tools/fonts.py` writes absolute paths into `resolved.json` for system fonts, so `is_relative_to(root)` would drop every installed bold font.
- `common.body_matches` skips fenced blocks but not inline code spans, so prose showing `![alt](shot:...)` in backticks is rewritten or reported as an unknown shot.
- `images._callouts` draws the digits in white on `design.accent`; an accent such as `#ffffff` makes them invisible. Choose the digit colour from the accent's luminance.
- `Design.text`, `background` and `secondary` are validated and never read by postkit (the README says "validated only").
- Test gaps: the manifest validation branches (bad boxes, wrong source, absolute file, webm escape, scale <= 0) and the tui default frame `none`.

## webcap

- `Shooter.shot`: `full_page=True` is silently ignored when `selector` is given; reject the combination or document it.
- A `capture_shots` failure part-way through a scenario leaves overwritten PNGs while the manifest still lists the old dimensions, so postkit would apply stale pixel boxes. Drop the scenario's entries or update the manifest per shot.
- `world.Clock.inverse` has no caller outside its definition.

## Kit scripts and guides

- `setup.sh` `KIT_SKILLS` duplicates install.sh's skill discovery; a new skill added to `claude-skills/` would not be checked in installed projects until the list is updated.
- `claude-skills/brand/check.py` and `setup.sh` exclude `resolved.json` and `brand/fonts/.local/*` from the freshness check, but not the static instances `tools/fonts.py` derives from a variable font into `brand/fonts/<Family>/`, so the first skill run can print one spurious `design.json older than` WARN; rerunning clears it.
- `tests/smoke.sh`: the comment "sh has no pipefail" is out of date (POSIX 2024 added it; "portable sh has no pipefail" stays true); the prune list is hard-coded and can drift from what `install.sh` skips (harmless: extra copied files do not affect the install). Keep the inner `[ -f ] || [ -L ]` check: `find -type` misreports sandbox placeholder dotfiles.
