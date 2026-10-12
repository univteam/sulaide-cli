import json
import base64
import os
import stat
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from sulaide_cli import cli


class AuthCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SULAIDE_STATE_DIR": self.temp_dir.name}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp_dir.cleanup()

    def test_login_prompts_for_password_and_persists_only_the_api_key(self):
        calls = []

        def request(method, path, *, token=None, json_body=None):
            calls.append((method, path, token, json_body))
            if path == "/api/auth/login":
                return {"token": "jwt-only-for-key-creation", "username": "alice", "role": "USER"}
            if path == "/api/account/me":
                return {"id": 42}
            if method == "POST":
                return {"id": 7, "secret": "sul_private.once"}
            raise AssertionError(path)

        with patch.object(cli, "_auth_request", side_effect=request), \
             patch.object(cli.getpass, "getpass", return_value="hidden-password"):
            result = cli._auth_command(Namespace(action="login", username="alice"))

        stored = json.loads((Path(self.temp_dir.name) / "auth.json").read_text())
        self.assertEqual(result["username"], "alice")
        self.assertTrue(result["api_key_saved"])
        self.assertEqual(stored["api_key"], "sul_private.once")
        self.assertNotIn("token", stored)
        self.assertNotIn("password", stored)
        self.assertEqual(stat.S_IMODE((Path(self.temp_dir.name) / "auth.json").stat().st_mode), 0o600)
        self.assertEqual(calls[-1][2], "jwt-only-for-key-creation")

    def test_registration_requires_explicit_consent_and_posts_current_legal_versions(self):
        args = Namespace(action="register", username="alice", email="alice@example.com", invite_code=None)
        calls = []

        def request(method, path, *, token=None, json_body=None):
            calls.append((method, path, json_body))
            if path == "/api/auth/legal-config":
                return {"privacy_policy_version": "privacy-v2", "terms_version": "terms-v3"}
            if path == "/api/auth/email-verification-config":
                return {"enabled": False}
            if path == "/api/auth/register":
                return {"token": "jwt", "username": "alice", "role": "USER"}
            if path == "/api/account/me":
                return {"id": 42}
            if path == "/api/account/api-keys":
                return {"id": 7, "secret": "sul_private.once"}
            raise AssertionError(path)

        with patch.object(cli, "_auth_request", side_effect=request), \
             patch.object(cli.getpass, "getpass", side_effect=["secret-pass", "secret-pass"]), \
             patch("builtins.input", return_value="yes"):
            cli._auth_command(args)

        payload = next(body for _, path, body in calls if path == "/api/auth/register")
        self.assertTrue(payload["accepted_legal"])
        self.assertEqual(payload["privacy_policy_version"], "privacy-v2")
        self.assertEqual(payload["terms_version"], "terms-v3")
        self.assertEqual(payload["password"], "secret-pass")

    def test_parser_has_auth_lifecycle_commands_without_password_arguments(self):
        parser = cli.build_parser()
        login = parser.parse_args(["auth", "login", "--username", "alice"])
        register = parser.parse_args(["auth", "register", "--username", "alice", "--email", "alice@example.com"])
        self.assertEqual(login.action, "login")
        self.assertEqual(register.action, "register")
        with self.assertRaises(SystemExit):
            parser.parse_args(["auth", "login", "--username", "alice", "--password", "unsafe"])

    def test_logout_removes_local_credential(self):
        cli._write_auth({"api_key": "sul_private.secret"})
        result = cli._auth_command(Namespace(action="logout"))
        self.assertTrue(result["logged_out"])
        self.assertFalse((Path(self.temp_dir.name) / "auth.json").exists())

    def test_email_verification_uses_server_captcha_and_removes_temporary_image(self):
        challenge = {"token": "captcha-token", "image_base64": base64.b64encode(b"png-bytes").decode()}
        calls = []

        def request(method, path, *, token=None, json_body=None):
            calls.append((method, path, json_body))
            return challenge if path == "/api/captcha/generate" else None

        with patch.object(cli, "_auth_request", side_effect=request), \
             patch.object(cli.getpass, "getpass", return_value="4"), \
             patch("builtins.input", return_value="123456"), \
             patch.object(cli.sys.stdin, "isatty", return_value=False):
            code = cli._captcha_answer("alice@example.com")

        sent = calls[-1][2]
        self.assertEqual(code, "123456")
        self.assertEqual(sent, {"email": "alice@example.com", "captcha_token": "captcha-token", "captcha_answer": "4"})
        self.assertFalse((Path(self.temp_dir.name) / "registration-captcha.png").exists())


if __name__ == "__main__":
    unittest.main()
