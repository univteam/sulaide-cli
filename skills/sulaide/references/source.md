# Source and project settings

Read `interaction.md` and `web-options.md` first. This stage ends with saved settings and the user's decision to start analysis; do not run an unattended chain through export.

## One settings conversation

1. Check `sulaide auth status`. Read `projects.md` to locate the requested project without duplicates; for existing work, get `sulaide projects show PROJECT_ID` and retain its source revision and settings.
2. Run `sulaide styles list`. Carry forward choices the user already stated. Show a compact material/title summary and collect only missing settings together: master, narrative preference, pages and language.
3. Offer an existing master by its real name, uploading a master, or the default fixed layer. An empty list does not remove the upload choice; a failed list does not authorize choosing no master.
4. Mark new-project defaults as suggestions: **5 pages, 中文, 严谨架构, default fixed layer**. Present 严谨架构 and 流利表达 with their website explanations. Do not infer narrative preference from “formal report” or infer output language from the source alone.
5. Wait for the settings/analysis decision. Already supplied settings need only appear in the summary; do not ask them again one by one. Record any requested visual style for the later combined outline/style review instead of opening another questionnaire here.

## Save the confirmed choices

Before `source set` / `source upload`, check that the user has answered the settings checkpoint, supplied the complete settings with a request to proceed, or explicitly requested full automation. Merely naming a source file in “用这个材料做 PPT” is not that confirmation: read the file and saved settings, present the summary, and stop before writing. Saved defaults are values to present, not a prior user reply. A specific single-step request such as “只替换项目 42 的底稿，沿用其余设置” directly authorizes that limited source update; perform it without reopening the full questionnaire.

Create a project only for new work: `sulaide projects create --title "..." [--language zh|en]`. Reuse its returned ID; if website upload needs a target project earlier, create it once and preserve that ID through the handoff.

For text, use `sulaide source set PROJECT_ID --file PATH --expected-revision REVISION [options]` or `--text TEXT`. `sulaide source upload PROJECT_ID PATH --expected-revision REVISION [options]` is also text-only; its name does not imply Office/PDF parsing. Source text must be UTF-8.

| Setting | CLI option | Conversation rule |
|---|---|---|
| 项目标题 | `--title "..."` | Use the confirmed title; preserve an existing title unless changed. |
| 输出语言 | `--language zh\|en` | 中文 or 英文; carry forward the user's choice. |
| 页数设定 | `--target-pages N` | Submit the confirmed count explicitly on new work, including the 5-page suggestion once accepted. Initial website settings are 1–30; CLI compatibility accepts 1–50. |
| 母版 | `--style-id ID` | ID must come from the account's current master list. |
| 清除母版 | `--clear-style` | Only when the user chooses the default fixed layer/removes the master. Mutually exclusive with `--style-id`. |
| 叙事偏好 | `--narrative rigorous\|fluent` | Maps to 严谨架构／流利表达. New work submits the confirmed preference. |

Check `source_settings_patch: true` in `auth status` before relying on omitted settings being preserved or clearing a master. On a compatible server, omission means keep the existing setting; `--clear-style` explicitly clears the master. If unsupported, explain the compatibility limit and use the website settings path; do not omit fields on an old server and claim they will be preserved.

`--source-page-count` records the original document's page count, not the target. Never substitute it for the confirmed target. If a requested count is outside the website stage's range, explain the range and available reanalysis path; do not silently clamp it or make a smaller deck first.

After saving, re-read `sulaide projects show PROJECT_ID`; compare saved settings with the confirmation. Keep the new `source_revision` for analysis. A mismatch or conflict must be resolved before starting analysis. On existing work, explain that replacing source content returns to the source stage and requires a new outline; preserve settings the user did not change.

## Uploading a master on the website

Use the same service as the CLI; the public master library is [母版库](https://www.sulide.com.cn/app/templates). Tell the user to create a master and upload its material, or upload to an existing master card; the website accepts PPT/PPTX, PDF and supported image formats. If they edit the master, finish saving it there before returning.

Keep all already supplied choices while waiting. After the user reports completion, refresh `sulaide styles list` and resolve the intended master. Uploading to an existing master can keep the **same ID**; do not wait only for a new ID. Use names/descriptions to resolve ambiguity without asking users to copy technical identifiers.

The current list proves the master exists, not that upload/parse succeeded. Use the user's completion feedback and distinguish that from verification. If upload failed or they have not finished, remain at this checkpoint; do not silently switch to the default master. Return to the original settings summary and the original project.

## PDF, Office, spreadsheets and image source files

These files require the website upload/parser. Explain this limit and direct the user to the same project's source/upload screen on the configured service. Preserve the known title, master, language, pages and narrative preference; do not create another project when they return.

After upload, re-read the project's material, settings and source revision. Show any differences from the choices already made and resolve only those differences. A file merely selected locally in the browser is not a saved source revision. If the website's save/analyse action has already started analysis, continue that existing work rather than submitting a duplicate analysis. If its run identity is not available through the CLI, use the website to inspect it; do not invent an operation ID.

Upload failure leaves the workflow at source preparation. Do not claim the CLI uploaded the binary file, pass the binary bytes as text, or start analysis against the old material.

Return the project ID, saved revision, actual settings and material limitations. Keep request/operation IDs for recovery; a timeout is not permission to submit a new copy of the material.
