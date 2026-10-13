# Sulaide source preparation

Use the shared `sulaide` CLI. Do not call undocumented HTTP routes or write the API key into a command, file, prompt, or handoff.

1. Check `sulaide auth status`, then get the project list with `sulaide projects list` (see `references/projects.md` for reuse-vs-create rules).
2. Reuse the requested project, or create one with `sulaide projects create --title "..."`. Keep the returned `project_id` and `request_id` in the handoff.
3. Read the source material, preserve its facts and numbers, and submit it with `sulaide source set PROJECT_ID --file PATH --expected-revision REVISION` (or `--text TEXT`). The first version supports UTF-8 text input; scanned files, PDF, DOCX, PPTX, spreadsheets, and image OCR require the Sulaide web upload flow.
4. Confirm the returned source revision and warnings. Do not claim source preparation succeeded unless the server returns a saved revision.

Return `project_id`, `source_revision`, source filename, and any extraction limits. If a request times out, reuse its request ID or inspect the operation; do not submit the same material as a new request automatically.
