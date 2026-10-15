# Sulaide narrative analysis

Use only the shared `sulaide` CLI. Confirm the project and source revision first.

1. Run `sulaide projects show PROJECT_ID` and record `source_revision` and `settings.target_page_count`.
2. Start work with `sulaide analysis start PROJECT_ID --expected-revision REVISION [--page-count N] [--structure-requirements "..."]`.
   - `--page-count` overrides the saved target page count (页数设定) for this run; omit it to use the saved value. The outline uses exactly that many pages.
   - `--structure-requirements` (结构要求, optional, ≤4000 chars) states how chapters should be grouped or ordered, e.g. "将产品体验和客户服务合为一章，按问题、证据、建议组织". Pass the user's own wording; do not invent requirements.
   - Re-running analysis with a new page count or requirements is the web "重新分析" action and replaces the outline.
3. Save `operation_id` and `run_id`. Poll with `sulaide wait OPERATION_ID --timeout 180`, or resume with `sulaide operations show OPERATION_ID` after interruption.
4. Report the exact run status and resulting project outline. Failed or uncertain upstream outcomes must be reported for review; do not create a replacement request automatically.

Ask the user for page count or structure requirements only when they are material and cannot be inferred from the request.

Return project ID, source revision, operation ID, run ID, status, page count, and questions the outline still needs answered. Sulaide performs model calls and charges the user's Sulaide credit account.
