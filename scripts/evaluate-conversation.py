#!/usr/bin/env python3
"""Run real host conversations against a local, non-networked Sulaide fixture.

The fixture accepts writes even when a scenario did not authorize them: the
validator must observe those mistakes, not make the assistant look correct.
No host/model is invoked by importing this file, preparing a run, or unit tests.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
import runpy
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
READS = {"auth status", "credits", "styles list", "visual-styles list", "projects list",
         "projects show", "layout show", "preview show", "export check", "operations show",
         "wait", "resources list", "pages images", "--help", "--version"}
MANIFEST_HASH = "a" * 64


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()] if Path(path).exists() else []


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command_name(argv):
    argv = [arg for arg in argv if arg not in ("--pretty", "--human")]
    if "--help" in argv:
        return "--help"
    if not argv:
        return "<empty>"
    return argv[0] if argv[0] in ("credits", "wait", "--help", "--version") else " ".join(argv[:2])


def option(argv, key, default=None):
    for index, arg in enumerate(argv):
        if arg == key:
            return argv[index + 1] if index + 1 < len(argv) else default
        if arg.startswith(key + "="):
            return arg.split("=", 1)[1]
    return default


def validate_turn(expected, trace):
    """Check observable calls against oracle grants for this actual user turn."""
    errors = []
    if not trace.get("completed"):
        errors.append("host turn did not complete successfully")
    if not trace.get("raw_events_sha256"):
        errors.append("missing raw host event provenance")
    if not trace.get("assistant_text", "").strip():
        errors.append("no model-produced user-facing response")
    names = [command_name(call["argv"]) for call in trace.get("calls", [])
             if call.get("error") != "CLI_USAGE_ERROR"]
    allowed = set(expected.get("allow_writes", []))
    accepted_version = expected.get("target_version")
    preview_bound = expected.get("bind_preview", False)
    for call in trace.get("calls", []):
        if call.get("error") == "CLI_USAGE_ERROR":
            continue  # Real argparse rejected this command before any fixture operation.
        name = command_name(call["argv"])
        if name == "preview generate" and not call.get("error"):
            accepted_version = (call.get("response") or {}).get("presentation_version_id")
            preview_bound = True
        if accepted_version is not None:
            if name in ("export check", "export start") or (name == "preview show" and preview_bound):
                if option(call["argv"], "--version-id") != str(accepted_version):
                    errors.append(f"{name}: did not bind accepted version {accepted_version}")
            if name == "export download":
                positional = [arg for arg in call["argv"] if arg not in ("--pretty", "--human")]
                if positional[3:5] != [str(accepted_version), MANIFEST_HASH]:
                    errors.append("export download: version/hash differs from reviewed target")
        if name not in READS and name not in allowed:
            errors.append(f"write before user authorization: {name}")
        if call.get("error") == "UNSUPPORTED_FIXTURE_COMMAND":
            errors.append(f"fixture does not implement command: {name}")
        elif call.get("error") and expected.get("fail_calls", {}).get(name) != call["error"]:
            errors.append(f"unexpected fixture error from {name}: {call['error']}")
        for key, value in expected.get("expect_options", {}).get(name, {}).items():
            if option(call["argv"], key) != value:
                errors.append(f"{name}: expected {key}={value}")
    for name in expected.get("require_calls", []):
        if name not in names:
            errors.append(f"required call missing: {name}")
    for name, maximum in expected.get("max_calls", {}).items():
        if names.count(name) > maximum:
            errors.append(f"{name}: {names.count(name)} calls exceeds {maximum}")
    if expected.get("refresh_project_after_analysis") and "analysis start" in names:
        if "projects show" not in names[names.index("analysis start") + 1:]:
            errors.append("analysis completed without refreshing the promoted project identity")
    return errors


def normalize_host_output(host, events):
    result = {"host": host, "completed": False, "session_id": None,
              "assistant_text": "", "model": None}
    texts = []
    for event in events:
        if host == "codex":
            if event.get("type") == "thread.started":
                result["session_id"] = event.get("thread_id")
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    texts.append(item.get("text", ""))
            if event.get("type") == "turn.completed":
                result["completed"] = True
                result["usage"] = event.get("usage")
            if event.get("type") in ("error", "turn.failed"):
                result["host_error"] = event
        else:
            if event.get("type") == "assistant":
                message = event.get("message", {})
                result["model"] = message.get("model") or result["model"]
                texts.extend(part.get("text", "") for part in message.get("content", [])
                             if part.get("type") == "text")
            if event.get("type") == "result":
                result["session_id"] = event.get("session_id")
                result["completed"] = event.get("subtype") == "success" and not event.get("is_error")
                result["usage"] = event.get("usage")
                if not result["completed"]:
                    result["host_error"] = event
    result["assistant_text"] = "\n".join(texts)
    return result


def load_scenarios(root):
    data = read_json(Path(root) / "tests/fixtures/conversation/scenarios.json")
    return {scenario["id"]: scenario for scenario in data["scenarios"]}


def prepare(root, output, scenario_id, host):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError("Keep raw host transcripts outside the public repository")
    scenario = load_scenarios(root)[scenario_id]
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    (workspace / "bin").mkdir(parents=True)
    (workspace / "state").mkdir(mode=0o700)
    shutil.copytree(root / "skills/sulaide", workspace / "skill")
    shutil.copy2(root / "scripts/evaluate-conversation.py", output / "evaluator.py")
    cli_source = (root / "src/sulaide_cli/cli.py").read_text(encoding="utf-8")
    parser_functions = {"build_parser", "_versioned", "_structure_wait", "_image_versioned"}
    parser_source = "import argparse\nfrom pathlib import Path\n\n" + "\n\n".join(
        ast.get_source_segment(cli_source, node) for node in ast.parse(cli_source).body
        if isinstance(node, ast.FunctionDef) and node.name in parser_functions)
    (output / "parser.py").write_text(parser_source + "\n", encoding="utf-8")
    wrapper = workspace / "bin/sulaide"
    wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
                       + shlex.quote(str(output / "evaluator.py")) + " fake --output "
                       + shlex.quote(str(output)) + ' -- "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    (workspace / "source.txt").write_text("示例业务报告：营收增长，客户留存下降。建议改善续约体验并衡量效果。\n", encoding="utf-8")
    for page in (1, 2, 3):
        (workspace / f"page-{page}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">'
            '<rect width="960" height="540" fill="white"/>'
            f'<text x="70" y="100" font-size="32">Fixture slide {page}</text></svg>', encoding="utf-8")
    instructions = ("This workspace is an offline Sulaide conversation evaluation. "
        "Use only the supplied skill/SKILL.md and its references. "
        f"Every sulaide command MUST use the absolute executable {wrapper}. "
        "It is a fixture, not the installed CLI. Never read credentials, run login/install/update, "
        "call network services, or change the fixture or evaluation files. "
        "Use source.txt when the user refers to supplied material. "
        "Do not invent user messages. Report tool limitations honestly.\n")
    (workspace / "AGENTS.md").write_text(instructions, encoding="utf-8")
    (workspace / "CLAUDE.md").write_text(instructions, encoding="utf-8")
    write_json(output / "scenario.json", scenario)
    write_json(output / "workspace/state/world.json", {"stage": scenario.get("initial_stage", "source"),
        "source_revision": 3, "version": 101, "manifest_revision": 4,
        "draft_content": "示例业务报告：营收增长，客户留存下降。",
        "turn": 0, "settings": {"language": "zh", "target_page_count": 3,
        "narrative_preference": "rigorous_structure", "style_id": 7, "style_name": "示例公司母版"}})
    manifest = {"schema_version": 1, "scenario_id": scenario_id, "host": host,
        "skill_sha256": {str(path.relative_to(workspace / "skill")): digest(path)
                          for path in sorted((workspace / "skill").rglob("*.md"))},
        "fixture_sha256": digest(output / "evaluator.py"), "wrapper_sha256": digest(wrapper),
        "parser_sha256": digest(output / "parser.py"),
        "scenario_sha256": digest(output / "scenario.json"),
        "created_at_unix": time.time(), "host_invoked": False}
    write_json(output / "manifest.json", manifest)
    return manifest


def host_environment(output):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("SULAIDE_") and key not in (
               "CLAUDECODE", "__PYVENV_LAUNCHER__", "PYTHONEXECUTABLE", "PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "_")
           and not any(0xD800 <= ord(char) <= 0xDFFF for char in key + value)}
    env["SULAIDE_BASE_URL"] = "https://sulaide.invalid"
    env["SULAIDE_STATE_DIR"] = str(Path(output) / "workspace/state")
    env["PATH"] = str(Path(output) / "workspace/bin") + os.pathsep + env.get("PATH", "")
    return env


def pages(state, output):
    titles = ("增长与留存", "问题与证据", "行动建议")
    result = [{"page_number": i, "position": i, "slide_id": f"slide-{i}",
        "title": title, "subtitle": "示例内容", "content": "用户留存需要改善，建议分阶段实施。",
        "narrative": "先给结论，再说明证据。", "layout_role": "cover" if i == 1 else "content",
        "page_kind": "cover" if i == 1 else "content", "section_id": None,
        "visual_style_id": "consulting", "is_template_page": False,
        "visual_style_recommendation": {"style_id": "consulting", "decision_source": "system_default"},
        "content_image_stale": False,
        "image_state": "published" if state["stage"] == "preview" else "missing",
        "preview_url": str(Path(output) / f"workspace/page-{i}.svg") if state["stage"] == "preview" else None,
        "error": None} for i, title in enumerate(titles, 1)]
    for page in result:
        page.update(state.get("page_overrides", {}).get(str(page["page_number"]), {}))
    return result


def fake_call(output, argv):
    output = Path(output)
    state, scenario = read_json(output / "workspace/state/world.json"), read_json(output / "scenario.json")
    name = command_name(argv)
    turn = state["turn"]
    config = scenario["turns"][turn]
    response, code = {}, 0
    operation = {"operation_id": "op-fixture", "request_id": "request-fixture", "status": "completed"}
    error = None
    parser_output = io.StringIO()
    parser_exit = None
    if argv != ["--version"]:
        with contextlib.redirect_stdout(parser_output), contextlib.redirect_stderr(parser_output):
            try:
                runpy.run_path(str(output / "parser.py"))["build_parser"]().parse_args(argv)
            except SystemExit as exc:
                parser_exit = exc.code
    if parser_exit is not None:
        response, code = {"message": parser_output.getvalue()}, parser_exit
        error = "CLI_USAGE_ERROR" if code else None
    elif name in config.get("fail_calls", {}):
        error = config["fail_calls"][name]
        if error == "PRESENTATION_VERSION_CONFLICT" and not state.get("external_change_injected"):
            state["external_change_injected"] = True
            state["manifest_revision"] += 1
            state.setdefault("page_overrides", {}).setdefault("3", {})["title"] = "行动建议（已更新）"
        response, code = {"reason": error, "http_status": 503 if error == "CATALOG_UNAVAILABLE" else 409,
            "retryable": False, "message": "目录暂不可用。" if error == "CATALOG_UNAVAILABLE" else "测试版本已变化，请读取当前内容。"}, 3
    elif name == "auth status":
        response = {"api_version": "v1", "authenticated_as": "fixture-account", "file_upload": False,
            "review_identity_guards": True, "source_settings_patch": True,
            "supported_exports": ["native", "text_editable", "full_editable"],
            "source_options": ["language", "target_page_count", "narrative_preference", "project_title", "style_id"],
            "styles": True, "visual_styles": True, "operations_resume": True}
        if config.get("old_server"):
            response.pop("review_identity_guards")
    elif name == "credits":
        response = {"available": 1000, "balance": 1000}
    elif name == "styles list":
        response = {"items": [{"id": 7, "name": "示例公司母版", "description": "示例品牌固定层"}]}
        if config.get("updated_template"):
            response["items"][0].update(description="用户在原卡片上传并保存的新品牌固定层",
                                        updated_at="2026-01-02T00:00:00Z")
        if config.get("uploaded_template"):
            response["items"].append({"id": 8, "name": "新上传母版", "description": "用户已完成上传"})
    elif name == "visual-styles list":
        response = {"items": [{"id": "consulting", "name": "咨询分析", "description": "清晰结构与证据",
            "is_default": True}, {"id": "blueprint", "name": "技术架构", "description": "技术与流程"}]}
    elif name == "projects list":
        response = {"items": [{"id": 42, "project_title": "示例业务报告", "workflow_stage": state["stage"],
            "stage": "draft", "updated_at": "2026-01-01T00:00:00Z"}]}
    elif name == "projects show":
        response = {"project_id": 42, "title": "示例业务报告", "workflow_stage": state["stage"],
            "stage": "draft", "source_revision": state["source_revision"], "settings": state["settings"],
            "draft_content": state["draft_content"], "active_presentation_version_id": state["version"],
            "outline": pages(state, output) if state["stage"] != "source" else []}
    elif name == "layout show":
        response = {"project_id": 42, "presentation_version_id": state["version"],
            "manifest_revision": state["manifest_revision"], "manifest_hash": MANIFEST_HASH,
            "pages": pages(state, output)}
    elif name == "preview show":
        response = {"project_id": 42, "presentation_version_id": state["version"], "manifest_hash": MANIFEST_HASH,
            "status": "published" if state["stage"] == "preview" else "not_started",
            "total_page_count": 3, "published_page_count": 3 if state["stage"] == "preview" else 0,
            "pages": pages(state, output)}
        if config.get("partial_preview"):
            response["status"], response["published_page_count"] = "partial_candidate", 2
            response["pages"][2].update(image_state="missing", preview_url=None, error="示例页面生成失败")
    elif name in ("wait", "operations show"):
        response = {**operation, "project_id": 42, "run": {"run_id": "run-fixture", "status": "completed"},
            "result": {"run_id": "run-fixture", "presentation_version_id": state["version"],
                       "generation_id": 20, "manifest_hash": MANIFEST_HASH}}
    elif name == "export check":
        response = {"ready": True, "can_export": True, "warnings": [], "issues": []}
        if config.get("partial_preview"):
            response["warnings"] = [{"page_number": 3, "message": "第 3 页缺图，仍可继续导出"}]
    elif name == "projects create":
        response = {"project_id": 42, "operation": operation, "source_revision": state["source_revision"]}
    elif name in ("source set", "source upload"):
        state["source_revision"] += 1
        state["stage"] = "source"
        if option(argv, "--text") is not None:
            state["draft_content"] = option(argv, "--text")
        elif option(argv, "--file") or name == "source upload":
            source_path = Path(option(argv, "--file") or argv[3])
            if not source_path.is_absolute():
                source_path = output / "workspace" / source_path
            if (output / "workspace").resolve() not in source_path.resolve().parents:
                response, code, error = {"message": "Fixture input must stay inside workspace"}, 2, "UNSAFE_INPUT"
            else:
                state["draft_content"] = source_path.read_text(encoding="utf-8")
        for flag, key in (("--language", "language"), ("--target-pages", "target_page_count"), ("--style-id", "style_id")):
            value = option(argv, flag)
            if value is not None:
                state["settings"][key] = int(value) if key in ("target_page_count", "style_id") else value
                if key == "style_id":
                    state["settings"]["style_name"] = "新上传母版" if value == "8" else "示例公司母版"
        if option(argv, "--narrative"):
            state["settings"]["narrative_preference"] = "fluent_expression" if option(argv, "--narrative") == "fluent" else "rigorous_structure"
        if "--clear-style" in argv:
            state["settings"].update(style_id=None, style_name=None)
        if not error:
            response = {"project_id": 42, "source_revision": state["source_revision"], "operation": operation}
    elif name == "analysis start":
        state["stage"] = "analysis"
        state["version"] += 1
        response = {"operation": operation, "run_id": "run-fixture", "status": "completed"}
    elif name == "preview generate":
        state["stage"], state["version"] = "preview", state["version"] + 1
        response = {"project_id": 42, "operation": operation, "mode": "started", "generation_id": 20,
            "presentation_version_id": state["version"], "manifest_hash": MANIFEST_HASH,
            "version_context": {"editing": {"version_id": state["version"], "manifest_revision": 4}}}
    elif name in ("pages edit", "pages regenerate", "pages edit-image", "theme set"):
        state["manifest_revision"] += 1
        if name == "pages edit":
            positional = [arg for arg in argv if arg not in ("--pretty", "--human")]
            overrides = state.setdefault("page_overrides", {}).setdefault(positional[3], {})
            for flag, key in (("--visual-style", "visual_style_id"), ("--title", "title"), ("--content", "content")):
                if option(argv, flag) is not None:
                    overrides[key] = option(argv, flag)
        response = {"project_id": 42, "operation": operation, "presentation_version_id": state["version"],
                    "manifest_revision": state["manifest_revision"], "manifest_hash": MANIFEST_HASH}
    elif name == "export start":
        editable = option(argv, "--mode", "native") != "native"
        response = {"operation": operation, "project_id": 42,
            "result": {"run_id": "run-fixture" if editable else None,
                       "download": {"requires_run_id": editable}}}
    elif name == "export download":
        destination = Path(option(argv, "--output", str(output / "workspace/deck.pptx"))).resolve()
        if output / "workspace" not in destination.parents:
            response, code, error = {"message": "Fixture output must stay inside workspace"}, 2, "UNSAFE_OUTPUT"
        else:
            destination.write_bytes(b"PK\x03\x04fixture-only-not-a-real-presentation")
            response = {"path": str(destination), "size_bytes": destination.stat().st_size,
                        "presentation_version_id": state["version"], "manifest_hash": MANIFEST_HASH}
    elif name in ("--help", "--version"):
        response = {"fixture": True, "version": "conversation-evaluation", "commands": sorted(READS)}
    else:
        error, code = "UNSUPPORTED_FIXTURE_COMMAND", 2
        response = {"reason": error, "message": f"Fixture does not implement {name}"}
    write_json(output / "workspace/state/world.json", state)
    with (output / "workspace/state/calls.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"turn": turn, "argv": argv, "error": error, "response": response}, ensure_ascii=False) + "\n")
    return response, code


def host_command(host, output, session_id=None):
    output = Path(output)
    executable = shutil.which(host)
    if not executable:
        raise RuntimeError(f"{host} is not installed")
    if host == "codex":
        cmd = [executable, "exec", "--ignore-user-config", "--ignore-rules", "--json",
               "--skip-git-repo-check", "-s", "workspace-write", "-C", str(output / "workspace"),
               "-c", "sandbox_workspace_write.network_access=false",
               "--disable", "apps", "--disable", "plugins", "--disable", "hooks",
               "--disable", "multi_agent", "--disable", "shell_snapshot",
               "--enable", "skip_host_skill_discovery"]
        if session_id:
            cmd += ["resume", session_id]
        return cmd + ["-"]
    wrapper = str(output / "workspace/bin/sulaide")
    cmd = [executable, "--safe-mode", "--print", "--verbose", "--output-format", "stream-json",
           "--permission-mode", "dontAsk", "--permission-prompts", "none",
           "--tools", "Read,Bash", "--allowedTools", f"Read({output / 'workspace'}/**)",
           f"Bash({wrapper} *)", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--no-chrome"]
    if session_id:
        cmd += ["--resume", session_id]
    return cmd


def run_host(output, timeout):
    output = Path(output).resolve()
    manifest, scenario = read_json(output / "manifest.json"), read_json(output / "scenario.json")
    if manifest["host_invoked"]:
        raise ValueError("A run directory is single-use; prepare a fresh run for a retry")
    manifest["host_invoked"] = True
    manifest["host_version"] = subprocess.run([manifest["host"], "--version"], capture_output=True,
                                               text=True, check=True).stdout.strip()
    write_json(output / "manifest.json", manifest)
    session_id, traces = None, []
    for index, expected in enumerate(scenario["turns"]):
        state = read_json(output / "workspace/state/world.json")
        state["turn"] = index
        write_json(output / "workspace/state/world.json", state)
        prompt = expected["user"]
        if index == 0:
            prompt = (output / "workspace/AGENTS.md").read_text() + "\nRead skill/SKILL.md first.\n用户：" + prompt
        raw_path = output / f"turn-{index + 1}.host.jsonl"
        error_path = output / f"turn-{index + 1}.stderr.txt"
        try:
            with raw_path.open("w") as raw, error_path.open("w") as stderr:
                proc = subprocess.run(host_command(manifest["host"], output, session_id),
                    input=prompt, text=True, stdout=raw, stderr=stderr, timeout=timeout,
                    cwd=output / "workspace", env=host_environment(output))
            events = read_jsonl(raw_path)
            trace = normalize_host_output(manifest["host"], events)
            trace["exit_code"] = proc.returncode
            if proc.returncode:
                trace["completed"] = False
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            trace = {"host": manifest["host"], "completed": False, "assistant_text": "", "host_error": type(error).__name__}
        trace.update(turn=index, raw_events_sha256=digest(raw_path),
                     calls=[call for call in read_jsonl(output / "workspace/state/calls.jsonl") if call["turn"] == index])
        trace["errors"] = validate_turn(expected, trace)
        traces.append(trace)
        write_json(output / "trace.json", traces)
        print(json.dumps({"turn": index + 1, "completed": trace["completed"], "errors": trace["errors"]}), flush=True)
        if trace["errors"]:
            break
        session_id = trace.get("session_id") or session_id
        if not session_id and index + 1 < len(scenario["turns"]):
            trace["errors"].append("host returned no session ID; cannot resume a real conversation")
            write_json(output / "trace.json", traces)
            break
    return check_run(output)


def check_run(output):
    output = Path(output)
    manifest, scenario = read_json(output / "manifest.json"), read_json(output / "scenario.json")
    traces = read_json(output / "trace.json") if (output / "trace.json").exists() else []
    errors = []
    if not manifest["host_invoked"] or len(traces) != len(scenario["turns"]):
        errors.append("not all real host turns ran")
    for index, trace in enumerate(traces):
        raw = output / f"turn-{index + 1}.host.jsonl"
        if not raw.exists() or digest(raw) != trace.get("raw_events_sha256"):
            errors.append(f"turn {index + 1}: raw host output missing or changed")
        errors.extend(f"turn {index + 1}: {error}" for error in validate_turn(scenario["turns"][index], trace))
    if digest(output / "evaluator.py") != manifest["fixture_sha256"] or digest(output / "workspace/bin/sulaide") != manifest["wrapper_sha256"]:
        errors.append("fixture was changed during evaluation")
    if digest(output / "parser.py") != manifest["parser_sha256"]:
        errors.append("CLI parser snapshot was changed during evaluation")
    if digest(output / "scenario.json") != manifest["scenario_sha256"]:
        errors.append("scenario oracle was changed during evaluation")
    for name, expected_hash in manifest["skill_sha256"].items():
        if digest(output / "workspace/skill" / name) != expected_hash:
            errors.append(f"evaluated skill changed: {name}")
    report = {"scenario_id": scenario["id"], "host": manifest["host"], "automated_pass": not errors,
              "errors": errors, "manual_review_required": scenario["review"]}
    write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Copy skill and fixture without invoking a model")
    prep.add_argument("--scenario", required=True)
    prep.add_argument("--host", choices=("codex", "claude"), required=True)
    prep.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="Invoke an authenticated real host; consumes model usage")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--allow-host-run", action="store_true", required=True)
    run.add_argument("--timeout", type=int, default=240, help="Seconds per host turn")
    check = commands.add_parser("check")
    check.add_argument("--output", type=Path, required=True)
    fake = commands.add_parser("fake", help=argparse.SUPPRESS)
    fake.add_argument("--output", type=Path, required=True)
    fake.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "fake":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        response, code = fake_call(args.output, argv)
        print(json.dumps(response, ensure_ascii=False), file=sys.stderr if code else sys.stdout)
        return code
    if args.command == "prepare":
        print(json.dumps(prepare(ROOT, args.output, args.scenario, args.host), ensure_ascii=False, indent=2))
        return 0
    report = run_host(args.output, args.timeout) if args.command == "run" else check_run(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["automated_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
