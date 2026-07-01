#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = "0.1.0"
EXCLUDED_PARTS = {".git", "dist", "runtime", "__pycache__", "eval-workspace"}
EXCLUDED_NAMES = {".DS_Store", ".env"}
SKILL_PREFIXES = {"SKILL.md", "LICENSE", "agents", "scripts", "references", "assets"}
SKILL_EXCLUDED = {"scripts/package_release.py", "scripts/release_audit.py"}


def files() -> list[pathlib.Path]:
    output: list[pathlib.Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in EXCLUDED_NAMES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts) or path.suffix in {".pyc"}:
            continue
        output.append(path)
    return sorted(output)


def write_zip(path: pathlib.Path, selected: list[pathlib.Path], include_root: bool) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in selected:
            relative = source.relative_to(ROOT)
            arcname = pathlib.Path(ROOT.name) / relative if include_root else relative
            archive.write(source, arcname.as_posix())


def main() -> int:
    DIST.mkdir(parents=True, exist_ok=True)
    all_files = files()
    skill_files = [
        path for path in all_files
        if path.relative_to(ROOT).parts[0] in SKILL_PREFIXES
        and path.relative_to(ROOT).as_posix() not in SKILL_EXCLUDED
    ]
    skill_path = DIST / "social-demand-signal-agent.skill"
    source_path = DIST / f"social-demand-signal-agent-v{VERSION}.zip"
    write_zip(skill_path, skill_files, include_root=False)
    write_zip(source_path, all_files, include_root=True)
    print(skill_path)
    print(source_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
