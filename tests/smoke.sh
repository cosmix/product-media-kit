#!/bin/sh
# End-to-end smoke test: install the kit into a scratch project, set its media to blog, capture a
# web and a TUI still with their selftests, build a post from them and check it, then a second
# draft revision and a final.
# Usage: sh tests/smoke.sh <kit-dir>      KEEP=1 keeps the scratch folder for a look.
set -eu

[ $# -eq 1 ] && [ -f "$1/install.sh" ] || { echo "usage: sh tests/smoke.sh <kit-dir>" >&2; exit 2; }
command -v ffmpeg >/dev/null 2>&1 || { echo "smoke: ffmpeg not on PATH; the TUI selftest renders a clip and needs it (./system-deps.sh)" >&2; exit 1; }
KIT=$(cd "$1" && pwd)
H=$(mktemp -d "${TMPDIR:-/tmp}/mediakit.XXXXXX")
P="$H/Demo_Post"
SLUG=demo-post

cleanup() {
  if [ "${KEEP:-}" = 1 ]; then
    echo "kept: $H"
  else
    rm -rf "$H"
  fi
}
trap cleanup EXIT

step() { echo "== $*"; }
need() { [ -s "$P/$1" ] || { echo "missing: $1" >&2; exit 1; }; echo "ok $1"; }

step "copy the kit's files into $H/kit"
# A sandbox can mount device nodes over paths in a checkout; install.sh's tar would try to
# recreate them, so install from a copy that holds only regular files and symlinks.
mkdir "$H/kit"
(cd "$KIT" && find . \( -name .git -o -name .loom -o -name .worktrees -o -name .venv -o -name __pycache__ \) -prune \
  -o \( -type f -o -type l \) -print > "$H/found")
# find may take a file's type from its directory entry, which a mount over it does not change;
# test stats the path and sees the mounted device.
while IFS= read -r f; do
  if [ -f "$KIT/$f" ] || [ -L "$KIT/$f" ]; then printf '%s\n' "$f"; fi
done < "$H/found" > "$H/files"
# separate commands: sh has no pipefail, so set -e catches each failure
tar -C "$KIT" -cf "$H/kit.tar" -T "$H/files"
tar -C "$H/kit" -xpf "$H/kit.tar"

step "install the kit into $P"
"$H/kit/install.sh" "$P" --no-system --no-pull

step "check the install"
need CLAUDE.md
need .claude/skills/begin/SKILL.md
need guides/capture.md
grep -q "\"slug\": \"$SLUG\"" "$P/project.json" || { echo "project.json lacks slug $SLUG" >&2; exit 1; }
for d in doc tests captures outputs; do
  [ ! -e "$P/$d" ] || { echo "the install copied $d/" >&2; exit 1; }
done

step "set media to blog"
printf '{"slug": "%s", "media": ["blog"]}\n' "$SLUG" > "$P/project.json"

step "web selftest into captures/web"
(cd "$P/fixtures/web" && uv run --frozen python -m webcap.capture --selftest --out "$P/captures/web")

step "TUI selftest into captures/tui"
(cd "$P/fixtures/tui" && uv run --frozen tuicap --selftest --out "$P/captures/tui")

step "write post/draft.md"
cat > "$P/post/draft.md" <<'DRAFT'
---
title: Smoke test post
---

# Smoke test post

One paragraph of text between the title and the two screenshots.

![The built-in test page](shot:web/selftest/page)

![The built-in test terminal](shot:tui/selftest/screen)
DRAFT

step "postkit build, then check"
(cd "$P/post" && uv run --frozen postkit build --root "$P")
(cd "$P/post" && uv run --frozen postkit check --root "$P")
need "outputs/blog/draft-$SLUG-v1.md"
need outputs/blog/images/web-selftest-page.png
need outputs/blog/images/tui-selftest-screen.png

step "postkit build rewrites v1, --next writes v2, --final writes final v1"
(cd "$P/post" && uv run --frozen postkit build --root "$P")
[ ! -e "$P/outputs/blog/draft-$SLUG-v2.md" ] || { echo "a plain build wrote a new revision" >&2; exit 1; }
(cd "$P/post" && uv run --frozen postkit build --root "$P" --next)
(cd "$P/post" && uv run --frozen postkit build --root "$P" --final)
(cd "$P/post" && uv run --frozen postkit check --root "$P")
need "outputs/blog/draft-$SLUG-v2.md"
need "outputs/blog/final-$SLUG-v1.md"

echo "smoke: ok"
