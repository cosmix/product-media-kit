"""tools/metrics.py: records, METRICS.md, failure handling, the CLI and the pytest guard."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from tools import metrics


@pytest.fixture
def where(tmp_path, monkeypatch):
    monkeypatch.setenv("PMK_METRICS_DIR", str(tmp_path))
    return tmp_path


def lines(where: Path) -> list[dict]:
    return [json.loads(x) for x in (where / "metrics.jsonl").read_text().splitlines()]


def test_timed_records_a_run_and_the_report(where):
    with metrics.timed("edit", "render final", mode="final"):
        pass
    [run] = lines(where)
    assert (run["category"], run["operation"], run["status"]) == ("edit", "render final", "ok")
    assert run["detail"] == {"mode": "final"} and run["seconds"] >= 0
    text = (where / "METRICS.md").read_text()
    assert "do not edit by hand" in text and "## edit" in text and "render final" in text and "mode=final" in text


def test_failure_is_recorded_and_the_exception_reraised(where):
    with pytest.raises(KeyError, match="boom"), metrics.timed("music", "render"):
        raise KeyError("boom")
    with pytest.raises(SystemExit), metrics.timed("music", "render"):
        raise SystemExit("bad input")
    with pytest.raises(SystemExit), metrics.timed("music", "render"):
        raise SystemExit(0)
    assert [r["status"] for r in lines(where)] == ["failed", "failed", "ok"]


def test_aggregation(where):
    for secs, status in ((2.0, "ok"), (4.0, "failed"), (90.0, "ok")):
        metrics.record("motion", "scene a", secs, status)
    metrics.record("blog", "build", 3720)
    s = metrics.stats([r for r in metrics.load(where) if r["category"] == "motion"])
    assert (s["runs"], s["failed"], s["total"], s["max"]) == (3, 1, 96.0, 90.0)
    assert s["mean"] == 32.0
    text = (where / "METRICS.md").read_text()
    assert "1m 30s" in text and "1h 02m" in text
    assert text.index("## By category") < text.index("## blog") < text.index("## motion") < text.index("## Last 4 runs")


def test_report_lists_only_the_last_runs(where):
    for i in range(metrics.RECENT + 5):
        metrics.record("blog", f"op{i}", 1)
    text = (where / "METRICS.md").read_text()
    recent = text.split(f"## Last {metrics.RECENT} runs")[1]
    assert "op24" in recent and "op5 " in recent and "op4 " not in recent


def test_duration_formats():
    assert [metrics.duration(s) for s in (0.424, 12.34, 185, 3720)] == ["0.42s", "12.3s", "3m 05s", "1h 02m"]


def test_unreadable_lines_are_skipped(where):
    (where / "metrics.jsonl").write_text('not json\n{"category": "a"}\n[1]\n')
    metrics.record("blog", "check", 1)
    assert len(metrics.load(where)) == 1


def test_unwritable_directory_only_warns(tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("PMK_METRICS_DIR", str(blocker / "sub"))
    with metrics.timed("blog", "build"):
        result = 1 + 1
    assert result == 2
    assert capsys.readouterr().err.startswith("WARN metrics:")


def test_nothing_is_recorded_under_pytest_without_an_override(monkeypatch, tmp_path):
    monkeypatch.delenv("PMK_METRICS_DIR", raising=False)
    assert metrics.directory() is None
    monkeypatch.chdir(tmp_path)
    metrics.record("blog", "build", 1)
    assert not list(tmp_path.iterdir())
    monkeypatch.setenv("PMK_METRICS_DIR", str(tmp_path))
    assert metrics.directory() == tmp_path


def cli(where, *args):
    return subprocess.run([sys.executable, str(KIT / "tools" / "metrics.py"), *args], check=False,
                          capture_output=True, text=True, env={"PMK_METRICS_DIR": str(where), "PATH": ""})


def test_cli_run_passes_the_exit_status_through(where):
    ok = cli(where, "run", "narration", "tts", "--", sys.executable, "-c", "pass")
    bad = cli(where, "run", "narration", "tts", "--", sys.executable, "-c", "raise SystemExit(7)")
    missing = cli(where, "run", "narration", "tts", "--", "no-such-command-here")
    assert (ok.returncode, bad.returncode, missing.returncode) == (0, 7, 127)
    runs = lines(where)
    assert [r["status"] for r in runs] == ["ok", "failed", "failed"] and runs[1]["detail"] == {"exit": 7}


def test_cli_regenerates_the_report_and_rejects_bad_usage(where):
    metrics.record("blog", "build", 1)
    (where / "METRICS.md").unlink()
    assert cli(where).returncode == 0 and (where / "METRICS.md").exists()
    assert cli(where, "run", "blog").returncode != 0
