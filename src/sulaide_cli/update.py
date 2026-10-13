"""`sulaide update`: upgrade the CLI through uv, then refresh installed skills."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from importlib import metadata

import httpx

from . import __version__

DIST_NAME = "sulaide-cli"
REPO = "univteam/sulaide-cli"
GIT_SOURCE = f"git+https://github.com/{REPO}.git"
LATEST_COMMIT_API = f"https://api.github.com/repos/{REPO}/commits/main"
LATEST_PYPROJECT = f"https://raw.githubusercontent.com/{REPO}/main/pyproject.toml"


def local_info() -> dict:
    """Version and git commit of the running installation (commit only for git installs)."""
    commit = None
    try:
        raw = metadata.distribution(DIST_NAME).read_text("direct_url.json")
        if raw:
            commit = (json.loads(raw).get("vcs_info") or {}).get("commit_id")
    except (metadata.PackageNotFoundError, ValueError):
        pass
    return {"version": __version__, "commit": commit}


def latest_info() -> dict:
    with httpx.Client(timeout=15, headers={"Accept": "application/vnd.github+json"}) as client:
        sha = client.get(LATEST_COMMIT_API).raise_for_status().json()["sha"]
        text = client.get(LATEST_PYPROJECT).raise_for_status().text
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return {"version": match.group(1) if match else None, "commit": sha}


def check() -> dict:
    local, latest = local_info(), latest_info()
    if local["commit"]:
        available = local["commit"] != latest["commit"]
    else:
        available = local["version"] != latest["version"]
    return {"current": local, "latest": latest, "update_available": available,
            "message": "有新版本，运行 `sulaide update` 升级" if available else "已是最新版本"}


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise ValueError("未找到 uv。请先安装 uv（https://docs.astral.sh/uv/getting-started/installation/），"
                         f"然后运行 `uv tool install --force {GIT_SOURCE}`")
    return uv


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _installed_tool_name(uv: str) -> str | None:
    result = _run([uv, "tool", "list"])
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        name = line.split(" ", 1)[0].strip()
        if name in {DIST_NAME, "sulaide_cli"}:
            return name
    return None


def _new_info() -> dict | None:
    """Ask the (possibly replaced) installed binary for its version, so we see the new code."""
    exe = shutil.which("sulaide")
    cmd = [exe] if exe else [sys.executable, "-m", "sulaide_cli.cli"]
    result = _run([*cmd, "--version", "--json"])
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def _refresh_skills() -> dict:
    exe = shutil.which("sulaide")
    cmd = [exe] if exe else [sys.executable, "-m", "sulaide_cli.cli"]
    result = _run([*cmd, "skills", "update"])
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (result.stderr or result.stdout).strip()[-500:]}


def update(*, skills: bool = True) -> dict:
    uv = _uv()
    old = local_info()
    name = _installed_tool_name(uv)
    if name is None:
        raise ValueError(f"当前 sulaide 不是通过 `uv tool install` 安装的，无法自动升级。请运行 `uv tool install --force {GIT_SOURCE}`")
    steps = []
    upgraded = _run([uv, "tool", "upgrade", name])
    steps.append({"command": f"uv tool upgrade {name}", "ok": upgraded.returncode == 0})
    new = _new_info() if upgraded.returncode == 0 else None
    if new is None or new == old:
        forced = _run([uv, "tool", "install", "--force", GIT_SOURCE])
        steps.append({"command": f"uv tool install --force {GIT_SOURCE}", "ok": forced.returncode == 0})
        if forced.returncode != 0:
            raise ValueError("升级失败：" + (forced.stderr or forced.stdout).strip()[-800:])
        new = _new_info() or old
    changed = new != old
    result = {
        "old": old, "new": new, "changed": changed, "steps": steps,
        "message": f"sulaide {_label(old)} -> {_label(new)}" if changed else f"已是最新版本（{_label(new)}）",
    }
    if skills:
        result["skills"] = _refresh_skills()
    return result


def _label(info: dict) -> str:
    commit = (info.get("commit") or "")[:7]
    return f"{info.get('version')}" + (f"@{commit}" if commit else "")
