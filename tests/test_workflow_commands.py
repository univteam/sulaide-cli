import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
                return {"items": [{"id": 7, "project_title": "Q3", "stage": "draft"}]}

        args = build_parser().parse_args(["projects", "list"])
        with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
            self.assertEqual(run(args)["items"][0]["id"], 7)
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

    def test_resources_list_parses_filters(self):
        args = build_parser().parse_args(["resources", "list", "9", "--resource-type", "export_pptx", "--page-number", "2"])
        self.assertEqual(args.project_id, 9)
        self.assertEqual(args.resource_type, "export_pptx")
        self.assertEqual(args.page_number, 2)

    def test_resources_list_calls_get_resource_versions(self):
        calls = []

        class FakeClient:
            def request(self, method, path, **kwargs):
                calls.append((method, path, kwargs.get("params")))
                return {"items": []}

        args = build_parser().parse_args(["resources", "list", "9", "--resource-type", "upload"])
        with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
            self.assertEqual(run(args), {"items": []})
        self.assertEqual(calls, [("GET", "/resource-versions", {"project_id": 9, "resource_type": "upload"})])

    def test_resources_download_saves_redirected_file(self):
        downloaded = {}

        class FakeResponse:
            is_error = False
            content = b"resource-bytes"
            headers = {"content-type": "application/octet-stream"}

        class FakeHttp:
            def get(self, url, **kwargs):
                downloaded["url"] = url
                downloaded["kwargs"] = kwargs
                return FakeResponse()

        class FakeAnon:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get(self, url, **kwargs):
                downloaded["anonymous"] = True
                downloaded["url"] = url
                return FakeResponse()

        class FakeClient:
            http = FakeHttp()

            def request(self, method, path, **kwargs):
                return {"redirect_url": "https://files.example.com/signed", "filename": "deck.pptx"}

        with TemporaryDirectory() as directory:
            output = Path(directory) / "deck.pptx"
            args = build_parser().parse_args(["resources", "download", "5", "--output", str(output)])
            with patch("sulaide_cli.cli.Client", return_value=FakeClient()), \
                 patch("sulaide_cli.cli.httpx.Client", return_value=FakeAnon()):
                result = run(args)
                with self.assertRaises(FileExistsError):
                    run(args)
            self.assertEqual(result["path"], str(output.resolve()))
            self.assertEqual(result["size_bytes"], len(b"resource-bytes"))
            self.assertEqual(result["resource_version_id"], 5)
            self.assertEqual(output.read_bytes(), b"resource-bytes")
            self.assertEqual(downloaded["url"], "https://files.example.com/signed")
            self.assertTrue(downloaded["anonymous"])

    def test_resources_download_rejects_empty_payload(self):
        class FakeResponse:
            is_error = False
            content = b""
            headers = {"content-type": "application/pdf"}

        class FakeHttp:
            def get(self, url, **kwargs):
                return FakeResponse()

        class FakeClient:
            http = FakeHttp()

            def request(self, method, path, **kwargs):
                return {"redirect_url": "/files/empty", "filename": "draft.pdf"}

        with TemporaryDirectory() as directory:
            output = Path(directory) / "draft.pdf"
            args = build_parser().parse_args(["resources", "download", "6", "--output", str(output)])
            with patch("sulaide_cli.cli.Client", return_value=FakeClient()):
                with self.assertRaises(ValueError):
                    run(args)
            self.assertFalse(output.exists())
            self.assertFalse(Path(str(output) + ".part").exists())



if __name__ == "__main__":
    unittest.main()
