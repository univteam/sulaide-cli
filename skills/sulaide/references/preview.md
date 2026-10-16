# Sulaide preview and images

Use the shared `sulaide` CLI and the exact project/version from the handoff.

1. Read `sulaide preview show PROJECT_ID` and record the selected presentation version and manifest hash.
2. Start or continue generation with `sulaide preview generate PROJECT_ID --expected-version VERSION_ID` (VERSION_ID is the project's current `active_presentation_version_id` right after analysis) and retain its operation ID. The same command starts the first report after analysis and continues an incomplete one; the result's `mode` is `started` or `continued`. It consumes credits; if it fails with `code` 402, ask the user to top up (`sulaide packages`, `sulaide topup`).
3. Resume with `sulaide operations show OPERATION_ID`; after completion, inspect `sulaide preview show PROJECT_ID --version-id VERSION_ID`.
4. Errors are JSON on stderr with `message`, `code` and `trace_id`; quote them verbatim, including `trace_id` for support.
5. Report published, failed, missing, stale, or unpaid pages separately. A partially completed candidate is not a completed report. Do not silently regenerate the entire deck or switch versions.

## Adjusting the preview (web 预览阶段)

| Action | Command | Notes |
| --- | --- | --- |
| Regenerate one page image | `sulaide pages regenerate P N [--prompt "..."] [--visual-style ID]` | Consumes credits; `--visual-style` from `sulaide visual-styles list` |
| Edit one page image by instruction | `sulaide pages edit-image P N --prompt "..." [--reference-image FILE]` | Consumes credits |
| Image history / restore | `sulaide pages images P SLIDE_ID`, then `sulaide pages restore-image P SLIDE_ID --source-version V --version-id ACTIVE_ID --manifest-hash HASH` | Restores the old image while keeping every page's current content; free |
| Theme colours / section template | `sulaide theme set P [--primary #RRGGBB] [--secondary ..] [--accent ..] [--text-color ..] [--apply-section-template]` | Re-renders section pages |

Regenerate/edit-image require a started preview (`409 PREVIEW_NOT_STARTED` otherwise). They are asynchronous: poll `sulaide preview show` until that page is `published` again. Never regenerate pages the user did not ask about.

Return project ID, presentation version ID, manifest hash, page counts, page-level errors, and operation ID. Model and image generation use the user's Sulaide account and may consume credits. Do not describe a page as visually approved based only on generation status.
