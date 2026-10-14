# Making a product video: the human's guide

This kit enables you to create a two-to-three-minute intro or demo video for a piece of software from code alone. A team of Claude Code agents writes the script, records the narration, composes the score, draws
the motion graphics, captures your product, generates b-roll and edits the cut. You answer
questions and review previews. Nothing is edited by hand in a video editor, so a change you ask for
is applied by re-rendering.

The video can have narration, music and b-roll in any combination, or none or any combination of them, over motion graphics and captures of your product. You choose when Claude asks.

## What you need

- **A computer**: macOS (Apple Silicon or Intel), or Linux with any GPU (NVIDIA, AMD, Intel). A
  machine or VM without a GPU works too; renders are much slower.
- **Disk space**: about 25 GB free, or about 17 GB if the video has no music samples.
- **Claude Code**, installed and logged in, with access to Opus:

  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```

- **Your product**: its repository or docs, and for UI captures a build of its web frontend or
  its command-line program. Claude only reads them.
- **A Gemini API key**, only if you want a narrated voice, generated b-roll or the listening judge
  (Claude checks audio by ear through it). Get one at <https://aistudio.google.com/apikey> and
  enable billing: the free tier allows only 10 voice requests a day, which runs out while voices
  are auditioned.
- **Optional**: your brand guidelines, logo and fonts.

You install nothing else yourself. The install step below puts the system packages on the
machine (ffmpeg, graphics and font packages, `uv`; on a Mac it installs Homebrew first if you
lack it), which needs administrator rights and asks for your password. Claude then downloads the
rest without a password: the Python environments, a browser for web captures, the speech-timing
model and the music sample libraries.

## Make a video

1. Get this kit folder onto your machine and open a terminal in it.
2. First, create the project folder for the video. The kit folder stays as it is for the next video. Then run:

   ```bash
   ./install.sh ~/<product>-video
   ```

   This copies the kit into the project folder you just created and then runs the project's `./system-deps.sh`,
   which lists the system packages it will install and asks `Continue? [Y/n]`. It may ask for
   your password once. It supports macOS (Homebrew), Debian and Ubuntu (apt) and Fedora (dnf). On
   another Linux it prints the package list and stops.

   The installer then asks for two choices: frame rate (press Enter for 30 fps)
   and piano library (press Enter for VSCO, which needs no attribution). Choose
   Salamander only if you want its grand piano and accept the required credit on
   screen and in the video description. These answers are saved for the project.

   Without administrator rights, add `--no-system` and give an administrator the output of
   `./system-deps.sh --dry-run` (run in the project folder). Run `./system-deps.sh` yourself
   later at any time, always in your own terminal.

3. Go there and start Claude Code (in a new terminal if the install just put `uv` or Homebrew on
   the machine, so the shell finds them):

   ```bash
   cd ~/<product>-video
   claude
   ```

4. Say that you want to make a video ("let's make a video" is enough). Claude takes it from
   there and never needs your password.

Work only in the project folder from now on.

## What to expect

**Setup.** Claude checks the machine and downloads what is missing, without administrator
rights. At project creation you choose the frame rate (30 fps by default) and
VSCO piano (no attribution) or Salamander grand piano (requires attribution).
The answers are saved in `project.json`; Salamander is used only with your explicit opt-in.
Before downloading samples it asks whether the video will have music. VSCO is about
2.2 GB to download; Salamander adds about 1.2 GB when selected. If a system package
is still missing, Claude stops and asks you to run
`./system-deps.sh` in a separate terminal, outside Claude Code, then continues.

**Questions.** Claude asks about your product and where its code or site is, who the video is for,
its goal, length and format, and whether you want narration, music and b-roll (each optional), the
voice if you want narration, and what files you want at the end. It asks in a few groups, and
only what changes the plan. If you tell it to stop asking and decide, it does.
For frame rate and piano, delegated choices are 30 fps and VSCO; Salamander always
requires your explicit consent. Saved answers are reused when you resume.

To change the choices later, tell Claude or run this inside the project:

```bash
./configure.sh --fps 24 --piano vsco
```

Use `--piano salamander` to opt in to the grand piano, then run `./setup.sh` to
download it. The chosen frame rate applies to captures, motion graphics and the
final video. Existing media keeps its old settings until it is rendered again.

**The API key.** If you want narration, generated b-roll or the listening judge, add this line to
your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on most Linux machines), open a new terminal
and start `claude` again in the project folder. Claude picks the work up where it stopped. Do not
paste the key into the chat.

```bash
export GEMINI_API_KEY=<your key>
```

**Brand.** You may put these in the project folder before you start, or any time later:

- `BRAND.md`: your brand guidelines in prose (voice, colours, typography, logo rules, music
  feel, things to avoid);
- `brand/`: the files, with `logo/` (SVG, or PNG at least 2000 px wide, a variant for dark and
  one for light backgrounds), `fonts/` (font files with their licences), and optionally
  `palette/` and `reference/` (images or videos of the brand in use).

Without them, Claude offers to write `BRAND.md` with you in a short interview, or you say you have
no brand and the video uses plain defaults: system fonts, white text on black, no logo. Change the
brand later by editing `BRAND.md` or `brand/` and telling Claude; it regenerates the look.

## Review

Claude checks every piece itself before it shows you anything, using still frames, contact sheets,
measurements and, with a Gemini key, an audio listener. You then get something to look at:

- a **script** to read and approve first, short sections one per scene;
- if the video has narration, first a question about the **tone of voice** you want, then
  **voice variants** in that tone to listen to and choose from. Claude picks for you only if you
  tell it to;
- **previews**: a small, fast render of the whole video or of a range, in `edit/out/preview.mp4`,
  and stills of scenes Claude points you to;
- the **final render** only after you approve the preview.

Reply in plain, short notes: "the opening is too slow", "the product is called X, not Y", "drop
the guitar", "keep everything but redo the logo animation". Claude writes each decision to
`NOTES.md` first, so it is not asked twice and a rejected idea does not come back, then applies it
through the whole pipeline. A replaced beat leaves the rest of the cut unchanged. Expect several
rounds. If you want Claude to stop asking and decide, say so.

Rendering takes a while, more without a GPU. Claude tells you what it is waiting on.

## Where the video lands

In the project folder, under `edit/out/`:

- `intro.mp4`: the master, 1920x1080 at your chosen frame rate (default 30 fps);
- `intro-share.mp4`: a smaller 30 fps copy for social media and messaging, when you ask for it;
- `edit/out/intro.srt`: subtitles, when the video has narration.

Claude also tells you the paths when it finishes. The project folder also holds the script,
`NOTES.md` (every decision), `HANDBOOK.md`, `COSTS.md` (the estimated spend on narration and
b-roll, when the video has them) and the code that renders everything, so a later session can
re-render or change the video.

## Coming back later

Run `claude` in the project folder again and say what you want to change. Claude reads its records
(`NOTES.md`, `edit/ISSUES.md`, `narration/timeline.json`) and resumes. If you started the first
session without the Gemini key, set it and restart `claude` before asking for narration.

## Updating a project to a newer kit

From the newer kit folder:

```bash
./install.sh ~/<product>-video --force
```

It overwrites the kit's files that already exist in the project and deletes nothing, then runs
`./system-deps.sh` again (add `--no-system` to skip that). It never
overwrites `.claude/settings.json`, `.gitignore`, `project.json`, `music/CREDITS.md` or `broll/CREDITS.md`, and it
leaves your `BRAND.md`, `brand/`, `design.json`, script and other project files alone, because the
kit has no files of those names. If Claude patched a kit file during the project, `NOTES.md` lists
the patch: ask Claude to re-apply it after the update. If the install is interrupted, run the same
command again.

Without `--force`, the install stops and writes nothing when any file already exists.

## If something goes wrong

- **Setup reports MISSING**: run `./system-deps.sh` in a terminal outside Claude Code (or give
  an administrator the output of `./system-deps.sh --dry-run`), then tell Claude to recheck.
  `./setup.sh --check` lists what is missing and changes nothing.
- **Narration, b-roll or the listening judge does not work**: check that `GEMINI_API_KEY` is set
  in the terminal you started `claude` from (`echo $GEMINI_API_KEY` prints it) and that billing
  is on for the key. Restart `claude` after setting it.
- **Renders are slow**: without a GPU this is expected. Ask for previews of a range instead of
  full renders.
- **The install stops with "files already exist"**: you are installing into a folder that holds a
  project. Use `--force` to update it, or pick a new folder.
- **A skill is not found** in a session that was already open when you installed: run
  `/reload-skills`, or restart `claude`.
- **A colour, font or logo looks wrong**: change `BRAND.md` or `brand/` and ask Claude to rerun the
  brand step.
- **Still stuck**: paste the failing line into the chat and ask Claude to diagnose it.

## Share the project

From the project folder:

```bash
./export.sh --output ../project.tar.gz
```

Choose an archive name that does not already exist, outside the project folder.
The compressed archive preserves media (including narration, captures, b-roll and
rendered videos), code, brand assets and saved choices. It omits downloaded sample
libraries, Python environments, node_modules, caches, Git history and local
credential files such as `.env`. An external or broken file link stops export;
copy that project asset into the folder and export again.

The recipient extracts the archive and opens a terminal in its project folder:

```bash
tar -xzf project.tar.gz
cd <extracted-project-folder>
./inflate.sh
```

This installs dependencies and downloads the selected libraries, browser and speech
model. It needs internet access and may ask for an administrator password for
system packages. With system packages already installed, use `./inflate.sh --no-system`.
`./inflate.sh --check` checks readiness without installing anything. Supply API keys
separately on the recipient's machine. Existing projects must be updated to this kit
version before they can use export.
