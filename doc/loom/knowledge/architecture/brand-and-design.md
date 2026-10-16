# Brand And Design

> design.json schema and its loaders, tools/fonts.py, brand skill, check.py

## design.json schema and loaders

Loaders of `<project>/design.json`: `edit/editkit/design.py`, `motion/lib/design.py`, `fixtures/tui/src/tuicap/design.py`, `post/src/postkit/design.py` and the checker `claude-skills/brand/check.py`. Each package keeps its own copy (separate uv projects). Their `ROOT` is the project root.

Keys (all optional; the edit, motion, tuicap and the checker reject any other top-level, `fonts.*` or `logo.*` key with `unknown key <name>`):
- `fonts`: `regular`, `bold`, `italic`, `bold_italic`, `mono`, `weights`, `family`. A value ending `.ttf`, `.otf` or `.ttc` is a path under the project root; anything else is a family name. `family` fills the four text roles where unset.
- `colors`: `background`, `text`, `secondary`, `accent`, each `#rrggbb`.
- `logo`: `on_dark`, `on_light`, each an `.svg` or `.png` path.
- `grain`: a number >= 0, optional, read only by the edit (film grain strength); the blog ignores it.

Who reads what: motion and edit read fonts, colours and logo (edit adds grain); tuicap reads `colors.background`, `colors.text` and `fonts.mono`; postkit reads `colors.accent` and the bold font only, its frames use fixed colours. A family name needs an entry in `brand/fonts/resolved.json`, valid only while its `design_json_sha256` matches the current `design.json`; otherwise the loader tells the user to run `uv run tools/fonts.py`.

## tools/fonts.py

PEP 723 script run from the project root (`uv run tools/fonts.py [--check]`; fonttools). Never touches the network. Resolves every role naming a family: `wanted(fonts)` returns `{role: (family, weight, italic)}`; `Finder` indexes `brand/fonts/` (excluding `.local/`) then installed fonts (`fc-list`); `pick` chooses the closest face, using variable `wght` ranges; `materialize` makes static instances from variable fonts and extracts TTC faces (derived from installed fonts into `brand/fonts/.local/`, from `brand/fonts/` beside the source). `main` writes `brand/fonts/resolved.json` atomically (system fonts as absolute paths); `--check` writes nothing and exits 1 on a missing family. Callers: `setup.sh`, the loaders' error text, the brand skill and `check.py`.

## Brand skill (claude-skills/brand)

`SKILL.md` sets up and applies the brand: `<project>/BRAND.md` is the source of truth and `design.json` is generated, never hand-edited; never invent a brand value; never modify `brand/` (except `tools/fonts.py` outputs and open-licence font additions). Without `<project>/BRAND.md` it interviews and writes it from `BRAND.template.md`; with it, it writes `design.json`, runs `tools/fonts.py` when a family is named, runs `check.py`, writes the HANDBOOK "Brand" section with a block per role of each chosen medium, and reports gaps as numbered questions.

`check.py` (`uv run <project>/.claude/skills/brand/check.py [project-root]`): own copies of the key lists; `is_derived` skips `brand/fonts/resolved.json` and `brand/fonts/.local/*`; `schema_errors`, `check_font` (mono must be fixed-width), `check_logo` (SVG size, or PNG at least 2000 px wide), `check_families` (runs `tools/fonts.py --check`), `check_contrast` (WARN), `check_fresh` (WARN when `<project>/BRAND.md` or a non-derived `brand/` file is newer than `design.json`). Prints `ok`, `WARN`, `MISSING` lines and a summary; exit 1 only on `MISSING`.
