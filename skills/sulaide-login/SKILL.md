---
name: sulaide-login
description: Install the Sulaide CLI and sign a user in (register or log in) so agents can use the Sulaide Agent API. Use when `sulaide` is missing, `sulaide auth status` fails, a 401 occurs, or the user wants to create an account, rotate, or remove their API key.
---

# Sulaide login and API key（登录与 API Key）

The user types passwords and verification answers themselves. Never ask them to paste a password, captcha answer, email code, or API key into chat, and never put one on a command line, in a file you write, or in a handoff.

## 1. Check installation

1. Run `sulaide --help`. If the command is missing, install it: `uv tool install git+https://github.com/univteam/sulaide-cli.git`. If `uv` is missing, ask the user to install uv first (https://docs.astral.sh/uv/).
2. Run `sulaide auth status`. If it succeeds, the user is already signed in; report `authenticated_as` and stop.

## 2. Sign in (interactive, run in the user's terminal)

These commands prompt for secrets without echoing them. Ask the user to run them in their own terminal, or run them in an interactive terminal the user controls.

- Existing account: `sulaide auth login` (optionally `--username NAME`). Prompts for 用户名或邮箱 and 密码.
- New account: `sulaide auth register` (optionally `--username`, `--email`, `--invite-code`). It:
  1. prompts for username, email, password (twice, at least 6 characters), and an optional invite code;
  2. shows the privacy policy and terms versions and the register page URL; the user must read them and type `yes` to agree;
  3. if email verification is enabled, opens a captcha image (path printed on stderr), asks for the arithmetic answer, then sends a 6-digit code to the email and asks for it.

Both commands create a per-user Agent API key and save it to `~/.sulaide/auth.json` (directory `0700`, file `0600`). Re-running `login` replaces the saved key and revokes the previous one it created. The output reports `api_key_saved` and the key ID, not the secret.

## 3. Managed agents and CI

When a runtime cannot run interactive prompts, the user creates a key in the Sulaide web app (账户 → API Keys; the secret is shown once) and stores it as `SULAIDE_API_KEY` in that runtime's secret store. `SULAIDE_API_KEY` takes precedence over the saved key. Do not echo it, `export` it in visible shell history, or write it to project files.

`SULAIDE_BASE_URL` defaults to `https://www.sulide.com.cn`; only override it when the user names another deployment. Remote URLs must be HTTPS.

## 4. Verify

Run `sulaide auth status`. Success returns the capability contract and `authenticated_as` (username, `local API key`, or `environment API key`). Then hand off to the `sulaide-source` skill or the user's requested stage.

## Sign out / rotate

- `sulaide auth logout` deletes the local key file. To invalidate the key immediately, the user revokes it on the web API Keys page. If `SULAIDE_API_KEY` is set, it must also be removed from the environment.
- To rotate, run `sulaide auth login` again.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `sulaide: command not found` | Install with uv (step 1); ensure `~/.local/bin` is on `PATH` (`uv tool update-shell`) |
| 401 / exit 4 after login | Key revoked or a stale `SULAIDE_API_KEY` overrides the saved key; unset it or log in again |
| "两次输入的密码不一致" / "密码至少需要 6 个字符" | Re-run register and re-enter the password |
| "未同意条款，已取消注册" | The user must type `yes` after reading the terms |
| Captcha or email code rejected | Re-run register; check spam folder for the code |
| HTTP 503 `AGENT_API_DISABLED` | Server-side switch is off; login cannot fix it — tell the user and retry later |
| "SULAIDE_BASE_URL must use HTTPS" | Unset `SULAIDE_BASE_URL` |
