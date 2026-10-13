# Feedback: reporting problems

Use `sulaide feedback` (alias `sulaide issue`) to send a problem report or suggestion to the public sulaide-cli GitHub repo.

When to offer it: a `sulaide` command fails in a way that is not the user's input (unexpected 5xx, crash, wrong output, missing feature), or the user says they want to report a problem or give feedback. Offer; do not file automatically.

Steps:
1. Draft from context: a short title, a description (what the user did, what happened, what they expected), and the failing command plus its error output.
2. Remove secrets yourself before showing the draft: API keys (`sul_...`), tokens, `Authorization` headers, passwords, signed download URLs, and personal data the user did not ask to include. The CLI also redacts these, but do not rely on that alone. Never include the contents of `~/.sulaide/auth.json`.
3. Show the user the exact title and body and ask for confirmation. The issue is public.
4. After the user confirms, run:
   `sulaide feedback --type bug|feature|question --title "..." -m "..." --error "..."` (use `--error -` to pipe long output via stdin).
   This opens a prefilled GitHub page; the user reviews and clicks submit. In a headless environment add `--no-open` and give the user the returned `url`.
5. Only use `--gh` (creates the issue immediately with the user's own logged-in gh) when the user explicitly asks for it after seeing the draft.

The CLI attaches CLI version/commit, OS and Python version, and the base URL only if it is the official default (otherwise `<custom>`). The body is truncated at about 6000 characters.
