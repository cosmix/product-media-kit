"""Music credits: CC BY sample libraries only, and nothing for a Lyria soundtrack."""

import json

import pytest

from editkit import credit_data

CREDITS = """# Sample credits

## Salamander Grand Piano V3 (48 kHz / 24-bit)

- Source: Alexander Holm, https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html
- Licence: Creative Commons Attribution 3.0 Unported (CC BY 3.0),
  http://creativecommons.org/licenses/by/3.0/

## VSCO 2 Community Edition

- Source: Versilian Studios, https://github.com/sgossner/VSCO-2-CE
- Licence: CC0 1.0 Universal (public domain dedication),
  https://creativecommons.org/publicdomain/zero/1.0/

## Lyria soundtrack

- Model: lyria-3-clip-preview (Google Lyria, through the Gemini API)
- Take: out/lyria/take-02.wav, generated 2026-10-25T10:00:00
- Credit: none on screen; the audio carries Google's SynthID watermark
"""


@pytest.fixture
def music(tmp_path, monkeypatch):
    (tmp_path / "music" / "out").mkdir(parents=True)
    (tmp_path / "music" / "CREDITS.md").write_text(CREDITS)
    soundtrack = tmp_path / "music" / "out" / "soundtrack.wav"
    soundtrack.write_bytes(b"")
    monkeypatch.setattr(credit_data, "ROOT", tmp_path)
    monkeypatch.setattr(credit_data, "SOUNDTRACK", soundtrack)

    def used(libraries):
        (tmp_path / "music" / "manifest.json").write_text(json.dumps({"sample_libraries": libraries}))
    return used


def test_lyria_soundtrack_credits_nothing(music) -> None:
    music([])
    assert credit_data.music_samples() == []


def test_score_with_salamander_credits_it_alone(music) -> None:
    music(["salamander", "vsco"])
    assert [(c.title, c.by, c.licence) for c in credit_data.music_samples()] == [
        ("Salamander Grand Piano V3", "Alexander Holm", "CC BY 3.0")]


def test_section_without_a_licence_line_is_still_credited(music, tmp_path) -> None:
    path = tmp_path / "music" / "CREDITS.md"
    path.write_text(CREDITS.replace("- Licence: Creative", "- License: Creative"))
    music(["salamander"])
    assert [c.title for c in credit_data.music_samples()] == ["Salamander Grand Piano V3"]
