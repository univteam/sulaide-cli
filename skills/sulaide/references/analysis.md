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

## Editing pages after analysis (web 叙事分析工作台)

Read the pages and the editing version first: `sulaide layout show PROJECT_ID` → `pages[]`, `presentation_version_id`, `manifest_revision`. Pass those back as `--expected-version` / `--expected-revision` so a concurrent web edit fails with 409 `PRESENTATION_VERSION_CONFLICT` instead of being overwritten (omit them only for a single, immediate edit). Every edit returns the new version; re-read `layout show` before the next one.

| Action | Command | Notes |
| --- | --- | --- |
| Edit title / subtitle / body / narrative | `sulaide pages edit P N --title ... --subtitle ... --content ... (or --content-file F) --narrative ...` | Marks the page image stale |
| Per-page 视觉风格 | `sulaide pages edit P N --visual-style ID` | IDs from `sulaide visual-styles list` |
| Title / subtitle width | `sulaide pages edit P N --title-width 800 --subtitle-width 700` | px on a 1600-wide canvas, clamped to [240, canvas − x] |
| Add / delete / duplicate / move | `pages add P [--after N] [--title] [--content]`, `pages delete P N`, `pages duplicate P N`, `pages move P N up\|down` | Last page and section pages that still have body pages cannot be deleted; structured decks can only move body pages within one section |
| Split a page | `sulaide pages split P N --at OFFSET` | OFFSET = character index in the body where page 2 starts; AI rewrites both titles (and narration), then the CLI applies it |
| Merge into previous page | `sulaide pages merge P N` | Page N merges into N−1 (same section); AI rewrites the title |
| Single-page re-analysis | `sulaide pages reanalyze P N [--instruction "..."]` | Rewrites title, subtitle, body and narrative of that page only |

Split/merge wait for the title run (`--timeout`, default 180 s); with `--no-wait` they return `run_id`, and re-running the same command later resumes and applies it. Title runs and re-analysis use model calls billed to the user's account. Ask the user before deleting pages or rewriting content they did not ask to change.

Return project ID, source revision, operation ID, run ID, status, page count, and questions the outline still needs answered. Sulaide performs model calls and charges the user's Sulaide credit account.
