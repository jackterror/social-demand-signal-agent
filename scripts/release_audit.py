#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import zipfile
from typing import Iterable


EXCLUDED_PARTS = {".git", "dist", "runtime", "__pycache__", "eval-workspace", "node_modules"}
DEFAULT_FORBIDDEN = (
    "med" + "finder",
    "a" + "dhd",
    "medi" + "cation",
    "prescrip" + "tion",
    "health" + "care",
    "take" + "-home",
    "take" + " home",
)
ARCHIVE_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".sqlite3", ".pyc"}
SKILL_PREFIXES = {"SKILL.md", "LICENSE", "agents", "scripts", "references", "assets"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"),
    re.compile(r"sc_[A-Za-z0-9]{24,}"),
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def iter_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        yield path


def scan_text(label: str, text: str, forbidden: list[str], failures: list[str], check_secrets: bool = True) -> None:
    lowered = text.lower()
    for pattern in forbidden:
        if pattern.lower() in lowered:
            failures.append(f"forbidden content match {pattern!r}: {label}")
    if check_secrets:
        for secret_pattern in SECRET_PATTERNS:
            if secret_pattern.search(text):
                failures.append(f"possible secret: {label}")


def audit_archives(root: pathlib.Path, forbidden: list[str], failures: list[str]) -> None:
    dist = root / "dist"
    if not dist.exists():
        return
    for archive_path in sorted([*dist.glob("*.zip"), *dist.glob("*.skill")]):
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for name in archive.namelist():
                    first = pathlib.PurePosixPath(name).parts[0]
                    if archive_path.suffix == ".skill" and first not in SKILL_PREFIXES:
                        failures.append(f"repository-only file in skill archive: {name}")
                    lowered_name = name.lower()
                    for pattern in forbidden:
                        if pattern.lower() in lowered_name:
                            failures.append(f"forbidden filename match {pattern!r}: {archive_path.name}:{name}")
                    if pathlib.PurePosixPath(name).suffix.lower() in ARCHIVE_BINARY_SUFFIXES:
                        continue
                    try:
                        text = archive.read(name).decode("utf-8")
                    except (KeyError, UnicodeDecodeError):
                        continue
                    scan_text(
                        f"{archive_path.name}:{name}",
                        text,
                        forbidden,
                        failures,
                        check_secrets=not name.endswith(".env.example"),
                    )
        except zipfile.BadZipFile:
            failures.append(f"invalid release archive: {archive_path.name}")


def audit_git_history(root: pathlib.Path, forbidden: list[str], failures: list[str]) -> None:
    if not (root / ".git").exists():
        return
    result = subprocess.run(
        ["git", "log", "--all", "--format=commit:%H%n%B", "--name-status", "-p", "--no-ext-diff"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        failures.append("could not inspect Git history")
        return
    scan_text("Git history", result.stdout, forbidden, failures)


def audit(root: pathlib.Path, forbidden: list[str]) -> dict[str, object]:
    failures: list[str] = []
    forbidden = list(dict.fromkeys([*DEFAULT_FORBIDDEN, *forbidden]))
    files = list(iter_files(root))
    for path in files:
        relative = path.relative_to(root)
        lower_name = str(relative).lower()
        for pattern in forbidden:
            if pattern.lower() in lower_name:
                failures.append(f"forbidden filename match {pattern!r}: {relative}")
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".zip", ".skill", ".sqlite3"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scan_text(str(relative), text, forbidden, failures, check_secrets=path.name != ".env.example")
        if path.suffix.lower() == ".md":
            for target in MARKDOWN_LINK.findall(text):
                clean = target.split("#", 1)[0].strip()
                if not clean or clean.startswith(("http://", "https://", "mailto:")):
                    continue
                linked = (path.parent / clean).resolve()
                if not linked.exists():
                    failures.append(f"broken local link {target!r}: {relative}")
    required = [
        "SKILL.md",
        "README.md",
        "LICENSE",
        ".env.example",
        "package.json",
        "CHANGELOG.md",
        "PACKAGE-DESCRIPTION.md",
        "CREATOR.md",
        "SOURCES.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "GITHUB-PUBLISHING.md",
        "RELEASE-NOTES.md",
        "tools/capture-release-assets.mjs",
        "docs/social-preview.html",
        "scripts/signal_agent.py",
        "assets/company-profile.schema.json",
    ]
    for item in required:
        if not (root / item).exists():
            failures.append(f"missing required file: {item}")
    audit_archives(root, forbidden, failures)
    audit_git_history(root, forbidden, failures)
    return {"ok": not failures, "files_checked": len(files), "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a release tree for secrets, required files, and forbidden provenance.")
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("--forbid", action="append", default=[])
    args = parser.parse_args()
    result = audit(args.root.resolve(), args.forbid)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
