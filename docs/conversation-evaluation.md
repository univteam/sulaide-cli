# Conversation evaluation

This evaluates a real Codex or Claude conversation using the repository skill and an offline Sulaide fixture. The fixture returns project data; the host model decides which questions and commands to produce. No prewritten assistant dialogue is used as evidence.

The evaluator checks **observable tool ordering and arguments**, not whether a document contains the word “confirm”. Each user turn has explicit allowed writes and required calls. An unauthorized write still runs against the fake backend and is logged, so the validator can fail the actual behavior. Missing calls also fail: merely saying “done” cannot pass. Scenario assertions cover generation source/editing/manifest/active guards, page-edit guards, and the accepted generation version used by preview/export.

## Scope

The twelve fixtures cover AE1–AE8: grouped settings, reuse of explicit choices, outline and visual style review, website template-upload handoff, ordinary PPT export and deferred editable requests, stale review rejection, partial preview, and explicit full automation. `staged_deck` supplies four separate user turns to one resumed host conversation. `template_update_same_id` covers replacing an existing master without getting a new catalog ID. `editable_deferred` checks that even a full-auto editable request cannot trigger conversion or an unapproved native substitute; native export follows only after the next user turn accepts it. The backend fixture still advertises editable modes to test this skill boundary. `catalog_failure` checks that missing options do not become invented defaults. `old_server_guard` verifies that a server without review protection does not receive a generation write.

Analysis promotes the fixture's initial version 101 to 102; generation then accepts version 103. This deliberate identity change checks that the model refreshes the project after analysis, sends the reviewed active/editing identity, and follows the generation receipt instead of reusing the earlier version.

CLI/API correctness, database concurrency, PPTX validity, image quality, and real upload parsing remain separate tests. The three fixture pages and downloaded file are intentionally fake. Successful evaluation must never be described as a real presentation generation or export.

## Isolation

- Prepare copies the current skill into a fresh directory outside this public repository, hashes its files, and creates an absolute `bin/sulaide` shim. The shim has no HTTP client or network operations.
- The real CLI's argument-parser functions are frozen separately, without its network/client code. Invalid commands return their real parser error before any fixture action; corrected calls are still required. Help output comes from the same snapshot.
- The model is instructed to use only that executable. `SULAIDE_API_KEY` is removed from the child environment, `SULAIDE_STATE_DIR` points to empty scratch state, and the base URL is the reserved non-service address `https://sulaide.invalid`. The evaluator never reads Sulaide credentials.
- Codex uses `workspace-write` with sandbox network disabled, ignores user config and exec rules, and disables apps, plugins, hooks, delegation, shell snapshots and global skill discovery. It retains its normal host authentication for inference. Claude uses safe mode to disable customizations while retaining authentication, and gets only Read and Bash tools, an allowlist for scratch reads and the exact shim, `dontAsk` permissions, no external MCP configuration, and no Chrome integration. Neither host is launched with permission or sandbox bypass flags.
- Host inference uses the operator's existing authenticated account and consumes model usage. `prepare`, `check`, and unit tests never invoke a model. `run` requires the explicit `--allow-host-run` switch.
- The fixture and skill hashes are checked after the conversation. Raw events and stderr can contain local paths; keep them in scratch and do not commit or publish them without review. Do not point the harness at real projects or add credentials to fixtures.

These controls are an evaluation boundary, not a hostile-code security boundary. Stop if the host attempts to use any executable other than the supplied shim for product operations. A host/tool permission failure is a blocked run, not a pass. Normal host authentication must already work; do not log in or install dependencies as part of an evaluation.

## Run

Use the repository's existing Python environment. Choose a fresh output directory outside the checkout; the examples below use `/tmp`.

```sh
.venv/bin/python scripts/evaluate-conversation.py prepare --scenario staged_deck --host codex --output /tmp/sulaide-eval-codex-staged
.venv/bin/python scripts/evaluate-conversation.py run --output /tmp/sulaide-eval-codex-staged --allow-host-run
.venv/bin/python scripts/evaluate-conversation.py check --output /tmp/sulaide-eval-codex-staged
```

For Claude, prepare a separate directory with `--host claude`. No model override is selected by the harness; it uses the host's default. Run only after the corresponding skill and CLI/API contract changes are ready. A run directory is single-use so retries cannot silently merge evidence from different model conversations.

Scenario IDs are in `tests/fixtures/conversation/scenarios.json`. Start with `settings_missing`, `outline_style_edit`, and `editable_deferred`; then run `staged_deck` and the remaining scenarios. The default timeout is 240 seconds per host turn and can be reduced with `--timeout`. A scenario stops on its first failed turn.

## Evidence and verdict

Each run retains:

- `manifest.json`: host/version, source skill hashes and fixture/parser hashes.
- `scenario.json`: exact user messages, grants and the manual review rubric.
- `turn-N.host.jsonl` and `turn-N.stderr.txt`: unmodified host event output and diagnostics.
- `workspace/state/calls.jsonl`: exact fixture command arguments, turn number, result and error.
- `trace.json`: model-produced assistant text, session identity, completion state and calls for each turn.
- `report.json`: automatic failures and the manual checks still required.

`automated_pass: true` means only the machine-checkable gates passed. A reviewer must inspect the actual assistant text and raw tools using the scenario's `manual_review_required` list. Record the review separately with scenario, host, observed model (when emitted), skill hashes, verdict and concrete observations. Check settings are grouped, known choices are not re-asked, outline/style summaries are useful, preview artifacts are shown, and ordinary export proceeds without a mode/page-range questionnaire. Explicit editable requests must pause without conversion or an unapproved native substitute. Do not replace actual model traces with hand-authored ideal transcripts.

For an immutable historical run, use its own `evaluator.py check --output RUN_DIRECTORY`; newer evaluators may have a newer manifest schema. Additional assertions can be audited against the existing raw calls and recorded separately without rewriting the original trace or claiming another model run.

The print/exec harness exercises the text-question fallback. Native interactive question widgets need a separate manual host session using the same skill and fixtures. A missing second authenticated host, unsupported tool permission, timeout, or unavailable native question widget must remain an explicit evidence gap.

Unit tests in `tests/test_conversation_traces.py` deliberately feed invalid call traces into the validator (early analysis/export, unapproved writes, missing required calls, retries after conflict, and wrong export arguments). Those synthetic traces prove the validator detects errors; they are **not** evidence that an agent follows the skill.

## Server-owned generation boundary: 2026-10-29

The skill was subsequently updated to keep proprietary generation on the service: the host handles public interaction and returned results, never downloads private recipes or replaces Sulaide stages with local model output. Style review uses the recommended style ID and public catalog, not internal scores or routing evidence. This wording revision has unit/distribution verification; it has **not** been rerun through the real-host conversation matrix below. Those conversations remain evidence for their recorded snapshots only. Real media rendering is also outside this offline harness.

This snapshot's skill-file-map SHA-256 is `64e8f9455a825c5d52a6873f3d996038ff54279ecbb46bf0baf76ab58dd945bf`. CLI validation: 129 passed, 1 skipped; plugin manifests match. All 12 public files match byte-for-byte in source, wheel, ZIP and an isolated installation. The user's real installation was not changed.

## Native-only scope verification: 2026-10-29

After the user deferred editable export, two affected scenarios were rerun with Codex CLI 0.163.0: six real user turns, automatic assertions passed, and all scenario rubrics manually reviewed from assistant text and exact calls. This is targeted verification, not a rerun of the whole historical matrix or a second-host result. The model name was not emitted by Codex JSONL.

Historical skill snapshot **D** has skill-file-map SHA-256 `90230bdf9ef4cbaaf3fb27381c0c6a3dc420bbca0ace883c3f7f65c165301006` (same serialization as the historical hashes below).

| Scenario | Result | Manual observations |
|---|---|---|
| `staged_deck` | Pass, four turns | Settings wait; combined outline/style review; exact version 103 previews; only ordinary PPT offered; “继续导出” triggers native export without asking mode/page numbers. Both start and download use version 103/hash; no conversion page range or run ID. |
| `editable_deferred` | Pass, two turns | Even an explicit full-auto editable request produces zero product calls in turn 1; the final response explains the limit and waits. Turn 2 accepts ordinary PPT, then exports native version 101/hash without reopening settings or asking mode again. |

The deferred run's first acknowledgement, before reading the skill, prematurely repeated the requested conversion; after reading, it corrected the scope before any product call. This wording weakness remains visible in the raw trace and is not described as flawless dialogue. Both final delivery responses correctly identified the tiny fixture output as a placeholder, not proof of real PPTX validity. The existing artifact/native-widget limits still apply.

Raw runs are retained locally at `/tmp/sulaide-eval-20261029-native-staged` and `/tmp/sulaide-eval-20261029-native-deferred`. CLI tests: 129 passed, 1 skipped. The updated wheel, ZIP and isolated installation contain the same 12 skill files as source; no real user skill installation was changed.

## Recorded evaluation: 2026-10-29 (before scope reduction)

The user subsequently deferred editable export from this skill release. This table preserves historical evidence, not current editable-export support or a rerun of the revised skill. Current fixtures replace `editable_subset` with `editable_deferred` and make the staged flow export native PPT.

The accepted matrix contains **15 real host conversations and 25 user turns**: all 12 scenarios on Codex and three on Claude Code. A reviewer read the assistant responses and CLI calls for every scenario's rubric, checked the immutable run reports, and separately audited generation/page-edit guards and preview/export version/hash arguments. Every scoped rubric passed, subject to the artifact and host limits below. Earlier attempts remain preserved separately; they are not included in this accepted matrix.

Hosts were Codex CLI `0.163.0` and Claude Code `2.1.268`, with no model override. Codex JSONL did not emit a model name. Claude Code reported its configured default as `moonshotai/kimi-k3`; these are Claude **host** results, not evidence about an Anthropic Claude model.

The skill changed during evaluation, so the table identifies its frozen snapshot:

- **A:** initial evaluation snapshot; skill-file-map SHA-256 `dee22223ad68e93d7b6e2aa258f9c89cc3610d24956d04eab5bfddd234b34a0f`.
- **B:** explicit source-write gate reinforced; SHA-256 `c1030736a57456752c45b8960f59c11e8155efab54360eaefd139ca11e9e405f`.
- **C:** analysis promotion identity refreshed before outline review; SHA-256 `615fc49c006480fbb383bf4bd598792443c5c7976c65938d5b3077edc804d350`.

These hashes are SHA-256 of the JSON-serialized, key-sorted `skill_sha256` map in each run manifest. Generation flows affected by the final identity change were rerun on C with analysis 101→102 and generation 102→103. Other focused results retain their original snapshot; they are not presented as reruns of C.

| Scenario | Codex | Claude Code | Manual observation |
|---|---|---|---|
| `settings_missing` | Pass A | Pass B | Grouped material/settings summary; waits before source write or analysis. |
| `staged_deck` | Pass C | Pass C | Four resumed turns; combined outline/styles review; actual page references and rendering limitations; full guards; exact version 103; all three pages editable without a page-count question. |
| `settings_provided` | Pass B | — | Keeps explicit fluent narrative and supplied settings; does not ask them again; stops after outline/style review. |
| `outline_style_edit` | Pass B | — | Only page 3 changes to the live catalog's blueprint style; version/revision guards; no generation. |
| `template_upload` | Pass B | — | Website upload guidance and wait; fresh catalog after completion feedback; selects new master 8 on the original project. |
| `template_update_same_id` | Pass B | — | Waits for upload into the original card; refreshes and rebinds master 7; explicitly attributes parsing completion to the user's feedback. |
| `editable_subset` | Pass B | Pass A | Converts only 2,3 while delivering the whole deck; keeps page 1 as image; no settings restart; exact export identity. |
| `stale_outline` | Pass B | — | One guarded attempt gets 409; rereads updated page 3, redisplays outline, asks renewed confirmation; no automatic retry or guard removal. |
| `partial_preview` | Pass B | — | Discloses missing page 3; offers targeted completion/adjustment/export check; no blanket export ban or unrequested regeneration. |
| `auto_deck` | Pass C | — | Explicit full-auto advances through the workflow, refreshes analysis identity, and exports ordinary PPT on version 103. |
| `catalog_failure` | Pass B | — | Discloses unavailable catalog; no invented ID, default substitution, source write or analysis. |
| `old_server_guard` | Pass A | — | Missing review capability produces website handoff and zero generation writes. |

A real regression was observed and repaired: the first Claude staged run wrote the source before showing the settings checkpoint. Fresh runs after the source-guide correction waited before that write. Setup failures (host customization startup/environment and authentication visibility), a recovered invalid `projects get` command, and an inconsistent source fixture were retained as failed/blocked evidence instead of being called skill passes. The fixture was also strengthened to expose external revision changes and analysis promotion rather than holding identity constant.

The accepted Claude subset response overstated placeholder PPTX validity and absence of fallback pages; its pass is limited to interaction, command arguments, and delivery scope. All page images/downloads here are fixtures. Native question controls, visual rendering, real template parsing, actual PPTX validity/editability, and behavior of other models remain unverified by this harness. There were 24 host-attempt directories containing 42 turn traces including setup failures and superseded runs; raw transcripts and the detailed manual review index remain local, outside the public repository.
