import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = Path(__file__).parent / "schemas"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class PluginManifestTests(unittest.TestCase):
    def test_manifests_are_in_sync_with_pyproject(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sync-plugin-manifests.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_agent_plugins_manifest_matches_schema(self):
        schema = json.loads((SCHEMAS / "agent-plugins-1.0.0.plugin.schema.json").read_text())
        jsonschema.validate(load("plugin.json"), schema)

    @unittest.skipUnless(os.environ.get("CURSOR_SCHEMA_DIR"), "CURSOR_SCHEMA_DIR not set (CI downloads Cursor schemas)")
    def test_cursor_manifests_match_schema(self):
        schemas = Path(os.environ["CURSOR_SCHEMA_DIR"])
        jsonschema.validate(load(".cursor-plugin/plugin.json"),
                            json.loads((schemas / "plugin.schema.json").read_text()))
        jsonschema.validate(load(".cursor-plugin/marketplace.json"),
                            json.loads((schemas / "marketplace.schema.json").read_text()))

    def test_every_marketplace_points_at_repo_root_with_skills(self):
        claude = load(".claude-plugin/marketplace.json")
        self.assertEqual(claude["plugins"][0]["source"], "./")
        codex = load(".agents/plugins/marketplace.json")
        self.assertEqual(codex["plugins"][0]["source"]["path"], "./")
        self.assertTrue((ROOT / "skills/sulaide/SKILL.md").is_file())

    def test_no_duplicate_skill_copies_in_repo(self):
        copies = [p for p in ROOT.rglob("SKILL.md")
                  if ".git" not in p.parts and ".venv" not in p.parts and "build" not in p.parts
                  and p.parent.parent != ROOT / "skills"]
        self.assertEqual(copies, [])


if __name__ == "__main__":
    unittest.main()
