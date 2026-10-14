#!/usr/bin/env bash
# Restore dependencies after extracting a shared project.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then
  echo 'Usage: ./inflate.sh [--no-system] [setup options: --no-samples, --check]'
  echo 'Restores system packages, Python environments, selected samples, browser and model.'
  exit 0
fi
SYSTEM=1
OPTIONS=()
for arg in "$@"; do
  case "$arg" in
    --no-system) SYSTEM=0 ;;
    --check) SYSTEM=0; OPTIONS+=("$arg") ;;
    --no-samples) OPTIONS+=("$arg") ;;
    *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done
if [ "$SYSTEM" = 1 ]; then "$ROOT/system-deps.sh"; fi
exec "$ROOT/setup.sh" "${OPTIONS[@]}"
