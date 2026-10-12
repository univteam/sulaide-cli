"""Install the bundled Sulaide workflow skills into coding-agent skill directories."""
from __future__ import annotations

import os
import shutil
from importlib import resources
from pathlib import Path

from . import __version__

SKILL_NAMES = ("sulaide-source", "sulaide-analysis", "sulaide-preview", "sulaide-export")
MARKER = ".sulaide-skill"

# agent -> (detection dir, skills dir), both relative to the home directory.
# Agents with their own plugin system can also use the plugin (see README).
AGENTS: dict[str, tuple[str, str]] = {
    "claude": (".claude", ".claude/skills"),
    "codex": (".codex", ".codex/skills"),
    "cursor": (".cursor", ".cursor/skills"),
    "gemini": (".gemini", ".gemini/skills"),
    "copilot": (".copilot", ".copilot/skills"),
    "opencode": (".config/opencode", ".config/opencode/skills"),
    "windsurf": (".codeium/windsurf", ".codeium/windsurf/skills"),
    "amp": (".config/amp", ".config/agents/skills"),
    "pi": (".pi", ".pi/agent/skills"),
    "hermes": (".hermes", ".hermes/skills/sulaide"),
    "agents": (".agents", ".agents/skills"),
}


def _home() -> Path:
    return Path(os.environ.get("SULAIDE_SKILLS_HOME") or Path.home())


def bundled_skills_root() -> Path:
    """Return the directory holding the packaged skills (wheel data or repo checkout)."""
    try:
        root = Path(str(resources.files("sulaide_cli") / "_skills"))
        if (root / SKILL_NAMES[0] / "SKILL.md").is_file():
            return root
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    checkout = Path(__file__).resolve().parents[2] / "skills"
    if (checkout / SKILL_NAMES[0] / "SKILL.md").is_file():
        return checkout
    raise FileNotFoundError("bundled skills not found; reinstall sulaide-cli")


def detected_agents() -> list[str]:
    home = _home()
    return [name for name, (probe, _) in AGENTS.items() if (home / probe).is_dir()]


def _target(agent: str) -> Path:
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}; choose from {', '.join(AGENTS)}")
    return _home() / AGENTS[agent][1]


def _installed_version(path: Path) -> str | None:
    marker = path / MARKER
    return marker.read_text(encoding="utf-8").strip() if marker.is_file() else None


def install(agents: list[str], *, force: bool = False) -> dict:
    source = bundled_skills_root()
    results = []
    for agent in agents:
        base = _target(agent)
        for name in SKILL_NAMES:
            dest = base / name
            if dest.exists() or dest.is_symlink():
                if _installed_version(dest) is None and not force:
                    results.append({"agent": agent, "skill": name, "status": "skipped_foreign", "path": str(dest)})
                    continue
                if dest.is_symlink() or dest.is_file():
                    dest.unlink()
                else:
                    shutil.rmtree(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source / name, dest, ignore=shutil.ignore_patterns("__pycache__"))
            (dest / MARKER).write_text(__version__ + "\n", encoding="utf-8")
            results.append({"agent": agent, "skill": name, "status": "installed", "version": __version__, "path": str(dest)})
    return {"version": __version__, "results": results}


def installed_agents() -> list[str]:
    return [a for a in AGENTS if any(_installed_version(_target(a) / n) for n in SKILL_NAMES)]


def update() -> dict:
    agents = installed_agents()
    if not agents:
        return {"version": __version__, "results": [], "message": "no agents have Sulaide skills installed; run `sulaide skills install`"}
    return install(agents)


def uninstall(agents: list[str]) -> dict:
    results = []
    for agent in agents:
        for name in SKILL_NAMES:
            dest = _target(agent) / name
            if _installed_version(dest) is not None:
                shutil.rmtree(dest)
                results.append({"agent": agent, "skill": name, "status": "removed"})
    return {"results": results}


def status() -> dict:
    detected = set(detected_agents())
    rows = []
    for agent in AGENTS:
        base = _target(agent)
        rows.append({"agent": agent, "detected": agent in detected, "path": str(base),
                     "skills": {n: _installed_version(base / n) for n in SKILL_NAMES}})
    return {"version": __version__, "skills": list(SKILL_NAMES), "agents": rows}


def resolve_agents(agent: list[str] | None, all_agents: bool) -> list[str]:
    if all_agents:
        return list(AGENTS)
    if agent:
        for a in agent:
            _target(a)
        return agent
    found = detected_agents()
    if not found:
        raise ValueError("no coding agent detected; pass --agent NAME or --all")
    return found
