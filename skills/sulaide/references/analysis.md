# Outline and slide-style review

Read `interaction.md`. Start analysis after the settings checkpoint is answered, or when an explicit reanalysis request has resolved its target and settings. Analysis completion opens the **combined outline and visual-style checkpoint**; it does not automatically start images.

Run analysis and style recommendation on Sulaide through the CLI. Present and explain the returned outline and public style choices; do not fetch private prompts or generate a substitute analysis with the host model. If the service fails, recover or report that failure instead of presenting a local draft as its result. User-requested content edits are still supported below.

## Analyse and show the result

1. Read `sulaide projects show PROJECT_ID`; retain the confirmed `source_revision`, active presentation ID and target page count.
2. Run `sulaide analysis start PROJECT_ID --expected-revision REVISION [--page-count N] [--structure-requirements "..."]`.
3. Keep `operation_id` and `run_id`. Use `sulaide wait OPERATION_ID --timeout 180`; after interruption inspect `sulaide operations show OPERATION_ID`. Resume the original operation on timeout instead of creating another paid request.
4. On completion, read `sulaide projects show PROJECT_ID`, `sulaide layout show PROJECT_ID` and `sulaide visual-styles list`. Analysis can publish a new active version: capture the resulting source revision and active presentation ID from the project, and `presentation_version_id` / `manifest_revision` from layout. Do not carry the pre-analysis active ID into generation.
5. Present sections, each page's title and concise content points. In that same message, group current visual styles by page/section and distinguish recommendations from user overrides. Use real catalog names, not a hard-coded default style.
6. Ask whether to generate with this outline/style selection or what to change, then wait. The reply can confirm both together. If a visual style was explicitly requested earlier, apply it to the applicable pages before this review and show it as the user's choice; do not ask the same preference again.

The website's reanalysis page count is **1–50**, defaulting to current pages; `--page-count` overrides the saved target for this run. Changing it replaces the outline, so explain the impact before reanalysis. The website “结构要求” input allows 2000 characters; the existing CLI/API accepts up to 4000 for compatibility. Collect this field only when the user wants structural guidance, preserve their wording, and never invent chapter requirements just to fill it.

## Style selection without a page-by-page questionnaire

Use returned page recommendation/override and template-page information. Do not infer template status from page position. Frozen-template section/end pages keep their template; their lack of an AI-style selector is not an error.

Label an automatic choice as the service's recommendation. Explain styles using their public catalog descriptions; do not request or invent routing scores, evidence tags or internal decision reasons.

Offer live available styles for a requested change, with descriptions where useful. Users may choose one style for a page, a group or all applicable AI pages. Translate that into existing page edits, not a new “whole-deck style” command. Preserve explicit user overrides when recommendations change. If the requested style is unavailable or its name is ambiguous, resolve only that choice.

After an edit, read the project and layout again, display the changed page/content or style group and keep the generation checkpoint pending. Every new outline review captures source, active, editing and manifest identities together before asking the user. “Change page 3” does not mean “generate the deck now”. Distinguish content changes from visual-style changes when the wording could mean either.

## Editing the outline

Before each write, read the editing identity with `sulaide layout show PROJECT_ID` and match the affected page to the user's reviewed content. Pass `--expected-version V --expected-revision R` on versioned edits, including reanalysis; do not omit them for an “immediate” edit. A new current revision does not renew an old confirmation.

| Requested action | Command | Relevant limit |
|---|---|---|
| Change title/subtitle/body/core narrative | `sulaide pages edit P N --title ... --subtitle ... --content ... --narrative ...` | Send only changed fields; `--content-file F` is available for longer body text. |
| Change visual style | `sulaide pages edit P N --visual-style ID` | Use a live catalog ID and an applicable AI page. |
| Adjust title/subtitle width | `sulaide pages edit P N --title-width 800 --subtitle-width 700` | Advanced only; dimensions follow the website canvas constraints. |
| Add/delete/duplicate/move | `pages add P --after N`, `pages delete P N`, `pages duplicate P N`, `pages move P N up\|down` | Last page and sections with body pages cannot be deleted; structured body pages move within their section. |
| Split a page | `sulaide pages split P N --at OFFSET` | Resolve the content split with the user; derive the character offset internally. |
| Merge into previous | `sulaide pages merge P N` | Same section; page N merges into N−1. |
| Reanalyse one page | `sulaide pages reanalyze P N --instruction "..."` | Rewrites only the requested page; include the version guards above. |

Do not expose these technical controls as the default conversation. Chapter movement and undo of a split/merge remain website-only; provide a clear handoff and read the changed layout when the user returns.

Split/merge generate titles through a billed background run. They normally wait; `--no-wait` returns a run to resume. Preserve the original request ID when resuming the same action. For different edits, use different request IDs; never reuse one ID across different verbs or changed bodies. Re-read the returned layout identity after every successful edit. Partial batch failure means report completed and remaining edits, recover uncertain requests, then continue only the remaining work.

HTTP 409 means conflict: re-read, show the relevant differences and return to review. Other HTTP 4xx layout-rule failures are validation errors, not permission to retry blindly. Report failed/uncertain upstream outcomes without automatically replacing the request.

When the user confirms generation, hand the exact source revision, editing version and manifest revision to `preview.md`, together with the current choices and operation references. Sulaide performs analysis and charges the user's account; a finished analysis is not a completed presentation.
