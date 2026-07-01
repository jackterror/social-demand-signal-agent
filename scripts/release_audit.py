#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Iterable


EXCLUDED_PARTS = {".git", "dist", "runtime", "__pycache__", "eval-workspace", "node_modules"}
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


def audit(root: pathlib.Path, forbidden: list[str]) -> dict[str, object]:
    failures: list[str] = []
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
        for pattern in forbidden:
            if pattern.lower() in text.lower():
                failures.append(f"forbidden content match {pattern!r}: {relative}")
        if path.name != ".env.example":
            for secret_pattern in SECRET_PATTERNS:
                if secret_pattern.search(text):
                    failures.append(f"possible secret: {relative}")
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
