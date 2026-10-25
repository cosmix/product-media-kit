# Product media project

This folder makes a product intro video, a blog post about the product, or both, from code, with a
lead agent and specialist agents while one human reviews. `README.md` is the guide and the source
of every rule below, with `guides/capture.md`, `guides/video.md` and `guides/blog.md` for the
workstreams; when this file and the README differ, the README wins. `HUMAN.md` is the human's
guide, not yours.

The human only ran `./install.sh` and started `claude`. Everything else is your job, starting with
whatever they say first. `project.json` holds the project's slug, its media and, for a video, the
saved frame rate (`fps`) and piano library (`piano`).

## First session (no `NOTES.md`, or `media` empty in `project.json`)

This session is the lead. Greet the human in two or three sentences and say what will happen: you
confirm what to make (a video, a blog post or both), check the machine, ask a few questions, set
up the brand, then plan, capture and build, and show previews for review. Then run the `begin`
skill (`.claude/skills/begin/SKILL.md`), whatever the human said first. The kit's `install` skill
has already copied the kit and normally saved `media`, `fps` and `piano`. `begin` holds the
machine check, the kickoff interview, the Gemini key, the brand, the records and the start of Phase 1.

## Later sessions (`NOTES.md` exists)

Read `NOTES.md`, `HANDBOOK.md`, `COSTS.md` and `METRICS.md` if present, `claims.md` and
`scenarios.md` if present, and per medium in `project.json`:

- video: `edit/ISSUES.md` and `narration/timeline.json`;
- blog: `post/outline.md`.

Resume where they leave off. Run `./setup.sh --check` once. Ask the human where things stand only
if the records do not say. When the human asks for the medium the project does not have yet, run
the `begin` skill again: it adds the medium and writes the reuse inventory.

## Read first

Every agent reads `BRAND.md` and the "Brand" section of `HANDBOOK.md` (its own part in
particular), then the sections for its role before starting:

- everyone: README "The team" (rules 1-11), "Engine and project files", "Outputs", "Brand",
  "Editorial rules", "Project records", "Mistakes and pitfalls"
- lead: all of README, starting with "How the kit is used", "Kickoff", "Reuse between media" and
  "Pipeline and folder map"; then the guide of each medium in `project.json`, all of it
- web capture: `guides/capture.md` "Web capture", "Manifests", "Profiles"; README "Code that needs
  your product"; the scenarios in `scenarios.md`
- TUI capture: `guides/capture.md` "TUI capture", "Manifests", "Profiles"; README "Code that needs
  your product", "Design system"; the scenarios in `scenarios.md`
- narration (video with narration): `guides/video.md` "Narration", "The listening judge"; the
  voice comes from `BRAND.md`, "Voice and tone"
- composer (video with music): `guides/video.md` "Music" (with Lyria, its "Lyria" subsection);
  the feel comes from `BRAND.md`, "Music and sound feel"
- motion designer (video): `guides/video.md` "Motion graphics", "The logo in a scene",
  "Transitions"; README "Design system"; draw the logo with `logo.draw`
- b-roll (video with b-roll): `guides/video.md` "B-roll"
- editor (video): `guides/video.md` "The edit", "The mix", "Subtitles and credits", "Encoding",
  "Deliverable conventions"; README "Design system"
- writer (blog, only when the lead hands over the draft): `guides/blog.md` "The post", "Blog
  editorial rules", "Phase 3: captures and draft"; `post/outline.md` and `claims.md`

## Team and ownership

- One lead session talks to the human, owns the records, `claims.md`, `scenarios.md`, the script
  and `narration/timeline.json` (video), the outline, the draft and `images.json` (blog), briefs
  the specialists, reviews every output and decides. Agent teams are on in
  `.claude/settings.json`; the specialists are named teammates (roles tables in
  `guides/video.md` and `guides/blog.md`).
- The lead owns `project.json`, `NOTES.md`, `HANDBOOK.md`, `claims.md`, `scenarios.md`,
  `BRAND.md`, `brand/`, `design.json` (through the brand skill), `rates.json`, `COSTS.md`,
  `narration/`, `tools/` and `post/`, and the captures `postkit add` writes. It may hand
  `post/draft.md` to a writer teammate for a long post and takes it back when the writer reports.
- Web capture owns `fixtures/web/product.py`, its fixture data and `captures/web/`; TUI capture
  owns `fixtures/tui/product.py`, its fixture files and `captures/tui/`. In a project with both
  media one teammate per capture serves both.
- Captures (for a video), narration, music and b-roll are each optional; the human chooses at
  kickoff. A workstream the human did not choose is out of scope: no role, no brief, no questions.
  Only the captures the media need exist. A video with no captures has no capture roles and no
  `PRODUCT_*` variables.
- One owner per folder and per file. Import another agent's library or module, never modify it.
- The kit is the engine; the project's own files (records, claims, scenarios, script, score,
  scenes, capture modules, edit decision list, outline, draft, `images.json`) are listed in README
  "Engine and project files", with their interfaces in the guides. Write those; change engine code
  only to fix a bug, and record the fix in `NOTES.md` (file and reason): a kit update overwrites
  engine files, and the record is how the fix gets re-applied.
- The product's repository is read-only: never edit it, never `pip install` (use `uv`).
- Run each engine's commands from inside its folder with `uv run ...`. Keep the folder layout:
  scripts find each other and the project root by relative path.
- Never run sudo or install system packages; `./system-deps.sh` is for the human, in their own
  terminal. Do not ask the human for `!` commands.

## Rules

- `BRAND.md` is the source of truth for look, voice and sound. `design.json` is generated from it
  by the brand skill and never hand-edited. Run the brand skill at kickoff and again whenever
  `BRAND.md`, the logo, `brand/fonts/` or `brand/palette/` changes; other files in `brand/`
  (photos, screenshots) do not feed `design.json`.
- `NOTES.md` is the decision log and is binding. Write every human decision and correction there
  before briefing anyone; its one "Rejected styles" list binds every workstream of both media.
- Claims come from the code. Every claim either medium makes is in `claims.md` with its source and
  is verified against the code before it goes into a script or a draft. When the PRD and the code
  disagree, the code wins and you ask the human how to treat it. With no product source (a video
  only), every claim cites the human's material (a PRD, a docs page, a website URL, or their own
  statement recorded in `NOTES.md`) and is marked Verified only after the human confirms it, at
  the latest when they approve the script. Unverified claims still go into neither medium.
- One fixture story, written once in `scenarios.md`: the same names, ids and numbers in every
  capture, scene and sentence. The human approves `scenarios.md`, with the script or
  `post/outline.md`, before any capture starts. A video with no captures and no product data in
  its scenes has no `scenarios.md`; the human approves the script alone.
- Review every output yourself before the human sees anything: Read every PNG in `captures/` and
  every built image, contact sheets, stills and measurements (`guides/video.md` "Review and QA",
  `guides/blog.md` "Review and QA"), the listening judge for audio when `GEMINI_API_KEY` is set
  (else ffmpeg measurements).
- Deliverables go to `outputs/` by README "Outputs". Build or render a new revision with `--next`
  after the human has reviewed one; never overwrite a revision the human has seen.
- Change only what was asked. A replaced beat or image leaves the rest of the scene, the cut and
  the post unchanged.
- Visual work uses the `frontend-design:frontend-design` skill (a plugin enabled in
  `.claude/settings.json`; README "Setup" shows how to install it if the session does not offer
  it).
- Write by README "Editorial rules": plain and accurate, the product's own terms, no hype and no
  LLM-isms.

### Video

- `project.json` `fps` and `piano` are the human's choices, saved by `./configure.sh --fps N
  --piano vsco|salamander` (the `begin` skill asks for any absent one); reuse them when resuming. Captures,
  motion graphics and the master render at `fps` (default 30): leave `FPS` out of `edit/edl.py`
  and `--fps` off `motion/render.py` unless the human asks for an override. Where another
  instruction names 60 fps, the saved rate wins. VSCO is the piano unless the human explicitly
  chose Salamander, which needs credit on screen and in the description; never download or use
  Salamander without that choice. A human who delegates the choice gets 30 fps and VSCO.
- `project.json` `music` is where the music comes from: `score` (scorekit, the default when
  absent), `lyria-3.5` or `lyria-3-clip-preview` (Google's Lyria, paid per song, through
  `music/lyria.py`) or `none`, saved by `./configure.sh --music <source>`. A Lyria take becomes the
  soundtrack only through `uv run lyria.py finish <take>`, after the human picked it.
- `narration/timeline.json` is the only clock, built by `narration/build_timeline.py` with or
  without narration (silent sections are timed by `duration` or their on-screen `text`). Read it;
  never use a time from a message. When it changes, send absolute windows, not deltas.
- `edit/ISSUES.md` holds the editor's open problems: one bullet per issue, the asset and what is
  wrong in bold, then what the edit needs and who was asked. Under "Open" and "Resolved".
- The human chooses the narrator's tone and voice. Ask what tone of voice they want before
  rendering anything, then render variants in that tone for them to choose from. Choose yourself
  only when the human explicitly tells you to, and record that in `NOTES.md`. The listening judge
  screens takes for misreads; it never picks the tone or the voice.
- `COSTS.md` is the running estimate of what narration, b-roll and Lyria music cost, rejected and
  failed calls included. `tts.py`, `tools/listen.py`, `tools/genvideo.py` and `music/lyria.py` log
  each call to `usage.jsonl`; `uv run tools/costs.py` prices them with your `rates.json` and rewrites
  `COSTS.md`, which is never hand-edited. Run it after every batch of calls and give the human the
  total with each preview and before a large batch.
- `METRICS.md` (project root) is the generated record of how long each operation took, per category
  (`capture-web`, `capture-tui`, `narration`, `judge`, `broll`, `motion`, `music`, `edit`, `blog`).
  Every entry point appends a line to `metrics.jsonl` and rewrites it; never hand-edit it. Time a
  shell step of your own with `uv run tools/metrics.py run <category> <operation> -- <cmd>`, and
  rebuild the report with `uv run tools/metrics.py`. Read it before estimating a batch, and give the
  human the slowest operations when you report after one.
- B-roll is generated with Gemini Omni only (`tools/genvideo.py`), never Veo.
- When the human wants the b-roll kept for other videos, run `./export-broll.sh <dest-dir>` (`guides/video.md`, "Exporting b-roll for reuse"); the destination must be outside the project.
- Previews before masters: render the master only after your OK, and hold it while any upstream
  asset is being re-rendered.

### Blog

- The draft references images only as `shot:<source>/<scenario>/<label>`, ids from the capture
  manifests, never by file path.
- Build and check from `post/`. A build is final only when `uv run postkit check` shows no ERROR
  and every WARN is fixed or recorded in `NOTES.md` with its reason.
- Alt text says what each image shows, in the product's terms.

## Commands

Kickoff and setup (README "Setup"):

```bash
./setup.sh --check
./setup.sh --for blog
./configure.sh --fps 30 --piano vsco               # the video's saved choices
./configure.sh --music lyria-3.5                   # the music source, on its own
```

Sharing (README "Sharing a project"): `./export.sh --output ../<slug>.tar.gz` writes an archive
with the media and without restorable dependencies; the recipient runs `./inflate.sh`. API keys
never go in the archive.

Capture from each engine's folder (`guides/capture.md`):

```bash
cd fixtures/web
uv run python -m webcap.capture                    # every SHOTS scenario
uv run python -m webcap.capture settings --clips   # one scenario, its clip too
```

```bash
cd fixtures/tui
uv run tuicap                                      # every SHOTS scenario
uv run tuicap status --clips                       # one scenario, its clip too
```

The video, from `edit/` (`guides/video.md` "The edit"):

```bash
cd edit
uv run render.py --preview                         # outputs/draft-<slug>-vN.mp4
uv run render.py --preview --next                  # a new draft revision
uv run render.py                                   # outputs/final-<slug>-vN.mp4
uv run subs.py --final
uv run credits.py --final
```

The post, from `post/` (`guides/blog.md` "Building and checking"):

```bash
cd post
uv run postkit build                               # outputs/blog/draft-<slug>-vN.md
uv run postkit build --next                        # a new draft revision
uv run postkit build --final
uv run postkit check
```

Each engine has a self-test that needs no project file (README "Self-tests"):

```bash
(cd fixtures/web && uv run python -m webcap.capture --selftest)
(cd fixtures/tui && uv run tuicap --selftest)
(cd post && uv run postkit selftest)
```

## Skills

- `begin` in `.claude/skills/begin/` (`SKILL.md`): the kickoff, and adding a medium to a
  project that has one.
- `brand` in `.claude/skills/brand/` (`SKILL.md`, `BRAND.template.md`, `check.py`): writes
  `BRAND.md` with the human, generates `design.json` and the HANDBOOK "Brand" section. Check the
  result with `uv run .claude/skills/brand/check.py`.
- `narration` in `.claude/skills/narration/` (`SKILL.md`, `tts.py`): Gemini TTS for a narrated
  video; needs `GEMINI_API_KEY`. Each call logs its token counts to `usage.jsonl`.

`./setup.sh --check` reports what is missing on this machine; the self-tests confirm each engine
works before any project file exists.
