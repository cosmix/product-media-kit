#!/usr/bin/env bash
# Sourced by setup.sh: the music sample libraries, for a video only. VSCO-2 CE always; the
# Salamander piano only when project.json's piano is salamander (./configure.sh --get piano).
# fetch_archive URL DEST_ARCHIVE: resumable download, renamed only when complete. Some hosts (GitHub's
# generated zips) ignore Range requests, so a failed resume discards the .part file and retries once.
fetch_archive() {
  [ -f "$2" ] && return 0
  if ! curl -fL --retry 3 -C - -o "$2.part" "$1"; then
    rm -f "$2.part"
    curl -fL --retry 3 -o "$2.part" "$1" || { rm -f "$2.part"; return 1; }
  fi
  mv "$2.part" "$2"
}

# warn_disk_space: once, before the first download, if under 10 GB is free
DISK_WARNED=0
warn_disk_space() {
  [ "$DISK_WARNED" = 0 ] || return 0
  DISK_WARNED=1
  local free_kb
  free_kb="$(df -Pk "$ROOT/music" | tail -n 1 | tr -s ' ' | cut -d' ' -f4)"
  if [ "${free_kb:-0}" -lt 10485760 ]; then
    status WARN "disk space" "under 10 GB free in $SAMPLES; archives plus unpacked files need about 9 GB"
  fi
}

# unpack ARCHIVE KIND TOPDIR: extract to a temp dir, then move the top folder into place.
# Every step is chained: errexit is off inside an `if` condition, so a failed extract must not reach the mv.
unpack() {
  local archive="$1" kind="$2" top="$3" tmp="$SAMPLES/.extract-$3"
  rm -rf "$tmp" && mkdir -p "$tmp" || return 1
  if [ "$kind" = zip ]; then unzip -q "$archive" -d "$tmp" || return 1
  else tar -xJf "$archive" -C "$tmp" || return 1; fi
  rm -rf "${SAMPLES:?}/$top" && mv "$tmp/$top" "$SAMPLES/$top" && rm -rf "$tmp" "$archive"
}

# sample_set NAME KIND TOPDIR SIZE URL DONE_PATH...: one library, complete when every DONE_PATH exists
sample_set() {
  local name="$1" kind="$2" top="$3" size="$4" url="$5" p; shift 5
  local archive="$SAMPLES/$top.$kind"
  [ "$kind" = zip ] || archive="$SAMPLES/$top.tar.xz"
  local done=1
  for p in "$@"; do [ -e "$SAMPLES/$p" ] || done=0; done
  if [ "$done" = 1 ]; then status ok "$name"; return; fi
  if [ "$CHECK" = 1 ]; then status WARN "$name" "music with sampled instruments only; ./setup.sh downloads it (about $size)"; return; fi
  if [ "$WANT_SAMPLES" = 0 ]; then status WARN "$name" "skipped (--no-samples): music with sampled instruments only"; return; fi
  warn_disk_space
  echo "          downloading $name (about $size) ..."
  if ! fetch_archive "$url" "$archive"; then
    status WARN "$name" "download failed; rerun ./setup.sh to resume ($url)"
  elif unpack "$archive" "$kind" "$top"; then
    status fetched "$name"
  else
    rm -rf "$archive" "$SAMPLES/.extract-$top"
    status WARN "$name" "archive did not unpack; rerun ./setup.sh to download it again"
  fi
}

# fetch_samples: optional; only a score with sampled instruments (piano, strings, mallets, brass) needs them
fetch_samples() {
  [ "$WANT_VIDEO" = 1 ] || return 0
  section "Sample libraries"
  if [ "$CHECK" = 0 ] && [ "$WANT_SAMPLES" = 1 ]; then mkdir -p "$SAMPLES"; fi
  local piano err
  err="$(mktemp)"
  # a malformed project.json is reported in the summary, not an abort under set -e;
  # stderr (uv download chatter) stays out of the value and shows only in the MISSING message
  piano="$("$ROOT/configure.sh" --get piano 2>"$err")" \
    || { status MISSING "project.json" "$(cat "$err")"; rm -f "$err"; return 0; }
  rm -f "$err"
  if [ "$piano" = salamander ]; then
    sample_set "Salamander piano" tar SalamanderGrandPianoV3_48khz24bit "1.2 GB" \
      "https://freepats.zenvoid.org/Piano/SalamanderGrandPiano/SalamanderGrandPianoV3+20161209_48khz24bit.tar.xz" \
      SalamanderGrandPianoV3_48khz24bit/SalamanderGrandPianoV3Retuned.sfz SalamanderGrandPianoV3_48khz24bit/48khz24bit
  else
    status ok "Salamander piano" "disabled (VSCO only; no attribution required)"
  fi
  sample_set "VSCO-2 CE" zip VSCO-2-CE-master "2.2 GB" \
    "https://github.com/sgossner/VSCO-2-CE/archive/refs/heads/master.zip" \
    VSCO-2-CE-master/Brass "VSCO-2-CE-master/Keys/Upright Nr1"
}

