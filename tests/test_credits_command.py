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
