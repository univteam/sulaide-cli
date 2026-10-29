"""Checks the evaluator, not the quality of a fabricated agent transcript."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("conversation_eval", ROOT / "scripts/evaluate-conversation.py")
evaluator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluator)


class ConversationTraceTests(unittest.TestCase):
    def turn(self, allow=(), required=(), maximum=None):
        return {"user": "请继续", "allow_writes": list(allow), "require_calls": list(required),
                "max_calls": maximum or {}}

    def trace(self, calls, text="请确认设置", **extra):
        return {"host": "codex", "raw_events_sha256": "test-only-hash", "completed": True,
                "assistant_text": text, "calls": calls, **extra}

    def call(self, *args, error=None):
        return {"argv": list(args), "error": error}

    def test_analysis_before_settings_reply_fails(self):
        errors = evaluator.validate_turn(self.turn(), self.trace([
            self.call("auth", "status"), self.call("analysis", "start", "42")]))
        self.assertTrue(any("analysis start" in error for error in errors))

    def test_outline_reply_authorizes_generation_but_not_export(self):
        turn = self.turn(["preview generate"], ["preview generate"])
        self.assertEqual(evaluator.validate_turn(turn, self.trace([
            self.call("preview", "generate", "42")])), [])
        self.assertTrue(evaluator.validate_turn(turn, self.trace([
            self.call("preview", "generate", "42"),
            self.call("export", "start", "42", "--mode", "native")])))

    def test_success_text_without_required_tool_call_fails(self):
        self.assertTrue(evaluator.validate_turn(self.turn(required=["export start"]),
                                              self.trace([], text="已经导出成功")))

    def test_trace_requires_actual_completed_host_output(self):
        for change in ({"raw_events_sha256": ""}, {"completed": False}, {"assistant_text": ""}):
            self.assertTrue(evaluator.validate_turn(self.turn(), self.trace([], **change)))

    def test_conflict_cannot_be_retried_as_a_new_write_in_same_turn(self):
        turn = self.turn(["preview generate"], maximum={"preview generate": 1})
        turn["fail_calls"] = {"preview generate": "PRESENTATION_VERSION_CONFLICT"}
        calls = [self.call("preview", "generate", "42", error="PRESENTATION_VERSION_CONFLICT"),
                 self.call("preview", "generate", "42")]
        self.assertTrue(evaluator.validate_turn(turn, self.trace(calls)))

    def test_unspecified_mutation_is_rejected_including_unknown_verbs(self):
        for argv in (("theme", "set", "42"), ("topup", "--package", "1"),
                     ("future", "write", "42")):
            self.assertTrue(evaluator.validate_turn(self.turn(), self.trace([self.call(*argv)])))

    def test_native_export_rejects_conversion_mode_or_page_range(self):
        turn = self.turn(["export start"], ["export start"])
        turn["expect_options"] = {"export start": {"--mode": "native", "--page-numbers": None}}
        valid = self.call("export", "start", "42", "--mode", "native")
        self.assertEqual(evaluator.validate_turn(turn, self.trace([valid])), [])
        for arguments in (("--mode", "text_editable"), ("--mode", "full_editable"),
                          ("--mode", "native", "--page-numbers", "2,3")):
            invalid = self.call("export", "start", "42", *arguments)
            self.assertTrue(evaluator.validate_turn(turn, self.trace([invalid])))

    def test_generation_receipt_binds_following_preview_and_export(self):
        turn = self.turn(["preview generate", "export start"])
        generation = self.call("preview", "generate", "42")
        generation["response"] = {"presentation_version_id": 102}
        calls = [generation, self.call("preview", "show", "42", "--version-id", "101")]
        self.assertTrue(evaluator.validate_turn(turn, self.trace(calls)))
        calls[1] = self.call("preview", "show", "42", "--version-id", "102")
        self.assertEqual(evaluator.validate_turn(turn, self.trace(calls)), [])
        turn["target_version"] = 102
        self.assertTrue(evaluator.validate_turn(turn, self.trace([
            self.call("export", "start", "42", "--version-id", "101")])) )

    def test_analysis_requires_refreshing_promoted_project_identity(self):
        turn = self.turn(["analysis start"])
        turn["refresh_project_after_analysis"] = True
        calls = [self.call("projects", "show", "42"), self.call("analysis", "start", "42"),
                 self.call("layout", "show", "42")]
        self.assertTrue(evaluator.validate_turn(turn, self.trace(calls)))
        calls.append(self.call("projects", "show", "42"))
        self.assertEqual(evaluator.validate_turn(turn, self.trace(calls)), [])

    def test_native_host_adapters_retain_model_text_and_completion(self):
        codex = [{"type": "thread.started", "thread_id": "session-a"},
                 {"type": "item.completed", "item": {"type": "agent_message", "text": "请确认"}},
                 {"type": "turn.completed", "usage": {"input_tokens": 3}}]
        claude = [{"type": "assistant", "message": {"model": "host-default", "content": [
            {"type": "text", "text": "请选择母版"}]}},
            {"type": "result", "subtype": "success", "session_id": "session-b", "is_error": False}]
        for host, events, session in (("codex", codex, "session-a"), ("claude", claude, "session-b")):
            result = evaluator.normalize_host_output(host, events)
            self.assertTrue(result["completed"])
            self.assertEqual(result["session_id"], session)
            self.assertTrue(result["assistant_text"])

    def test_prepare_copies_skill_and_isolates_sulaide_state(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            manifest = evaluator.prepare(ROOT, output, "settings_missing", "codex")
            self.assertEqual(manifest["scenario_id"], "settings_missing")
            self.assertTrue((output / "workspace/skill/SKILL.md").is_file())
            self.assertTrue((output / "workspace/bin/sulaide").is_file())
            env = evaluator.host_environment(output)
            self.assertEqual(env["SULAIDE_BASE_URL"], "https://sulaide.invalid")
            self.assertNotIn("SULAIDE_API_KEY", env)
            self.assertEqual(Path(env["SULAIDE_STATE_DIR"]), output / "workspace/state")

    def test_fake_backend_records_disallowed_command_instead_of_hiding_it(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            evaluator.prepare(ROOT, output, "settings_missing", "codex")
            result, exit_code = evaluator.fake_call(output, ["analysis", "start", "42"])
            self.assertEqual(exit_code, 0)
            self.assertIn("operation", result)
            calls = evaluator.read_jsonl(output / "workspace/state/calls.jsonl")
            self.assertEqual(calls[0]["argv"], ["analysis", "start", "42"])
            self.assertTrue(evaluator.validate_turn(self.turn(), self.trace(calls)))

    def test_real_parser_rejects_invalid_command_without_satisfying_required_call(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            evaluator.prepare(ROOT, output, "settings_missing", "codex")
            before = evaluator.read_json(output / "workspace/state/world.json")
            response, code = evaluator.fake_call(output, ["projects", "get", "42"])
            self.assertEqual(code, 2)
            self.assertIn("invalid choice", response["message"])
            self.assertEqual(before, evaluator.read_json(output / "workspace/state/world.json"))
            calls = evaluator.read_jsonl(output / "workspace/state/calls.jsonl")
            self.assertEqual(evaluator.validate_turn(self.turn(), self.trace(calls)), [])
            self.assertTrue(evaluator.validate_turn(self.turn(required=["projects show"]), self.trace(calls)))
            response, code = evaluator.fake_call(output, ["preview", "generate", "--help"])
            self.assertEqual(code, 0)
            self.assertIn("--expected-source-revision", response["message"])

    def test_saved_source_reads_back_its_content_and_preserved_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            evaluator.prepare(ROOT, output, "settings_missing", "codex")
            evaluator.fake_call(output, ["source", "set", "42", "--file", "source.txt"])
            project, code = evaluator.fake_call(output, ["projects", "show", "42"])
            self.assertEqual(code, 0)
            self.assertIn("改善续约体验", project["draft_content"])
            self.assertEqual(project["settings"]["style_id"], 7)
            evaluator.fake_call(output, ["analysis", "start", "42"])
            project, _ = evaluator.fake_call(output, ["projects", "show", "42"])
            self.assertEqual(project["active_presentation_version_id"], 102)
            generated, _ = evaluator.fake_call(output, ["preview", "generate", "42"])
            self.assertEqual(generated["presentation_version_id"], 103)

    def test_conflict_fixture_exposes_the_external_revision_on_reread(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            evaluator.prepare(ROOT, output, "stale_outline", "codex")
            state = evaluator.read_json(output / "workspace/state/world.json")
            state["turn"] = 1
            evaluator.write_json(output / "workspace/state/world.json", state)
            _, code = evaluator.fake_call(output, ["preview", "generate", "42"])
            self.assertEqual(code, 3)
            layout, _ = evaluator.fake_call(output, ["layout", "show", "42"])
            self.assertEqual(layout["manifest_revision"], 5)
            self.assertEqual(layout["pages"][2]["title"], "行动建议（已更新）")

    def test_scenarios_cover_acceptance_examples_and_real_waits(self):
        scenarios = evaluator.load_scenarios(ROOT)
        covered = {item for scenario in scenarios.values() for item in scenario["covers"]}
        self.assertTrue(set(f"AE{i}" for i in range(1, 9)) <= covered)
        self.assertGreaterEqual(len(scenarios["staged_deck"]["turns"]), 4)
        self.assertFalse(scenarios["staged_deck"]["turns"][0]["allow_writes"])


if __name__ == "__main__":
    unittest.main()
