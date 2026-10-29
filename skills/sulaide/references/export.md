# Deliver ordinary PPTX

Read `interaction.md`. Export the presentation version the user actually reviewed or explicitly requested; keep its `presentation_version_id` and `manifest_hash`. Do not substitute a newer active version.

## Ordinary PPT in this release

Use **普通 PPT (`native`)**, preserving the current page appearance. Combine export confirmation with the preview's “continue or adjust” question. After that offer, the user's “继续” is sufficient; do not ask again for a mode or page range. A direct ordinary-PPT export request enters this stage immediately. An explicit full-auto request may export ordinary PPT without another checkpoint.

Editable export is deferred. Do not start `text_editable` or `full_editable`, resolve conversion page ranges, or promise editable text/objects. If the user explicitly requests editable output, explain that the current skill supports ordinary PPT only and wait for them to accept that alternative. This also applies in full-auto mode: do not silently substitute native output. The underlying CLI/server may expose more modes; that does not expand this release's conversation scope.

## Export the reviewed version

1. Read `sulaide preview show PROJECT_ID --version-id VERSION_ID` and ensure its identity matches the selected version/hash. Run `sulaide export check PROJECT_ID --version-id VERSION_ID --manifest-hash HASH`.
2. Explain any missing/older images or quality warnings and their effects. Website warnings do not automatically block export; let the user continue with the disclosed result or return to adjustments. Hard service errors, such as an invalid version or denied access, must be resolved. Never claim all pages are complete because export is allowed.
3. After export is authorized, run `sulaide export start PROJECT_ID --version-id VERSION_ID --manifest-hash HASH --mode native`. Do not pass conversion page numbers.
4. Preserve the operation ID. Native output has `result.run_id: null` and `result.download.requires_run_id: false`. After a timeout or lost response, recover the accepted operation rather than submitting a replacement.
5. Download with `sulaide export download PROJECT_ID VERSION_ID HASH --output FILE.pptx`, without `--run-id`. The CLI refuses to overwrite an existing file and checks that it received a real PPTX package.
6. Return a usable local file link, size and any page-level limitations. Keep the frozen version/hash for later recovery; there is no need to make the user interpret those fields. Successful download and visual fidelity are separate facts; ordinary output does not promise that page-image text or objects are editable.

If the user wants an already exported file, find it with `sulaide resources list PROJECT_ID --resource-type export_pptx` and download its resource version through `resources.md`. This may retrieve an existing editable file without starting conversion. Do not generate a new export unnecessarily.
