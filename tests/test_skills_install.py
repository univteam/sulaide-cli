import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sulaide_cli import __version__, skills


class SkillsInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"SULAIDE_SKILLS_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_bundled_skills_are_available(self):
        root = skills.bundled_skills_root()
        for name in skills.SKILL_NAMES:
            self.assertTrue((root / name / "SKILL.md").is_file())

    def test_detects_agents_and_installs_into_them(self):
        (self.home / ".claude").mkdir()
        (self.home / ".config/opencode").mkdir(parents=True)
        targets = skills.resolve_agents(None, False)
        self.assertEqual(targets, ["claude", "opencode"])
        skills.install(targets)
        for base in (self.home / ".claude/skills", self.home / ".config/opencode/skills"):
            for name in skills.SKILL_NAMES:
                self.assertTrue((base / name / "SKILL.md").is_file())
                self.assertEqual((base / name / skills.MARKER).read_text().strip(), __version__)

    def test_no_agent_detected_requires_explicit_choice(self):
        with self.assertRaisesRegex(ValueError, "--agent"):
            skills.resolve_agents(None, False)

    def test_unknown_agent_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown agent"):
            skills.resolve_agents(["nope"], False)

    def test_update_refreshes_only_installed_agents(self):
        skills.install(["codex"])
        skill_file = self.home / ".codex/skills/sulaide-source/SKILL.md"
        skill_file.write_text("stale")
        (self.home / ".cursor").mkdir()
        result = skills.update()
        self.assertEqual({r["agent"] for r in result["results"]}, {"codex"})
        self.assertIn("name: sulaide-source", skill_file.read_text())
        self.assertFalse((self.home / ".cursor/skills").exists())

    def test_foreign_directory_is_not_overwritten_without_force(self):
        foreign = self.home / ".claude/skills/sulaide-source"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("mine")
        result = skills.install(["claude"])
        self.assertIn("skipped_foreign", {r["status"] for r in result["results"]})
        self.assertEqual((foreign / "SKILL.md").read_text(), "mine")
        skills.install(["claude"], force=True)
        self.assertIn("name: sulaide-source", (foreign / "SKILL.md").read_text())

    def test_uninstall_and_status(self):
        skills.install(["gemini"])
        row = next(r for r in skills.status()["agents"] if r["agent"] == "gemini")
        self.assertEqual(row["skills"]["sulaide-export"], __version__)
        skills.uninstall(["gemini"])
        self.assertFalse((self.home / ".gemini/skills/sulaide-export").exists())


if __name__ == "__main__":
    unittest.main()
