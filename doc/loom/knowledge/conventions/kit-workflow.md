# Kit Workflow

> Team roles, ownership rules, briefs, workflow phases, editorial rules for both media

## Team roles and ownership

README "The team" and `CLAUDE-project.md` (installed as `<project>/CLAUDE.md`): one lead session talks to the human and owns, at the project root, `project.json`, `<project>/NOTES.md`, `<project>/HANDBOOK.md`, `<project>/claims.md`, `<project>/scenarios.md`, `<project>/BRAND.md`, `brand/`, `design.json` (through the brand skill) and, for the video, `narration/timeline.json`, `rates.json` and `<project>/COSTS.md`; for the post, `<project>/post/outline.md`, `<project>/post/draft.md` and `post/images.json`. Specialists are agent-team teammates with names. Capture roles are shared: one web capture teammate (owns `<project>/fixtures/web/product.py` and `captures/web/`) and one TUI capture teammate (owns `<project>/fixtures/tui/product.py` and `captures/tui/`) serve both media. Video roles add composer (`music/`), motion designer (`motion/scenes/`), b-roll and editor (`edit/`); the blog adds an optional writer who owns `<project>/post/draft.md` only while the lead has handed it over. Only the roles the chosen media need exist; narration, music, b-roll and (for a video) captures are each optional, so a video can be b-roll, motion graphics and narration or on-screen text with no product source, no capture roles and no `<project>/scenarios.md` (needed only when captures or motion scenes show the product's data). Pick the tier per job and escalate one tier only after a failed attempt, handing over the task, both attempts and their evidence.

## Rules that make the team work

1. One owner per file; import another agent's module, never modify it.
2. Files plus short messages: engines write outputs and a manifest; messages say what changed.
3. The records are the contract: `narration/timeline.json` is the video's only clock (absolute windows, never deltas); the post references an image only as `shot:<source>/<scenario>/<label>`; both media take claims from `<project>/claims.md` and fixture data from `<project>/scenarios.md`.
4. Human decisions go into `<project>/NOTES.md` before anyone is briefed and bind every agent.
5. The lead reviews every output (Reads each PNG and contact sheet) before the human sees anything and purges rejected elements from every agent's work.
6. Plans before production: the human approves the script (video) or `<project>/post/outline.md` and the scenarios first; previews before masters; a post is final after `postkit check` passes.
7. Messages cross; check whether the agent is running or idle and read file timestamps before re-sending.
8. Wait on files or explicit messages; a watcher that `pgrep`s another agent's command line can match itself.
9. Change only what was asked.
10. Hands off the product: no writes to its repository, no system installs, never `pip install` (use `uv`), no git inside the project unless the human wants it.
11. Visual work uses the `frontend-design:frontend-design` skill.
Engine files change only to fix a bug, and the fix is recorded in `<project>/NOTES.md` because a kit update overwrites them.

## Good briefs

A brief states the goal and audience, the agent's part of the HANDBOOK "Brand" section plus the human's references and what each means, what the agent owns and must not touch, exact deliverables (scenario and label names, boxes, marks, codecs), how to check its own work without eyes or ears, and a report format (paths, commands to rerun, known weaknesses).

## Workflow and kickoff

`guides/video.md` and `guides/blog.md` hold each medium's Phases 1-5; the shared part is Phase 0. Two skills split the kickoff. The kit-only `/install` (`.claude/skills/install/`, run in the kit folder) asks the project folder, the media (and the order for both) and for a video the frame rate (30 suggested), music and, with music, the piano (VSCO unless the human explicitly picks Salamander, CC BY); runs `install.sh --no-system` (skipped when `project.json` exists, so a rerun resumes), shows `system-deps.sh --dry-run --for X` and has the human run `system-deps.sh` in a second terminal, saves the choices with `./configure.sh --fps N --piano X` (a delegated choice is 30 fps and VSCO; a saved `project.json` value wins over any 60 fps in other instructions) and `media`, runs `./setup.sh --check --for X` then `./setup.sh --for X` until `0 MISSING`, and sees to the Gemini key. A first project session (no `<project>/NOTES.md`) runs the `begin` skill whatever the human says first: read what exists, confirm `media` in one line (or ask when unset), ask the video choices only when `fps` or `piano` is absent, check the machine once (`setup.sh --for X` only on MISSING or when a medium is added; `system-deps.sh` stays the human's), one shared interview then each medium's group, the Gemini key when narration, b-roll or the judge is wanted, the brand skill, then set or confirm `media` in `project.json`, write `<project>/NOTES.md`, `rates.json` when billed calls are planned and, when a medium is added, a reuse inventory. Later sessions read `<project>/NOTES.md`, `<project>/edit/ISSUES.md`, `narration/timeline.json`, `<project>/HANDBOOK.md` and `<project>/COSTS.md` if present, run `./setup.sh --check` once and resume. Every role reads `<project>/BRAND.md` and the HANDBOOK "Brand" section first. `./system-deps.sh` is for the human only. Phase 1 puts every claim into `<project>/claims.md`, verified only when the code shows it (the code wins over the PRD; the human decides the wording); with no product source each claim cites the human's material (PRD, docs page, URL, or a statement recorded in `<project>/NOTES.md`) and is verified only once the human confirms it, at the latest with the script. The post's Phase 5 ends when `postkit check` shows no ERROR; the video's with the QA checklist on every master.

## Editorial rules

README "Editorial rules". Record the human's own rules in `<project>/NOTES.md` as stated. Plain and accurate tone, no hype, no anthropomorphism; name things as the product's UI and help text do; never name a component after what it wraps; never claim a setting the product lacks; every claim verified against the code; no LLM-isms; alt text says what the image shows in the product's terms; code blocks name their language and use the fixture story's names; name a category, never other companies; one fixture story; decide the length with the human at kickoff; once the human says to stop asking, the lead decides and reports.
