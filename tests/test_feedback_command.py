import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import httpx

from sulaide_cli import cli, feedback


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"SULAIDE_API_KEY": "sul_live_SECRETVALUE123", "SULAIDE_BASE_URL": ""})
        self.env.start()
        self.calls = []
        test = self

        class FakeClient:
            def request(self, method, path, **kwargs):
                test.calls.append((method, path, kwargs))
                if method == "GET":
                    return {"items": [{"id": 3, "status": "resolved"}], "total": 1, "page": 1, "page_size": 20}
                return {"id": 3, "status": "open", "title": kwargs["json_body"]["title"], "created_at": "2026-10-15T08:00:00"}
        self.client = patch("sulaide_cli.cli.Client", return_value=FakeClient())
        self.client.start()

    def tearDown(self):
        self.client.stop(); self.env.stop()

    def _main(self, *argv):
        out = io.StringIO()
        with patch("sys.argv", ["sulaide", *argv]), redirect_stdout(out):
            cli.main()
        return json.loads(out.getvalue())

    def test_redacts_secrets(self):
        text = feedback.redact(
            "Authorization: Bearer abcdefghijkl key sul_abcDEF123456.secretpart ghp_" + "a" * 36 +
            " api_key=xyz123 me@example.com eyJhbGciOiJI.eyJzdWIiOiIx.c2lnbmF0dXJl sul_live_SECRETVALUE123")
        for secret in ("abcdefghijkl", "sul_abcDEF123456", "secretpart", "ghp_aaaa", "xyz123", "me@example.com",
                       "eyJhbGciOiJI", "SECRETVALUE"):
            self.assertNotIn(secret, text)
        self.assertIn("me@example.com", feedback.redact("me@example.com", emails=False))

    def test_submits_redacted_payload_to_platform(self):
        result = self._main("feedback", "-m", "导出失败 me@example.com", "--error",
                            "HTTP 500 Authorization: Bearer tok_abcdefgh123")
        self.assertTrue(result["submitted"])
        self.assertEqual((result["id"], result["status"]), (3, "open"))
        method, path, kwargs = self.calls[0]
        self.assertEqual((method, path), ("POST", "/feedback"))
        payload = kwargs["json_body"]
        self.assertEqual(payload["type"], "bug")
        self.assertEqual(payload["title"], "导出失败 <email>")
        self.assertIn("HTTP 500", payload["error_output"])
        self.assertNotIn("tok_abcdefgh123", json.dumps(payload))
        self.assertEqual(payload["client_meta"]["base_url"], "https://www.sulide.com.cn")
        self.assertTrue(payload["client_meta"]["cli_version"])
        self.assertNotIn("github", json.dumps(result).lower())

    def test_custom_base_url_hidden_and_alias(self):
        with patch.dict("os.environ", {"SULAIDE_BASE_URL": "https://internal.example.org"}):
            self._main("issue", "--type", "feature", "--title", "加个功能", "-m", "想要批量导出")
        payload = self.calls[0][2]["json_body"]
        self.assertEqual((payload["type"], payload["title"]), ("feature", "加个功能"))
        self.assertEqual(payload["client_meta"]["base_url"], "<custom>")
        self.assertNotIn("internal.example.org", json.dumps(payload))

    def test_dry_run_does_not_submit(self):
        result = self._main("feedback", "-m", "预览一下", "--dry-run")
        self.assertFalse(result["submitted"])
        self.assertEqual(result["payload"]["body"], "预览一下")
        self.assertEqual(self.calls, [])

    def test_list_own_feedback(self):
        result = self._main("feedback", "--list")
        self.assertEqual(result["items"][0]["status"], "resolved")
        self.assertEqual(self.calls[0][:2], ("GET", "/feedback"))
        self.assertEqual(self.calls[0][2]["params"], {"page": 1, "page_size": 20})

    def test_requires_description_or_error(self):
        with self.assertRaises(ValueError):
            feedback.build(title="only title", body=None)

    def test_truncation(self):
        result = feedback.build(title="t" * 500, body="x" * 20000, error="e" * 20000)
        self.assertLessEqual(len(result["body"]), feedback.MAX_BODY)
        self.assertLessEqual(len(result["error_output"]), feedback.MAX_ERROR)
        self.assertLessEqual(len(result["title"]), feedback.MAX_TITLE)
        self.assertIn("截断", result["body"])

    def test_error_from_stdin(self):
        with patch("sys.stdin", io.StringIO("Traceback: boom\n")):
            self._main("feedback", "--title", "崩了", "--error", "-")
        self.assertEqual(self.calls[0][2]["json_body"]["error_output"], "Traceback: boom")

    def test_not_logged_in(self):
        self.client.stop()
        try:
            with patch.dict("os.environ", {"SULAIDE_API_KEY": ""}), \
                    patch("sulaide_cli.cli._read_auth", return_value={}), self.assertRaises(ValueError):
                feedback.submit(cli.build_parser().parse_args(["feedback", "-m", "x"]))
        finally:
            self.client.start()

    def test_business_error_from_server_is_raised(self):
        def handler(request):
            self.assertEqual(request.url.path, "/api/agent/v1/feedback")
            self.assertEqual(request.headers["authorization"], "Bearer sul_live_SECRETVALUE123")
            return httpx.Response(200, json={"code": 429, "message": "反馈提交太频繁，请稍后再试", "data": None})
        self.client.stop()
        try:
            real = cli.Client()
            real.http = httpx.Client(transport=httpx.MockTransport(handler), headers=real.http.headers)
            with self.assertRaises(cli.ApiError) as ctx:
                feedback.submit(cli.build_parser().parse_args(["feedback", "-m", "x"]), client=real)
            self.assertEqual(ctx.exception.status, 429)
        finally:
            self.client.start()


if __name__ == "__main__":
    unittest.main()
