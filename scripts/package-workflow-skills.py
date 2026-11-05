#!/usr/bin/env python3
"""Package the reviewed public Sulaide skills as one versioned ZIP."""
from pathlib import Path
import argparse
import zipfile
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sulaide_cli.skills import PUBLIC_SKILL_FILES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "workflow-skills")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT / "skills"
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    archive = args.output / f"sulaide-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, files in PUBLIC_SKILL_FILES.items():
            for relative in files:
                path = source / name / relative
                if not path.is_file():
                    raise SystemExit(f"missing reviewed skill file: {path}")
                bundle.write(path, f"{name}/{relative}")
    print(f"Packaged {archive}")


if __name__ == "__main__":
    main()
