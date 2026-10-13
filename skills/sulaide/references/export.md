# Sulaide PPTX export

Use the shared `sulaide` CLI and the exact frozen `presentation_version_id` and `manifest_hash` from preview.

1. Verify the selected version is the intended version and its page manifest is complete.
2. Start an export with `sulaide export start PROJECT_ID --version-id VERSION_ID --manifest-hash HASH --mode native` (or an explicitly requested editable mode).
3. Preserve the returned operation ID. If the outcome is uncertain, inspect that operation before retrying.
4. Download with `sulaide export download PROJECT_ID VERSION_ID HASH --output FILE.pptx`. The CLI will not overwrite an existing file and checks that the response is a PPTX package.
5. Report the file path, byte size, frozen version, and manifest hash. Opening or inspecting the deck is a separate validation step; do not claim visual fidelity without checking it.

Export runs against Sulaide's existing project and credit rules. Never substitute a newer active version for the requested frozen version.

If the user wants a file that was already exported earlier instead of a fresh export, find it in the resource library: `sulaide resources list PROJECT_ID --resource-type export_pptx` then `sulaide resources download RESOURCE_VERSION_ID --output FILE.pptx` (see `references/resources.md`).
