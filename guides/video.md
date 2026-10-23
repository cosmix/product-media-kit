# Video guide

Everything specific to the product intro video: the workflow from the timeline to the master, and
each workstream's techniques. `README.md` holds what both media share (setup, the team's rules,
the kickoff, outputs, brand, design system, editorial rules, project records). Web and TUI capture
live in `guides/capture.md`.

## Contents

- [What the video is](#what-the-video-is)
- [The stack](#the-stack)
- [CPU-only machines](#cpu-only-machines)
- [Roles for a video](#roles-for-a-video)
- [The workflow](#the-workflow)
  - [Phase 1: the timeline first](#phase-1-the-timeline-first)
  - [Phase 2: the shared spec and the briefs](#phase-2-the-shared-spec-and-the-briefs)
  - [Phase 3: production](#phase-3-production)
  - [Phase 4: the review loop](#phase-4-the-review-loop)
  - [Phase 5: finishing](#phase-5-finishing)
  - [A reusable plan](#a-reusable-plan)
- [Deliverable conventions](#deliverable-conventions)
- [Narration](#narration)
- [The listening judge](#the-listening-judge)
- [Music](#music)
- [Motion graphics](#motion-graphics)
- [The logo in a scene](#the-logo-in-a-scene)
- [B-roll](#b-roll)
- [The edit](#the-edit)
- [Transitions](#transitions)
- [The mix](#the-mix)
- [Subtitles and credits](#subtitles-and-credits)
- [Review and QA](#review-and-qa)
- [Encoding](#encoding)
- [Records the video adds](#records-the-video-adds)
- [Mistakes and pitfalls](#mistakes-and-pitfalls)
- [Snippets](#snippets)

Every agent on the video reads `BRAND.md`, the "Brand" section of `HANDBOOK.md` (its own part in
particular), and `README.md` "The team", "Outputs", "Brand", "Editorial rules" and "Project
records" before this guide.

## What the video is

A video of about two to three minutes at 1920x1080 and the project's frame rate (default 30) with:

- a narrator (Gemini TTS) reading a script the human and the lead agent write together;
- an original score composed as Python code and rendered from free sample libraries;
- motion graphics drawn with skia-python on the GPU, including the product's logo from its SVG or
  PNG;
- real captures of the product: its web UI (the real built frontend, driven by a mock server with
  fixture data), its terminal UIs (the real binary in a pseudo-terminal) and real CLI output;
- b-roll generated with Gemini Omni;
- a GPU compositor in Python (moderngl) that places everything on 3D planes with window chrome,
  depth of field, motion blur and grading, mixes the audio, and writes subtitles and credits.

Captures, narration, the score and b-roll are each optional, chosen at kickoff. Without narration
the sections are timed from their on-screen text or from set durations and there are no subtitles;
without music the mix is sound design alone; without b-roll the cut uses motion graphics and
captures. With no narration, score or b-roll the video is motion graphics and captures over sound
design. Without captures (a product with no source code to run, or by choice) the video is b-roll,
motion graphics, and narration or on-screen text, over music or sound design: no capture roles, no
capture questions, no `PRODUCT_*` variables, and `./setup.sh --check --for video` WARNs about
Chromium, tmux and terminal fonts ("web/terminal captures only") do not matter. A choice not made
is out of scope: no role, no brief, no questions about it.

When the project also has a blog, the video takes the claims (`claims.md`), the fixture story
(`scenarios.md`) and the captures from it, when the video has captures, and gives back motion stills, logo renders and frames
(`postkit add`). See `README.md` "Reuse between media". Run the captures with `--for both` when
both media are chosen, so one capture serves both: the video needs the `clip.mp4` that the
`video` and `both` profiles write at the project's frame rate (`guides/capture.md` "Profiles").

## The stack

| Need                | Tool                                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Narration           | `gemini-3.8-flash-tts` through the `narration` Claude Code skill (`tts.py`)                                                                                   |
| Ears for the agents | `tools/listen.py`: uploads audio or video to a Gemini model and asks questions about it                                                                       |
| Music               | numpy/scipy sample playback, `pedalboard` for reverb and mastering, `pyloudnorm` for loudness; VSCO-2 CE (CC0) samples, Salamander Grand Piano (CC BY 3.0) by opt-in |
| Motion graphics     | skia-python (vector drawing, text, the logo), on the GPU through a moderngl OpenGL context (headless EGL on Linux, CGL on macOS)                              |
| B-roll              | Gemini Omni (`gemini-omni-1.1-flash`) through `tools/genvideo.py`, prompts in `broll/gen/shots.json`                                                          |
| Word timings        | `faster-whisper` on the narration                                                                                                                             |
| Compositing         | moderngl and GLSL shaders, frames piped to ffmpeg                                                                                                             |
| Encoding and QA     | ffmpeg (`ebur128`, `signalstats`, `silencedetect`, tile filters for contact sheets)                                                                           |
| Environments        | one `uv` project per workstream                                                                                                                               |

Capture tools (Playwright and the mock server for the web, `ptyprocess`, `pyte` and skia for the
terminal) are in `guides/capture.md`.

## CPU-only machines

The kit runs on a Linux machine or VM without a GPU, more slowly; it was tested on a Proxmox VM
with no GPU:

- **Rendering**: headless EGL falls back to Mesa's llvmpipe when no GPU driver is present. If the
  context does not open, Mesa is missing (`libegl1`, `libegl-mesa0`, `libgl1-mesa-dri`): the human
  runs `./system-deps.sh`. `setup.sh` reports the two GPU lines as WARN ("CPU rendering: much
  slower") rather than MISSING.
- **Encoding and decoding**: previews and placeholders encode with `libx264 -preset veryfast`, and
  sources decode and scale on the CPU. `edit/editkit/hw.py` probes NVENC and CUDA once per process
  with a short test encode and decode, so an ffmpeg build that lists `h264_nvenc` without an
  NVIDIA driver is handled.
- **Speed**: CPU rendering is many times slower than a GPU, and how much slower depends on the
  machine's core count. Time the self-tests on your machine to know what to expect, and review
  with `--preview` and `--range` rather than full-quality renders.
- **Forcing CPU rendering** on a machine with a GPU (to compare, or around a driver problem): set
  `LIBGL_ALWAYS_SOFTWARE=1`. With the NVIDIA driver installed, also set
  `__EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json`, or NVIDIA's EGL
  answers instead of Mesa. glcontext's `GLCONTEXT_DEVICE_INDEX=<n>` picks one of several EGL
  devices. Only an NVIDIA machine was tested this way; with an AMD or Intel driver Mesa may refuse
  `LIBGL_ALWAYS_SOFTWARE` for a context opened on a hardware device, and the device index is the
  way to reach llvmpipe.

## Roles for a video

The team's rules (one owner per file, files plus short messages, the timeline as the only clock)
are in `README.md` "The team". The video's roles, each a named agent-team teammate with exclusive
ownership of its folders:

| Role                | Tier                                                   | Owns                                                                                                                                       | Job                                                                 |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| lead (main session) | Opus                                                   | `narration/`, `tools/`, `NOTES.md`, `HANDBOOK.md`, `rates.json`, `COSTS.md`, `BRAND.md`, `brand/`, `design.json` (through the brand skill) | script, narration, timeline, shared spec, briefs, review, decisions |
| composer            | Fable (an Opus composer had two scores rejected first) | `music/`                                                                                                                                   | composition and rendering                                           |
| motion designer     | Fable                                                  | `motion/`, minus any scene handed to a second designer                                                                                     | motion-graphics scenes                                              |
| scene designer      | Fable                                                  | one scene file and its outputs                                                                                                             | a scene the human asked to have rebuilt from scratch                |
| web capture         | Opus                                                   | `fixtures/web/`, `captures/web/`                                                                                                           | mock server and browser capture of the web UI                       |
| TUI capture         | Opus                                                   | `fixtures/tui/`, `captures/tui/`                                                                                                           | terminal and CLI captures                                           |
| b-roll              | Sonnet (or the lead)                                   | `broll/`                                                                                                                                   | generating shots, contact sheets, normalising picks                 |
| editor              | Opus                                                   | `edit/`                                                                                                                                    | compositor, edit decision list, mix, subtitles, credits, masters    |

Only the workstreams the human chose exist: the composer only with music, b-roll only with
b-roll, and the lead's narration work (script recording, takes, the judge) only with narration.
Without narration the lead still owns `narration/`, because it holds the timeline. The capture
roles are the same for a blog; their guide is `guides/capture.md`. A video with no captures has
neither capture role.

Pick the tier per job: Sonnet for a search-and-cut task, Opus for engineering-heavy capture and
editing, Fable where taste is the product (motion design, music) or where an attempt at the same
thing already failed. Escalate one tier only after a failed attempt, and hand the stronger agent
the task, both attempts and their evidence. Later work on the same piece (extending a score after
a new section) goes to the tier that succeeded.

## The workflow

Phase 0 is the `/begin` kickoff in `README.md` "Kickoff": the machine check, the frame rate
and piano saved in `project.json`, the interview, the Gemini key, the brand skill, `NOTES.md` and
`rates.json`. It ends by sending the lead here.

**The frame rate is the project's.** `project.json` `fps` (default 30, set with
`./configure.sh --fps N --piano vsco|salamander`) is the rate of the video captures, motion
graphics and the master. Leave `FPS` out of `edit/edl.py` and `--fps` off `motion/render.py` so
both inherit it; set them only when the human asks for an override. Where another instruction
names 60 fps, the saved rate wins. After a change of rate, rerender the captures, motion scenes
and master made before it; after a change of piano, rerender the score.
Learn the product from its own documentation first: read the repository's docs index and pull
only the sections the video needs (the features it will mention). Accurate claims in the script
depend on this, and so do the fixtures later. Put the claims in `claims.md` and verify each one.
With no product source, learn it from the human's material (a PRD, a docs page, a website URL)
and have the human confirm each claim, at the latest when they approve the script
(`README.md` "`claims.md` and `scenarios.md`").

### Phase 1: the timeline first

Every workstream is timed to `narration/timeline.json`, so it comes first. Write the script as
short sections, one per scene.

- **With narration** the voice is the clock: ask the human what tone of voice they want, render
  variants in that tone for the human to choose from, record two or three takes per line in the
  chosen voice and tone, judge them against the text, process the chosen takes uniformly, and
  build the timeline.
- **Without narration** the lead writes `sections.json` with each section's on-screen text
  (titles, captions, card text) and, where the script or storyboard fixes one, a `duration`. The
  timeline estimates the other sections' lengths from the reading time of their text and marks
  them `~est`; the human approves the pacing, and tunes it at review with `duration`.

A video can mix both, section by section. Details in [Narration](#narration).

### Phase 2: the shared spec and the briefs

The lead writes a shared spec (the design system from `design.json` and the HANDBOOK "Brand"
section, the fixture story every capture must tell, the scene list, deliverable conventions,
manifest marks) and spawns the agents for the chosen workstreams in one message, each with a
complete brief that points to `BRAND.md` and its part of the "Brand" section (`README.md` "Good
briefs").

**The fixture story** is `scenarios.md` at the project root, shared with the blog
(`README.md` "Project records"). Every capture shows the same imaginary project, account or
dataset, so the web UI, the terminal UI and the motion graphics agree. Write it once as data: the
things the product shows (ids, names, states), every relationship between them, and the arc over
time (what is true at the start, what changes in which order, how it ends, and how many on-screen
seconds each change takes). The web mock, the TUI fixtures and every scene that shows the story
copy it from that one table. Mark the rows the video uses in the Media column. A video with no
captures and no motion scene that shows the product's data has no fixture story and no
`scenarios.md`; the human approves the script alone.

- If the story holds a graph, it has no redundant (transitively implied) edges. A reviewer will
  spot one in the rendered graph; check the data before capturing, because a fix afterwards costs
  a re-capture and several re-renders.
- One notation for the same data across fixtures (a column of names, a unit). If two fixtures
  already render a row differently, both can stay, but new work follows one of them. The same
  goes for version strings such as a tool's banner: keep them equal everywhere, and re-capture
  only the clips where a stale value is visible.
- Keep the mood calm: things work, change and finish; no alarms unless the narration is about
  one.
- Show only what the real product renders, and name things as the product names them.

Scenario and label names are hyphen slugs (`overview`, `settings-dialog`): they become folder
names under `captures/` and the edit's asset references.

### Phase 3: production

Every workstream runs in parallel from the spec and the timeline. Techniques, commands and
lessons per workstream are in the sections below; capture is in `guides/capture.md`.

**Rebuild order after a change**: brand (after a change to `BRAND.md` or a brand file
`design.json` is built from: the brand skill, then every renderer that shows the change),
narration, timeline, music (if timing moved), motion (if a scene window or its content changed),
captures (only if the fixture story changed), edit.

### Phase 4: the review loop

The lead reviews every output without watching it, through contact sheets, stills, crops and
measurements ([Review and QA](#review-and-qa)), then points the human at a preview.

The human sends short, direct notes. Most are about taste (energy, colour, motion) or about facts
in the script. Typical ones and what they turn into:

| Kind of note                                                               | What it turns into                                                                                                                                                                                                         |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The score is rejected                                                      | Rewrite the composer's brief with what was rejected and why. If the second score is also rejected, give the job to a stronger model with both failures as evidence                                                         |
| The logo animation is disliked                                             | Offer three alternatives as one-line options with ASCII previews; record the rejected one in `NOTES.md` under "Rejected styles" (`README.md` "Project records"); the chosen one can become the visual motif of the whole piece |
| A product term is wrong (a component called by the name of something else) | Correct the script, the scene and every label; record the rule in `NOTES.md`                                                                                                                                               |
| A diagram of the product's data is wrong                                   | Fix the fixture story and every web clip, TUI clip and motion scene that shows it; put the lesson in the shared spec                                                                                                       |
| The look is wrong (too dark, wrong colour, wrong type)                     | Change `BRAND.md` with the human, rerun the brand skill, then delete `edit/build/placeholders/` and re-render stills of the affected scenes for the human to compare                                                       |
| The human asks the lead to stop asking and decide                          | From then on the lead decides and reports, asking nothing                                                                                                                                                                  |
| A defect on the logo in the first frame                                    | Trace it by comparing the source frame with the master; fix it at the source, never by repairing the frame downstream                                                                                                      |

Each preview is a new revision (`render.py --preview --next`), so the human can compare rounds
([Deliverable conventions](#deliverable-conventions)).

**Propagating a change.** When the script changes, the order is always the same: record the
decision in `NOTES.md`, re-record the line (two or three takes, judged; without narration, update
the section's `text` or `duration`), rebuild `timeline.json`, then message the composer (re-grid),
the motion designer (new windows, absolute times) and the editor (re-anchor on words), each only
if the video has that workstream. The editor holds the master until every upstream re-render has
finished. Inserting a new section shifts everything after it by its length; give every
downstream agent the new absolute windows.

During long renders a recurring five-minute status check (a scheduled prompt) keeps the human
informed; cancel it when the work settles.

### Phase 5: finishing

- **The first frame.** Many sites show the first frame as the thumbnail, so frame 0 is a designed
  image, never black: for example the logo alone on the project background, a motion scene's
  still drawn with `logo.draw` ([The logo in a scene](#the-logo-in-a-scene)) and held by the edit
  as a `still:` asset.
- **Credits** generated from the files that record licences, so the on-screen credits and the
  video description cannot disagree ([Subtitles and credits](#subtitles-and-credits)).
- **The ending.** A measured fade to pure black: grain and dither have to fade with the picture,
  or the black frames stay gray.
- **Subtitles.** An SRT built from the script text and the whisper word times; none without
  narration.
- **A render guard.** The editor's full render refuses to run while any shot would use a
  placeholder.
- **Encodes**: the master, then the share copy ([Encoding](#encoding)).

### A reusable plan

1. Read the product's docs; list the features and the claims you'll make; verify each claim.
2. Run the `/begin` kickoff: media, setup, interview, key, brand skill (`BRAND.md` and
   `brand/` in, `design.json` and the HANDBOOK "Brand" section out), `NOTES.md`. With narration or
   b-roll, `rates.json`.
3. Write the script as short sections. With narration: ask the tone, let the human choose among
   voice variants, record takes in the chosen voice, judge them. Without: give each section its
   on-screen text or a duration.
4. Build `timeline.json`. From here on it is the only clock.
5. Write the shared spec: design system, fixture story (`scenarios.md`, only with captures), deliverable conventions,
   manifest marks.
6. Spawn one agent per workstream, each with exclusive ownership and a complete brief.
7. Let the lead review every output with contact sheets, stills, crops and measurements.
8. Show the human a preview; record every note in `NOTES.md`; propagate changes in a fixed order.
9. Finish: a designed first frame, credits from data, subtitles, loudness, a measured fade, a
   render guard.
10. Keep `HANDBOOK.md` current so the next agent can pick the project up cold.

## Deliverable conventions

- **Output names**: `README.md` "Outputs" is the rule. The video's files sit flat in `outputs/`:
  `draft-<slug>-vN.mp4` (`render.py --preview`), `final-<slug>-vN.mp4` (`render.py`),
  `final-<slug>-vN-share.mp4`, `<stage>-<slug>-vN.srt`, `<stage>-<slug>-vN-credits.txt`,
  `<stage>-<slug>-vN-range-<A>-<B>.mp4` and `draft-<slug>-vN-contact-NN.png`. Tools rewrite the
  latest revision of their stage; `--next` starts the next one and `--revision vN` names one.
  Intermediates stay put: `edit/out/mix.wav`, `edit/build/frames/`, `motion/out/`, `music/out/`.
- **Target format**: see [Encoding](#encoding).
- **Intermediates**: H.264 `-crf 10 -preset slow -pix_fmt yuv420p`, or ProRes 4444
  (`yuva444p10le`) when alpha is needed; constant frame rate, the project's. Video captures are scale 2 (3840x2160
  for a 1920x1080 viewport) so pushes stay sharp; motion graphics at 1920x1080, rendered
  supersampled.
- **Manifests**: every workstream writes a `manifest.json` next to its outputs: file, size, fps,
  duration and timed marks. A capture manifest (`captures/<source>/manifest.json`, shape in
  `guides/capture.md` "Manifests") holds `marks` as `{t, event, key}` entries and per-frame
  cursor tracks; motion's `manifest.json` holds the retimed marks per file; the music manifest
  holds the bar grid. The edit places shots by these mark names, never by hard-coded times.
- **Files**: stills are lossless PNG. Write outputs to a temporary name and rename atomically, so
  a reader never sees a half-written file, and say "final" explicitly in the message.

`narration/timeline.json`, which every agent reads:

```json
{
  "total": 150.0,
  "narration": [
    {
      "name": "01_open",
      "file": "narration/final/01_open.wav",
      "start": 2.5,
      "end": 18.4
    },
    {
      "name": "01b_intro",
      "file": "narration/final/01b_intro.wav",
      "start": 20.5,
      "end": 22.1,
      "insert": true
    }
  ],
  "scenes": [
    { "scene": 1, "key": "open", "start": 0.0 },
    { "scene": 2, "key": "pitch", "start": 23.5 }
  ]
}
```

In a video without narration `narration` is an empty list; `total` and `scenes` are always
there.

A capture manifest entry the edit syncs to (the clip of scenario `settings`):

```json
{
  "id": "settings/clip",
  "kind": "clip",
  "file": "settings/clip.gif",
  "video": "settings/clip.mp4",
  "width": 3840,
  "height": 2160,
  "scale": 2.0,
  "fps": 30,
  "duration": 18.85,
  "marks": [
    { "t": 1.817, "event": "dialog opens", "key": true },
    { "t": 3.417, "event": "field focused", "key": true },
    { "t": 14.35, "event": "saved", "key": true }
  ],
  "cursor": [{ "t": 0.0, "x": 100, "y": 200, "down": false }],
  "cursor_space": "css-1920x1080"
}
```

## Narration

Owner: the lead. Folder: `narration/`.

The folder holds the video's clock, `timeline.json`, with or without a voice. A video without
narration needs only `sections.json` and `build_timeline.py` from this guide: skip to
[`sections.json`](#sectionsjson) and [A section without a take](#a-section-without-a-take).

**The `narration` skill** (`claude-skills/narration/`, installed to `.claude/skills/narration/` in
the project) turns a script into a 24 kHz mono WAV with `gemini-3.8-flash-tts`. Claude Code loads
it whenever narration or text-to-speech is asked for; `SKILL.md` is the full reference. The
essentials:

```bash
SKILL=.claude/skills/narration   # from the project root
uv run $SKILL/tts.py script.txt --voice Charon --style "calm and warm" -o intro.wav
echo "Hello there." | uv run $SKILL/tts.py - -o hello.wav
uv run $SKILL/tts.py --list-voices
```

- Flags: `--voice` (prebuilt name or a `voicekey_...` id; default `Kore`), `--style` (one
  sustained delivery direction for the file), `-o`, `--model`. One narrator per file.
- Each call prints its token counts and, in a project, logs them to `usage.jsonl` for the
  [cost estimate](#costsmd-the-cost-estimate).
- Age, gender and accent come from the voice choice, never from `--style`. `SKILL.md` lists 30
  voices with their traits; for explainers try `Charon`, `Sadaltager`, `Iapetus`, for product
  demos `Puck`, `Achird`.
- The script is a verbatim transcript: every word in it is spoken, so directions go in `--style`.
  Pacing comes from punctuation plus `<short pause>` and `<long pause>` tags; momentary sounds
  (`<breath>`, `<laugh>`) are inline tags; spell out anything that might be read wrong (years,
  abbreviations), and drop markdown, URLs and code.
- Long scripts that stop early or drift: split at paragraphs, narrate each part with the same
  voice and style, join with `sox`.
- If you edit `tts.py`, keep the API client in a local variable (`client = genai.Client()`): a
  temporary client object is garbage-collected mid-request.

**Start from the brand.** The narrator's character, the vocabulary and the delivery come from
`BRAND.md`, "Voice and tone", and the narration part of the HANDBOOK "Brand" section. Audition
voices that fit it, and write style directions in its words.

**Write short sections**, one per idea, each in its own `narration/NN_name.txt` (`01_open.txt`,
`02_pitch.txt`, ...). Separate files let each section carry its own delivery direction and be
re-recorded alone. `edit/subs.py` reads these files for the subtitles, so they hold exactly what
is spoken. Delete or mark stale leftover scripts. When the project has a blog, its claims
(`claims.md`) bound what the script may say.

**Ask for the tone first.** Before rendering any voice, ask the human what tone of voice they
want: warm and confident, upbeat and quick, calm and authoritative, dry and matter-of-fact. Offer
`BRAND.md`, "Voice and tone" as a starting point, but let the human confirm or change it. Record
the answer in `NOTES.md`.

**Audition voices** in that tone on the same two lines: render 3-4 variants (different voices, or
style wordings of the tone) and let the human choose. The lead does not pick the voice or the tone
unless the human explicitly tells it to choose; record that permission in `NOTES.md`. The lead
cannot hear, so it asks the [listening judge](#the-listening-judge) about each variant (perceived
age, warmth, pacing, artifacts) and to catch misreads, and re-renders a broken variant before the
human hears it. The judge describes; the human chooses.

**Calibrate the energy** with the human, each round a set of variants for the human to choose
from, and expect to overshoot both ways. "Warm and contemplative, speaking slowly" reads as bored;
"energetic, speaking with conviction" as too eager; "warm and engaged, natural conversational
pace, quietly confident" lands in the middle. Never use "hushed", whispering, breathy or overly
dramatic directions, or "slowly" or "contemplative" as the whole style. Keep a full, clear
speaking voice. Per-section changes stay small (`, firm`, `, reflective`, `, lightly wry`,
`, relaxed`, `, hopeful`, `, a touch of gravitas`). Give the judge a target (energy 5-6 of 10).

**Record and judge takes.** Only after the human has chosen the voice and tone. The TTS model
occasionally speaks stage directions (`<short pause>` read aloud), drops a word, or adds vocal
fry. Render two or three takes per changed line, in exactly the chosen voice and style, into a new
`vN/` folder and have the judge list word differences and pick the most accurate one:

```bash
cd narration
uv run ../.claude/skills/narration/tts.py NN_name.txt --voice <Voice> \
  --style "warm and engaged, natural conversational pace, quietly confident" -o vN/NN_name_a.wav
uv run ../tools/listen.py --model gemini-3.5-flash \
  "Expected text: ... For each file: word differences, stage directions read aloud, mispronunciations, energy 1-10 (target 5-6). Final line: PICK <a|b>" vN/NN_name_a.wav vN/NN_name_b.wav
```

Budget TTS calls: batch auditions, and enable billing before you start. After each batch of TTS
and judge calls, run `uv run tools/costs.py` from the project root to update
[`COSTS.md`](#costsmd-the-cost-estimate).

**Install the chosen take.** Point `sources.json` at it, then process every take the same way and
rebuild the timeline:

```json
{
  "01_open": "v3/01_open_b.wav",
  "02_pitch": ["v2/02_pitch_a.wav", "v4/02_pitch_tail_a.wav"]
}
```

A list of two files joins them with 0.5 s of silence. Without `sources.json` (no narrated
section) `process.sh` has nothing to process and says so.

```bash
./process.sh               # trims ends, caps pauses at 0.45 s, atempo 1.04, 48 kHz -> final/*.wav
uv run build_timeline.py   # rewrites timeline.json and prints the scene table
```

#### `sections.json`

It holds the order, the delivery and the timing of the sections:

```json
{
  "first_start": 2.5,
  "tail": 3.8,
  "sections": [
    {
      "name": "01_open",
      "style": "warm and engaged, natural conversational pace, quietly confident"
    },
    {
      "name": "02_pitch",
      "style": "warm and confident",
      "gap": 2.0,
      "pin": 24.0,
      "scene_start": 23.5
    },
    { "name": "03_how", "style": "warm and engaged", "gap": 0.5 },
    { "name": "04_demo", "duration": 12.0 },
    { "name": "05_close", "text": "<tagline> <url>" },
    { "name": "01b_name", "style": "warm and confident", "insert": 20.5 }
  ]
}
```

| Field         | Meaning                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------- |
| `name`        | the section: `NN_name.txt` holds its words, `final/NN_name.wav` its processed take          |
| `style`       | the `--style` direction its takes were recorded with (a record for re-takes)                |
| `gap`         | seconds of silence before it (default 0.5; ignored for the first section)                   |
| `pin`         | a fixed section start, so a re-take earlier in the order shifts nothing after it            |
| `scene_start` | a fixed scene start (default: the midpoint of the gap before its narration)                 |
| `key`         | the scene key the other workstreams use (default: the name after its number, `open`)        |
| `insert`      | a fixed start inside another scene's window; it adds no scene and shifts nothing            |
| `duration`    | seconds a section without a take lasts; it is silent (no narration entry)                   |
| `text`        | the words shown on screen; without a take or `duration`, their reading time sets the length |

Three optional top-level keys tune the reading-time estimate: `reading_cps` (default 15
characters per second), `min_hold` (2.5 s) and `pad` (1.0 s). The default suits languages written
with spaces, such as English; for Chinese, Japanese or Korean on-screen text, set `reading_cps`
lower (around 5) at the top level of `sections.json`.

**Timing model** (`build_timeline.py`): sections without `insert` play in list order, the first at
`first_start`, each later one after its `gap`; each starts a scene. Inserted lines sit where
`insert` puts them (a product name spoken during the logo reveal). A silent window for a logo
reveal is a long `gap` before the section after it, with `scene_start` pinning where that scene
begins. The picture total is the last section's end plus `tail`; the editor appends the credits.

#### A section without a take

A section's length comes from the first of these that it has:

1. its processed take, `final/<name>.wav`: a narrated section, with an entry in `narration`;
2. `duration`: a silent section of that length;
3. `text`: a silent section lasting the text's reading time,
   `max(min_hold, len(text) / reading_cps + pad)`;
4. none of them: `build_timeline.py` stops and names the section and the three options.

A take in `final/` wins even over `duration`: delete a stale take to make its section silent.

A silent section starts a scene like any other but has no entry in `narration`, so it gets no
voice in the mix, no word timings and no subtitles. In a video without narration every section is
silent, `narration` is empty and `sources.json` is absent. The lead writes each section's
on-screen text (titles, captions, card text) into `sections.json`; the timeline estimates the
pacing from it, and the printed table marks those sections `~est`:

```text
 1 scene@   0.0  01_open             0.5 -     3.0  (2.50s) silent ~est (from text: confirm at review)
 2 scene@  3.25  02_pitch            3.5 -     6.7  (3.20s)
 3 scene@  6.95  03_demo             7.2 -    11.2  (4.00s) silent
```

The human confirms the pacing at review; a section whose estimate is wrong gets a `duration`,
which wins over `text`. Motion scenes can read the same `text`, so the on-screen words and their
timing come from one place.

- **Re-takes**: use one take whole. Splicing a new sentence into an approved take is audible
  (voice colour and room tone change at both joins).
- **Trims without re-recording**: find pauses with `silencedetect` and cut the source take with
  `atrim` and a short `afade` ([Snippets](#snippets)).
- **Wording changes of equal length** keep the timeline. Longer ones shift everything after them,
  so send downstream agents absolute windows.

## The listening judge

The judge is optional: it needs `GEMINI_API_KEY`. `tools/listen.py` uploads files to Gemini and
asks a question about them:

```bash
uv run tools/listen.py --model gemini-3.5-flash "question" file1.wav [file2.wav ...]
```

Pass `--model gemini-3.5-flash`: the default, `gemini-3.8-flash`, was often unavailable (503), and
Pro models may have no quota on your key. Scores drift by one point between identical calls, and
it occasionally hallucinates (it has heard voiceovers in instrumental files). Use it for direction,
for A/B comparisons and for catching misreads, never for a single-call pass or fail, and
cross-check what it says. It also watches video, so it can comment on a preview. It screens takes
for misreads; it never picks the tone or the voice.

Without a key the lead reviews audio with ffmpeg measurements only
([How the lead reviews without watching](#how-the-lead-reviews-without-watching),
[Snippets](#snippets)): loudness and true peak with `ebur128`, and gaps with `silencedetect`.

```bash
ffmpeg -i outputs/draft-<slug>-v1.mp4 -af ebur128=peak=true -f null - 2>&1 | rg 'I:|Peak:'
ffmpeg -i take.wav -af silencedetect=noise=-40dB:d=0.25 -f null - 2>&1 | rg -o 'silence_(start|end): [0-9.]+'
```

## Music

Owner: the composer. Folder: `music/`.

**A video without music** has no composer and no `music/arrangement.py`. `edit/mix.py` then has no
music bed, and the credits list no samples ([The mix](#the-mix)). A score of synthesized
instruments only (`pluck`, `sub`, the synthesized percussion) needs no sample libraries
(`./setup.sh --no-samples`); a sampled instrument without them stops the render with a message
naming the missing folder.

**Piano choice.** `piano` plays VSCO's Upright Nr1 (CC0) by default. It plays the Salamander
grand piano (CC BY 3.0) only when `project.json` `piano` is `salamander`, which the human chooses
explicitly, knowing the credit it requires on screen and in the video description; never select or
download Salamander otherwise. `setup.sh` fetches Salamander only under that setting. The render
records the libraries the score used in `music/manifest.json` `sample_libraries`, and the credits
name Salamander only when that render used it. A change of piano takes a new render of the score;
it does not change audio rendered before it.

**Score as code.** The composer writes the score as Python data (motifs, harmony, parts, an
arrangement per section) and renders it with a small sampler: nearest sample per note and
velocity, repitching for small intervals, release tails, round-robins, humanised timing, then
convolution reverb and mastering to -16 LUFS, with sample-aligned stems (piano, strings, mallets,
bass, percussion, synth, winds). Only the piano and orchestral samples come from the libraries;
kick, claps, snaps, sub bass, synth pluck, risers and the reverbs are synthesized
(`scorekit/synth.py`, `scorekit/mix.py`).

**The project's score** is `music/arrangement.py`, defining `compose(seed: int) -> Score`;
`render.py` calls it, renders every note and writes the manifest from the score's grid. A
skeleton with placeholder numbers:

```python
from scorekit import drums as D
from scorekit.parts import Dyn, bass, melody, ostinato
from scorekit.score import Score
from scorekit.timing import Grid

GRID = Grid(bpm=120.0, bar0_at=2.0, total=180.0,       # total: the picture's end, fade tail included
            local=[],                                    # (first bar, bars, seconds) at their own tempo
            sections=[("open", 0, 0.0), ("pitch", 13, 23.5)])   # (id, first bar, picture cut in s)
HARMONY = [(0, 2, "C"), (2, 2, "Am7"), (4, 2, "F"), (6, 2, "Gsus4")]   # (bar, bars, chord)
HOOK = [(0, 0.5, 69), (0.5, 0.5, 71), (1, 1, 74), (2, 2, 76)]          # (beat, beats, MIDI pitch)


def compose(seed: int) -> Score:
    sc = Score(GRID, HARMONY, seed)
    ostinato(sc, "piano", 0, 8, ("r", "5", "9", "5", "3", "5", "9", "5"), 60, Dyn(70))
    melody(sc, "glock", 4, HOOK, 80)
    bass(sc, 0, 8, 72)
    D.kick(sc, 0, 8, 90)
    D.backbeat(sc, 0, 8, 82)
    sc.auto("piano", 6, -3.0)                            # stem gain breakpoint: -3 dB at bar 6
    return sc
```

The engine's pieces:

- **`Score`** (`scorekit/score.py`): `add(inst, beat, beats, pitch, vel)` places a note (beats count
  from bar 0: bar 13 beat 3 is `13 * 4 + 2`), `chord(...)`, `hit(kind, beat, vel)` for percussion,
  `auto(stem, bar, db)` for stem gain, `spans(start, end)` and `chord_at(bar)` read the harmony.
  Timing and velocity are humanised per instrument.
- **`Grid`** (`scorekit/timing.py`): the tempo map and bar grid: `t(bar)`, `beat_t(beat)`,
  `bars_at(seconds)`, `manifest()`. Its speech windows come from `narration/timeline.json` for the
  QC plots.
- **Textures** (`scorekit/parts.py`): `ostinato` (broken chords from the harmony, with accent
  shapes `ACCENT_332` and `ACCENT_EVEN`), `block_chords`, `bass` (`eighths`, `pulse`, `long`),
  `melody`, `pad`, `soar`, `sparkle`, `flourish`, `harp_run`. `scorekit/theory.py` parses chord
  symbols and voices chords.
- **Drums** (`scorekit/drums.py`): `kick`, `backbeat`, `shaker`, `tambourine`, `clicks`, `fill`,
  `build` (a crescendo into a downbeat), `crash`.
- **Instruments**: sampled `piano`, `vln_spic`, `vla_spic`, `vc_spic`, `cb_spic`, `vln_pizz`,
  `vla_pizz`, `vc_pizz`, `cb_pizz`, `vln_sus`, `vla_sus`, `vc_sus`, `harp`, `marimba`, `xylo`,
  `glock`, `horn`; synthesized `pluck` and `sub`; percussion `kick`, `clap`, `snap`, `riser`,
  `sub_drop` (synthesized) and `bdrum`, `snare`, `click`, `shaker`, `tamb`, `tom_lo`, `tom_hi`,
  `taiko`, `cym_hit`, `cym_swell`, `cym_swell_short`, `triangle`, `fingcymb`, `chimes` (sampled).
  Keep `music/CREDITS.md` true to the libraries the score uses.

**The arrangement follows the timeline.** The tempo and bar grid are chosen so scene cuts land
within about 0.3 s of a downbeat or a half bar, and melodies thin out inside speech windows. When
the timeline changes, the score re-renders in under a minute with the same character; the tempo
may shift a few BPM. No single tempo puts every cut on a downbeat: weight the cuts that matter
most (the logo reveal, the close), let the others fall on half bars, and keep within any tempo
range the human has set. Record the fit in `HANDBOOK.md`: tempo, bar 0, which cuts land on
downbeats or half bars, and the worst offset. When a section's length is fixed and the bars do
not fit, give it a `local` tempo that spans it exactly; the manifest's `tempo_map` records it, and
every later section keeps its offset from its cut.

**An arc per section**, agreed with the human: what the music does under the problem statement,
on the logo reveal, under the product name, under dense explanation, in the strongest section and
at the close. Techniques that serve any arc: rest the melody about 10 dB lower under the product
name; ease under dense explanation with a 3 dB stem duck; let the hook and the pulse carry an
arrival instead of a new sustained layer entering on it; resolve the close to a chord held under
the end card. Under a single credit line, the end card's chord can ring on with one soft touch and
fade to silence; a reprise is not needed.

**Taste comes from the brand and the human.** Start from `BRAND.md`, "Music and sound feel", and
the composer's part of the HANDBOOK "Brand" section. Ask what each reference means to this person:
a game soundtrack or a genre name can mean a tempo and an energy to one listener and an
instrumentation to another, and a misread reference costs a whole score. Record every rejection
with its reasons in `NOTES.md` under "Rejected styles", keep rejected scores' code and renders in
a reference folder, and escalate the composer one tier after two failures, with both attempts and
the feedback as evidence.

**Checking without ears**: numbers (onset density, tempo estimate, spectral centroid, loudness
curve, click detection, from `--qc`) and the judge, asked pointed questions (rate each quality
`BRAND.md` asks for and each quality of a rejected score 1-10; name the instruments heard) and
compared against the rejected version.

```bash
cd music
uv run render.py --selftest    # eight synthesized bars -> out/selftest/; checks the engine, no samples needed
uv run render.py --qc          # render (~50 s for a full cue) plus QC plots in out/qc/
uv run render.py --excerpt A B # a slice from A to B seconds, for the judge
uv run render.py --qc-only     # re-analyse the existing files
```

`manifest.json` holds the bpm, `bar_0_at`, downbeats, beats, sections (with `offset_from_cut`),
speech windows and any `tempo_map`.

## Motion graphics

Owner: the motion designer. Folder: `motion/` (Python 3.12, skia-python on the GPU through
OpenGL: EGL on Linux, CGL on macOS). Run everything from `motion/`:

```bash
uv run python render.py --selftest                                       # the kit's test scene: GPU, fonts, encoder
uv run python render.py <scene> --duration 22.83 --handle 0.5            # opaque .mp4
uv run python render.py <scene> --duration 22.83 --handle 0.5 --alpha    # ProRes 4444 _alpha.mov
uv run python render.py <scene> --contact                                # 9-frame contact sheet
uv run python render.py <scene> --still 12.0 [--over <hex>]              # one PNG, optionally composited
./render_all.sh                                                          # every scene in scenes.txt, both variants
```

Without narration, a section's on-screen words are its `text` in `narration/sections.json`, which
also sets its length ([A section without a take](#a-section-without-a-take)). A scene can read its
text from there, so the words and the timing come from one place.

**Start from the brand.** `design.json` supplies the fonts and colours; `BRAND.md`, "Imagery and
motion feel" and "Logo", and the motion part of the HANDBOOK "Brand" section say how things move
and how the logo may be used.

**A scene** is a module `motion/scenes/<name>.py` that defines `SCENE`, a subclass of
`lib.scene.Scene`; `render.py <name>` loads it. A skeleton:

```python
from lib import gfx
from lib.ease import cubic_out, seg, smooth
from lib.scene import Scene


class Title(Scene):
    name = "title"           # the module name: out/title.mp4
    key = "open"             # the timeline scene it belongs to
    nominal = 6.0            # its window in narration/timeline.json
    marks = [(0.5, "title in"), (4.0, "title out")]

    def draw(self, canvas, t, opaque):
        u = self.u(t)                       # nominal seconds, whatever --duration is
        a = smooth(seg(u, 0.5, 1.3)) * (1 - smooth(seg(u, 4.0, 4.6)))
        y = 560 - 12 * cubic_out(seg(u, 0.5, 1.6))
        gfx.text(canvas, "<a line from the script>", 960, y, 52, gfx.FG, 500, 0.0, a, align="center")


SCENE = Title
```

- `draw(canvas, t, opaque)` paints one frame on a skia canvas in 1920x1080 logical units (the
  renderer supersamples at 2x); `t` is seconds into the window. The renderer clears an opaque
  frame to `gfx.BG` and a transparent one to nothing before it calls `draw`; `opaque` is False
  for the transparent variant, which must leave out any ground the scene paints itself. Set
  `alpha = True` for a scene that is transparent by default. `setup()` (optional) builds state
  that does not depend on time.
- Each scene is parametric in duration, so a timeline change is one command: author it in
  nominal seconds through `self.u(t)`; `--duration` retimes it uniformly (every beat scales), and
  `out/manifest.json` carries the retimed `marks` per file.
- The engine's helpers: `lib/gfx.py` (the colours `BG`, `FG`, `FG2`, `ACCENT` from `design.json`
  and `HAIR`, `CARD` mixed from them; `typeface(weight, italic=False)`, `font(size, weight=400,
  italic=False)`, `text`, `text_width`, `text_glow`, `label`, `card`, `pill`, `hairline`,
  `soft_stroke`, `glow_stroke`, `glow_dot`, `col`, `mixcol`), `lib/logo.py` (the logo from
  `design.json`, [The logo in a scene](#the-logo-in-a-scene)), `lib/ui.py` (`persp_matrix` for a
  tilted pane, `status_glyph`, `edge_path`, `trimmed` and `draw_edge` for connectors drawn in
  over time, `port`, `CodeLines` for typed code), `lib/ease.py` (`seg`, `lerp`, `smooth`,
  `cubic_io`, `quint_io`, `back_out`, `spring`, `stagger`, `ease_in_linear`, ...). `text`,
  `text_width` and `text_glow` default to weight 400, `text_glow` to `ACCENT`. A helper several
  scenes share goes in `lib/` beside them.
- **`scenes.txt`** lists what `render_all.sh` renders, one scene per line with its `render.py`
  arguments, usually the window from `timeline.json`:

  ```text
  # scene   arguments
  title     --duration 6.1
  steps     --duration 18.32
  ```

  Each line renders the scene's default and, when that is opaque, its transparent variant
  (`--variants`), with 0.5 s handles.

- `--alpha` writes a transparent ProRes 4444 `.mov` of an opaque scene, leaving out the
  background, so the editor can place it over any ground. `--opaque` forces H.264. A full-frame
  scene that paints its own ground stays opaque; other scenes are composited through alpha.
- Every clip has 0.5 s handles; manifest marks include the handle, so clip time = master time -
  scene start + 0.5.
- Alpha variants draw in the same colours as the opaque render. Check a transparent still
  composited over the colour it will sit on (`--still t --over <design.json background>`), and
  over a capture or b-roll frame if the edit places it there.
- Render intermediate buffers in RGBA F16. 8-bit premultiplied accumulation of a temporally
  blurred log produced blocky glyphs.
- A still from a scene can go to the blog: `uv run postkit add motion/<scenario>/<label> <png>`
  from `post/` (`guides/blog.md`).

**GPU gotchas**, both from mixing skia and moderngl on one GL context:

- On Linux, `skia.GrDirectContext.MakeGL()` returns `None` under a moderngl EGL context, because
  skia's native interface there is GLX's; `skia.GrDirectContext.MakeGL(skia.GrGLInterface.MakeEGL())`
  works, with the NVIDIA driver and with Mesa (about 10 ms per 4K frame with blurs on an NVIDIA
  GPU). On macOS the native interface is CGL's, so `lib/gfx.py` calls `MakeGL()` with no argument.
- skia's flush leaves `GL_BLEND` enabled and moderngl does not reset it, so an uncleared
  framebuffer accumulates across frames: single stills look right while the encoded movie
  saturates to opaque white. A moderngl shader pass added to the renderer must call
  `fbo.clear()` and `ctx.disable(moderngl.BLEND)` first. Verify alpha by decoding the encoded
  `.mov`, never only from stills.

Keep a table of the scenes in `HANDBOOK.md`: name, window, duration, content. Scene guidance from
a finished video:

- An opening scene that dramatises a problem (a dial, an odometer, a counter) needs a designed
  ground (a flat gray open reads as dull), nothing cut off at the edges (a percentage clipped on
  the right reads as spartan), and no decorative marks a viewer could find confusing (radial scar
  ticks, comparison bars).
- A table scene: typographic and uncluttered; an accent bar that hops between rows fades and never
  crosses glyphs; no axis touching its container.
- A diagram or graph: built from real data (the fixture story or the product's real output),
  solid lines for facts and dashed for inferred ones, sized from measured content; put the beat
  the narration lands on last.
- A sequence of steps or checks: a cascade, a stepper and a ledger of results. Place call-out
  cards so they never overlap prompt text.
- A scene showing a terminal session with a third-party tool (a coding agent, say): one person,
  unnamed, working in it; the tool's banner shows the installed version; show a document's prose
  first, then scroll to its structured parts with call-outs.
- An end card: the logo (`logo.draw`, within `BRAND.md`'s clear space and minimum size),
  tagline, URL; a licence line only if the human wants one.

## The logo in a scene

`design.json` names the logo files, both optional:

```json
{
  "logo": {
    "on_dark": "brand/logo/<name>-on-dark.svg",
    "on_light": "brand/logo/<name>-on-light.png"
  }
}
```

`design.logo(variant=None)` returns the file. With no variant it picks `on_dark` when the
`background` colour's WCAG relative luminance is below 0.179, else `on_light`, and falls back to
the other variant when one is missing. An unknown variant raises `ValueError`; with no logo set
it raises `FileNotFoundError: no logo in <root>/design.json: name logo.on_dark or logo.on_light
(README.md, "Brand")`.

Motion scenes draw it with `motion/lib/logo.py`:

- `logo.draw(canvas, cx, cy, width, alpha=1.0, variant=None)` draws it centred at `(cx, cy)`,
  `width` px wide, aspect kept.
- `logo.size(width, variant=None) -> (w, h)` gives the drawn size, for layout.
- `logo.load(path)` (cached per path) and `logo.svg_size(path)` are the lower-level pieces.

An SVG is drawn through Skia's SVG module, a PNG through `skia.Image`. An SVG's size comes from
its numeric `width` and `height`, else its `viewBox`. Skia's SVG module draws filters, gradients
and masks, but draws nothing for `<text>`, CSS `<style>` class rules or an embedded `<image>`:
convert text to outlines and write styles as inline attributes, or export a PNG at least 2000 px
wide and name that instead. An end card:

```python
from lib import gfx, logo
from lib.ease import seg, smooth
from lib.scene import Scene


class EndCard(Scene):
    name, key, nominal = "endcard", "close", 6.0

    def draw(self, canvas, t, opaque):
        u = self.u(t)
        w, h = logo.size(480)
        logo.draw(canvas, 960, 480, 480, smooth(seg(u, 0.3, 1.2)))
        gfx.text(canvas, "<tagline>", 960, 480 + h / 2 + 90, 40, gfx.FG, 400, 0.0,
                 smooth(seg(u, 1.0, 1.8)), align="center")


SCENE = EndCard
```

Draw only the files in `brand/logo/`: never redraw, recolour or distort the logo. Keep
`BRAND.md`'s clear space and minimum size, and animate it only in ways its "Logo" do and don't
list allows. When `design.json` names a logo, the motion self-test draws it under the card,
fitted to a 320x130 box.

## B-roll

Owner: b-roll (or the lead). Folder: `broll/`.

B-roll is optional, chosen at kickoff. Without it there is no b-roll workstream, the EDL's
`BROLL_CLIPS` stays empty and the credits list none. Generated b-roll needs `GEMINI_API_KEY`.

Generate b-roll with Gemini Omni only, never Veo: reviewers rejected Veo output as poor.
`broll/gen/shots.json` is a list of `{"id", "prompt"}` plus the optional `"images"` and `"mode"`
below; an id is letters, digits, `_` and `-`, used once. `genvideo.py` fixes the format (16:9,
1080p), and Omni returns about 10 s at 24 fps per shot. The script renders three shots at a time,
retries a failed call once, skips ids already rendered, and writes `broll/gen/omni/<id>.mp4` plus
`<id>.json` (prompt, config, the Omni `task`, clip length, timing, attempts, and the `mode` and
`images` with their sha256 when the shot used images).

```json
[
  {
    "id": "01_server_aisle",
    "prompt": "Slow dolly along ... No people. Photorealistic documentary footage, 35mm lens, shallow depth of field, natural film grain."
  },
  {
    "id": "02_dashboard_push",
    "mode": "first_frame",
    "images": ["brand/hero.png"],
    "prompt": "Slow camera push-in on this screen, subtle monitor glow, no text changes."
  },
  {
    "id": "03_aisle_continues",
    "mode": "first_frame",
    "images": ["frame:01_server_aisle"],
    "prompt": "The camera keeps dollying left along the same aisle ... No people. Photorealistic documentary footage, 35mm lens, shallow depth of field, natural film grain."
  }
]
```

A shot with no `images` is text-to-video. With `images` (paths from the project root to files the
human put in `brand/`; png, jpeg or webp, the type read from the file content) it needs a `mode`:

| `mode`        | Images | Omni task            | Use it for                                                                                                        |
| ------------- | ------ | -------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `first_frame` | 1      | `image_to_video`     | A product photo or screenshot as the opening frame; the clip animates from it                                     |
| `first_last`  | 2      | `image_to_video`     | `images[0]` is the first frame and `images[1]` the last; the prompt describes the move between them               |
| `reference`   | 1 to 6 | `reference_to_video` | A logo or product that must appear in a new scene; the prompt names each as `<IMAGE_REF_0>`, `<IMAGE_REF_1>`, ... |

A reference is not used as a literal first frame. Only a `reference` prompt contains
`<IMAGE_REF_n>`, and it names each of `<IMAGE_REF_0>` up to one less than the image count, no
other. Before the first call `genvideo.py` checks every shot not yet rendered (the fields above,
files inside the project, the count for the mode, a real image, the size caps, the
`<IMAGE_REF_n>` tokens) and exits listing every error with its shot id, so a bad entry costs
nothing. The caps are the kit's own, since the Omni docs state none: 7 MB per image, 20 MB for all
of a shot's images, 6 images. Ask the human for the images: they must be their own or licensed,
never lifted from the web. Large zooms on screen text garble it (a long push-in turned terminal
text to noise), so keep moves slow on text.

**Continuity between shots.** An entry in a shot's `images` may be a frame of another shot's clip
instead of a file: `frame:<shot id>` or `frame:<shot id>@last` (that clip's last frame), or
`frame:<shot id>@<seconds>` (the frame at that time, for example `frame:01_server_aisle@4.5`). It
works in every mode:

- `first_frame` with the previous shot's last frame continues that shot;
- `first_last` with a frame as `images[1]` makes a clip end on a frame of another shot, a bridge
  into it;
- `reference` with frames keeps a subject or place consistent across shots (the prompt still names
  `<IMAGE_REF_n>`).

`genvideo.py` extracts the frame with ffmpeg into `broll/gen/frames/<shot id>@<last|seconds>.png`,
fresh before each render, and checks it like any image (size caps, png). `<id>.json` records it as
`{"path", "sha256", "source": "frame:..."}`. Before any paid call it checks that the named shot is
in `shots.json`, is not the shot itself, forms no cycle, and is rendered or rendered in this run.
When the named shot renders in the same run, its frame (a time past its end, an oversized frame)
can only be checked after that shot renders, and then the child fails without its own call: use
`@last` or a time well under the clip length (Omni clips are about 10 s). A shot that uses a
frame of another starts after that shot finishes; unrelated shots render in parallel, three at a
time. When a shot fails, every shot that uses a frame of it, directly or down a chain, is skipped
without a call. With `--only <id>`, a parent that is not rendered yet is an error: render it
first. Re-rendering a parent does not re-render children already rendered:
`genvideo.py` prints a warning naming each such child, and deleting the child's mp4 renders it
again from the new clip.

For a continuation, describe the motion carrying on from the frame ("The camera keeps dollying
left along the same aisle ...") and keep the look words identical to the parent's prompt. The
child's first frame repeats the parent's last, so in the edit start the child one frame in
(`src_in` of 1/24 s; Omni clips are 24 fps) or dissolve between them. A chain drifts after several
links; re-anchor a long chain with a `reference` frame from the first shot.

`tools/costs.py` prices Omni with the `per_second` rate in `rates.json` ("`COSTS.md`: the cost
estimate"): the rate times the clip length `genvideo.py` logs for each clip. A failed attempt logs
no length, so it adds $0. `usage.jsonl` still records each attempt's input tokens, image tokens
included, and `COSTS.md` counts them in its tokens column, but they add nothing to the estimate.

```bash
uv run tools/genvideo.py [--only <shot id>]   # from the project root; needs GEMINI_API_KEY
```

- Write prompts as a shot description: camera move, subject, light, "No people", then the look
  ("Photorealistic documentary footage, 35mm lens, shallow depth of field, natural film grain"),
  taken from `BRAND.md`, "Imagery and motion feel".
- Render several shots, cut a reel, and let the human pick.
- Pick imagery that matches what the narration says at that moment: an unrelated object under a
  sentence confuses the viewer.
- Normalise the chosen clips to `broll/candidates/NN_<id>.mp4` (H.264 crf 10, no audio) and list
  them in `edl.py`'s `BROLL_CLIPS`; the edit grades them (30 % saturation, 50 % brightness worked)
  so they sit under graphics.
- The lead checks every contact sheet: an agent's "no logos" claim once missed two branded clips.
- Every Omni attempt is billed, retries and failed shots included. `genvideo.py` logs each
  attempt's token counts and clip length to `usage.jsonl`; the lead runs `tools/costs.py` after
  each batch ([`COSTS.md`](#costsmd-the-cost-estimate)).
- Generated footage needs no attribution. A generated clip or frame can go to the blog with
  `postkit add broll/...` (`guides/blog.md`).

Creative Commons stock is a last resort, and reviewers often reject it as off-message. If you use
it: search with an up-to-date `yt-dlp` (an outdated one only got 360p streams), check each
candidate's licence field for Creative Commons Attribution, cut short segments, make contact
sheets, and record title, channel, URL, licence and the range used in `broll/CREDITS.md`
([Subtitles and credits](#subtitles-and-credits)).

### Exporting b-roll for reuse

The lead exports a project's b-roll when the human wants it kept for other videos. Each clip goes
out with a contact sheet and its metadata, in a folder that can be uploaded to a synced drive or a
bucket:

```bash
./export-broll.sh <dest-dir> [--only <id>]... [--tar <file.tar.gz>] [--force]
```

- Exported: every rendered generated clip in `broll/gen/omni/`, whether a video used it or not,
  and every candidate in `broll/candidates/` that has a `broll/CREDITS.md` section. A clip whose
  `<id>.json` is missing or unreadable still goes out, with its prompt taken from
  `broll/gen/shots.json` and `meta_source` set in its sidecar. A candidate matches a section when
  its file name without `.mp4`, or without the `NN_` prefix, equals the section's name; one whose
  name equals a generated clip's id is exported as `stock-<name>`. Unfinished renders
  (`.<id>.tmp.mp4`) and uncredited candidates are left out.
- Layout: `<dest-dir>/<slug>/` holds `<id>.mp4` (unchanged), `<id>-contact.png` (12 frames tiled
  4x3), `<id>.json` (project slug, kind, prompt/model/mode or credit, duration, resolution, fps,
  sha256, export time) and `INDEX.md`. `<dest-dir>/catalog.json` and `CATALOG.md` list every
  project in the location; an export replaces its own project's entries and keeps the others, so
  exports from many projects accumulate into one library.
- A generated clip needs no attribution. A CC BY stock clip travels with its credit lines in the
  sidecar and in `INDEX.md`; show them wherever the clip is used again.
- Rerunning is safe: a clip whose sha256 matches is not recopied. A clip that differs from the one
  already exported stops the run (exit 1, nothing written) until `--force` replaces it.
- `--tar` also writes a gzip tar of the project folder and the catalog files; it refuses an
  existing file. The destination must be outside the project.

## The edit

Owner: the editor. Folder: `edit/`. Every output lands in `outputs/` under the names in
[Deliverable conventions](#deliverable-conventions); the slug comes from `project.json`.

```bash
cd edit
uv run bg_test.py [seconds]   # self-test (default 6 s): background and a test window -> out/bg_test.mp4
uv run words.py            # faster-whisper word timings -> build/words.json (rerun after any narration change; empty without narration)
uv run mix.py              # narration chain + ducked music + sound design -> out/mix.wav (-14 LUFS)
uv run subs.py             # outputs/draft-<slug>-vN.srt (none without narration)
uv run credits.py          # outputs/draft-<slug>-vN-credits.txt
uv run render.py --preview                 # 540p at up to 30 fps, no grain, DOF or motion blur -> outputs/draft-<slug>-vN.mp4
uv run render.py --range 14 30             # a time range only (any mode) -> outputs/<stage>-<slug>-vN-range-14-30.mp4
uv run render.py --contact --every 2       # contact sheets -> outputs/draft-<slug>-vN-contact-NN.png
uv run render.py --frames 0 25.8 166.5     # single frames -> build/frames/ (--full-frames for full quality)
uv run render.py                           # full master -> outputs/final-<slug>-vN.mp4 (~3-4 min on a GPU)
uv run render.py --fast                    # full quality with the fast encoder (as previews use)
uv run render.py --share                   # the share copy of the latest final master ([Encoding](#the-share-copy))
```

- **Revisions.** A render rewrites the latest revision of its stage (v1 when none). `--next`
  starts the next revision of a preview or a full render; `--revision vN` names one. Contact
  sheets, ranges, subtitles and credits attach to the latest primary file of their stage unless
  `--revision vN` is given. Subtitles and credits write the draft stage by default and the final
  stage with `--final`. A range's bounds appear in its name with the decimal point as `p`
  (`range-0p5-1p5`). `--out` overrides the destination of a video.
- A contact render and `--frames` skip the placeholder guard; `--allow-placeholders` skips it for
  a video.

**`edl.py` is the edit as data**: which source, which in-point (by manifest mark or by spoken
word), which camera move, which transition. The project writes it; `editkit/project.py` loads it
for `render.py`, `mix.py` and `credits.py`. It defines `END` (the last frame, in seconds) and
`build() -> Timeline`, and optionally `BROLL_CLIPS` (b-roll names the cut uses, for the credits),
`BUSY` (scene keys where the mix ducks the melody further) and `FPS` (an override of the master's
frame rate, which is otherwise `project.json` `fps`, default 30; `--preview` renders at most 30).
A skeleton:

```python
from editkit import cards
from editkit import credit_data as cd
from editkit.assets import resolve
from editkit.ease import Track
from editkit.scene import Camera, Segment, Timeline, Transition
from editkit.shots import browser, framed, fullframe, scene_starts, sync, timeline

S = scene_starts()                       # scene key -> start, from narration/timeline.json
TOTAL = timeline()["total"]              # end of the narrated picture
END = TOTAL + 5.0                        # plus the credit line's slot
BROLL_CLIPS = []                         # b-roll names the cut uses, for the credits
BUSY = ()                                # scene keys where the mix ducks the melody further


def motion(key: str, scene: str, start: float, end: float, **kw):
    """A motion clip clock-locked to its scene window: clip time = master - scene start + handle."""
    handle = float(resolve(key).entry.get("handle", 0.0))
    return fullframe(key, start, end, src_in=start - S[scene] + handle, **kw)


def build() -> Timeline:
    first = fullframe("still:motion/out/title_00.00.png", 0.0, 1.3, fade_out=0.55)   # the designed first frame
    title = motion("motion:title", "open", 0.0, S["pitch"] + 0.8)
    t = S["pitch"]
    ui = browser("web:overview", t, S["end"])
    ui.src_in = sync("web:overview", "dialog opens", t + 1.0, t, default=1.8)
    framed(ui, [(t, (0.5, 0.5, 1.05, 2.0, -3.0)), (t + 1.5, (0.5, 0.45, 0.7, 1.0, -1.0), "quint")])
    card = cards.credit_line("credits", cd.lines(BROLL_CLIPS))
    segs = [Segment("open", 0.0, [title, first]),
            Segment("pitch", t, [ui], Camera(aperture=4.0), Transition("push", 0.7)),
            Segment("credits", TOTAL, [fullframe(card, TOTAL, END + 1)], trans=Transition("dissolve", 0.6, ease="sine"))]
    fade = Track((0.0, 0.0), (END - 1.9, 0.0), (END - 0.5, 1.0, "sine"))
    return Timeline(END, segs, fade=fade)
```

A video with no captures uses no `web:` or `tui:` assets. A b-roll-only cut places each clip as a
`fullframe` plane, for example `fullframe("broll:02_dashboard_push", t, t + 4.0, src_in=1 / 24)`.

- **Asset keys** name sources (`editkit/assets.py`):
  - `web:<scenario>` and `tui:<scenario>`: `captures/<source>/<scenario>/clip.mp4`. When only
    `clip.webm` exists (a capture made with `--for blog`) the edit uses it and prints a warning:
    it is 30 fps at scale 1, so recapture with `--for video` or `--for both`.
  - `still:<source>/<scenario>/<label>`: `captures/<source>/<scenario>/<label>.png`. A path
    that is not under `captures/` is read from the project root (`still:motion/out/title_00.00.png`).
  - `motion:<scene>` and `motion_alpha:<scene>`: motion's opaque and transparent files.
  - `broll:<clip>`: a file in `broll/candidates/`.
  - `image:<card>`: a card generated into `edit/build/art/` (`cards.py`).

  `resolve(key)` gives the file, its probe, its manifest entry and its marks; a missing asset
  becomes a placeholder of the right shape. A capture's size in local px is its pixel size over
  the manifest entry's `scale`, so a 3840x2160 scale-2 clip lays out as 1920x1080.
- **Shot helpers** (`editkit/shots.py`): `scene_starts()`, `timeline()`, `word(section, text)` and
  `word_end(...)` (master time of a spoken word, from `build/words.json`; lookups are strict, so a
  missing word fails the build and a shot can open on a named word without drifting;
  `narration(name)` and the word lookups raise a `KeyError` for a silent section),
  `sync(key, event, at, start, default)` (the in-point that puts a manifest mark at a master time),
  `anchor(...)`, `fullframe`, `browser` and `terminal` (a plane dressed as a window), `framed`
  (drive a window's position, scale and tilt from framings of its content), `cursor_for(key)`
  (the capture's cursor track).
- **The scene model** (`editkit/scene.py`): a `Plane` has a source, a time span, `src_in`,
  `speed`, `hold`, `pos`, `rot`, `scale`, `opacity`, `blur`, `dim`, `saturation`, `view` (a crop),
  `fade_in`, `fade_out` and window `chrome`; any of them can be a `Track` of keyframes
  (`editkit/ease.py`). A `Segment` groups planes under a `Camera` (`aperture` for depth of field)
  and enters with a `Transition`: `kind` (`cut`, `dissolve`, `push`, `zoom`), `dur`,
  `direction` (where a push sends the outgoing scene) and `ease`. During a transition each
  segment's group is drawn with a `GroupState` (`opacity`, `offset`, `zoom`). A segment lasts
  until the next one has entered, unless it sets its own `end`: then it spans the segments after
  it and stops at `end` (a cut; fade its planes with `fade_out`). List such a segment first, so
  it draws under the others, for a ground layer that runs under every scene. A
  `Timeline(total, segments, fade, background_level)` carries the fade to black (0 to 1) and a
  brightness multiplier for the background; both can be `Track`s.
- Scene windows come from `timeline.json`, word sync from `words.json`, capture in-points from
  manifest marks. Motion scenes are clock-locked to their windows.
- **The compositor** (`editkit/compositor.py`, moderngl over EGL on Linux or CGL on macOS, chosen
  with the encoder and decoder in `editkit/hw.py`): sources decoded through ffmpeg pipes, layers
  on 3D planes with perspective-correct sampling and mipmaps, window chrome and soft shadows,
  per-layer depth of field, shutter motion blur, the cursor drawn from the capture's track, the
  background, bloom and grain, frames piped back to ffmpeg. `shaders/` holds the GLSL
  (background, plane, group, dof, bloom, shadow, final). The background is flat: `design.json`'s
  `background` colour, scaled by `Timeline.background_level`, with grain (`design.json`'s
  `grain`; the preview renders without grain). `cards.py` draws the credit line.
- **Design**: the edit reads the fonts, `background`, `text`, `secondary` and `grain` from
  `design.json` (`editkit/design.py`, `editkit/art.py`); window chrome is a fixed neutral grey.
  `grain` is an optional number of at least 0 that only the edit reads; the blog ignores it.
  Placeholders are cached in `edit/build/placeholders/`: delete them after `design.json`
  changes.
- **The render guard** refuses a full render while any shot resolves to a placeholder, and prints
  each key still on one (`--allow-placeholders` for drafts).
- **Colour**: untagged H.264 sources are decoded as BT.601, because motion clips are encoded with
  ffmpeg's default BT.601 matrix and left untagged.
- **Handles and manifests**: motion clips carry a 0.5 s handle, honoured by the edit. Manifests
  are read by file name, so a stale entry cannot shadow the current file.
- **The first frame**: hold a designed still from motion as it is ([Phase 5](#phase-5-finishing)).
  Repairing a frame in the edit (replacing its background, say) leaves artefacts; fix it at the
  source.
- **The open and the reveal**: a hold on the first frame with a fade, then the logo reveal in a
  silent window, then a narration line (the product name) once the logo is settled.
- **The end card**: the logo, tagline and URL as `BRAND.md` and the editor's part of the
  HANDBOOK "Brand" section describe them, usually a motion scene; the credit line dissolves in
  after it.
- **The end**: a real fade to black (~2.5 s, eased), then a pure-black hold. Transparency, grain
  and dither fade with the picture, or black stays above Y=16; verify with `signalstats`.

## Transitions

A `Segment` enters with a `Transition(kind, dur, direction, ease)`:

| `kind`     | What it does                                                                                  |
| ---------- | --------------------------------------------------------------------------------------------- |
| `cut`      | the new segment replaces the old at once                                                      |
| `dissolve` | a crossfade over `dur` seconds                                                                |
| `push`     | the old segment travels out along `direction` as the new one enters, with motion blur         |
| `zoom`     | the old segment scales up and fades out; the new one grows from slightly smaller and fades in |

`ease` names the curve (`quint` by default, `sine` for a gentle one). The mix adds a quiet whoosh
to `push` and `zoom` only. The background stays the same through every transition. Pick a small
set in the shared spec, give each a meaning (a push for the next step in a sequence, a dissolve
for a change of subject, say), and dissolve the credit line in.

## The mix

`edit/mix.py` writes `edit/out/mix.wav`: the narration chain (high-pass, presence, de-essing, light
compression, voice at about -18 LUFS), the music ducked 8.5 dB under speech (rhythm stems only
4.5 dB) with a hold and smooth ramps so gaps swell back up, a further melodic duck in the EDL's
`BUSY` scenes where a dense score meets dense narration, quiet UI sound design (whooshes on
`push` and `zoom` transitions, ticks on cursor clicks) placed from the edit decision list, and
mastering to -14 LUFS integrated with true peak under -1 dBTP (the limiter sits at -1.6 dBTP to
leave margin for AAC overshoot).

Every part is optional. Without narration there is no voice bus and nothing ducks the music.
Without a soundtrack (`music/out/soundtrack.wav`) there is no music bed. With neither, the sound
design keeps its own level: there is no loudness target, only the limiter. With no sound design
either, the mix is silence of the EDL's length, so the master still gets an audio track.

## Subtitles and credits

`edit/subs.py` builds `outputs/<stage>-<slug>-vN.srt` from the narration scripts
(`narration/NN_name.txt`) and the whisper word times (lines of at most 42 characters). A video
without narration has no subtitles: `subs.py` writes nothing and says so.

Credits are data, so the on-screen card and the video description
(`outputs/<stage>-<slug>-vN-credits.txt`, from `edit/credits.py`) cannot disagree:

- `music/CREDITS.md` records each sample library: source, files, licence, what it is used for.
  `credit_data.music_samples()` credits only the libraries whose licence requires attribution
  (CC0 ones are left out), Salamander only when `music/manifest.json` `sample_libraries` lists
  it, and none without a soundtrack.
- `broll/CREDITS.md` gets a `## <clip name>` section with `- Title:`, `- Channel:`, `- URL:`,
  `- Licence:` and `- Range used:` lines for every CC BY clip. `credit_data.broll()` credits only
  clips with a section, so generated clips (no section) get no row, and a video without b-roll
  none.
- `edit/credits.json` (optional) holds the description's title line and any row the human asks
  for: `{"title": "<product>: introduction", "rows": [["Narration", "Gemini TTS (<voice>)"]]}`.
- `credit_data.lines(BROLL_CLIPS)` gives the on-screen lines; `cards.credit_line(name, lines,
  size=22)` draws them as a full-frame transparent card the EDL places as `image:<name>`. `size`
  is the text height in design px (the line pitch scales with it); raise it over a busy or
  colourful ground, where 22 px is hard to read.

Show only what a licence requires: CC BY samples or footage, and a typeface only if its licence
asks for on-screen credit (most font licences, the SIL Open Font License among them, do not). No
row for generated b-roll, CC0 samples or the narration, and no row naming an AI tool. The credits
are real end credits on screen, never a box that points elsewhere. The card is one subtle centred
line on the background (about 22 px, secondary text colour; no heading, rule or page number),
dissolved in from the end card and short: about 5 s including the fade to black. Each further
credit adds a line, never a page that outstays its content.

## Review and QA

### How the lead reviews without watching

Claude Code's Read tool shows images, so every sheet and crop can be looked at. The commands run
on the latest preview, `outputs/draft-<slug>-vN.mp4` (a master is `outputs/final-<slug>-vN.mp4`):

```bash
# a frame every 2 s as one image
ffmpeg -i outputs/draft-<slug>-v1.mp4 -vf "fps=1/2,scale=384:-1,tile=6x6" -frames:v 1 sheet.png
# a single frame at a moment that changed
ffmpeg -ss 26.0 -i outputs/final-<slug>-v1.mp4 -frames:v 1 frame.png
# a 200 % crop to inspect a fine defect
ffmpeg -i outputs/final-<slug>-v1.mp4 -frames:v 1 -vf "crop=600:360:950:380,scale=1200:-1" crop.png
# does a transparent clip really composite? decode the movie, not a still
ffmpeg -ss 11 -i motion/out/scene_alpha.mov -f lavfi -i color=0x<background>:s=1920x1080 -filter_complex "[1][0]overlay" -frames:v 1 over.png
# loudness and true peak
ffmpeg -i outputs/final-<slug>-v1.mp4 -af ebur128=peak=true -f null - 2>&1 | rg 'I:|Peak:'
# is the end really black? (Y=16 in tv range)
ffmpeg -ss 182.2 -i outputs/final-<slug>-v1.mp4 -frames:v 1 -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null -
```

The editor's own tools do the same from the edit: `render.py --contact --every 2` (sheets at
`outputs/draft-<slug>-vN-contact-NN.png`, 24 frames each), `render.py --frames <t...>`,
`render.py --range A B`. Motion has `--contact` and `--still t --over <hex>`. The listening judge
(optional; it needs the API key) answers questions about audio and video; without it, audio is
reviewed by the loudness and silence measurements ([The listening judge](#the-listening-judge)).

Defects found this way before the human sees them: blocky glyphs in a blurred log, a clipped label
at the frame edge, text overflowing its card, a logo reveal layered over text that should have
gone, a double exposure where an end card dissolves over the previous shot, a beat where a
scene's frame is nearly empty. Static previews hide what motion shows: check contact sheets
across time.

### QA checklist (every master)

```bash
M=outputs/final-<slug>-v1.mp4   # from the project root
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,color_space -of csv=p=0 $M
ffmpeg -hide_banner -nostats -i $M -af ebur128=peak=true -f null - 2>&1 | rg 'I:|Peak:'
for t in 199.6 199.9; do ffmpeg -loglevel error -ss $t -i $M -frames:v 1 -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - ; done   # expect YAVG=16 (use times near your end)
ffmpeg -loglevel error -y -i $M -frames:v 1 -vf "crop=600:360:950:380,scale=1200:-1" /tmp/m.png   # 200 % crop of the first frame around a fine detail of the logo
ffmpeg -loglevel error -y -i $M -vf "fps=1/2,scale=384:-1,tile=6x6" -frames:v 1 /tmp/sheet.png
```

Also check:

- the file's mtime is later than every upstream asset it should contain;
- frame 0 is the designed first frame;
- nothing from the "Rejected styles" list in `NOTES.md` anywhere;
- the logo is one of the files in `brand/logo/`, within `BRAND.md`'s clear space and minimum size;
- every diagram shows exactly the fixture story's data;
- text never overflows its card;
- motion alpha files verified by decoding the `.mov` itself (stills can hide accumulation bugs)
  and compositing over `design.json`'s `background` and over the shot it sits on in the edit;
- every claim in the narration and the on-screen text is true of the product;
- loudness -14 LUFS integrated with narration or music (a mix of sound design alone has no
  target), true peak at most -1 dBTP; the last frames at Y=16.

## Encoding

**Target format**: 1920x1080 at the project's frame rate (`project.json` `fps`, default 30), H.264 High (yuv420p,
BT.709, tv range), AAC 48 kHz stereo, -14 LUFS integrated with true peak at most -1 dBTP,
faststart. Frame 0 is a designed image; the video ends on a fade to pure black (Y=16).

### The master

`edit/render.py` pipes the compositor's frames to ffmpeg as raw RGB and muxes in `out/mix.wav`,
writing `outputs/final-<slug>-vN.mp4`. The full render encodes with x264 at `-crf 14` and
`aq-mode=3` (adaptive quantisation that biases bits toward dark areas), converts to tv-range
BT.709 4:2:0, tags the stream as BT.709, and adds 320 kb/s AAC at 48 kHz. `--preview` renders,
and full renders with `--fast`, swap the video encoder for a faster one: `h264_nvenc -preset p5
-cq 20` on Linux when a test encode shows NVENC works, `h264_videotoolbox -b:v 20M` on macOS,
`libx264 -preset veryfast -crf 20` otherwise.

```bash
# the full render, as run from edit/; render.py also trims the audio input to the rendered range (-ss/-t)
ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1920x1080 -r 60 -i - \
  -i out/mix.wav \
  -vf "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv" \
  -c:v libx264 -profile:v high -preset slow -crf 14 -x264-params aq-mode=3 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -map 0:v -map 1:a -c:a aac -b:a 320k -ar 48000 -shortest \
  -movflags +faststart outputs/final-<slug>-v1.mp4
```

### The share copy

For social media and messaging, `uv run render.py --share` (from `edit/`) transcodes the latest
final master to `outputs/final-<slug>-vN-share.mp4`; `--revision vN` picks another. It keeps
1920x1080, drops a higher frame rate to 30 fps (a master at 30 fps or less keeps its rate),
and uses H.264 High Profile, Level 4.1, 8-bit 4:2:0 video at `-crf 21` with AAC-LC stereo audio
at 160 kb/s (a silent master stays silent) in an MP4 container, which Apple devices play.
`-crf 21` sets visual quality rather than a fixed bitrate; `+faststart` moves the MP4 index to
the front so web playback starts promptly.
The command refuses to overwrite an existing share copy: remove it to regenerate. With no final
master it stops and says so.

Measured on one 205.9 s master:

| Property            | Share copy                                           |
| ------------------- | ---------------------------------------------------- |
| Duration            | 205.888 s                                            |
| Frame size and rate | 1920x1080, 30 fps                                    |
| Video               | H.264 High, Level 4.1, `yuv420p`, about 2.41 Mb/s    |
| Audio               | AAC-LC, 48 kHz stereo, nominal 160 kb/s              |
| Container           | MP4 with `+faststart`                                |
| File size           | 66.7 MB, about 90.5 % smaller than the 704 MB master |

A full decode of the share copy completed without errors.

## Records the video adds

`NOTES.md`, `HANDBOOK.md`, "Rejected styles", `claims.md` and `scenarios.md` are in `README.md`
"Project records". Three more belong to the video.

### `edit/ISSUES.md`: the editor's issue log

Asset, problem, what the edit needs. Status is re-checked on every render; `render.py` prints any
key still on a placeholder. One bullet per issue: the asset and what is wrong in bold, then what
the edit needs and who was asked.

```markdown
# Editor issues (asset, problem, what the edit needs)

## Open

- **motion `sNN_name_alpha.mov` (time stamp): alpha nearly opaque over the whole frame with white
  RGB**, so the scene composites as a white frame. Asked motion to re-render (ground alpha 0). The
  preview for the lead is held on it.
- **unused captures:** list captures that exist but the cut does not use, and why.

## Resolved

- music: soundtrack and stems match the current grid (duration); note any stale stem that is ignored.
- a fact in a scene was confirmed correct by the lead (record it so it is not asked again).
- web manifest delivered: marks and cursor tracks are wired (list each clip and its mark).
- a rejected motif was removed from the edit (list the transitions and elements that replaced it).
```

### The video's `HANDBOOK.md` parts

Besides the sections in `README.md` "Project records", the video's HANDBOOK holds the timeline
table (one row per scene, from `timeline.json`) and the per-workstream tables: motion scenes
(name, window, duration, content), web clips (length, key marks), TUI clips (size, key times),
b-roll picks, the score's tempo, grid and arc.

| Scene key | Start | Narration window | Narration text           | Picture                                                                                                              |
| --------- | ----- | ---------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| open      | 0.0   | `<start>-<end>`  | the problem statement    | first-frame hold with a fade, a motion scene on its own ground, b-roll for the last beat, the logo reveal from `<t>` |
| (insert)  | n/a   | `<start>-<end>`  | "Introducing <product>." | during the logo reveal, once the logo is settled                                                                     |
| pitch     | `<t>` | `<start>-<end>`  | what the product is      | a motion scene                                                                                                       |
| ...       |       |                  |                          | one row per scene: capture clips, motion scenes, insets and the marks they sync to                                   |
| close     | `<t>` | `<start>-<end>`  | tagline, licence line    | the last capture dissolves to the end card                                                                           |
| credits   | `<t>` | n/a              | n/a                      | one subtle centred line on the background; fade to black; pure black hold                                            |

### `COSTS.md`: the cost estimate

A running estimate of what the paid Gemini calls cost: TTS for narration, the listening judge,
and Omni for b-roll. Every one of them is billed, auditions, rejected takes, re-takes, retries and
failed shots included, so every one is counted.

The API returns token counts with each response, never a price. The scripts that call it log
those counts, and `tools/costs.py` prices them:

- **`usage.jsonl`** (project root): one JSON line per call, appended by `tts.py`, `tools/listen.py`
  and `tools/genvideo.py` through `tools/usage_log.py`. Each line holds the time, the script, the
  model, the tokens in and out by modality and any thinking tokens, plus the output file (TTS), the
  files judged (the judge), or the shot, whether a video came back, and the clip length (b-roll).
  Each call also prints its counts. Nobody edits this file; it is a record.
- **`rates.json`** (project root, the lead's): the prices from
  <https://ai.google.dev/gemini-api/docs/pricing>, with the date they were read. Token rates are
  USD per million tokens, either one number for every modality or a table by modality (`text`,
  `audio`, `video`, `image`); thinking tokens are priced as text output. A model priced by the
  second of video takes `per_second` instead. `null` marks a rate not filled in yet.
- **`COSTS.md`** (project root): generated by `uv run tools/costs.py` from the project root. A
  total per workstream, then one row per day, workstream and model with calls, failed calls,
  tokens, video seconds and the estimate. Any model or modality without a rate counts as $0 and is
  listed under "Unpriced", and the script prints it: add the rate and run it again. Never edit
  `COSTS.md` by hand.

```json
{
  "source": "https://ai.google.dev/gemini-api/docs/pricing",
  "read": "<date>",
  "models": {
    "gemini-3.8-flash-tts": { "input": null, "output": { "audio": null } },
    "gemini-3.5-flash": { "input": { "text": null, "audio": null }, "output": null },
    "gemini-omni-1.1-flash": { "per_second": null }
  }
}
```

The lead writes `rates.json` at kickoff when the video has narration or b-roll, with an entry for
every model the project calls (the judge's model too), and re-reads the pricing page when a
session resumes after a long gap. It runs `tools/costs.py` after every batch of calls and gives
the human the total with each preview and before a large batch (a new shot list, a full
re-record), with an estimate for that batch from the rows of a similar earlier one.

### `METRICS.md`: how long each operation took

- **`metrics.jsonl`** (project root): one JSON line per run, appended by every entry point through
  `tools/metrics.py`: `capture-web`, `capture-tui`, `narration` (`tts.py`, `process.sh`,
  `build_timeline.py`), `judge` (`tools/listen.py`), `broll` (one line per paid attempt, retries
  included, plus the whole run), `motion` (per scene and mode), `music`, `edit` (`words.py`,
  `mix.py`, `subs.py`, `credits.py`, and `render.py` as `render final`, `render preview`,
  `render range`, `render contact`, `render frames` or `render share`) and `blog`.
- **`METRICS.md`** (project root): generated from the log on every run, never hand-edited: a table per
  category, a table per operation (runs, failed, total, mean, max, last run) and the last 20 runs.
  `uv run tools/metrics.py` rebuilds it; `uv run tools/metrics.py run <category> <operation> -- <cmd>`
  times a shell step and exits with its status. A log that cannot be written prints one `WARN metrics`
  line and the operation carries on.

## Mistakes and pitfalls

Shared mistakes are in `README.md` "Mistakes and pitfalls"; capture ones in `guides/capture.md`.

| Area      | What went wrong                                                                                                                 | Rule                                                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Brief     | The lead redirected the composer toward the wrong genre, misreading a music reference the human gave                            | Ask what a reference means to this person, or offer short excerpts early                               |
| Narration | A hushed, then a bored, then an eager narrator                                                                                  | Audition a few directions on the same lines and let the human pick; keep style directions short        |
| Narration | The lead chose a tone itself and rendered several takes in it before asking the human                                           | Ask the human what tone of voice they want first; render variants for the human to choose from         |
| Narration | TTS read `<short pause>` aloud, dropped words, added vocal fry                                                                  | Render 2-3 takes and judge each against the expected text                                              |
| Narration | A sentence spliced into an approved take was audible                                                                            | Use one take whole                                                                                     |
| Narration | A re-take of an early line would have shifted every later scene                                                                 | Give later sections a `pin` in `sections.json`                                                         |
| Narration | The TTS client was garbage-collected mid-request                                                                                | Keep `client = genai.Client()` in a local variable                                                     |
| Narration | The free tier's 10 TTS requests a day ran out during auditions                                                                  | Enable billing; batch auditions                                                                        |
| Script    | Cheesy or inaccurate lines (anthropomorphism, a setting the product does not have, a component called by the wrong name)        | Check every claim against the product's source or docs before recording                                |
| Judge     | Scores drifted between identical calls; it heard voiceovers in instrumentals                                                    | Use it for direction and A/B comparisons, never single-call pass or fail                               |
| Music     | A new sustained layer entering on the logo reveal was rejected                                                                  | Let the hook and the pulse carry an arrival                                                            |
| Review    | A preview containing an already-rejected animation reached the human (the edit still referenced it)                             | The lead reviews every preview first; purge rejected elements from every agent's work                  |
| Review    | A b-roll agent's "no logos" claim missed two branded clips                                                                      | The lead checks every contact sheet itself                                                             |
| Review    | Card and node text overflowed its card in a pull-back graph                                                                     | Size cards from measured content                                                                       |
| Fixtures  | A redundant dependency edge in the fixture story, found after capture                                                           | Review the fixture data for sense before capturing anything                                            |
| Motion    | Stills looked right but the encoded transparent movie was opaque white (GL blending left on by skia, framebuffer never cleared) | `fbo.clear()` and disable blending before every shader pass; verify transparency by decoding the movie |
| Motion    | `GrDirectContext.MakeGL()` returned `None` under moderngl's EGL context on Linux                                                | `GrDirectContext.MakeGL(skia.GrGLInterface.MakeEGL())` on Linux; `MakeGL()` on macOS                   |
| Motion    | Blocky text from 8-bit accumulation of a temporal blur                                                                          | Accumulate in half-float (RGBA F16) render targets                                                     |
| Edit      | A background-replacement step in the edit drew a smudge on the logo in the first frame                                          | Render the asset at the source instead of repairing it downstream                                      |
| Edit      | Grain and dither added after the fade kept black frames above Y=16                                                              | Fade them with the picture; check with `signalstats`                                                   |
| Edit      | Untagged motion clips decoded with the wrong matrix                                                                             | Decode untagged H.264 as BT.601                                                                        |
| Credits   | A credits card held for 11 s for a single credit                                                                                | One subtle line, about 5 s with the fade                                                               |
| B-roll    | Veo output and CC BY stock were rejected as poor or off-message                                                                 | Generate with Gemini Omni                                                                              |
| B-roll    | An outdated `yt-dlp` only got 360p streams                                                                                      | Upgrade it before searching                                                                            |

## Snippets

The listening judge (`tools/listen.py`), in essence:

```python
from google import genai

client = genai.Client()
parts = []
for path in files:
    uploaded = client.files.upload(file=path)
    parts += [f"File: {path}", uploaded]
parts.append(question)
print(client.models.generate_content(model="gemini-3.5-flash", contents=parts).text)
```

Finding pauses in a take, to cut a sentence without re-recording:

```bash
ffmpeg -i take.wav -af silencedetect=noise=-40dB:d=0.25 -f null - 2>&1 | rg -o 'silence_(start|end): [0-9.]+'
ffmpeg -i take.wav -af "atrim=0:20.35,afade=t=out:st=20.15:d=0.2" take_trim.wav
```

Deterministic browser capture and terminal rendering, in outline, are in `guides/capture.md`.
