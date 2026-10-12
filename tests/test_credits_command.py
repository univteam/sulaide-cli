import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sulaide_cli import cli


class CreditsCommandTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        test = self

        class FakeClient:
            def request(self, method, path, **kwargs):
                test.calls.append((method, path))
                return {"balance": "12.5", "available": "10",
                        "balance_micros": 12_500_000, "available_micros": 10_000_000}
        self.patcher = patch("sulaide_cli.cli.Client", return_value=FakeClient())
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _main(self, *argv):
        out = io.StringIO()
        with patch("sys.argv", ["sulaide", *argv]), redirect_stdout(out):
            cli.main()
        return out.getvalue()

    def test_credits_reads_agent_credit_endpoint_as_json(self):
        output = self._main("credits")
        self.assertEqual(self.calls, [("GET", "/credits")])
        self.assertIn('"available":"10"', output)

    def test_credits_human_summary(self):
        output = self._main("credits", "--human")
        self.assertEqual(output.strip(), "可用积分：10（账户余额：12.5）")


if __name__ == "__main__":
    unittest.main()


class CouponsCommandTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        test = self

        class FakeClient:
            def request(self, method, path, **kwargs):
                test.calls.append((method, path, kwargs.get("params")))
                return {"items": [{"id": 3, "name": "新人券", "status": "available", "amount": "5",
                                   "amount_cents": 500, "valid_until": "2026-10-20T00:00:00"}],
                        "total": 1, "page": 1, "size": 20}
        self.patcher = patch("sulaide_cli.cli.Client", return_value=FakeClient())
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _main(self, *argv):
        out = io.StringIO()
        with patch("sys.argv", ["sulaide", *argv]), redirect_stdout(out):
            cli.main()
        return out.getvalue()

    def test_coupons_passes_status_filter(self):
        output = self._main("coupons", "--status", "available")
        self.assertEqual(self.calls, [("GET", "/coupons", {"page": 1, "size": 20, "status": "available"})])
        self.assertIn('"name":"新人券"', output)

    def test_coupons_without_filter(self):
        self._main("coupons")
        self.assertEqual(self.calls[0][2], {"page": 1, "size": 20})

    def test_coupons_human_list(self):
        output = self._main("coupons", "--human")
        self.assertIn("- 新人券：¥5，可用，有效期至 2026-10-20", output)

    def test_invalid_status_rejected_by_parser(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["coupons", "--status", "bogus"])

    def test_no_redeem_command(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["coupons", "redeem", "X"])
