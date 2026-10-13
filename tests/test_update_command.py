import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sulaide_cli import cli, update

OLD = {"version": "0.2.0", "commit": "a" * 40}
NEW = {"version": "0.2.0", "commit": "b" * 40}


def _proc(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, out, err)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.cmds = []
        patch("sulaide_cli.update.shutil.which", side_effect=lambda n: f"/bin/{n}").start()
        patch("sulaide_cli.update.local_info", return_value=OLD).start()
        self.addCleanup(patch.stopall)

    def _fake_run(self, upgrade_rc=0, after_upgrade=NEW, after_force=NEW):
        state = {"forced": False}

        def run(cmd):
            self.cmds.append(cmd[1:])
            if cmd[1:3] == ["tool", "list"]:
                return _proc(out="sulaide-cli v0.2.0\n- sulaide\n")
            if cmd[1:3] == ["tool", "upgrade"]:
                return _proc(upgrade_rc, err="boom" if upgrade_rc else "")
            if cmd[1:3] == ["tool", "install"]:
                state["forced"] = True
                return _proc()
            if "--version" in cmd:
                return _proc(out=json.dumps(after_force if state["forced"] else after_upgrade))
            if cmd[1:] == ["skills", "update"]:
                return _proc(out=json.dumps({"results": [{"agent": "claude", "status": "installed"}]}))
            raise AssertionError(cmd)
        patch("sulaide_cli.update._run", side_effect=run).start()

    def test_upgrade_reports_old_new_and_refreshes_skills(self):
        self._fake_run()
        result = update.update()
        self.assertTrue(result["changed"])
        self.assertEqual(result["message"], "sulaide 0.2.0@aaaaaaa -> 0.2.0@bbbbbbb")
        self.assertIn(["tool", "upgrade", "sulaide-cli"], self.cmds)
        self.assertNotIn("install", [c[1] for c in self.cmds if c[0] == "tool"])
        self.assertIn(["skills", "update"], self.cmds)

    def test_falls_back_to_force_install_when_unchanged(self):
        self._fake_run(after_upgrade=OLD)
        result = update.update()
        self.assertIn(["tool", "install", "--force", update.GIT_SOURCE], self.cmds)
        self.assertTrue(result["changed"])

    def test_falls_back_when_upgrade_fails(self):
        self._fake_run(upgrade_rc=2)
        update.update()
        self.assertIn(["tool", "install", "--force", update.GIT_SOURCE], self.cmds)

    def test_no_skills(self):
        self._fake_run()
        result = update.update(skills=False)
        self.assertNotIn(["skills", "update"], self.cmds)
        self.assertNotIn("skills", result)

    def test_already_latest(self):
        self._fake_run(after_upgrade=OLD, after_force=OLD)
        result = update.update(skills=False)
        self.assertFalse(result["changed"])
        self.assertIn("已是最新版本", result["message"])

    def test_uv_missing(self):
        with patch("sulaide_cli.update.shutil.which", return_value=None), self.assertRaises(ValueError) as ctx:
            update.update()
        self.assertIn("未找到 uv", str(ctx.exception))

    def test_not_a_uv_tool_install(self):
        patch("sulaide_cli.update._run", return_value=_proc(out="ruff v0.1\n- ruff\n")).start()
        with self.assertRaises(ValueError):
            update.update()

    def test_check_compares_commits_without_installing(self):
        run = patch("sulaide_cli.update._run").start()
        with patch("sulaide_cli.update.latest_info", return_value=NEW):
            result = update.check()
        self.assertTrue(result["update_available"])
        run.assert_not_called()
        with patch("sulaide_cli.update.latest_info", return_value=OLD):
            self.assertFalse(update.check()["update_available"])

    def test_check_falls_back_to_version_without_commit(self):
        with patch("sulaide_cli.update.local_info", return_value={"version": "0.2.0", "commit": None}), \
             patch("sulaide_cli.update.latest_info", return_value={"version": "0.3.0", "commit": "c" * 40}):
            self.assertTrue(update.check()["update_available"])

    def test_cli_wiring_and_version(self):
        out = io.StringIO()
        with patch("sulaide_cli.update.check", return_value={"update_available": False}) as chk, \
             patch("sys.argv", ["sulaide", "update", "--check"]), redirect_stdout(out):
            cli.main()
        chk.assert_called_once()
        out = io.StringIO()
        with patch("sys.argv", ["sulaide", "--version", "--json"]), redirect_stdout(out):
            cli.main()
        self.assertEqual(json.loads(out.getvalue()), OLD)


if __name__ == "__main__":
    unittest.main()
