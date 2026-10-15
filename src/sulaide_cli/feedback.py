"""`sulaide feedback` / `sulaide issue`: report problems to the Sulaide platform (redacted, not public).

Feedback goes to ``POST /api/agent/v1/feedback`` with the user's API key, so no GitHub account is
needed. Only the submitter and the Sulaide admins can see it; the status can be tracked with
``sulaide feedback --list`` or on the web at ``/app/feedback``.
"""
from __future__ import annotations

import os
import platform
import re
import sys

MAX_BODY = 6000
MAX_ERROR = 6000
MAX_TITLE = 200
TYPES = ("bug", "feature", "question")

_REDACTIONS = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+|basic\s+|token\s+)?[^\s,'\"]+"), r"\1\2<redacted>"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer <redacted>"),
    (re.compile(r"\bsul_[A-Za-z0-9_.-]{6,}"), "sul_<redacted>"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), "<redacted-github-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "<redacted-jwt>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), "<redacted-key>"),
    (re.compile(r"(?i)\b((?:api[_-]?key|secret|token|password|passwd)\s*[\"']?\s*[:=]\s*[\"']?)[^\s,'\"]+"), r"\1<redacted>"),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_TRUNCATED = "\n…（内容过长已截断）"


def redact(text: str, *, emails: bool = True) -> str:
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    key = os.environ.get("SULAIDE_API_KEY")
    if key and len(key) >= 6:
        text = text.replace(key, "<redacted>")
    if emails:
        text = _EMAIL.sub("<email>", text)
    return text


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - len(_TRUNCATED)].rstrip() + _TRUNCATED


def environment() -> dict:
    from .update import local_info
    from .cli import DEFAULT_BASE_URL
    info = local_info()
    base = (os.environ.get("SULAIDE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    return {
        "cli_version": str(info.get("version")),
        "cli_commit": (info.get("commit") or "")[:12] or None,
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": platform.python_version(),
        "base_url": base if base == DEFAULT_BASE_URL else "<custom>",
    }


def build(*, title: str | None, body: str | None, kind: str = "bug", error: str | None = None,
          keep_emails: bool = False) -> dict:
    if kind not in TYPES:
        raise ValueError("--type 只能是 bug、feature 或 question")
    desc = (body or "").strip()
    err = (error or "").strip()
    if not desc and not err:
        raise ValueError("请用 -m/--body 描述问题，或用 --error 附上错误输出")
    final_title = (title or "").strip() or (desc or err).splitlines()[0][:80]
    emails = not keep_emails
    return {
        "type": kind,
        "title": _truncate(redact(final_title, emails=emails), MAX_TITLE),
        "body": _truncate(redact(desc, emails=emails), MAX_BODY),
        "error_output": _truncate(redact(err, emails=emails), MAX_ERROR) if err else None,
        "client_meta": environment(),
    }


def submit(args, client=None) -> dict:
    from .cli import Client
    client = client or Client()
    if args.list:
        return client.request("GET", "/feedback", params={"page": args.page, "page_size": args.size})
    error = args.error
    if error == "-" or (error is None and args.stdin):
        error = sys.stdin.read()
    payload = build(title=args.title, body=args.body, kind=args.type, error=error, keep_emails=args.keep_emails)
    if args.dry_run:
        return {"submitted": False, "payload": payload, "message": "预览：未提交。去掉 --dry-run 即可提交。"}
    issue = client.request("POST", "/feedback", json_body=payload)
    return {
        "submitted": True,
        "id": issue.get("id"),
        "status": issue.get("status"),
        "title": issue.get("title"),
        "created_at": issue.get("created_at"),
        "message": "反馈已提交到速来得平台，仅你和速来得团队可见；可用 `sulaide feedback --list` 或网页「问题反馈」查看处理状态。",
    }
