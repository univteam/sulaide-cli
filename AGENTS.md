# AGENTS.md

## If the user asks you to set up / install sulaide (帮我 setup)

Follow the numbered steps in README.md, section "给 AI 助手的安装说明 / For AI agents". Short version:

1. `uv --version` (install uv if missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`, Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`)
2. `uv tool install git+https://github.com/univteam/sulaide-cli.git`
3. `sulaide --version`
4. `sulaide skills install --agent <claude|codex|cursor|gemini|copilot|opencode|windsurf|amp|pi|hermes|agents>`
5. The user runs `sulaide auth login` (or `sulaide auth register`) in their own terminal, or sets `SULAIDE_API_KEY` themselves. Never ask for passwords or keys in chat; never read `~/.sulaide/auth.json`.
6. `sulaide auth status` and `sulaide credits --human`
7. If `sulaide` is not found: `uv tool update-shell`, then open a new terminal.
8. Later upgrades: `sulaide update`.

## If you are developing this repository

- `uv sync` then `uv run pytest`.
- `skills/` is the single skill source; after changing the version in `pyproject.toml` run `uv run scripts/sync-plugin-manifests.py`.
- This repo is public: do not add internal or non-production environment addresses, credentials, or links to private repositories.
