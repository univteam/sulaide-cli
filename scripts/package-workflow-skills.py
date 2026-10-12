#!/usr/bin/env python3
"""Package the four public Sulaide workflow skills independently."""
from pathlib import Path
import argparse
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("sulaide-source", "sulaide-analysis", "sulaide-preview", "sulaide-export")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "workflow-skills")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name in SKILLS:
        source = ROOT / "skills" / name
        skill_file = source / "SKILL.md"
        if not skill_file.is_file():
            raise SystemExit(f"missing skill definition: {skill_file}")
        archive = args.output / f"{name}-0.1.0.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(skill_file, f"{name}/SKILL.md")
    print(f"Packaged {len(SKILLS)} skills in {args.output}")


if __name__ == "__main__":
    main()
