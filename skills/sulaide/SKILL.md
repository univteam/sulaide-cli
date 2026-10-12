---
name: sulaide
description: Overview and router for the Sulaide (速来PPT) AI presentation workflow. Use when a user wants to make, continue, or export a PPT with Sulaide and you need to decide which stage skill to run (login, source, analysis, preview, export) or diagnose a Sulaide CLI error.
---

# Sulaide AI PPT workflow（速来PPT 工作流总览）

Sulaide turns source material into a presentation in four stages. Every stage uses the shared `sulaide` CLI; do not call HTTP routes directly or invent commands.

## Prerequisites

1. CLI installed: `sulaide --help` works. If not, install with `uv tool install git+https://github.com/univteam/sulaide-cli.git` (upgrade: `uv tool upgrade sulaide-cli`).
2. Authenticated: `sulaide auth status` succeeds. If it fails with 401 or "Run `sulaide auth login`", use the `sulaide-login` skill first.
3. The user's Sulaide account has credits; model and image calls are charged to it.

## Routing

| User intent | Skill | Key output to hand off |
| --- | --- | --- |
| Install, register, log in, API key problems | `sulaide-login` | authenticated account (never the key itself) |
| Start a deck / add or update material | `sulaide-source` | `project_id`, `source_revision` |
| Build or recover the outline | `sulaide-analysis` | `operation_id`, outline, page count |
| Generate pages, inspect page status | `sulaide-preview` | `presentation_version_id`, `manifest_hash` |
| Download a PPTX | `sulaide-export` | file path, version, manifest hash |

Run stages in order: source → analysis → preview → export. Resume from the stage the handoff reached; do not restart earlier stages unless the user asks.

## Operating rules

- Every write returns an operation. Keep `request_id` and `operation_id`; after a timeout or lost response, run `sulaide operations show OPERATION_ID` or `sulaide wait OPERATION_ID` instead of submitting a new request.
- Pass `--expected-revision` / `--expected-version` so concurrent edits fail loudly instead of overwriting.
- Report failed, partial, or unpaid pages exactly; never claim visual quality from status alone.
- Never print, log, or hand off an API key or password.

## Common errors

The CLI prints errors as JSON on stderr with `http_status`, `reason`, `retryable`, and `next_action`.

| Symptom | Meaning | What to do |
| --- | --- | --- |
| exit 4 / HTTP 401 | Missing, revoked, or invalid key | Use `sulaide-login`; `sulaide auth login` creates a new key |
| HTTP 503 `AGENT_API_DISABLED` | Agent API is turned off on the server | Tell the user; retry later. Not fixable from the client |
| HTTP 429 `AGENT_RATE_LIMITED` | Per-account rate limit (default 120 reads / 10 writes per minute) | Wait, then retry the same request ID |
| HTTP 503 `AGENT_RATE_LIMIT_UNAVAILABLE` | Temporary server issue | Retry later with the same request ID |
| exit 3 / HTTP 409 (`SOURCE_REVISION_CONFLICT`, `PRESENTATION_VERSION_CONFLICT`, `IDEMPOTENCY_CONFLICT`) | State changed or request ID reused with different input | Re-read the project/version, then decide with the user |
| Insufficient credits / unpaid pages | Account balance too low | Ask the user to top up in the Sulaide web app; do not retry in a loop |
| exit 5 `wait_timeout` | Operation still running | `sulaide wait OPERATION_ID` again |
| exit 6 `network_error` | Response lost | Reuse the request ID or query the operation |
| "SULAIDE_BASE_URL must use HTTPS" | Bad override | Unset `SULAIDE_BASE_URL` to use the default `https://www.sulide.com.cn` |

Source input via the CLI is UTF-8 text only; PDF, Office, spreadsheets, and images must be uploaded in the Sulaide web app.
