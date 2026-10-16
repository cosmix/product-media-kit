---
name: mediatime
description: Kick off a product media project, or add a medium to one. Asks which media to make (a video, a blog post or both), saves a video's frame rate and piano with configure.sh, checks the machine with setup.sh, interviews the human, sets up the Gemini key and the brand, and writes project.json, NOTES.md, rates.json and the reuse inventory before Phase 1. Use on "/mediatime", "let's make a video", "write a blog post", "let's write the post", "start the project", on the first session of a project, and when the human asks for the other medium ("now a blog post too", "make a video from this post").
---

# Mediatime

The kickoff. Run it in the first session of a project (no `NOTES.md`, or `media` empty in
`project.json`) whatever the human said first, and again whenever the human asks for a medium the
project does not have yet. You are the lead. README "Kickoff" and "Reuse between media" give the
reasons; this file gives the steps. Do them in order and skip any question the human or the
records already answered.

## 1. Read what exists

Read `project.json` (`{"slug": ..., "media": [...], "fps": ..., "piano": ...}`; `fps` and `piano`
are absent until saved) and `NOTES.md` if present. List what the
project already holds, with your file tools:

```text
captures/*/manifest.json       web, tui, motion, broll, video captures
motion/out/manifest.json       rendered motion scenes
narration/*.txt                the script
broll/candidates/              b-roll picks
outputs/, outputs/blog/        rendered and built deliverables
claims.md, scenarios.md, BRAND.md, design.json, rates.json, HANDBOOK.md
```

`project.json` missing means the project was not made by `install.sh`: tell the human to run
`./install.sh <this folder> --force` from the kit and stop. Note the media already made and the
artefacts each left; step 7 needs them.

## 2. Which media

Ask what to make: a video, a blog post, or both. For both, ask which comes first; the second
reuses what the first produced. When the project already has a medium, ask only whether to add
the other. Out of scope from here on: a medium not chosen gets no question, no check, no role.

## 3. Video choices, then check the machine

With a video, ask these together, before any download or render. Answers already saved in
`project.json` (`fps`, `piano`) stand; reuse them without asking.

- **Frame rate**: suggest 30 fps; any whole number from 1 to 120. It applies to the captures,
  motion graphics and the master.
- **Music**: whether the video has music. The sample libraries are needed only for a score with
  sampled instruments: VSCO-2 CE, about 2.2 GB.
- **Piano**, only with music: VSCO's upright (CC0, no attribution), unless the human explicitly
  picks the Salamander grand piano. Explain its duty first: CC BY 3.0, credited on screen and in
  the video description; 1.2 GB more to download. Never select or download Salamander without
  that explicit choice.

Save them before the setup run: `./configure.sh --fps <N> --piano <vsco|salamander>`. A video
without music saves `--piano vsco`. If the human asks you to decide, save 30 fps and VSCO. Record
the choices in `NOTES.md` (step 7). `project.json` is the source of truth for both from here on:
where another instruction names 60 fps, the saved rate wins. To change them later, rerun
`./configure.sh` (it keeps `slug` and `media`), then `./setup.sh` for a new piano, and rerender
what the change touches.

Then, with `<media>` as `video`, `blog` or `both`:

1. Run `./setup.sh --check --for <media>`.
2. Run `./setup.sh --for <media>`, with `--no-samples` when the video has no music or the human is
   unsure (rerun without the flag later to fetch the samples).
3. `setup.sh` needs no administrator rights and neither do you. Never run sudo and never try to
   install a system package (ffmpeg, Mesa, fonts, a command-line tool) yourself, and do not ask
   the human for `!` commands. If a system dependency is MISSING, stop and ask the human to run
   `./system-deps.sh` in a separate terminal outside Claude Code (`./system-deps.sh --for blog`
   for a blog-only project), or to give an administrator the output of
   `./system-deps.sh --dry-run`. When they say it is done, rerun `./setup.sh --check --for <media>`.
4. Repeat until the summary shows `0 MISSING`. WARN lines are optional; explain one only when it
   matters for this project (README "Setup" lists what each affects; for a post, ffmpeg matters
   only when it has clips).

## 4. The interview

Ask in a few grouped questions, never one long form. Ask only what changes the plan, decide the
rest and report it. When adding a medium, the shared group is answered already: confirm it in one
line and ask only the new medium's group.

**Shared group** (both media):

- **Product**: what it does in a line, who it is for, and where its source and docs are (a path
  or URL; read-only). Which features must appear.
- **PRD**: for a post always; for a video when there is one. A path, a URL, or a file they drop in
  the project folder. Read it in full before the next group.
- **Audience and goal**: who watches or reads, where (site, social, a launch, the company blog),
  and what they should do or feel afterwards.
- **Captures and theme**: web, terminal or both; light or dark. How to run the web frontend (a
  built `dist` folder for the mock server, or the URL of a running instance for live mode) and the
  CLI binary (README "Code that needs your product").
- **Guidance**: tone, references (ask what each means to them), things to avoid, anything already
  decided.
- **Deliverables**: what they want at the end (each medium's group below lists the options).

**Video group:**

- **Length and format**: about two minutes by default (the kit makes two to three); 1920x1080 at
  the frame rate saved in step 3; whether they also want the smaller share copy for social media.
- **Narration, music, b-roll**: each optional, any combination or none. A choice not made is out
  of scope: no role, no brief, no questions about it.
  - Narration: the narrator's character and the tone of voice they want (warm and confident,
    upbeat, calm and authoritative, ...), and that a Gemini key is needed. Ask the tone before
    rendering any voice.
  - Music: genre and feel, and how to make it (compose with real sample libraries, or a local AI
    model with a non-commercial licence).
  - B-roll: the kind of shots, generated with Gemini Omni.
- **Deliverables**: the master, the share copy, subtitles (only with narration), credits, any
  other files.

**Blog group:**

- **Length and shape**: 1,200 to 1,800 words by default; a launch announcement, a how-to or a deep
  dive.
- **Platform**: plain GitHub-flavoured markdown by default; the front matter fields, when the site
  that publishes it needs some.
- **Clips**: short GIF clips yes or no (they need ffmpeg).
- **Deliverables**: the markdown and its images by default; anything else (a summary for social
  media, title options).

**Adding the video to a blog project**: the viewport changes from 1440x900 to 1920x1080 for every
capture. Ask whether to recapture everything for both media or pin `VIEWPORT = (1440, 900)` in
`fixtures/web/product.py` and keep the post's stills.

## 5. The Gemini key

Narration, generated b-roll and the listening judge need `GEMINI_API_KEY`. When one of them is
wanted and `./setup.sh --check` shows the key as not set:

1. Tell the human to create a key at https://aistudio.google.com/apikey with billing on: the free
   tier allows 10 voice requests a day, which runs out during voice auditions.
2. Tell them to add `export GEMINI_API_KEY=<key>` to their shell profile (`~/.zshrc` on macOS,
   `~/.bashrc` on most Linux machines), then quit, open a new terminal and start `claude` in the
   project folder again.
3. Never ask them to paste the key into the chat.
4. Tell them that narration and b-roll are billed per request and that you keep a running
   estimate in `COSTS.md`.

Write the decisions so far to `NOTES.md` before they restart. After the restart, read `NOTES.md`
and resume at the step it leaves off. Without a key, review audio with ffmpeg measurements. A post
needs no key.

## 6. The brand

- `BRAND.md` exists: run the `brand` skill to generate `design.json` and the HANDBOOK "Brand"
  section, with a part per role of each chosen medium; put its gap and conflict questions to the
  human with the interview.
- Not there: offer to write `BRAND.md` with them through the `brand` skill (README "Brand"; the
  human adds the logo and font files to `brand/`), or proceed with neutral defaults if they have
  no brand.
- Adding a medium: rerun the `brand` skill so the HANDBOOK gains the new medium's parts.

## 7. Write the records

All of these are lead-owned files; write them yourself with the Edit or Write tool.

- **`project.json`**: set `media` to the chosen media in the agreed order (`["video", "blog"]`,
  `["blog"]`, ...), keeping `slug` as `install.sh` wrote it and `fps` and `piano` as
  `./configure.sh` saved them. Adding a medium appends it. The capture engines and `setup.sh` read
  it for their defaults.
- **`NOTES.md`**: the decision log (README "`NOTES.md`: the decision log"). A "Kickoff" section
  with the shared decisions, then one block per medium, then the "Rejected styles" list seeded
  from `BRAND.md`, "Things to avoid". When adding a medium, append its block; change nothing above.
- **`rates.json`**, when the video has narration or b-roll: the current prices from
  https://ai.google.dev/gemini-api/docs/pricing, with the date read, an entry for every model the
  project calls (the judge's too) (`guides/video.md`, "`COSTS.md`").
- **The reuse inventory**, when a medium joins a project that already has one: a "Reuse
  inventory" section in `NOTES.md`, one bullet per artefact, each marked *reuse as is*,
  *recapture* (with the command) or *not needed*:
  - each `captures/<source>/manifest.json`: its scenarios and labels, and for each clip the
    profile that made it (a `video` key means video or both; a `webm` key means blog or both);
    clips the new medium needs from the other profile are recaptured with `--for both`;
  - `motion/out/manifest.json`: scenes whose stills or frames the post can take with
    `postkit add`;
  - the narration script (`narration/NN_*.txt`): terms and the pitch wording the post reuses;
  - `claims.md`: claims already verified, with the new medium's "Used in" to fill;
  - `scenarios.md`: scenarios whose Media column becomes `both`;
  - b-roll picks in `broll/candidates/`, and the finished cut in `outputs/`, for `postkit add`;
  - the viewport decision from step 4.

## 8. Start Phase 1

Begin Phase 1 of `guides/video.md` or `guides/blog.md`, for the first medium in `media` (or the
medium just added). Learn the product from its docs or PRD and code first, and start `claims.md`:
both media take their claims from it. Tell the human what comes next and what they will review
first (the script, or the outline and the scenarios).
