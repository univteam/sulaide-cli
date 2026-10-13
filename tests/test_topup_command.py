import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from sulaide_cli import cli

PAY_URL = "https://openapi.alipay.com/gateway.do?sign=abc"


class TopupCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict("os.environ", {"SULAIDE_STATE_DIR": self.tmp.name, "SULAIDE_API_KEY": "k"})
        self.env.start()
        self.calls = []
        self.statuses = ["pending_payment", "paid"]
        self.pay_url = PAY_URL
        test = self

        class FakeClient:
            def request(self, method, path, **kwargs):
                test.calls.append((method, path, kwargs.get("json_body")))
                if path == "/topup/packages":
                    return {"items": [{"id": 3, "name": "基础包", "price": "9.90", "credit_amount": "100", "promotion_label": None}]}
                if method == "POST":
                    return {"order_no": "CO1", "status": "pending_payment", "payable_amount": "9.90", "credit_amount": "100",
                            "payment": {"pay_url": test.pay_url, "expires_at": "2026-10-13T15:00:00"}}
                status = test.statuses.pop(0)
                body = {"order_no": "CO1", "status": status, "credit_amount": "100"}
                if status == "paid":
                    body["balance"] = {"available": "110", "balance": "110"}
                return body
        self.patcher = patch("sulaide_cli.cli.Client", return_value=FakeClient())
        self.patcher.start()
        self.sleep = patch("sulaide_cli.cli.time.sleep")
        self.sleep.start()
        self.browser = patch("sulaide_cli.cli.webbrowser.open", return_value=True)
        self.opened = self.browser.start()

    def tearDown(self):
        for p in (self.patcher, self.sleep, self.browser, self.env):
            p.stop()
        self.tmp.cleanup()

    def _main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["sulaide", *argv]), redirect_stdout(out), redirect_stderr(err):
            cli.main()
        return out.getvalue(), err.getvalue()

    def test_lists_packages(self):
        out, _ = self._main("topup", "--human")
        self.assertIn("[3] 基础包：¥9.90 → 100 积分", out)

    def test_creates_order_opens_alipay_and_polls_until_paid(self):
        out, err = self._main("topup", "--package", "3", "--open", "--human")
        self.assertIn(PAY_URL, err)
        self.opened.assert_called_once_with(PAY_URL)
        self.assertIn("当前可用积分 110", out)
        post = [c for c in self.calls if c[0] == "POST"][0]
        self.assertEqual(post[2]["package_id"], 3)
        self.assertGreaterEqual(len(post[2]["request_id"]), 8)
        self.assertEqual([c[1] for c in self.calls if c[0] == "GET"], ["/topup/orders/CO1"] * 2)

    def test_new_run_gets_new_request_id(self):
        self._main("topup", "--package", "3", "--no-wait")
        self._main("topup", "--package", "3", "--no-wait")
        ids = [c[2]["request_id"] for c in self.calls if c[0] == "POST"]
        self.assertNotEqual(ids[0], ids[1])

    def test_no_wait_returns_order(self):
        out, _ = self._main("topup", "--package", "3", "--no-wait")
        self.assertEqual(json.loads(out)["payment"]["pay_url"], PAY_URL)
        self.opened.assert_not_called()

    def test_refuses_non_alipay_link(self):
        self.pay_url = "https://evil.example.com/pay"
        with self.assertRaises(SystemExit):
            self._main("topup", "--package", "3", "--open")
        self.opened.assert_not_called()

    def test_timeout(self):
        self.statuses = ["pending_payment"] * 10
        with patch("sulaide_cli.cli.time.monotonic", side_effect=[0, 0, 1000]), self.assertRaises(SystemExit) as ctx:
            self._main("topup", "--package", "3", "--timeout", "10")
        self.assertEqual(ctx.exception.code, 5)

    def test_packages_commands(self):
        for argv in (("packages", "--human"), ("topup", "packages", "--human")):
            out, _ = self._main(*argv)
            self.assertIn("[3] 基础包", out)
            self.assertIn("--package <ID>", out)
        out, _ = self._main("topup")
        self.assertEqual(json.loads(out)["how_to_buy"], "sulaide topup --package <ID> --open")
        self.assertNotIn("POST", [c[0] for c in self.calls])

    def test_status(self):
        self.statuses = ["paid"]
        out, _ = self._main("topup", "--status", "CO1")
        self.assertEqual(json.loads(out)["status"], "paid")

    def test_web_opens_recharge_page_without_api_key(self):
        with patch.dict("os.environ", {"SULAIDE_API_KEY": ""}):
            out, _ = self._main("topup", "--web")
        self.opened.assert_called_once_with("https://www.sulide.com.cn/app/credits")
        self.assertEqual(self.calls, [])

    def test_alipay_host_check(self):
        self.assertTrue(cli._is_alipay_url("https://openapi.alipay.com/gateway.do"))
        self.assertFalse(cli._is_alipay_url("http://openapi.alipay.com/gateway.do"))
        self.assertFalse(cli._is_alipay_url("https://alipay.com.evil.cn/x"))


if __name__ == "__main__":
    unittest.main()
