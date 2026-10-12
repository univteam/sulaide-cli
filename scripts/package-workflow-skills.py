#!/usr/bin/env python3
"""Package the single public Sulaide skill (SKILL.md plus references/) as a zip."""
from pathlib import Path
import argparse
import zipfile

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
SKILL = "sulaide"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "workflow-skills")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT / "skills" / SKILL
    if not (source / "SKILL.md").is_file():
        raise SystemExit(f"missing skill definition: {source / 'SKILL.md'}")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    archive = args.output / f"{SKILL}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                bundle.write(path, f"{SKILL}/{path.relative_to(source).as_posix()}")
    print(f"Packaged {archive}")


if __name__ == "__main__":
    main()
