"""Shared harness for kit tests: a fake kit holding the real install.sh and a few marker files."""

import shutil
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]

FAKE_FILES = {
    "CLAUDE-project.md": "# Project instructions\n",
    "claude-settings.json": '{"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}}\n',
    "claude-skills/brand/SKILL.md": "---\nname: brand\n---\n# Brand\n",
    "doc/plans/x.md": "# plan\n",
    "tests/test_x.py": "def test_x():\n    pass\n",
    ".loom/x": "loom state\n",
    "fixtures/web/a.py": "A = 1\n",
    "claude-skills/narration/SKILL.md": "---\nname: narration\n---\n# Narration\n",
    "CLAUDE.md": "# Kit development instructions\n",
    "captures/web/x.png": "capture\n",
    "outputs/final-x-v1.mp4": "video\n",
    "music/samples/lib.sfz": "sample\n",
    "music/CREDITS.md": "# Music credits\n",
    "broll/CREDITS.md": "# B-roll credits\n",
    "README.md": "# Kit\n",
}


@pytest.fixture
def fake_kit(tmp_path: Path) -> Path:
    """tmp_path/kit: the kit's install.sh plus the files in FAKE_FILES."""
    kit = tmp_path / "kit"
    kit.mkdir()
    shutil.copy2(KIT / "install.sh", kit / "install.sh")
    for rel, text in FAKE_FILES.items():
        path = kit / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return kit
