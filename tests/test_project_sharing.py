"""Project settings and portable archive integration checks (no downloads)."""

import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.export_project import export
from tools.project_settings import configure, read

ROOT = Path(__file__).resolve().parents[1]


class ProjectSharing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / "video with spaces"
        self.project.mkdir()

    def write(self, name, content="asset"):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_choices_require_answers_and_persist(self):
        self.assertEqual(read(self.project), {"fps": 30, "piano": "vsco"})
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "Ask the user"):
                configure(self.project)
        configure(self.project, 24, "vsco")
        with patch("builtins.input", side_effect=AssertionError("asked twice")):
            self.assertEqual(configure(self.project)["fps"], 24)
        configure(self.project, 60, "salamander")
        self.assertEqual(read(self.project)["piano"], "salamander")
        self.write("project.json", '{"fps": true}')
        with self.assertRaises(ValueError):
            read(self.project)

    def test_interactive_startup(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["", ""]):
            self.assertEqual(configure(self.project), {"fps": 30, "piano": "vsco"})

    def test_archive_roundtrip_and_inflation(self):
        for name in ("inflate.sh", "configure.sh", "system-deps.sh", "setup.sh",
                     "tools/project_settings.py", "tools/setup-samples.sh"):
            content = (ROOT / name).read_text() if name == "inflate.sh" else "#!/bin/bash\necho restored >> calls\n"
            self.write(name, content).chmod(0o755)
        configure(self.project, 25, "vsco")
        keep = ("narration/final/voice.wav", "broll/source.mp4", "music/out/soundtrack.wav",
                "motion/out/scene.mov", "brand/fonts/font.ttf", "fixtures/web/uv.lock", ".env.example")
        omit = ("music/samples/piano.wav", "music/.venv/bin/python", "fixtures/web/node_modules/bin",
                ".env", ".env.production", ".aws/credentials", "music/build/fine_tune.json")
        for name in keep + omit:
            self.write(name)
        (self.project / "voice-link.wav").symlink_to(self.project / keep[0])
        output = export(self.project, self.base / "share.tar.gz")
        recipient = self.base / "recipient"
        recipient.mkdir()
        with tarfile.open(output) as archive:
            names = archive.getnames()
            for name in keep:
                self.assertIn(f"{self.project.name}/{name}", names)
            for name in omit:
                self.assertNotIn(f"{self.project.name}/{name}", names)
            archive.extractall(recipient, filter="data")
        restored = recipient / self.project.name
        self.assertEqual((restored / "voice-link.wav").read_text(), "asset")
        self.assertEqual(read(restored)["fps"], 25)
        subprocess.run(["./inflate.sh", "--no-system"], cwd=restored, check=True)
        self.assertEqual((restored / "calls").read_text().splitlines(), ["restored"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            export(self.project, output)

    def test_external_symlink_rejected(self):
        for name in ("setup.sh", "inflate.sh", "configure.sh", "system-deps.sh",
                     "tools/project_settings.py", "tools/setup-samples.sh"):
            self.write(name)
        external = self.base / "external.wav"
        external.write_text("audio")
        (self.project / "external.wav").symlink_to(external)
        output = self.base / "share.tar.gz"
        with self.assertRaisesRegex(ValueError, "outside"):
            export(self.project, output)
        self.assertFalse(output.exists())

    def test_install_saves_choices_and_force_preserves_them(self):
        kit = self.base / "kit"
        kit.mkdir()
        for name in ("install.sh", "configure.sh", "tools/project_settings.py"):
            target = kit / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        (kit / "claude-settings.json").write_text("{}")
        skill = kit / "claude-skills/test/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("fixture skill")
        command = [str(kit / "install.sh"), str(self.project), "--no-system", "--fps", "24",
                   "--piano", "vsco"]
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(read(self.project), {"fps": 24, "piano": "vsco"})
        subprocess.run([str(kit / "install.sh"), str(self.project), "--no-system", "--force"],
                       check=True, capture_output=True)
        self.assertEqual(read(self.project)["fps"], 24)

    def test_setup_fetches_only_selected_libraries(self):
        for name in ("configure.sh", "tools/project_settings.py"):
            target = self.project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        script = ('source "$1/setup.sh" --check; ROOT="$2"; '
                  'sample_set() { echo "LIBRARY:$1"; }; fetch_samples')
        for choice, expected in (("vsco", False), ("salamander", True)):
            configure(self.project, 30, choice)
            result = subprocess.run(["bash", "-c", script, "bash", str(ROOT), str(self.project)],
                                    check=True, capture_output=True, text=True)
            self.assertIn("LIBRARY:VSCO-2 CE", result.stdout)
            self.assertEqual("LIBRARY:Salamander piano" in result.stdout, expected)


if __name__ == "__main__":
    unittest.main()
