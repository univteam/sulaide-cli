# Sulaide project list（获取项目列表）

Use only the shared `sulaide` CLI. Do not call undocumented HTTP routes, invent project IDs, or put an API key on a command line, in a file, or in a handoff.

Listing or inspecting projects is read-only: answer the request without starting a new presentation. For continuation or changes, read `interaction.md` and enter the relevant checkpoint with the project's saved choices.

## 1. Confirm signed in first

`projects list` calls the authenticated Agent API, so run `sulaide auth status` first. If it fails with 401 or "Run `sulaide auth login`", follow `references/login.md` and come back.

## 2. Get the project list

```bash
sulaide projects list            # compact JSON on stdout
sulaide --pretty projects list   # indented, easier to read with the user
```

The response is `{"items": [...]}` (at most 100 projects). Each list item has `id` (the project ID — pass it to `projects show` and the stage guides as `PROJECT_ID`), `project_title`, `project_subtitle`, `stage`, `workflow_stage`, and `updated_at`. List items have no `project_id`, `title`, or `status` field; report exactly these fields as returned. Do not infer, renumber, or promise fields the response does not contain. If the list is empty, say so; create a project only when the user requested new work.

Common failures are listed in the error table in `SKILL.md`: 401 means re-login, 503 `AGENT_API_DISABLED` means the server has the Agent API turned off, and 429 means the per-account read limit was hit — wait and retry, do not poll in a loop.

## 3. Inspect one project when the user names it

```bash
sulaide projects show PROJECT_ID
```

Use this to verify the requested project exists and read `source_revision`, `settings` (language, target page count, narrative preference, master template), and active presentation ID. If the user names a project, match it against the actual list; ask only when multiple candidates or an imprecise description leave a real ambiguity. Do not make users repeat an unambiguous project choice or guess a `project_id`.

Read `layout show` for editing-version context and `preview show --version-id VERSION_ID` for an already selected presentation. An unpinned preview query may show an in-flight candidate rather than the version reviewed earlier, so it cannot silently renew confirmation for that earlier version.

## 4. Reuse or create

- **Reuse** when the user asks to continue, fix or re-export something that exists: take the item's `id` and enter the matching stage guide. Keep saved settings and explicit choices; a single export request does not reopen settings or analysis.
- **Create** only when the user wants new work and no existing project fits: `sulaide projects create --title "..." [--language zh|en]` (language defaults to `zh`; the other project settings are set with `source set`, see `references/source.md`). Keep the returned `project_id` and `request_id` in the handoff.
- Do not duplicate a project the user already asked about; list first and ask only if the target remains ambiguous.

When returning from website template/source upload, keep the same project ID, read the updated source/settings and resolve only differences. When resuming accepted work, inspect its original operation/run rather than creating another. A new conversation without a known confirmation re-establishes the relevant checkpoint after reading state; it does not rerun completed stages.

## 5. Handoff

Hand off the list itself (or the chosen project's ID) plus `source_revision` when the next stage needs it. Never print, log, or forward an API key or password, and never write project data into a file the user did not ask for.
