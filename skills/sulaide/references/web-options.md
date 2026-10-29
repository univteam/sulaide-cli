# Website choices for the conversation

Use the website's choices below, not an invented questionnaire. Fixed options were checked against the website workflow on 2026-10-29. Master templates and visual styles are live account/catalog data: query them for the current session and preserve their real IDs and names.

| Decision | User-facing choices and explanation | Default/context | Execution guide |
|---|---|---|---|
| 母版 | Existing account master; upload your own; or default fixed layer. Masters control title/subtitle, logo, footer, page number, fonts and branding. | Preserve the existing master. New projects may use no master; offer upload even when the list is empty. | `source.md`; `sulaide styles list` |
| 叙事偏好 | **严谨架构**：更强调结论、层级和论证顺序。 **流利表达**：更强调阅读节奏和自然叙述。 | New-project suggestion: 严谨架构. Do not choose based only on a guessed audience or purpose. | `source.md` |
| 页数设定 | Exact target page count, including the presentation's structural pages. | New-project suggestion: 5; website source settings allow 1–30. Reanalysis allows 1–50 and starts from current pages. | `source.md`, `analysis.md` |
| 输出语言 | 中文 or 英文. This is the requested output language, not necessarily the source language. | New-project suggestion: 中文; preserve an explicit English request or saved English setting. | `source.md` |
| 内容大纲 | Review section/page titles and content points; request content changes or reanalysis. | Show all page titles with concise points before generation. Expand complete page text only as needed. | `analysis.md` |
| slides 视觉风格 | The live `sulaide visual-styles list` choices; present recommendations and user overrides by group. | Use actual page recommendations/current choices. Do not hard-code a style name or invent a “formal”, “humorous” or “automatic” style ID. | `analysis.md`, `preview.md` |
| 预览调整 | Continue generation; adjust a page's image/layout; edit with an instruction; restore an image; change theme where supported. | Keep the shown presentation version. Offer local changes without opening every advanced control. | `preview.md` |
| 导出 | **普通 PPT**：保留当前页面画面。 | The only export mode in this skill release; combine export confirmation with preview acceptance. | `export.md` |

Editable export is deferred from this skill release even though the website/CLI may expose it. Do not offer conversion modes or page ranges. If the user explicitly requests editable output, explain the limit and wait for their choice of ordinary PPT; do not treat that request as permission to substitute native output.

“演讲稿风格” in this workflow maps to the existing narrative preference, not a separate script-generation stage. Visual style is selected separately during outline review. Section/end pages rendered from a frozen template have no AI visual-style selector.

The website's reanalysis “结构要求” field allows 2000 characters. Present that limit in the guided flow; the CLI/API's existing 4000-character compatibility limit is not a new website option. Likewise, the CLI accepts 1–50 target pages, but the website's initial source settings expose 1–30. Explain the relevant stage when a request exceeds its range; do not silently truncate it or first create a smaller deck without consent.

## Dynamic choices and website handoff

- Fetch masters and styles; show names/descriptions and retain IDs internally. If names are duplicated, use available distinguishing details and ask only which one the user means.
- An empty master list still allows uploading a master or using the default fixed layer. A failed list request is not an empty list and does not authorize a default.
- A removed/disabled style or master cannot be silently replaced. Refresh choices and resolve the affected selection with the user.
- Use the same configured service for website links and CLI operations. The public default is `https://www.sulide.com.cn`; the master library is `/app/templates`. Never put API keys in links.
- Template upload and binary-source parsing are currently website actions. Follow `source.md` to return to the same project and settings afterward.

## Maintainer parity anchors

Website source components: `frontend/src/features/project-workflow/ui/ProjectUploadFlow.tsx`, `ProjectAnalysisWorkbench.tsx`, `VisualStyleOptions.tsx`, `ProjectPreviewWorkspace.tsx`, `ProjectExportGate.tsx`; template upload: `frontend/src/features/template-management/ui/TemplateLibrary.tsx` in the website repository. These are release-check references, not instructions to inspect source code during a user's PPT task. Recheck the fixed mapping when website choices change; never copy private service addresses or internal prompts into this public skill.
