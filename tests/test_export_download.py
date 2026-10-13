"""sulaide-cli#14: native export download (no run_id) and error bodies never written to disk."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sulaide_cli.cli import ApiError, build_parser, run


class _Resp:
    def __init__(self, content, ctype, status=200):
        self.content, self.status_code = content, status
        self.headers = {"content-type": ctype, "x-sulaide-source-hash": "src"}
        self.is_error = status >= 400
        self.text = content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.content)


def _client(resp, seen):
    class Http:
        def get(self, url, **kwargs):
            seen.append(kwargs.get("params"))
            return resp

    class C:
        http = Http()
        base = "https://example.invalid/api/agent/v1"
    return C()


class ExportDownloadTests(unittest.TestCase):
    def _run(self, resp, *extra):
        seen = []
        with TemporaryDirectory() as d:
            out = Path(d) / "deck.pptx"
            args = build_parser().parse_args(["export", "download", "309", "654", "hash", "--output", str(out), *extra])
            with patch("sulaide_cli.cli.Client", return_value=_client(resp, seen)):
                try:
                    return run(args), seen, out.exists(), list(Path(d).iterdir())
                except Exception as exc:  # noqa: BLE001
                    return exc, seen, out.exists(), list(Path(d).iterdir())

    def test_native_download_omits_run_id(self):
        result, seen, exists, _ = self._run(_Resp(b"PK\x03\x04data", "application/vnd.openxmlformats-officedocument.presentationml.presentation"))
        self.assertEqual(seen, [{"manifest_hash": "hash"}])
        self.assertTrue(exists)
        self.assertEqual(result["size_bytes"], 8)

    def test_run_id_is_forwarded(self):
        _, seen, _, _ = self._run(_Resp(b"PKxx", "application/octet-stream"), "--run-id", "r1")
        self.assertEqual(seen, [{"manifest_hash": "hash", "run_id": "r1"}])

    def test_http200_business_error_raises_and_writes_nothing(self):
        body = json.dumps({"code": 404, "message": "可编辑导出任务不存在", "data": None}).encode()
        exc, _, exists, files = self._run(_Resp(body, "application/json"))
        self.assertIsInstance(exc, ApiError)
        self.assertFalse(exists)
        self.assertEqual(files, [])

    def test_http_error_raises_and_writes_nothing(self):
        body = json.dumps({"code": 422, "message": "bad"}).encode()
        exc, _, exists, files = self._run(_Resp(body, "application/json", status=422))
        self.assertIsInstance(exc, ApiError)
        self.assertEqual(files, [])

    def test_non_zip_body_rejected_without_writing(self):
        exc, _, _, files = self._run(_Resp(b"<html>oops</html>", "text/html"))
        self.assertIsInstance(exc, ValueError)
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
