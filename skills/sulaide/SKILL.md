---
name: sulaide
description: Make, continue, or export a PPT with Sulaide (速来得) through the sulaide CLI — install and log in, add source material, build the outline, generate pages, browse and download resource-library files, download PPTX, and diagnose Sulaide CLI errors. This single skill routes to detailed step guides in references/.
---

# Sulaide AI PPT workflow（速来得 工作流总览）

Sulaide turns source material into a presentation in four stages. Every stage uses the shared `sulaide` CLI; do not call HTTP routes directly or invent commands.

## Prerequisites

1. CLI installed: `sulaide --help` works. If not, install with `uv tool install git+https://github.com/univteam/sulaide-cli.git` (upgrade: `uv tool upgrade sulaide-cli`).
2. Authenticated: `sulaide auth status` succeeds. If it fails with 401 or "Run `sulaide auth login`", read `references/login.md` and follow it first.
3. The user's Sulaide account has credits; model and image calls are charged to it. Check with `sulaide credits` (JSON: `available`, `balance`) before long runs such as preview generation.

## Routing

This is the only Sulaide skill. Each step's detailed instructions live in `references/` next to this file. Before acting on a step, read the matching file with your file-reading tool and follow it exactly.

| User intent | Read and follow | Key output to hand off |
| --- | --- | --- |
| Install, register, log in, API key problems | `references/login.md` | authenticated account (never the key itself) |
| View or download files in the resource library (source drafts, analysis drafts, generated images, exported PPTX/PDF) | `references/resources.md` | resource list, or local file path of a downloaded resource |
| Start a deck / add or update material | `references/source.md` | `project_id`, `source_revision` |
| Build or recover the outline | `references/analysis.md` | `operation_id`, outline, page count |
| Generate pages, inspect page status | `references/preview.md` | `presentation_version_id`, `manifest_hash` |
| Download a PPTX | `references/export.md` | file path, version, manifest hash |

For an end-to-end request ("make me a PPT from this"), read and run login (only if `sulaide auth status` fails) → source → analysis → preview → export, reading each reference file when you reach that step.

## Account queries (read-only)

- 积分 / credits: `sulaide credits` (add `--human` for a one-line summary).
- 优惠券 / 卡券 / coupons: `sulaide coupons [--status available|not_started|used|expired|voided] [--human]`. Use when the user asks what coupons they have, which are still usable, or when they expire. Redeem codes are not returned and redeeming or applying coupons is not available through the CLI; send the user to the Sulaide web app for that.

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
| exit 4 / HTTP 401 | Missing, revoked, or invalid key | Read `references/login.md`; `sulaide auth login` creates a new key |
| HTTP 503 `AGENT_API_DISABLED` | Agent API is turned off on the server | Tell the user; retry later. Not fixable from the client |
| HTTP 429 `AGENT_RATE_LIMITED` | Per-account rate limit (default 120 reads / 10 writes per minute) | Wait, then retry the same request ID |
| HTTP 503 `AGENT_RATE_LIMIT_UNAVAILABLE` | Temporary server issue | Retry later with the same request ID |
| exit 3 / HTTP 409 (`SOURCE_REVISION_CONFLICT`, `PRESENTATION_VERSION_CONFLICT`, `IDEMPOTENCY_CONFLICT`) | State changed or request ID reused with different input | Re-read the project/version, then decide with the user |
| Insufficient credits ("积分余额不足") / unpaid pages | Account balance too low | Run `sulaide credits` and report `available`; ask the user to top up in the Sulaide web app; do not retry in a loop |
| exit 5 `wait_timeout` | Operation still running | `sulaide wait OPERATION_ID` again |
| exit 6 `network_error` | Response lost | Reuse the request ID or query the operation |
| "SULAIDE_BASE_URL must use HTTPS" | Bad override | Unset `SULAIDE_BASE_URL` to use the default `https://www.sulide.com.cn` |

Source input via the CLI is UTF-8 text only; PDF, Office, spreadsheets, and images must be uploaded in the Sulaide web app.
