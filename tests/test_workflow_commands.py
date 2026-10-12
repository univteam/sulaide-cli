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

    def test_projects_list_and_show_parse(self):
        listed = build_parser().parse_args(["projects", "list"])
        self.assertEqual((listed.area, listed.action), ("projects", "list"))
        shown = build_parser().parse_args(["projects", "show", "7"])
        self.assertEqual(shown.project_id, 7)

    def test_projects_list_calls_get_projects(self):
        calls = []

        class FakeClient:
            def request(self, method, path, **kwargs):
                calls.append((method, path))
                return {"items": []}

        args = build_parser().parse_args(["projects", "list"])
        with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
            self.assertEqual(run(args), {"items": []})
        self.assertEqual(calls, [("GET", "/projects")])

    def test_projects_show_calls_get_project(self):
        calls = []

        class FakeClient:
            def request(self, method, path, **kwargs):
                calls.append((method, path))
                return {"project_id": 7}

        args = build_parser().parse_args(["projects", "show", "7"])
        with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
            self.assertEqual(run(args), {"project_id": 7})
        self.assertEqual(calls, [("GET", "/projects/7")])


if __name__ == "__main__":
    unittest.main()
