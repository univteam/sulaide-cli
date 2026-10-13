# Sulaide PPTX export

Use the shared `sulaide` CLI and the exact frozen `presentation_version_id` and `manifest_hash` from preview.

1. Verify the selected version is the intended version and its page manifest is complete.
2. Start an export with `sulaide export start PROJECT_ID --version-id VERSION_ID --manifest-hash HASH --mode native` (or an explicitly requested editable mode, see the table below).
3. Preserve the returned operation ID. If the outcome is uncertain, inspect that operation before retrying. For editable modes, `sulaide wait OPERATION_ID` until the run finishes and keep `result.run_id`.
4. Download with `sulaide export download PROJECT_ID VERSION_ID HASH --output FILE.pptx`, adding `--run-id RUN_ID` **only** for editable modes. The CLI will not overwrite an existing file, refuses error bodies (HTTP error or HTTP 200 with a non-zero `code`), and only writes a real PPTX (ZIP) package.
5. Report the file path, byte size, frozen version, and manifest hash. Opening or inspecting the deck is a separate validation step; do not claim visual fidelity without checking it.

## Export modes

| Mode | What you get | `export start` returns | Download |
| --- | --- | --- | --- |
| `native` (default) | PPTX built from the generated page images; fastest | `result.run_id` is `null`, `result.download.requires_run_id` is `false` | `export download PROJECT_ID VERSION_ID HASH --output FILE.pptx` (no `--run-id`); the file is keyed by version + manifest hash |
| `text_editable` | Page images with editable text boxes on top | `result.run_id` | `sulaide wait OPERATION_ID`, then `export download ... --run-id RUN_ID` |
| `full_editable` | Fully rebuilt editable shapes and text (slowest) | `result.run_id` | `sulaide wait OPERATION_ID`, then `export download ... --run-id RUN_ID` |

Editable modes take `--page-numbers 1,2,3` (comma separated); leave it empty only if the server accepts all pages. Never pass an operation ID as `--run-id`: it returns "可编辑导出任务不存在".

Export runs against Sulaide's existing project and credit rules. Never substitute a newer active version for the requested frozen version.

If the user wants a file that was already exported earlier instead of a fresh export, find it in the resource library: `sulaide resources list PROJECT_ID --resource-type export_pptx` then `sulaide resources download RESOURCE_VERSION_ID --output FILE.pptx` (see `references/resources.md`).
