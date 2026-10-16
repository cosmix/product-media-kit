---
name: install
description: Install the kit into a new project folder, from the kit folder. Asks where the project goes and what to make (a video, a blog post or both), copies the kit with install.sh, shows the system packages the human must install in a second terminal, saves a video's frame rate and piano, runs setup.sh until nothing is MISSING, helps with the Gemini key and ends with the command that starts the project. Use on "/install", "install the kit", "set up a project", "new project".
---

# Install

Run it in the kit folder (the one holding `install.sh`), once per project. You are the installer:
ask a few grouped questions, do everything that needs no password yourself, and tell the human
exactly what to type for the rest. Skip any question the human already answered. `/begin` runs
afterwards in the project folder and does the interview.

## 1. Ask

Ask these together:

- **Where**: the project folder; suggest `~/<product>-launch`. The folder name becomes the
  project's slug and names the finished files: `install.sh` lowercases it and turns other
  characters into single hyphens (`~/Acme Launch` gives `acme-launch`) and prints a note when it
  changed the name.
- **What to make**: a video, a blog post or both; for both, which comes first.
- **For a video**:
  - **Frame rate**: suggest 30 fps; any whole number from 1 to 120.
  - **Music**: whether the video has music. The sample libraries are needed only for a score with
    sampled instruments: VSCO-2 CE, about 2.2 GB.
  - **Piano**, only with music: VSCO's upright (CC0, no attribution), unless the human explicitly
    picks the Salamander grand piano. Explain its duty first: CC BY 3.0, credited on screen and in
    the video description; 1.2 GB more to download. Never select or download Salamander without
    that explicit choice.
- **Gemini**: whether narration, generated b-roll or the listening judge is likely. It decides
  whether step 7 applies.

If the human asks you to decide: 30 fps and VSCO.

## 2. Copy the kit

When `<dir>/project.json` exists, the install is done (the human may be running `/install` again
after a restart): skip to step 3. Otherwise run:

```bash
./install.sh <dir> --no-system
```

Do not pass `--fps` or `--piano` here: they make `install.sh` run `configure.sh`, which step 5 does
once the machine is ready. Read the output; relay the slug note if there is one.

## 3. System packages

With `<media>` as `video`, `blog` or `both`, run:

```bash
<dir>/system-deps.sh --dry-run --for <media>
```

Show the human the packages it lists. Nothing missing: go to step 5.

Never run sudo, never run `system-deps.sh` without `--dry-run` yourself, and never ask the human
for `!` commands: an interactive password prompt does not work through them. Ask the human to run
this in a separate terminal outside Claude Code (`--for blog` for a blog-only project) and say
when it is done:

```bash
<dir>/system-deps.sh
```

Without administrator rights, give the administrator the dry-run output instead. When the human
says it is done, run the dry run again and repeat until nothing is missing.

## 4. Tools just installed

When `uv` (or Homebrew on a Mac) was just installed and the shell does not find it, try its usual
path: `~/.local/bin/uv`, `/opt/homebrew/bin/brew`. When it is still missing, ask the human to quit
Claude, open a new terminal, `cd` to the kit, start `claude` and type `/install` again: step 2
makes that resume.

## 5. Save the choices

For a video, run `<dir>/configure.sh --fps <N> --piano <vsco|salamander>`. A video without music
saves `--piano vsco`. Then write `media` into `<dir>/project.json` with the Edit tool: an array in
the agreed order (`["video", "blog"]`, `["blog"]`, ...), keeping `slug`, `fps` and `piano`. `/begin`
reads it and does not ask again.

## 6. Set up the machine

```bash
<dir>/setup.sh --check --for <media>
<dir>/setup.sh --for <media>
```

Add `--no-samples` to the second command when the video has no music or the human is unsure (the
samples can be fetched later by rerunning without it). Repeat until the summary shows
`0 MISSING`; a MISSING system package sends the human back to step 3. WARN lines are optional:
explain one only when it matters for this project (for a post, ffmpeg matters only when it has
clips). A video without captures ignores the Chromium, tmux and terminal-font WARNs ("web/terminal
captures only").

## 7. The Gemini key

Needed for narration, generated b-roll and the listening judge; a post needs none. When one is
likely, tell the human to create a key at https://aistudio.google.com/apikey with billing on (the
free tier allows 10 voice requests a day, which runs out during voice auditions) and to pass it
when starting `claude` in the project (step 8). Never ask them to paste the key into the chat.

## 8. Hand over

End with exactly what to type, in a new terminal when a tool was just installed:

```bash
cd <dir> && claude                         # without a Gemini key
cd <dir> && GEMINI_API_KEY=<key> claude    # with one
```

then `/begin`. Name the media and the saved choices in one line so the human can correct them.
