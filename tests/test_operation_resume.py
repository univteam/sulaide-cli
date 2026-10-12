import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sulaide_cli.cli import _read_state, _request_id, _remember_operation, _write_state


class OperationResumeTests(unittest.TestCase):
    def test_request_and_operation_ids_persist_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SULAIDE_STATE_DIR": directory}, clear=False):
            request_id = _request_id("analysis:42", "handoff-1")
            _remember_operation("analysis:42", request_id, "operation-abc")
            state = _read_state()
            self.assertEqual(state["analysis:42:handoff-1"], request_id)
            self.assertEqual(state["operation:analysis:42:handoff-1"], "operation-abc")
            payload = Path(directory, "operations.json").read_text()
            self.assertNotIn("sul_", payload)
            self.assertEqual(Path(directory, "operations.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
