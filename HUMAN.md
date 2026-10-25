# Making a product video or blog post: the human's guide

This kit makes a two-to-three-minute video for a piece of software, a blog post about it, or both,
from its code. Claude Code agents read your product's docs and code, check every claim against the
code, capture its web UI and terminal, and write, narrate, compose, draw, edit and assemble the
rest. You answer questions and review; a change you ask for is applied by rendering again.

## What you need

| You need            | For the video                                                                                     | For the blog post                         |
| ------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| A computer          | macOS (Apple Silicon or Intel), or Linux with any GPU; without a GPU it works, renders much slower | macOS, or Linux (Debian, Ubuntu, Fedora)  |
| Disk space          | about 25 GB free, about 17 GB without music samples (no samples with Lyria music or none)         | about 2 GB free                           |
| A Gemini API key    | only for a narrated voice, generated b-roll, Lyria music or the listening judge                   | not needed                                |
| Your product        | its repository or docs                                                                            | its repository and the PRD of the feature |

Optional: your brand guidelines (`BRAND.md`) and logo and fonts (`brand/`), at any time.

## Steps

1. Install Claude Code, logged in, with access to Opus:

   ```bash
   curl -fsSL https://claude.ai/install.sh | bash
   ```

2. Only for a narrated voice, generated b-roll, Lyria music or the listening judge: create a
   Gemini API key at <https://aistudio.google.com/apikey> and enable billing (the free tier allows
   10 voice requests a day and no Lyria). Use is billed per request; Claude keeps an estimate in `COSTS.md`. You pass it when you
   start Claude in the project (step 4). Never paste the key into the chat.
3. Get this kit folder, open a terminal in it, run `claude` and type `/install`. Claude asks a few
   questions, installs, and tells you the one command to run in a second terminal: the system
   packages need your password.
4. When Claude says so, start it in the project and type `/begin`:

   ```bash
   cd <project> && claude                              # without a Gemini key
   cd <project> && GEMINI_API_KEY=<your key> claude    # with one
   ```

Coming back later: start `claude` in the project folder the same way; it picks up where it stopped.

Claude keeps `METRICS.md` with how long each step took. To keep the b-roll for other videos, ask
Claude, or run `./export-broll.sh <dest-dir>` and upload the folder.

Everything else (review, where the files land, sharing, updating, troubleshooting): ask Claude, or
see README.md, "For the human".
