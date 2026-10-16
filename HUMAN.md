# Making a product video or blog post: the human's guide

This kit makes a two-to-three-minute intro or demo video for a piece of software, a blog post
about it, or both, from its code. A team of Claude Code agents reads your product's docs and code,
checks every claim against the code, captures your product's web UI and terminal, and for the
video writes the script, records the narration, composes the score, draws the motion graphics,
generates b-roll and edits the cut; for the post it writes the text and assembles it with its
screenshots and short clips. You answer questions and review. Nothing is edited by hand, so a
change you ask for is applied by rendering or capturing again.

The video can have narration, music and b-roll in any combination, or none of them, over motion
graphics and captures of your product. The post is plain markdown with its images in a folder
beside it, ready for a blog, a docs site or a repository. When you make both, the second reuses
what the first produced: the screenshots, the made-up data they show, the checked claims, the
logo animations.

## What you need

| You need            | For the video                                                                                     | For the blog post                         |
| ------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| A computer          | macOS (Apple Silicon or Intel), or Linux with any GPU; without a GPU it works, renders much slower | macOS, or Linux (Debian, Ubuntu, Fedora)   |
| Disk space          | about 25 GB free, about 17 GB without music samples                                               | about 2 GB free                           |
| A Gemini API key    | only for a narrated voice, generated b-roll or the listening judge                                | not needed                                |
| Your product        | its repository or docs                                                                            | its repository and the PRD of the feature |

For both:

- **Claude Code**, installed and logged in, with access to Opus:

  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```

- **For screenshots and clips of your product**: a build of its web frontend (the folder with
  `index.html`) or the address of a running instance, and its command-line program if the
  terminal is shown. Claude only reads your product; it never changes it.
- **Optional**: your brand guidelines, logo and fonts.

The Gemini key comes from <https://aistudio.google.com/apikey>. Enable billing: the free tier
allows only 10 voice requests a day, which runs out while voices are auditioned. Narration and
b-roll are billed per request; Claude keeps a running estimate in `COSTS.md`.

You install nothing else yourself. The install step below puts the system packages on the machine
(ffmpeg, graphics and font packages, tmux, `uv`; on a Mac it installs Homebrew first if you lack
it), which needs administrator rights and asks for your password. Claude then downloads the rest
without a password: the Python environments, a browser for the screenshots, and for the video the
speech-timing model and the music sample libraries.

## Start a project

1. Get this kit folder onto your machine and open a terminal in it. The kit folder stays as it is
   for the next project.
2. Choose a folder for the project and run:

   ```bash
   ./install.sh ~/<product>-launch
   ```

   This creates the project folder, copies the kit into it and then runs the project's
   `./system-deps.sh`, which lists the system packages it will install and asks
   `Continue? [Y/n]`. It may ask for your password once. It supports macOS (Homebrew), Debian and
   Ubuntu (apt) and Fedora (dnf); on another Linux it prints the package list and stops. The
   folder's name also names the finished files: `~/Acme Launch` gives `acme-launch`, and the
   install tells you when it changed the name.

   Without administrator rights, add `--no-system` and give an administrator the output of
   `./system-deps.sh --dry-run` (run in the project folder). You can run `./system-deps.sh`
   yourself later at any time, always in your own terminal.

3. Go there and start Claude Code (in a new terminal if the install just put `uv` or Homebrew on
   the machine, so the shell finds them):

   ```bash
   cd ~/<product>-launch
   claude
   ```

4. Type `/mediatime`. ("let's make a video" or "let's write the blog post" works too.) Claude
   takes it from there and never needs your password.

Work only in the project folder from now on.

## What to expect

**Which media.** Claude first asks what to make: a video, a blog post, or both, and for both which
comes first.

**Setup.** Claude checks the machine for what the chosen media need and downloads what is missing,
without administrator rights. For a video it asks whether there will be music before downloading
the music samples (about 3.4 GB). If a system package is still missing, Claude stops and asks you
to run `./system-deps.sh` in a separate terminal, outside Claude Code, then continues.

**Questions.** Claude asks about your product and where its code and docs are, who the video or
post is for and what they should do afterwards, the screenshots (web, terminal, light or dark),
your tone and things to avoid, and what files you want at the end. For a video it also asks the
length, whether you want narration, music and b-roll (each optional) and, for narration, the tone
of voice. For a post it asks for the PRD, the length and kind of post (a launch announcement, a
how-to, a deep dive) and the front matter your site needs. It asks in a few groups, and only what
changes the plan. If you tell it to stop asking and decide, it does.

**The Gemini key.** If you want narration, generated b-roll or the listening judge, add this line
to your shell profile (`~/.zshrc` on macOS, `~/.bashrc` on most Linux machines), open a new
terminal and start `claude` again in the project folder. Claude picks the work up where it
stopped. Do not paste the key into the chat.

```bash
export GEMINI_API_KEY=<your key>
```

**The PRD and the code.** Claude reads the docs or the PRD in full, then the parts of the code the
video or post talks about. Where they disagree, Claude asks you how to treat it. Nothing is
claimed that the code does not show.

**Brand.** You may put these in the project folder before you start, or any time later:

- `BRAND.md`: your brand guidelines in prose (voice, colours, typography, logo rules, how
  screenshots look, music feel, things to avoid);
- `brand/`: the files, with `logo/` (SVG, or PNG at least 2000 px wide, a variant for dark and
  one for light backgrounds), `fonts/` (font files with their licences), and optionally
  `palette/` and `reference/` (images or videos of the brand in use).

Without them, Claude offers to write `BRAND.md` with you in a short interview, or you say you have
no brand and the project uses plain defaults: system fonts, white text on black in the video, no
logo. Change the brand later by editing `BRAND.md` or `brand/` and telling Claude; it regenerates
the look.

## Review

Claude checks every piece itself before it shows you anything, using still frames, contact
sheets, measurements and, with a Gemini key, an audio listener. You get things to review in this
order.

**The video:**

- a **script** to read and approve first, short sections one per scene, and the made-up data the
  captures will show;
- if the video has narration, first a question about the **tone of voice** you want, then **voice
  variants** in that tone to choose from. Claude picks for you only if you tell it to;
- **previews**: a fast render of the whole video or of a range, and stills of scenes Claude points
  you to;
- the **final render** only after you approve the preview.

**The blog post:**

- **the plan**, before any screenshot is taken: `post/outline.md` (what the post says, section by
  section), the claims it makes with where in the code each comes from, and what each screenshot
  and clip shows;
- **the assembled post**, with its images. Open it in any markdown viewer or your editor's
  preview.

Reply in plain, short notes: "the opening is too slow", "the product calls it a workspace, not a
project folder", "the second screenshot is too busy", "drop the guitar", "keep everything but redo
the logo animation". Claude writes each decision to `NOTES.md` first, so it is not asked twice and
a rejected idea does not come back in either medium, then applies it. A change to one beat or one
image leaves the rest unchanged. Expect several rounds. If you want Claude to stop asking and
decide, say so.

Rendering takes a while, more without a GPU. Claude tells you what it is waiting on.

## Where things land

Everything you receive is in `outputs/` in the project folder. Each file names its stage (`draft`
for review, `final` for delivery), the project and a revision number, so every version you
reviewed stays:

- `outputs/draft-<project>-v2.mp4`: a video preview;
- `outputs/final-<project>-v3.mp4`: the finished video, 1920x1080 at 60 fps;
- `outputs/final-<project>-v3-share.mp4`: a smaller 30 fps copy for social media and messaging,
  when you ask for it;
- `outputs/final-<project>-v3.srt`: subtitles, when the video has narration;
- `outputs/blog/draft-<project>-v1.md` and `outputs/blog/final-<project>-v2.md`: the post;
- `outputs/blog/images/`: every image the post links, as PNG stills and GIF clips, with a WebM copy
  of each clip beside its GIF.

The post links its images relatively (`images/<file>`), so publish the final `.md` together with
the `images/` folder. Claude tells you the paths when it finishes. The project folder also holds
`NOTES.md` (every decision), `HANDBOOK.md`, `COSTS.md` (the estimated spend on narration and
b-roll, when the video has them) and the code that renders and captures everything, so a later
session can change either medium or recapture after a product change.

## Adding the other medium later

Run `claude` in the project folder and type `/mediatime` again. Claude sees what the project
already has, asks only what the new medium needs, lists what it can reuse (screenshots, clips,
claims, the made-up data, logo animations, b-roll), and starts.

## Coming back later

Run `claude` in the project folder again and say what you want to change. Claude reads its records
(`NOTES.md`, `HANDBOOK.md` and the plans of each medium) and resumes. After the product changes,
ask Claude to recapture: the same screenshots and clips run again against the new version. If you
started without the Gemini key, set it and restart `claude` before asking for narration.

## Updating a project to a newer kit

From the newer kit folder:

```bash
./install.sh ~/<product>-launch --force
```

It overwrites the kit's files that already exist in the project and deletes nothing, then runs
`./system-deps.sh` again (add `--no-system` to skip that). It never overwrites `project.json`,
`.claude/settings.json`, `.gitignore`, `music/CREDITS.md` or `broll/CREDITS.md`, and it leaves
your `BRAND.md`, `brand/`, `design.json`, the script, the post, the captures and `outputs/` alone,
because the kit has no files of those names. If Claude patched a kit file during the project,
`NOTES.md` lists the patch: ask Claude to re-apply it after the update. If the install is
interrupted, run the same command again.

Without `--force`, the install stops and writes nothing when any file already exists.

## If something goes wrong

- **Setup reports MISSING**: run `./system-deps.sh` in a terminal outside Claude Code (or give an
  administrator the output of `./system-deps.sh --dry-run`), then tell Claude to recheck.
  `./setup.sh --check` lists what is missing and changes nothing.
- **Narration, b-roll or the listening judge does not work**: check that `GEMINI_API_KEY` is set
  in the terminal you started `claude` from (`echo $GEMINI_API_KEY` prints it) and that billing is
  on for the key. Restart `claude` after setting it.
- **Renders are slow**: without a GPU this is expected. Ask for previews of a range instead of full
  renders.
- **No clips in the post**: clips need ffmpeg (on Fedora, `system-deps.sh` installs it). Run
  `./system-deps.sh` in your own terminal, then ask Claude to capture the clips again. Screenshots
  work without it.
- **Screenshots show an old version of your product**: rebuild its web frontend (or point Claude at
  the updated instance) and ask Claude to recapture.
- **The install stops with "files already exist"**: you are installing into a folder that holds a
  project. Use `--force` to update it, or pick a new folder.
- **A skill is not found** in a session that was already open when you installed: run
  `/reload-skills`, or restart `claude`.
- **A colour, font or logo looks wrong**: change `BRAND.md` or `brand/` and ask Claude to rerun the
  brand step.
- **Still stuck**: paste the failing line into the chat and ask Claude to diagnose it.
