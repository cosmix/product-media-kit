"""lyria.py with a fake client: retries, refusals, usage lines, take numbering, delivered formats,
and the CREDITS.md record. No network."""

import binascii
import io
import json
from types import SimpleNamespace

import pytest
import soundfile as sf
from tools import usage_log

import lyria
from scorekit import finish


class Refused(Exception):
    status_code = 400


class Client:
    """interactions.create returns or raises the queued results in order and records its kwargs."""

    def __init__(self, *results):
        self.results, self.calls = list(results), []
        self.interactions = SimpleNamespace(create=self.create)

    def create(self, **kw):
        self.calls.append(kw)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(output_audio=SimpleNamespace(data=result), usage=None,
                               model_dump=lambda **_: {"id": "fake"})


def song(fmt: str) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, lyria.click_track(117.0, 0.31, 12.0), 44100, format=fmt)
    return buf.getvalue()


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(lyria, "OUT", tmp_path / "out" / "lyria")
    monkeypatch.setattr(lyria, "HERE", tmp_path)
    monkeypatch.setattr(usage_log, "LOG", tmp_path / "usage.jsonl")
    return tmp_path


def usage(root):
    return [json.loads(line) for line in (root / "usage.jsonl").read_text().splitlines()]


def test_refusal_is_not_retried(out) -> None:
    client = Client(Refused("artist names are not allowed"))
    name, status = lyria.take(client, "lyria-3-clip-preview", "like a famous band", "lyria/prompt.md", "take-01")
    assert (name, len(client.calls)) == ("take-01", 1)
    assert status.startswith("refused") and "artists" in status
    assert [(u["ok"], u["take"]) for u in usage(out)] == [(False, "take-01")]
    assert not lyria.OUT.exists() or not list(lyria.OUT.iterdir())


def test_failure_is_retried_once_and_every_attempt_logged(out) -> None:
    client = Client(RuntimeError("timeout"), song("MP3"))
    _, status = lyria.take(client, "lyria-3-clip-preview", "rock", "lyria/prompt.md", "take-01")
    assert status.startswith("ok"), status
    assert [u["ok"] for u in usage(out)] == [False, True]
    assert client.calls[0] == {"model": "lyria-3-clip-preview", "input": "rock"}
    assert sorted(p.name for p in lyria.OUT.iterdir()) == ["take-01.json", "take-01.mp3", "take-01.wav"]
    info = json.loads((lyria.OUT / "take-01.json").read_text())
    assert info["measured_bpm"] == pytest.approx(117.0, abs=0.5)
    assert (info["model"], info["attempts"], info["prompt_file"]) == ("lyria-3-clip-preview", 2, "lyria/prompt.md")


def test_two_failures_end_the_take(out) -> None:
    _, status = lyria.take(Client(RuntimeError("a"), RuntimeError("b")), "lyria-3.5", "x", "p", "take-01")
    assert status == "FAILED"
    assert [u["ok"] for u in usage(out)] == [False, False]


def test_lyria_35_asks_for_wav_and_gets_an_mp3_beside_it(out) -> None:
    client = Client(song("WAV"))
    lyria.take(client, "lyria-3.5", "a song", "p", "take-04")
    assert client.calls[0]["response_format"] == {"type": "audio"}
    assert sf.info(lyria.OUT / "take-04.wav").samplerate == 44100
    assert sf.info(lyria.OUT / "take-04.mp3").format == "MP3"


def test_takes_are_numbered_after_the_highest(out) -> None:
    assert lyria.next_names(2) == ["take-01", "take-02"]
    lyria.OUT.mkdir(parents=True)
    (lyria.OUT / "take-07.json").write_text("{}")
    assert lyria.next_names(1) == ["take-08"]


def test_sections_follow_the_timeline() -> None:
    timeline = {"total": 75.4, "scenes": [{"key": "intro", "start": 0.0}, {"key": "pitch", "start": 12.6}]}
    assert lyria.sections_text(timeline).splitlines()[-3:] == [
        "The song lasts 1:15, in these timed sections:", "[0:00 - 0:13] intro", "[0:13 - 1:15] pitch"]


def test_model_comes_from_project_json(monkeypatch) -> None:
    monkeypatch.setattr(lyria, "project_settings", lambda: {"music": "lyria-3.5"})
    assert lyria.pick_model(None) == "lyria-3.5"
    assert lyria.pick_model("lyria-3-clip-preview") == "lyria-3-clip-preview"
    monkeypatch.setattr(lyria, "project_settings", lambda: {"music": "score"})
    with pytest.raises(SystemExit, match="music is score"):
        lyria.pick_model(None)


def test_credit_record_is_replaced_in_place(tmp_path) -> None:
    path = tmp_path / "CREDITS.md"
    path.write_text("# Sample credits\n\n## VSCO 2 Community Edition\n\n- Licence: CC0 1.0\n")
    finish.write_credit(path, ["- Take: out/lyria/take-01.wav"])
    finish.write_credit(path, ["- Take: out/lyria/take-02.wav"])
    text = path.read_text()
    assert text.count("## Lyria soundtrack") == 1 and "take-02" in text and "take-01" not in text
    assert text.startswith("# Sample credits\n\n## VSCO 2 Community Edition\n\n- Licence: CC0 1.0\n\n## Lyria")


def test_raw_mp3_with_any_frame_sync_is_not_base64_decoded() -> None:
    for head in (b"\xff\xfb", b"\xff\xe3", b"\xff\xfd", b"ID3\x04"):
        raw = head + b"\x90\x00" * 40
        assert lyria.audio_bytes(SimpleNamespace(output_audio=SimpleNamespace(data=raw))) == raw
    wav = song("WAV")
    assert lyria.audio_bytes(SimpleNamespace(output_audio=SimpleNamespace(data=wav))) == wav


def test_bad_base64_raises_instead_of_dropping_bytes() -> None:
    for data in ("not base64 !!", b"@@@@ junk @@@@"):
        with pytest.raises(binascii.Error):
            lyria.audio_bytes(SimpleNamespace(output_audio=SimpleNamespace(data=data)))


def test_a_taken_name_moves_the_paid_song_to_the_next_take(out) -> None:
    lyria.OUT.mkdir(parents=True)
    (lyria.OUT / "take-01.mp3").write_bytes(b"other run")
    _, status = lyria.take(Client(song("MP3")), "lyria-3.5", "x", "p", "take-01")
    assert status.startswith("ok") and "take-02" in status, status
    assert (lyria.OUT / "take-01.mp3").read_bytes() == b"other run"
    assert sorted(p.name for p in lyria.OUT.iterdir()) == [
        "take-01.mp3", "take-02.json", "take-02.mp3", "take-02.wav"]
    assert [u["take"] for u in usage(out)] == ["take-02"]


def test_a_failed_tempo_measurement_keeps_the_take_and_its_json(out, monkeypatch) -> None:
    def boom(*_):
        raise ValueError("no beat")
    monkeypatch.setattr(lyria, "measure", boom)
    _, status = lyria.take(Client(song("MP3")), "lyria-3.5", "x", "p", "take-01")
    assert status.startswith("ok") and "tempo not measured" in status, status
    assert json.loads((lyria.OUT / "take-01.json").read_text())["measured_bpm"] is None


def test_sections_are_rounded_and_sub_second_ones_dropped() -> None:
    timeline = {"total": 20.0, "scenes": [{"key": "a", "start": 0.0}, {"key": "blip", "start": 9.6},
                                          {"key": "b", "start": 10.2}]}
    assert lyria.sections_text(timeline).splitlines()[-3:] == [
        "The song lasts 0:20, in these timed sections:", "[0:00 - 0:10] a", "[0:10 - 0:20] b"]
