import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillDistributionTests(unittest.TestCase):
    def test_each_workflow_skill_is_packaged_standalone(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "scripts/package-workflow-skills.py"),
                            "--output", directory], check=True, capture_output=True, text=True)
            archives = sorted(Path(directory).glob("*.zip"))
            self.assertEqual(len(archives), 6)
            for archive in archives:
                with zipfile.ZipFile(archive) as bundle:
                    names = bundle.namelist()
                    self.assertEqual(len(names), 1)
                    content = bundle.read(names[0]).decode()
                    self.assertIn("name: sulaide", content)
                    self.assertIn("sulaide", content)


if __name__ == "__main__":
    unittest.main()
