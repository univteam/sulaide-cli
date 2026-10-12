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

    def _legacy(self, agent_dir, name, marker=True):
        path = self.home / agent_dir / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        if marker:
            (path / skills.MARKER).write_text("0.2.0\n")
        return path

    def test_bundled_skill_has_references(self):
        root = skills.bundled_skills_root()
        self.assertEqual(skills.SKILL_NAMES, ("sulaide",))
        self.assertTrue((root / "sulaide/SKILL.md").is_file())
        self.assertTrue((root / "sulaide/references/login.md").is_file())

    def test_detects_agents_and_installs_single_skill(self):
        (self.home / ".claude").mkdir()
        (self.home / ".config/opencode").mkdir(parents=True)
        targets = skills.resolve_agents(None, False)
        self.assertEqual(targets, ["claude", "opencode"])
        skills.install(targets)
        for base in (self.home / ".claude/skills", self.home / ".config/opencode/skills"):
            self.assertTrue((base / "sulaide/SKILL.md").is_file())
            self.assertTrue((base / "sulaide/references/export.md").is_file())
            self.assertEqual((base / "sulaide" / skills.MARKER).read_text().strip(), __version__)
            self.assertEqual(sorted(p.name for p in base.iterdir()), ["sulaide"])

    def test_install_removes_only_our_legacy_skill_dirs(self):
        ours = self._legacy(".claude/skills", "sulaide-source")
        foreign = self._legacy(".claude/skills", "sulaide-export", marker=False)
        result = skills.install(["claude"])
        self.assertFalse(ours.exists())
        self.assertTrue(foreign.exists())
        self.assertIn("removed_legacy", {r["status"] for r in result["results"]})

    def test_update_migrates_agents_that_only_have_legacy_skills(self):
        self._legacy(".codex/skills", "sulaide-preview")
        (self.home / ".cursor").mkdir()
        result = skills.update()
        self.assertEqual({r["agent"] for r in result["results"]}, {"codex"})
        self.assertTrue((self.home / ".codex/skills/sulaide/SKILL.md").is_file())
        self.assertFalse((self.home / ".codex/skills/sulaide-preview").exists())
        self.assertFalse((self.home / ".cursor/skills").exists())

    def test_no_agent_detected_requires_explicit_choice(self):
        with self.assertRaisesRegex(ValueError, "--agent"):
            skills.resolve_agents(None, False)

    def test_unknown_agent_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown agent"):
            skills.resolve_agents(["nope"], False)

    def test_foreign_directory_is_not_overwritten_without_force(self):
        foreign = self.home / ".claude/skills/sulaide"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("mine")
        result = skills.install(["claude"])
        self.assertIn("skipped_foreign", {r["status"] for r in result["results"]})
        self.assertEqual((foreign / "SKILL.md").read_text(), "mine")
        skills.install(["claude"], force=True)
        self.assertIn("name: sulaide", (foreign / "SKILL.md").read_text())

    def test_uninstall_and_status(self):
        skills.install(["gemini"])
        legacy = self._legacy(".gemini/skills", "sulaide-login")
        row = next(r for r in skills.status()["agents"] if r["agent"] == "gemini")
        self.assertEqual(row["skills"]["sulaide"], __version__)
        skills.uninstall(["gemini"])
        self.assertFalse((self.home / ".gemini/skills/sulaide").exists())
        self.assertFalse(legacy.exists())


if __name__ == "__main__":
    unittest.main()
