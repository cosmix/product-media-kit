"""tools/costs.py pricing: token rates, per_second clips and per_call songs."""

import json

import pytest
from tools import costs

RATES = {"models": {
    "lyria-3.5": {"per_call": 0.08},
    "lyria-3-clip-preview": {"per_call": None},
    "gemini-omni-1.1-flash": {"per_second": 0.1},
    "gemini-3.8-flash-tts": {"input": 1.0, "output": {"audio": 20.0}},
}}


def call(model, ok=True, **extra):
    return {"time": "2026-10-25T10:00:00", "script": "lyria", "model": model, "usage": None, "ok": ok, **extra}


def test_per_call_prices_each_successful_call_once() -> None:
    unpriced = set()
    assert costs.price(call("lyria-3.5", seconds=120.0), RATES, unpriced) == pytest.approx(0.08)
    assert costs.price(call("lyria-3.5", ok=False, error="400"), RATES, unpriced) == 0.0
    assert not unpriced


def test_per_call_null_is_listed_as_unpriced() -> None:
    unpriced = set()
    assert costs.price(call("lyria-3-clip-preview"), RATES, unpriced) == 0.0
    assert unpriced == {"lyria-3-clip-preview: per_call"}


def test_other_rates_unchanged() -> None:
    unpriced = set()
    tts = {"model": "gemini-3.8-flash-tts", "usage": {"input": {"text": 1000}, "output": {"audio": 2000}, "thought": 0}}
    assert costs.price(tts, RATES, unpriced) == pytest.approx(0.001 + 0.04)
    assert costs.price({"model": "gemini-omni-1.1-flash", "seconds": 8.0}, RATES, unpriced) == pytest.approx(0.8)
    assert not unpriced


def test_lyria_calls_group_as_music(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(costs, "ROOT", tmp_path)
    (tmp_path / "rates.json").write_text(json.dumps(RATES | {"source": "pricing page", "read": "2026-10-25"}))
    lines = [call("lyria-3.5", seconds=118.2), call("lyria-3.5", ok=False), call("lyria-3.5", seconds=121.0)]
    (tmp_path / "usage.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
    costs.main()
    text = (tmp_path / "COSTS.md").read_text()
    assert "**Total: $0.16** (music $0.16)" in text
    row = next(line for line in text.splitlines() if "lyria-3.5" in line)
    assert [c.strip() for c in row.strip("|").split("|")][1:5] == ["music", "lyria-3.5", "3", "1"]
