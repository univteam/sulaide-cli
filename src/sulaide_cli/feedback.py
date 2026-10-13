"""`sulaide feedback` / `sulaide issue`: report problems as a GitHub issue (prefilled, redacted)."""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import webbrowser
from urllib.parse import urlencode

REPO = "univteam/sulaide-cli"
NEW_ISSUE_URL = f"https://github.com/{REPO}/issues/new"
MAX_BODY = 6000
TYPES = {"bug": ("bug", "Bug"), "feature": ("enhancement", "Feature"), "question": ("question", "Question")}

_REDACTIONS = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+|basic\s+|token\s+)?[^\s,'\"]+"), r"\1\2<redacted>"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer <redacted>"),
    (re.compile(r"\bsul_[A-Za-z0-9_-]{6,}"), "sul_<redacted>"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "<redacted-github-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "<redacted-jwt>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "<redacted-key>"),
    (re.compile(r"(?i)\b((?:api[_-]?key|secret|token|password|passwd)\s*[\"']?\s*[:=]\s*[\"']?)[^\s,'\"]+"), r"\1<redacted>"),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(text: str, *, emails: bool = True) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    key = os.environ.get("SULAIDE_API_KEY")
    if key and len(key) >= 6:
        text = text.replace(key, "<redacted>")
    if emails:
        text = _EMAIL.sub("<email>", text)
    return text


def environment() -> dict:
    from .update import local_info, _label
    from .cli import DEFAULT_BASE_URL
    base = (os.environ.get("SULAIDE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    return {
        "cli": _label(local_info()),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": platform.python_version(),
        "base_url": base if base == DEFAULT_BASE_URL else "<custom>",
    }


def build(*, title: str | None, body: str | None, kind: str = "bug", error: str | None = None,
          keep_emails: bool = False) -> dict:
    label, prefix = TYPES[kind]
    env = environment()
    desc = (body or "").strip() or "（请描述问题、复现步骤和期望结果）"
    parts = [f"## 描述\n\n{desc}"]
    if error and error.strip():
        parts.append(f"## 命令 / 错误输出\n\n```\n{error.strip()}\n```")
    parts.append("## 环境\n\n" + "\n".join(f"- {k}: {v}" for k, v in env.items()))
    text = redact("\n\n".join(parts), emails=not keep_emails)
    if len(text) > MAX_BODY:
        text = text[:MAX_BODY - 40].rstrip() + "\n\n…（内容过长已截断）"
    final_title = redact((title or "").strip() or desc.splitlines()[0][:80], emails=not keep_emails)
    final_title = f"[{prefix}] {final_title}"
    url = NEW_ISSUE_URL + "?" + urlencode({"title": final_title, "body": text, "labels": label})
    return {"title": final_title, "body": text, "label": label, "url": url, "environment": env}


def _gh_ready() -> bool:
    gh = shutil.which("gh")
    return bool(gh) and subprocess.run([gh, "auth", "status"], capture_output=True).returncode == 0


def submit(args) -> dict:
    error = args.error
    if error == "-" or (error is None and not sys.stdin.isatty() and args.stdin):
        error = sys.stdin.read()
    issue = build(title=args.title, body=args.body, kind=args.type, error=error, keep_emails=args.keep_emails)
    if args.gh:
        if not _gh_ready():
            raise ValueError("未找到已登录的 gh；去掉 --gh 改用浏览器提交，或先运行 `gh auth login`")
        cmd = ["gh", "issue", "create", "--repo", REPO, "--title", issue["title"], "--body", issue["body"]]
        result = subprocess.run(cmd + ["--label", issue["label"]], capture_output=True, text=True)
        if result.returncode != 0:  # labels need triage permission; retry without
            result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ValueError("gh issue create 失败：" + result.stderr.strip()[-500:])
        return {"created": True, "issue_url": result.stdout.strip().splitlines()[-1], "title": issue["title"]}
    opened = False if args.no_open else bool(webbrowser.open(issue["url"]))
    issue["opened"] = opened
    issue["message"] = ("已在浏览器打开预填好的 GitHub Issue 页面，确认内容后点击提交。" if opened
                        else "打开下面的链接，确认内容后在 GitHub 页面提交。")
    return issue
