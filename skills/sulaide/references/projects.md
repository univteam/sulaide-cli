# Sulaide project list（获取项目列表）

Use only the shared `sulaide` CLI. Do not call undocumented HTTP routes, invent project IDs, or put an API key on a command line, in a file, or in a handoff.

## 1. Confirm signed in first

`projects list` calls the authenticated Agent API, so run `sulaide auth status` first. If it fails with 401 or "Run `sulaide auth login`", follow `references/login.md` and come back.

## 2. Get the project list

```bash
sulaide projects list            # compact JSON on stdout
sulaide --pretty projects list   # indented, easier to read with the user
```

Report exactly what the server returns: each project's `project_id`, title, status, and any other fields present. Do not infer, renumber, or promise fields the response does not contain. If the list is empty, say so plainly and move on to creating a project (step 4).

Common failures are listed in the error table in `SKILL.md`: 401 means re-login, 503 `AGENT_API_DISABLED` means the server has the Agent API turned off, and 429 means the per-account read limit was hit — wait and retry, do not poll in a loop.

## 3. Inspect one project when the user names it

```bash
sulaide projects show PROJECT_ID
```

Use this to confirm a project before reusing it: check it exists, and read `source_revision` / presentation state from the response. If the user describes a project by title rather than ID, match it against the titles from `projects list` and confirm the choice with the user before acting. Never guess a `project_id`.

## 4. Reuse or create

- **Reuse** when the user asks to continue, fix, re-export, or list something that already exists: take the `project_id` from the list and hand it to the matching stage guide (`references/source.md`, `references/analysis.md`, `references/preview.md`, `references/export.md`, or `references/resources.md`).
- **Create** only when the user wants new work and no existing project fits: `sulaide projects create --title "..."`. Keep the returned `project_id` and `request_id` in the handoff.
- Creating duplicates a project the user already asked about is a real mistake; when in doubt, list first and confirm with the user.

## 5. Handoff

Hand off the list itself (or the chosen project's ID) plus `source_revision` when the next stage needs it. Never print, log, or forward an API key or password, and never write project data into a file the user did not ask for.
