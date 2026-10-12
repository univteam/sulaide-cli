import unittest
from unittest.mock import patch

from sulaide_cli.cli import build_parser, run


class WorkflowCommandTests(unittest.TestCase):
    def test_source_and_analysis_require_explicit_project(self):
        args = build_parser().parse_args(["analysis", "start", "23", "--request-id", "handoff"])
        self.assertEqual(args.project_id, 23)
        self.assertEqual(args.request_id, "handoff")

    def test_wait_timeout_does_not_submit_new_request(self):
        class FakeClient:
            def request(self, *args, **kwargs):
                return {"run": {"status": "running", "progress": 1}}
        args = build_parser().parse_args(["wait", "operation-1", "--timeout", "0"])
        with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
            with self.assertRaises(TimeoutError):
                run(args)


if __name__ == "__main__":
    unittest.main()
