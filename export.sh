#!/usr/bin/env bash
# Export this project, or a project supplied as the first argument.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/tools/export_project.py" "$@"
fi
exec uv run --no-project --python 3.12 python "$ROOT/tools/export_project.py" "$@"
