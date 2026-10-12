import os
import tempfile
import unittest
from unittest.mock import patch

import httpx

from sulaide_cli.cli import Client, _base_url

REAL_HTTPX_CLIENT = httpx.Client


class ClientAuthTests(unittest.TestCase):
    def test_remote_base_url_requires_https(self):
        with patch.dict(os.environ, {"SULAIDE_BASE_URL": "http://example.test"}, clear=False):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                _base_url()

    def test_default_base_url_is_production(self):
        env = {k: v for k, v in os.environ.items() if k != "SULAIDE_BASE_URL"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(_base_url(), "https://www.sulide.com.cn")

    def test_environment_overrides_default_base_url(self):
        with patch.dict(os.environ, {"SULAIDE_BASE_URL": "https://api.test/"}, clear=False):
            self.assertEqual(_base_url(), "https://api.test")

    def test_local_http_is_allowed(self):
        with patch.dict(os.environ, {"SULAIDE_BASE_URL": "http://localhost:8000"}, clear=False):
            self.assertEqual(_base_url(), "http://localhost:8000")

    def test_api_key_is_header_only_and_redirects_are_disabled(self):
        captured = {}
        def handler(request):
            captured["authorization"] = request.headers.get("Authorization")
            return httpx.Response(200, json={"data": {"api_version": "v1"}})
        transport = httpx.MockTransport(handler)
        with patch.dict(os.environ, {"SULAIDE_API_KEY": "sul_private.secret", "SULAIDE_BASE_URL": "https://api.test"}, clear=False), \
             patch("sulaide_cli.cli.httpx.Client", side_effect=lambda **kwargs: REAL_HTTPX_CLIENT(transport=transport, **kwargs)):
            client = Client()
            result = client.request("GET", "/capabilities")
            self.assertFalse(client.http.follow_redirects)
            self.assertEqual(result["api_version"], "v1")
            self.assertEqual(captured["authorization"], "Bearer sul_private.secret")

    def test_saved_cli_key_is_used_when_environment_key_is_absent(self):
        captured = {}
        def handler(request):
            captured["authorization"] = request.headers.get("Authorization")
            return httpx.Response(200, json={"data": {"api_version": "v1"}})
        transport = httpx.MockTransport(handler)
        with tempfile.TemporaryDirectory() as state_dir:
            with patch.dict(os.environ, {"SULAIDE_STATE_DIR": state_dir, "SULAIDE_BASE_URL": "https://api.test"}, clear=False):
                os.environ.pop("SULAIDE_API_KEY", None)
                from sulaide_cli.cli import _write_auth
                _write_auth({"api_key": "sul_local.saved"})
                with patch("sulaide_cli.cli.httpx.Client", side_effect=lambda **kwargs: REAL_HTTPX_CLIENT(transport=transport, **kwargs)):
                    self.assertEqual(Client().request("GET", "/capabilities")["api_version"], "v1")
        self.assertEqual(captured["authorization"], "Bearer sul_local.saved")


if __name__ == "__main__":
    unittest.main()
