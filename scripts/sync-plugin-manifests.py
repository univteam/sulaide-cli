#!/usr/bin/env python3
"""Generate every coding-agent plugin manifest from pyproject.toml.

skills/ is the single source of truth for skill content; all plugin formats
point at it (the plugin root is the repo root). Run without arguments to
rewrite the manifests, or with --check (CI) to fail when they are stale.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
NAME = "sulaide"
MARKETPLACE = "sulaide"
REPO = "https://github.com/univteam/sulaide-cli"
AUTHOR = {"name": "univteam", "url": "https://github.com/univteam"}
KEYWORDS = ["sulaide", "ppt", "presentation", "workflow"]


def manifests() -> dict[str, dict]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    desc = "速来PPT 工作流 skill：总览路由、登录，以及素材 → 分析 → 预览 → 导出四步法（需要 sulaide CLI）"
    common = {"name": NAME, "version": version, "description": desc, "author": AUTHOR,
              "homepage": REPO, "repository": REPO, "license": "Apache-2.0", "keywords": KEYWORDS}
    return {
        # Agent Plugins 1.0.0 portable manifest (Codex, Cursor, Copilot and other compatible hosts).
        "plugin.json": {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", **common},
        # Claude Code (also read by Copilot CLI and Codex as a compatible marketplace).
        ".claude-plugin/plugin.json": common,
        ".claude-plugin/marketplace.json": {
            "name": MARKETPLACE, "owner": AUTHOR, "description": desc,
            "plugins": [{"name": NAME, "source": "./", "description": desc, "version": version}],
        },
        # Codex marketplace + compatibility overlay.
        ".agents/plugins/marketplace.json": {
            "name": MARKETPLACE, "interface": {"displayName": "Sulaide"},
            "plugins": [{"name": NAME, "source": {"source": "local", "path": "./"},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"}],
        },
        ".codex-plugin/plugin.json": {**common, "skills": "./skills/", "interface": {
            "displayName": "Sulaide", "shortDescription": "速来PPT 四步法工作流",
            "developerName": "univteam", "category": "Productivity", "websiteURL": REPO}},
        # Cursor.
        ".cursor-plugin/plugin.json": {**common, "author": {"name": AUTHOR["name"]},
                                       "displayName": "Sulaide", "skills": "./skills/"},
        ".cursor-plugin/marketplace.json": {
            "name": MARKETPLACE, "owner": {"name": AUTHOR["name"]},
            "plugins": [{"name": NAME, "source": "./", "description": desc}],
        },
        # Gemini CLI extension (skills/ discovered automatically).
        "gemini-extension.json": {"name": NAME, "version": version, "description": desc},
    }


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    init = (ROOT / "src/sulaide_cli/__init__.py").read_text()
    stale = []
    if f'__version__ = "{project_version}"' not in init:
        stale.append("src/sulaide_cli/__init__.py (__version__ must equal pyproject version)")
    for rel, data in manifests().items():
        path = ROOT / rel
        text = render(data)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if not args.check:
        init_new = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{project_version}"', init)
        (ROOT / "src/sulaide_cli/__init__.py").write_text(init_new)
        print("plugin manifests updated")
        return 0
    if stale:
        print("stale plugin manifests; run `uv run scripts/sync-plugin-manifests.py`:\n  " + "\n  ".join(stale))
        return 1
    print("plugin manifests up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
