#!/usr/bin/env bash
# Copy this kit into a project folder: the tools, README.md, the project's CLAUDE.md (from
# claude-project.md), every skill in claude-skills/ under .claude/skills/, project.json and the
# project's Claude Code settings; then install the system packages with the project's
# system-deps.sh. Needs bash and the standard tools it calls: cat, cp, dirname, find, grep, head,
# mkdir, paste, sed, sort, tar, tr.
#   ./install.sh <project-dir> [--force] [--no-system] [--setup]
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd -P)"

usage() {
  cat <<'EOF'
Usage: ./install.sh <project-dir> [--force] [--no-system] [--setup]

Copies the kit into <project-dir> (created if missing). The project's slug comes from the folder
name (lowercase, other characters become single hyphens; "project" when nothing is left); a note
says so when it differs from the folder name.
  the kit's tools, guides and README.md                       -> <project-dir>/
  claude-project.md                                           -> <project-dir>/CLAUDE.md
  claude-skills/<skill>/ (each skill: brand, ...)             -> <project-dir>/.claude/skills/<skill>/
  claude-settings.json (agent teams on, frontend-design plugin) -> <project-dir>/.claude/settings.json,
                                                                 only when the project has none
  {"slug": "<slug>", "media": []}                             -> <project-dir>/project.json, only when absent
Development files (install.sh, doc/, tests/, .loom/, .worktrees/, .claude/), environments (.venv),
caches (__pycache__, .pytest_cache, .ruff_cache, .mypy_cache), build output (out/, build/),
captures/, outputs/ and downloaded sample libraries (music/samples/) are not copied.

  --force   overwrite files that already exist in <project-dir> (no file is ever deleted),
            except .gitignore, music/CREDITS.md, broll/CREDITS.md and project.json, which
            the project owns and which are written only when absent
  --no-system  do not run <project-dir>/system-deps.sh after copying. That script installs the
            system packages (ffmpeg, Mesa, fonts, uv, ...) and asks for your password; skip it
            when you have no administrator rights and give `./system-deps.sh --dry-run` output
            to an administrator
  --setup   run <project-dir>/setup.sh after copying (after system-deps.sh) and exit with its status

Without --force the install stops, writing nothing, if any file it would write already exists.
EOF
}

TARGET="" FORCE=0 SETUP=0 SYSTEM=1
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --force) FORCE=1 ;;
    --setup) SETUP=1 ;;
    --no-system) SYSTEM=0 ;;
    -*) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
    *) [ -z "$TARGET" ] || { echo "only one project folder allowed (try --help)" >&2; exit 2; }
       TARGET="$1" ;;
  esac
  shift
done
[ -n "$TARGET" ] || { usage >&2; exit 2; }

# abspath PATH: canonical absolute path of PATH, which need not exist yet (macOS has no `realpath -m`).
# The deepest existing folder is resolved by the shell; the rest is normalised as text.
abspath() {
  local p="$1" rest="" c
  case "$p" in /*) ;; *) p="${PWD%/}/$p" ;; esac
  while [ ! -d "$p" ]; do rest="${p##*/}/$rest"; p="${p%/*}"; p="${p:-/}"; done
  p="$(cd "$p" && pwd -P)"
  while [ -n "$rest" ]; do
    c="${rest%%/*}"; rest="${rest#*/}"
    case "$c" in
      ""|.) ;;
      ..) p="${p%/*}"; p="${p:-/}" ;;
      *) p="${p%/}/$c" ;;
    esac
  done
  printf '%s\n' "$p"
}

DEST="$(abspath "$TARGET")"
case "$DEST/" in
  "$KIT"/*) echo "refusing: $DEST is inside the kit folder $KIT" >&2; exit 2 ;;
esac
if [ -e "$DEST" ] && [ ! -d "$DEST" ]; then echo "refusing: $DEST is not a directory" >&2; exit 2; fi
SKILLS_DEST="$DEST/.claude/skills"

# the folder name is the project slug, normalised: lowercase, other characters to single hyphens
FOLDER="${DEST##*/}"
SLUG="$(printf '%s' "$FOLDER" | tr '[:upper:]' '[:lower:]' | LC_ALL=C sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
SLUG="${SLUG:-project}"
[ "$SLUG" = "$FOLDER" ] || echo "Note: the folder name \"$FOLDER\" is not a slug; the project's slug is \"$SLUG\"." >&2

# list_files DIR [EXCLUDE_PATH...]: files and symlinks under DIR as ./relative paths, skipping
# generated content (environments, caches, render output, sample libraries) and the excluded paths
list_files() {
  local dir="$1" p; shift
  local -a prune=(-name .venv -o -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache
                  -o -name out -o -name build -o -name .git -o -path ./music/samples)
  for p in "$@"; do prune+=(-o -path "$p"); done
  (cd "$dir" && find . \( "${prune[@]}" \) -prune -o \( -type f -o -type l \) -print | LC_ALL=C sort)
}

# development files and the kit's own project files do not belong in a project folder
[ -f "$KIT/claude-project.md" ] || { echo "kit is incomplete: claude-project.md missing" >&2; exit 1; }
KIT_LIST="$(list_files "$KIT" ./install.sh ./claude-skills ./claude-settings.json ./claude-project.md ./CLAUDE.md \
  ./doc ./tests ./.claude ./.loom ./.worktrees ./captures ./outputs)"
# project-owned records: copied only when absent, never overwritten, even with --force
KEEP_LIST="./.gitignore
./music/CREDITS.md
./broll/CREDITS.md"
COPY_LIST="" KEPT=""
while IFS= read -r f; do
  if grep -qxF -- "$f" <<<"$KEEP_LIST" && { [ -e "$DEST/${f#./}" ] || [ -L "$DEST/${f#./}" ]; }; then
    KEPT="${KEPT:+$KEPT
}${f#./}"
  else
    COPY_LIST="${COPY_LIST:+$COPY_LIST
}$f"
  fi
done <<<"$KIT_LIST"
# the skills: every folder in claude-skills/ except caches, one name per line
SKILLS="$(cd "$KIT/claude-skills" && for d in */; do
  case "$d" in __pycache__/|"*/") ;; *) printf '%s\n' "${d%/}" ;; esac
done)"
[ -n "$SKILLS" ] || { echo "kit is incomplete: no skills in claude-skills/" >&2; exit 1; }
while IFS= read -r s; do
  [ -f "$KIT/claude-skills/$s/SKILL.md" ] || { echo "kit is incomplete: claude-skills/$s/SKILL.md missing" >&2; exit 1; }
done <<<"$SKILLS"

# every destination this install would write, one per line, for the conflict check
planned() {
  local f s
  printf '%s\n' "$DEST/CLAUDE.md"
  while IFS= read -r f; do printf '%s\n' "$DEST/${f#./}"; done <<<"$COPY_LIST"
  while IFS= read -r s; do
    list_files "$KIT/claude-skills/$s" | while IFS= read -r f; do printf '%s\n' "$SKILLS_DEST/$s/${f#./}"; done
  done <<<"$SKILLS"
}

if [ "$FORCE" = 0 ] && [ -d "$DEST" ]; then
  CONFLICTS="$(planned | while IFS= read -r f; do if [ -e "$f" ] || [ -L "$f" ]; then printf '%s\n' "${f#"$DEST"/}"; fi; done)"
  if [ -n "$CONFLICTS" ]; then
    echo "These files already exist in $DEST; nothing was written:" >&2
    head -n 40 <<<"$CONFLICTS" | while IFS= read -r f; do printf '  %s\n' "$f" >&2; done
    echo "Rerun with --force to overwrite them (no other file is touched)." >&2
    exit 1
  fi
fi

# copy_tree SRC_DIR DST_DIR LIST: tar keeps executable bits and dotfiles. COPYING turns on once
# the folder exists: a mkdir that fails (unwritable parent) has written nothing to finish by rerunning.
copy_tree() {
  mkdir -p "$2"
  COPYING=1
  tar -C "$1" -cf - -T <(printf '%s\n' "$3") | tar -C "$2" -xpf -
}

# a failure partway through leaves a mix of old and new files; rerunning the install completes it
COPYING=0
trap '[ "$?" = 0 ] || [ "$COPYING" != 1 ] || echo "install failed partway: rerun the same ./install.sh command with --force to finish it" >&2' EXIT
copy_tree "$KIT" "$DEST" "$COPY_LIST"
cp "$KIT/claude-project.md" "$DEST/CLAUDE.md"
while IFS= read -r s; do
  copy_tree "$KIT/claude-skills/$s" "$SKILLS_DEST/$s" "$(list_files "$KIT/claude-skills/$s")"
done <<<"$SKILLS"
COPYING=0
# project.json names the project; written once, since the project owns it afterwards
if [ ! -e "$DEST/project.json" ]; then
  printf '{"slug": "%s", "media": []}\n' "$SLUG" > "$DEST/project.json"
  PROJECT_NOTE="written (slug $SLUG)"
else
  PROJECT_NOTE="kept (already in the project)"
fi
# the project's Claude Code settings: written once, never overwritten, since the project may add its own
SETTINGS="$DEST/.claude/settings.json"
if [ ! -e "$SETTINGS" ]; then
  cp "$KIT/claude-settings.json" "$SETTINGS"
  SETTINGS_NOTE="written (agent teams on, frontend-design plugin enabled)"
elif grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" *: *"1"' "$SETTINGS"; then
  SETTINGS_NOTE="kept (already in the project)"
else
  SETTINGS_NOTE="kept, but agent teams are not on: add the \"env\" entry from $KIT/claude-settings.json"
fi
printf 'Installed the kit into %s\n  skills: %s in %s\n  CLAUDE.md: %s/CLAUDE.md\n  project.json: %s\n  .claude/settings.json: %s\n' \
  "$DEST" "$(paste -sd ' ' - <<<"$SKILLS")" "$SKILLS_DEST" "$DEST" "$PROJECT_NOTE" "$SETTINGS_NOTE"
if [ -n "$KEPT" ]; then
  printf 'Kept (already in the project, never overwritten): %s\n' "$(paste -sd ' ' - <<<"$KEPT")"
fi

if [ "$SYSTEM" = 1 ]; then
  echo "Installing system packages with system-deps.sh (it may ask for your password) ..."
  (cd "$DEST" && ./system-deps.sh) || {
    echo "system-deps.sh failed; the kit is installed. Fix the error above, then run ./system-deps.sh in $DEST" >&2
    exit 1
  }
else
  echo "Skipped system packages (--no-system). Run ./system-deps.sh in $DEST yourself, or give"
  echo "the output of ./system-deps.sh --dry-run to an administrator."
fi

if [ "$SETUP" = 1 ]; then
  echo "Running setup.sh ..."
  cd "$DEST" && exec ./setup.sh
fi

cat <<EOF

Next steps (open a new terminal first if uv or Homebrew was just installed, so they are on PATH):
  1. cd $DEST
  2. claude
  3. type /mediatime: Claude checks the machine, asks which medium (video, blog post or both) and
     the rest (HUMAN.md describes what to expect; a Gemini API key is needed only for a narrated
     voice, generated b-roll and the listening judge)
EOF
