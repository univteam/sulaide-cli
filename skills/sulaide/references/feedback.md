# Feedback: reporting problems

Use `sulaide feedback` (alias `sulaide issue`) to send a problem report or suggestion to the Sulaide team. It is submitted to the Sulaide platform with the user's API key (no GitHub account needed) and is visible only to the user and Sulaide admins, not public.

When to offer it: a `sulaide` command fails in a way that is not the user's input (unexpected 5xx, crash, wrong output, missing feature), or the user says they want to report a problem or give feedback. Offer; do not file automatically.

Steps:
1. Draft from context: a short title, a description (what the user did, what happened, what they expected), and the failing command plus its error output.
2. Remove secrets yourself before showing the draft: API keys (`sul_...`), tokens, `Authorization` headers, passwords, signed download URLs, and personal data the user did not ask to include. The CLI and the server also redact these, but do not rely on that alone. Never include the contents of `~/.sulaide/auth.json`.
3. Show the user the exact title, description and error output and ask for confirmation. `sulaide feedback ... --dry-run` prints the exact redacted payload without submitting.
4. After the user confirms, run:
   `sulaide feedback --type bug|feature|question --title "..." -m "..." --error "..."` (use `--error -` to pipe long output via stdin).
   The result contains the feedback `id` and `status` (`open`).
5. To check progress: `sulaide feedback --list` returns the user's feedback with status `open` (待处理), `in_progress` (处理中), `resolved` (已解决) or `closed` (已关闭). On the web the same list is under 用户菜单 → 问题反馈 (`/app/feedback`).

The CLI attaches CLI version/commit, OS and Python version, and the base URL only if it is the official default (otherwise `<custom>`). Description and error output are each truncated at about 6000 characters. If the user is not logged in, ask them to run `sulaide auth login` first. The server allows about 10 submissions per hour per account.
