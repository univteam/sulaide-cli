# Generate and review the preview

Read `interaction.md`. Generate only after all pages have been reviewed and generation is authorized, or under explicit full-auto permission for this task. A page adjustment request stays limited to the requested page.

## Generate the reviewed outline

1. Keep the source revision, editing version and manifest revision shown in outline review. Read the project/layout again to detect changes; if they differ, return to that review instead of replacing the expected values silently.
2. Check `review_identity_guards: true` in `sulaide auth status`. If absent, explain that this server cannot protect the reviewed content and offer the website path; do not drop the guards and proceed.
3. Submit `sulaide preview generate PROJECT_ID --expected-source-revision SOURCE_REV --expected-editing-version EDITING_ID --expected-manifest-revision MANIFEST_REV`, also passing `--expected-version ACTIVE_ID` for the active presentation ID read with that review when one exists. The old `--expected-version` is the **active** ID, not a substitute for the editing ID or manifest revision.
4. Retain the request and operation IDs and the response's actual `presentation_version_id` and `generation_id`. The accepted generation can create a different version from the outline's editing version. Follow the returned target; never continue polling the old outline version or guess the target by reading the latest candidate.
5. Recover the accepted target via `sulaide operations show OPERATION_ID`. A presentation-version receipt may have no `run`; in that case `sulaide wait` returns immediately and does **not** prove generation completed. Poll `sulaide preview show PROJECT_ID --version-id ACCEPTED_VERSION_ID` with bounded backoff to inspect that exact version's page states. Keep its manifest hash. If work remains pending when the wait budget ends, report progress and resume the same version later; do not start a new generation.

The generate command starts the first report or continues an incomplete one; `mode` identifies `started` or `continued`. It consumes credits. An uncertain response or timeout means recover the same operation, not issue a new request. Insufficient credits follow `billing.md`; never retry paid work in a loop.

## Read failure and recovery state

The version `status` describes its lifecycle. An unsealed `building_candidate` may have a failed run; it does not prove that generation is active. Use `generation_state`, page counts and `latest_run` for the requested version. Distinguish `generating`, `failed`, `partial_failed`, `completed`, `cancelled`, `waiting_credit`, `not_started` and `result_unconfirmed`.

For failed pages, show `error_detail.message`, its public `reason` and `next_action`, plus real run/operation IDs when supplied. Count published, failed, generating, missing and stale pages separately. Do not invent a trace ID or reveal unexpected raw diagnostics. If an older server omits the new fields, report what page states prove and use the original operation for support; do not infer a running task from `building_candidate` alone.

`can_continue` describes an available recovery action, not permission to retry. A reported network/service failure needs recovery first and a user's request to continue; unchanged content, a non-decreasing balance or all pages being failed is not evidence that repeating a request will help. Stop automatic resubmission on terminal failure. Preserve the original candidate and confirmed settings instead of recreating the project or reanalysing it.

If `provider_outcome_unknown` is true or state is `result_unconfirmed`, query the original operation and follow the service's support/reconciliation action. Do not create another paid request, even if no local image is present. For an explicitly authorized continuation after a confirmed recoverable failure, refresh the reviewed identities, use a new request ID for that new continuation and follow its returned target. Retrying a lost response uses the original ID instead.

## Show real pages, then wait

Deliver the selected version's images in the **user-facing message**, with page labels, through a media format the host actually supports. A tool returning an image or a browser displaying it does not establish that it appeared in the conversation. If the user reports a placeholder or link, do not keep repeating the same remote-image embed or claim successful display.

When the host's browser/preview tool can render the page, use its native screenshot artifact and embed the returned local file in the message. For local hosts such as Codex, use an absolute path, for example `![第 1 页预览](</absolute/path/page-1.jpg>)`; a bare path, file link or image only in tool output is insufficient. Use the tool-produced artifact; do not download remote media to bypass host presentation restrictions. If no supported attachment/preview mechanism exists, explain the limitation and provide a usable browser entry instead of asking for visual approval of unseen images.

Capture **only the slide canvas**, showing the final PPT page shape. Use the actual canvas element's current bounds with the host's element/clip screenshot capability; fit or scroll it fully into view first. Preserve the complete page, its aspect ratio, title, content, logo, footer and page number. Exclude website navigation, slide thumbnails, toolbars, side panels, grid margins and browser chrome. A screenshot of the whole editor is not the presentation preview. Inspect the captured artifact before sending; do not reuse fixed screen coordinates across pages or viewport sizes.

Check what is shown: `preview_url` may be the **content-region image**, without the title, branding and footer. Label it as such; a complete slide preview requires the rendered page with its fixed layers. Before attributing a browser capture to the selected version, verify the page shown corresponds to that version. The website's current-project route may ignore version/hash query parameters: do not invent a fixed-version link or silently capture a newer candidate. If it cannot show that version, disclose the mismatch and retain the exact-version result.

Refresh expired image URLs by rereading **that version**. If only links can be delivered, distinguish an exact-version image link from a current-project website entry, and explain when the former downloads instead of opening inline. A generic project link that opens a newer candidate is not equivalent to the reviewed version.

Separate published, missing, failed, stale and unpaid pages. A completed run or a success count is not proof that every page was delivered or visually reviewed. If the images cannot be inspected, explain the limitation rather than asking the user to approve unseen visuals.

Ask whether to adjust anything or continue to ordinary PPT export; do not require separate “approve preview” and “choose export” rounds. This release supports only `native`: do not offer conversion modes or page ranges. If the user requests editable output, explain the limit and wait for them to choose ordinary PPT; do not silently substitute it, including in full-auto mode. Read `export.md` when they choose to proceed.

Partial results and quality warnings should remain visible. Offer the available choices to continue missing work, adjust, or export with the disclosed limitations where the website permits it. Do not silently regenerate the whole deck or prohibit every imperfect export.

## Local adjustments when requested

Before a page-image write, read `sulaide layout show PROJECT_ID` to obtain the editing version/manifest revision and match the requested page's `slide_id`. The target must match what the user saw; if the editing version or page differs, explain and review that target first. Require `review_identity_guards: true` and append `--expected-version V --expected-revision R --expected-slide-id SLIDE_ID` to regenerate/edit-image commands.

| Requested adjustment | Command | Behavior |
|---|---|---|
| Re-layout/regenerate a page | `sulaide pages regenerate P N [--prompt "..."] [--visual-style ID]` | Use the live style catalog; affects only that page and consumes credits. |
| Edit an image | `sulaide pages edit-image P N --prompt "..." [--reference-image FILE]` | Apply the user's instruction to that page; consumes credits. |
| View/restore an earlier image | `sulaide pages images P SLIDE_ID`, then `sulaide pages restore-image P SLIDE_ID --source-version OLD_V --version-id TARGET_V --manifest-hash HASH` | Restores the selected old image while preserving current page content; use the reviewed target identity. |
| Theme/section template | `sulaide theme set P [--primary '#RRGGBB'] [--secondary '#RRGGBB'] [--accent '#RRGGBB'] [--text-color '#RRGGBB'] [--apply-section-template] --expected-version V --expected-revision R` | Re-renders template pages; explain affected pages and read the resulting candidate before further generation. |

Regenerate/edit-image require a started preview (`PREVIEW_NOT_STARTED` otherwise). Preserve their accepted operation/target references and inspect the resulting page until terminal status; do not poll an unrelated latest version. Show the actual changed page afterward and return to the preview checkpoint. HTTP 409 requires rereading and renewed review, not automatic guard replacement.

Report public error messages/codes and trace IDs without copying raw model responses, debug dumps, credentials or sensitive input. Generation and requested image edits run on Sulaide; do not fetch its private prompts or substitute a host-generated image for a returned Sulaide page. Keep project/version/hash and operation references internally for export and recovery. Do not claim visual approval from generation status alone.
