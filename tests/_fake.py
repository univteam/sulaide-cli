import os
import tempfile
import unittest
from unittest.mock import patch

from sulaide_cli.cli import build_parser, run


class FakeClientCase(unittest.TestCase):
    """Runs CLI commands against a recording fake Agent API client."""

    responses: dict = {}

    def setUp(self):
        self.calls = []
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"SULAIDE_STATE_DIR": self.tmp.name})
        self.env.start()
        test = self

        class FakeClient:
            def request(self, method, path, **kwargs):
                test.calls.append((method, path, kwargs))
                handler = test.responses.get((method, path))
                if callable(handler):
                    return handler(kwargs)
                if handler is not None:
                    return handler
                if (method, path) == ("GET", "/capabilities"):
                    return {"analysis_page_count": {"available": True, "count_basis": "content", "min": 1, "max": 50}}
                return {}
        self.client = patch("sulaide_cli.cli.Client", return_value=FakeClient())
        self.client.start()

    def tearDown(self):
        self.client.stop(); self.env.stop(); self.tmp.cleanup()

    def cli(self, *argv):
        return run(build_parser().parse_args(list(argv)))

    def body(self, index=-1):
        return self.calls[index][2].get("json_body")
