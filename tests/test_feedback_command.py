import io
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from sulaide_cli import cli, feedback


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"SULAIDE_API_KEY": "sul_live_SECRETVALUE123", "SULAIDE_BASE_URL": ""})
        self.env.start()
        self.browser = patch("sulaide_cli.feedback.webbrowser.open", return_value=True)
        self.opened = self.browser.start()

    def tearDown(self):
        self.browser.stop(); self.env.stop()

    def _main(self, *argv):
        out = io.StringIO()
        with patch("sys.argv", ["sulaide", *argv]), redirect_stdout(out):
            cli.main()
        return json.loads(out.getvalue())

    def test_redacts_secrets(self):
        text = feedback.redact(
            "Authorization: Bearer abcdefghijkl key sul_abcDEF123456 ghp_" + "a" * 36 +
            " api_key=xyz123 me@example.com eyJhbGciOiJI.eyJzdWIiOiIx.c2lnbmF0dXJl sul_live_SECRETVALUE123")
        for secret in ("abcdefghijkl", "sul_abcDEF123456", "ghp_aaaa", "xyz123", "me@example.com", "eyJhbGciOiJI", "SECRETVALUE"):
            self.assertNotIn(secret, text)
        self.assertIn("me@example.com", feedback.redact("me@example.com", emails=False))

    def test_builds_prefilled_url_and_opens(self):
        result = self._main("feedback", "-m", "导出失败", "--error", "HTTP 500 Authorization: Bearer tok_abcdefgh123")
        q = parse_qs(urlparse(result["url"]).query)
        self.assertTrue(result["url"].startswith("https://github.com/univteam/sulaide-cli/issues/new?"))
        self.assertEqual(q["title"][0], "[Bug] 导出失败")
        self.assertEqual(q["labels"][0], "bug")
        body = q["body"][0]
        self.assertIn("导出失败", body); self.assertIn("HTTP 500", body)
        self.assertNotIn("tok_abcdefgh123", body)
        self.assertIn("base_url: https://www.sulide.com.cn", body)
        self.opened.assert_called_once_with(result["url"])

    def test_custom_base_url_hidden_and_no_open(self):
        with patch.dict("os.environ", {"SULAIDE_BASE_URL": "https://internal.example.org"}):
            result = self._main("issue", "--type", "feature", "--title", "加个功能", "--no-open")
        self.assertIn("base_url: <custom>", result["body"])
        self.assertNotIn("internal.example.org", result["url"])
        self.assertTrue(result["title"].startswith("[Feature]"))
        self.opened.assert_not_called()

    def test_body_truncated(self):
        result = feedback.build(title="t", body="x" * 20000)
        self.assertLessEqual(len(result["body"]), feedback.MAX_BODY)
        self.assertIn("截断", result["body"])

    def test_error_from_stdin(self):
        with patch("sys.stdin", io.StringIO("Traceback boom")):
            result = self._main("feedback", "-m", "x", "--error", "-", "--no-open")
        self.assertIn("Traceback boom", result["body"])

    def test_gh_create(self):
        calls = []
        def run(cmd, **kw):
            calls.append(cmd)
            if cmd[1:3] == ["auth", "status"]:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            return subprocess.CompletedProcess(cmd, 0, "https://github.com/univteam/sulaide-cli/issues/9\n", "")
        with patch("sulaide_cli.feedback.shutil.which", return_value="/bin/gh"), \
             patch("sulaide_cli.feedback.subprocess.run", side_effect=run):
            result = self._main("feedback", "-m", "坏了", "--gh")
        self.assertEqual(result["issue_url"], "https://github.com/univteam/sulaide-cli/issues/9")
        create = calls[-1]
        self.assertEqual(create[:5], ["gh", "issue", "create", "--repo", "univteam/sulaide-cli"])
        self.assertNotIn("SECRETVALUE", " ".join(create))
        self.opened.assert_not_called()

    def test_gh_missing(self):
        with patch("sulaide_cli.feedback.shutil.which", return_value=None), self.assertRaises(SystemExit):
            self._main("feedback", "-m", "x", "--gh")


if __name__ == "__main__":
    unittest.main()
