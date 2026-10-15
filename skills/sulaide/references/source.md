# Sulaide source preparation

Use the shared `sulaide` CLI. Do not call undocumented HTTP routes or write the API key into a command, file, prompt, or handoff.

1. Check `sulaide auth status`, then get the project list with `sulaide projects list` (see `references/projects.md` for reuse-vs-create rules).
2. Reuse the requested project, or create one with `sulaide projects create --title "..." [--language zh|en]`. Keep the returned `project_id` and `request_id` in the handoff.
3. Settle the project settings below (the same options as the web 项目设置 panel), then submit the material with `sulaide source set PROJECT_ID --file PATH --expected-revision REVISION [options]` (or `--text TEXT`). The first version supports UTF-8 text input; scanned files, PDF, DOCX, PPTX, spreadsheets, and image OCR require the Sulaide web upload flow.
4. Confirm the returned source revision and warnings with `sulaide projects show PROJECT_ID` (`settings` shows the saved language, target page count, narrative preference, and master template). Do not claim source preparation succeeded unless the server returns a saved revision.

## Project settings (项目设置)

| Option | Flag on `source set` / `source upload` | Default when omitted |
|---|---|---|
| 项目标题 | `--title "..."` | title given at `projects create` (`新PPT`) |
| 输出语言 | `--language zh\|en` | project language (`zh`) |
| 页数设定 | `--target-pages N` (1–50). Planned **strictly**: pages are never added or removed automatically | existing layout → source page count → 6 |
| 母版 | `--style-id ID` from `sulaide styles list` | no master: the project default fixed layer |
| 叙事偏好 | `--narrative rigorous` (严谨架构: conclusions, hierarchy, argument order) or `--narrative fluent` (流利表达: reading rhythm, natural narration) | `rigorous` |

Fixed-layer rule (固定层规则): title, subtitle, brand logo, footer, and page number are controlled by the chosen master and are never drawn into the AI content images.

When to ask the user (ask once, together, before `source set`; do not guess):
- **Language**: ask if the material and the request disagree or are mixed; otherwise use the request's language.
- **Page count**: ask unless the user stated it; it is strict, so a wrong value means re-analysis.
- **Master template**: run `sulaide styles list`; if the user has masters, ask which one (or none). If the list is empty, say the default fixed layer will be used.
- **Narrative preference**: ask only if the purpose is unclear (formal report → rigorous; talk or storytelling → fluent); otherwise use the default and say so.

`--source-page-count` only records how many pages the original document had; it is not the target.

Return `project_id`, `source_revision`, source filename, the settings used, and any extraction limits. If a request times out, reuse its request ID or inspect the operation; do not submit the same material as a new request automatically.
