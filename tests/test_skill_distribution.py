import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ("login", "projects", "resources", "source", "analysis", "preview", "export")


class SkillDistributionTests(unittest.TestCase):
    def test_single_skill_is_packaged_with_references(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "scripts/package-workflow-skills.py"),
                            "--output", directory], check=True, capture_output=True, text=True)
            archives = sorted(Path(directory).glob("*.zip"))
            self.assertEqual(len(archives), 1)
            with zipfile.ZipFile(archives[0]) as bundle:
                names = set(bundle.namelist())
                self.assertIn("sulaide/SKILL.md", names)
                for ref in REFERENCES:
                    self.assertIn(f"sulaide/references/{ref}.md", names)

    def test_sulaide_is_the_only_frontmatter_skill(self):
        skill_files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob("SKILL.md"))
        self.assertEqual(skill_files, ["skills/sulaide/SKILL.md"])
        self.assertTrue((ROOT / "skills/sulaide/SKILL.md").read_text().startswith("---\nname: sulaide\n"))
        for ref in (ROOT / "skills/sulaide/references").glob("*.md"):
            self.assertFalse(ref.read_text().startswith("---"), f"{ref} must not have frontmatter")

    def test_skill_routes_to_every_reference(self):
        body = (ROOT / "skills/sulaide/SKILL.md").read_text()
        for ref in REFERENCES:
            self.assertIn(f"references/{ref}.md", body)
            self.assertTrue((ROOT / f"skills/sulaide/references/{ref}.md").is_file())
        self.assertIsNone(re.search(r"`sulaide-(login|source|analysis|preview|export)`", body))


if __name__ == "__main__":
    unittest.main()
