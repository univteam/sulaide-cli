# Generate and review the preview

Read `interaction.md`. Generate only after the combined outline/style checkpoint is answered, or under explicit full-auto permission for this task. A page adjustment request stays limited to the requested page.

## Generate the reviewed outline

1. Keep the source revision, editing version and manifest revision shown in outline review. Read the project/layout again to detect changes; if they differ, return to that review instead of replacing the expected values silently.
2. Check `review_identity_guards: true` in `sulaide auth status`. If absent, explain that this server cannot protect the reviewed content and offer the website path; do not drop the guards and proceed.
3. Submit `sulaide preview generate PROJECT_ID --expected-source-revision SOURCE_REV --expected-editing-version EDITING_ID --expected-manifest-revision MANIFEST_REV`, also passing `--expected-version ACTIVE_ID` for the active presentation ID read with that review when one exists. The old `--expected-version` is the **active** ID, not a substitute for the editing ID or manifest revision.
4. Retain the request and operation IDs and the response's actual `presentation_version_id` and `generation_id`. The accepted generation can create a different version from the outline's editing version. Follow the returned target; never continue polling the old outline version or guess the target by reading the latest candidate.
5. Recover the accepted target via `sulaide operations show OPERATION_ID`. A presentation-version receipt may have no `run`; in that case `sulaide wait` returns immediately and does **not** prove generation completed. Poll `sulaide preview show PROJECT_ID --version-id ACCEPTED_VERSION_ID` with bounded backoff to inspect that exact version's page states. Keep its manifest hash. If work remains pending when the wait budget ends, report progress and resume the same version later; do not start a new generation.

The generate command starts the first report or continues an incomplete one; `mode` identifies `started` or `continued`. It consumes credits. An uncertain response or timeout means recover the same operation, not issue a new request. Insufficient credits follow `billing.md`; never retry paid work in a loop.

## Show real pages, then wait

Display the selected version's actual `preview_url` images in the conversation, with page labels. Use exact-version page links if the host cannot display the images; say what could not be shown. Refresh expired URLs by rereading **that version**. A generic project link that opens a newer candidate is not equivalent.

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
