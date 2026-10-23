"""Time the kit's operations: one JSON line per run in metrics.jsonl, a summary in METRICS.md.

    uv run tools/metrics.py                                      # rewrite METRICS.md from the log
    uv run tools/metrics.py run <category> <operation> -- <cmd> [args...]   # time a shell step

In Python: `with timed("edit", "render final", mode="final"): ...`. Both files live in the
project root (the folder holding project.json), or in $PMK_METRICS_DIR when that is set.
METRICS.md is generated; never edit it by hand. Recording never changes the timed operation:
a log that cannot be written prints one WARN line to stderr and the operation goes on. Under
pytest nothing is recorded unless PMK_METRICS_DIR is set, so test runs leave no files behind.

Categories: capture-web, capture-tui, narration, judge, broll, motion, music, edit, blog.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECENT = 20
_lock = threading.Lock()


def directory() -> Path | None:
    """Where the log and the report go; None when recording is off (pytest without an override)."""
    override = os.environ.get("PMK_METRICS_DIR")
    if override:
        return Path(override)
    return None if "PYTEST_CURRENT_TEST" in os.environ else ROOT


def duration(seconds: float) -> str:
    """Human-readable length: 0.42s, 12.3s, 3m 05s, 1h 02m."""
    if seconds < 1:
        return f"{seconds:.2f}s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(round(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def record(category: str, operation: str, seconds: float, status: str = "ok", **detail: object) -> None:
    """Append one run to metrics.jsonl and rewrite METRICS.md; warns instead of raising."""
    where = directory()
    if where is None:
        return
    line = {"time": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "category": category,
            "operation": operation, "seconds": round(seconds, 3), "status": status}
    if detail:
        line["detail"] = detail
    try:
        with _lock:
            where.mkdir(parents=True, exist_ok=True)
            with (where / "metrics.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, default=str) + "\n")
            write_report(where)
    except (OSError, ValueError, TypeError) as exc:
        print(f"WARN metrics: not recorded ({category} {operation}): {exc}", file=sys.stderr)


@contextlib.contextmanager
def timed(category: str, operation: str, **detail: object) -> Iterator[None]:
    """Time the block; status is `failed` when it raises (the exception goes on unchanged)."""
    start = time.monotonic()
    status = "ok"
    try:
        yield
    except SystemExit as exc:
        status = "ok" if exc.code in (None, 0) else "failed"
        raise
    except BaseException:
        status = "failed"
        raise
    finally:
        record(category, operation, time.monotonic() - start, status, **detail)


def load(where: Path) -> list[dict]:
    """The runs in the log, oldest first; lines that are not a run are skipped."""
    path = where / "metrics.jsonl"
    if not path.exists():
        return []
    runs = []
    for text in path.read_text(encoding="utf-8").splitlines():
        try:
            run = json.loads(text)
            if all(key in run for key in ("category", "operation", "time")):
                float(run["seconds"])
                runs.append(run)
        except (ValueError, KeyError, TypeError):
            continue
    return runs


def stats(runs: list[dict]) -> dict:
    """Runs, failed, total, mean, max and the last run's time for `runs`."""
    secs = [float(r["seconds"]) for r in runs]
    return {"runs": len(runs), "failed": sum(r.get("status") != "ok" for r in runs), "total": sum(secs),
            "mean": sum(secs) / len(secs), "max": max(secs), "last": max(str(r["time"]) for r in runs)}


def _table(head: list[str], rows: list[list[str]]) -> list[str]:
    cells = [head, *rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(head))]

    def fmt(row: list[str]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(row, widths)) + " |"

    return [fmt(head), fmt(["-" * w for w in widths]), *[fmt(row) for row in rows]]


def _stat_row(label: str, runs: list[dict]) -> list[str]:
    s = stats(runs)
    return [label, str(s["runs"]), str(s["failed"]), duration(s["total"]), duration(s["mean"]),
            duration(s["max"]), s["last"]]


def report(runs: list[dict]) -> str:
    """METRICS.md for `runs`."""
    head = ["Runs", "Failed", "Total", "Mean", "Max", "Last run (UTC)"]
    out = ["# Timing metrics", "",
           ("Generated by `tools/metrics.py` from `metrics.jsonl`; do not edit by hand. "
            "Regenerate with `uv run tools/metrics.py`."), ""]
    if not runs:
        return "\n".join([*out, "No runs recorded yet.", ""])
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        by_cat[run["category"]].append(run)
    out += ["## By category", "", *_table(["Category", *head], [_stat_row(c, r) for c, r in sorted(by_cat.items())]), ""]
    for cat, cat_runs in sorted(by_cat.items()):
        by_op: dict[str, list[dict]] = defaultdict(list)
        for run in cat_runs:
            by_op[run["operation"]].append(run)
        out += [f"## {cat}", "", *_table(["Operation", *head], [_stat_row(o, r) for o, r in sorted(by_op.items())]), ""]
    recent = [[r["time"], r["category"], r["operation"], duration(float(r["seconds"])), str(r.get("status")),
               ", ".join(f"{k}={v}" for k, v in (r.get("detail") or {}).items())] for r in reversed(runs[-RECENT:])]
    out += [f"## Last {len(recent)} runs", "",
            *_table(["Time (UTC)", "Category", "Operation", "Took", "Status", "Detail"], recent), ""]
    return "\n".join(out)


def write_report(where: Path) -> Path:
    """Rewrite METRICS.md in `where` from its log, atomically."""
    target = where / "METRICS.md"
    tmp = where / f".METRICS.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        tmp.write_text(report(load(where)), encoding="utf-8")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def run_command(category: str, operation: str, command: list[str]) -> int:
    """Run `command`, record its time and return its exit status."""
    start = time.monotonic()
    try:
        code = subprocess.run(command, check=False).returncode
    except OSError as exc:
        print(f"{command[0]}: {exc}", file=sys.stderr)
        code = 127
    record(category, operation, time.monotonic() - start, "ok" if code == 0 else "failed", exit=code)
    return 128 - code if code < 0 else code


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        where = directory() or ROOT
        print(f"{write_report(where)}: {len(load(where))} runs")
        return 0
    if len(args) > 4 and args[0] == "run" and args[3] == "--":
        return run_command(args[1], args[2], args[4:])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
