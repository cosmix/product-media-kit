#!/usr/bin/env bash
# Ask once for startup choices; explicit flags support agent-led kickoff.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/tools/project_settings.py" "$@"
fi
exec uv run --no-project --python 3.12 python "$ROOT/tools/project_settings.py" "$@"
