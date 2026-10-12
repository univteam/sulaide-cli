---
name: sulaide-analysis
description: Run or recover narrative analysis for a Sulaide project and return its outline and execution status.
---

# Sulaide narrative analysis

Use only the shared `sulaide` CLI. Confirm the project and source revision first. Ask the user for page count or narrative requirements only when they are material and cannot be inferred from the request.

1. Run `sulaide projects show PROJECT_ID` and record `source_revision`.
2. Start work with `sulaide analysis start PROJECT_ID --page-count N --expected-revision REVISION`.
3. Save `operation_id` and `run_id`. Poll with `sulaide wait OPERATION_ID --timeout 180`, or resume with `sulaide operations show OPERATION_ID` after interruption.
4. Report the exact run status and resulting project outline. Failed or uncertain upstream outcomes must be reported for review; do not create a replacement request automatically.

Return project ID, source revision, operation ID, run ID, status, page count, and questions the outline still needs answered. Sulaide performs model calls and charges the user's Sulaide credit account.
