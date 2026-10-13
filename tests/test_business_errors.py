import io
import json
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import httpx

from sulaide_cli import cli
from sulaide_cli.cli import ApiError, Client

REAL_HTTPX_CLIENT = httpx.Client
ENV = {"SULAIDE_API_KEY": "sul_test.secret", "SULAIDE_BASE_URL": "https://api.test"}


def _patched(handler):
    transport = httpx.MockTransport(handler)
    return patch("sulaide_cli.cli.httpx.Client",
                 side_effect=lambda **kwargs: REAL_HTTPX_CLIENT(transport=transport, **kwargs))


BUSINESS = {"code": 402, "message": "积分余额不足，请先购买积分", "data": None, "traceId": "abc123"}


class BusinessErrorTests(unittest.TestCase):
    def test_code_nonzero_raises_with_message_code_and_trace(self):
        with patch.dict(os.environ, ENV), _patched(lambda r: httpx.Response(200, json=BUSINESS)):
            with self.assertRaises(ApiError) as ctx:
                Client().request("POST", "/projects/1/analysis", json_body={})
        self.assertEqual(ctx.exception.status, 402)
        self.assertEqual(ctx.exception.detail["message"], "积分余额不足，请先购买积分")
        self.assertEqual(ctx.exception.detail["code"], 402)
        self.assertEqual(ctx.exception.detail["trace_id"], "abc123")

    def test_code_zero_returns_data(self):
        with patch.dict(os.environ, ENV), _patched(lambda r: httpx.Response(200, json={"code": 0, "data": {"x": 1}})):
            self.assertEqual(Client().request("GET", "/x"), {"x": 1})

    def test_http_error_envelope_is_parsed(self):
        body = {"code": 422, "message": "bad", "data": None, "traceId": "t1"}
        with patch.dict(os.environ, ENV), _patched(lambda r: httpx.Response(422, json=body)):
            with self.assertRaises(ApiError) as ctx:
                Client().request("GET", "/x")
        self.assertEqual(ctx.exception.detail, {"code": 422, "message": "bad", "trace_id": "t1"})

    def test_cli_prints_business_error_instead_of_crashing(self):
        stderr = io.StringIO()
        with patch.dict(os.environ, ENV), _patched(lambda r: httpx.Response(200, json=BUSINESS)), \
             patch.object(cli, "_request_id", return_value="rid"), redirect_stderr(stderr), \
             patch("sys.argv", ["sulaide", "analysis", "start", "1", "--page-count", "3"]):
            with self.assertRaises(SystemExit) as exit_ctx:
                cli.main()
        self.assertEqual(exit_ctx.exception.code, 2)
        error = json.loads(stderr.getvalue().strip().splitlines()[-1])["error"]
        self.assertEqual(error["http_status"], 402)
        self.assertEqual(error["message"], "积分余额不足，请先购买积分")
        self.assertEqual(error["trace_id"], "abc123")


class PreviewShowTests(unittest.TestCase):
    def _query(self, argv):
        seen = {}

        def handler(request):
            seen["query"] = dict(request.url.params)
            return httpx.Response(200, json={"code": 0, "data": {"project_id": 1}})
        with patch.dict(os.environ, ENV), _patched(handler), patch("sys.argv", argv), \
             redirect_stderr(io.StringIO()), patch("sys.stdout", io.StringIO()):
            cli.main()
        return seen["query"]

    def test_omitted_version_id_is_not_sent(self):
        self.assertEqual(self._query(["sulaide", "preview", "show", "1"]), {})

    def test_explicit_version_id_is_sent(self):
        self.assertEqual(self._query(["sulaide", "preview", "show", "1", "--version-id", "7"]), {"version_id": "7"})


if __name__ == "__main__":
    unittest.main()
