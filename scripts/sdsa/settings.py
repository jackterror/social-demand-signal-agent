from __future__ import annotations

import os
import pathlib
import re
import tempfile
from typing import Mapping


ENV_KEY = "SOCIALCRAWL_API_KEY"
KEY_PATTERN = re.compile(r"^sc_[A-Za-z0-9_-]{20,}$")


class SettingsError(ValueError):
    pass


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name:
            values[name] = value
    return values


def env_values(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return parse_env(path.read_text(encoding="utf-8"))


def runtime_api_key(path: pathlib.Path, environ: Mapping[str, str] | None = None) -> tuple[str, str]:
    active = os.environ if environ is None else environ
    process_value = str(active.get(ENV_KEY) or "").strip()
    if process_value:
        return process_value, "process"
    file_value = str(env_values(path).get(ENV_KEY) or "").strip()
    if file_value and file_value != "replace_with_your_key":
        return file_value, "env_file"
    return "", "missing"


def credential_status(path: pathlib.Path, environ: Mapping[str, str] | None = None) -> dict[str, object]:
    key, source = runtime_api_key(path, environ)
    return {"configured": bool(key), "source": source}


def validate_key(value: str) -> str:
    key = value.strip()
    if "\n" in key or "\r" in key or not KEY_PATTERN.fullmatch(key):
        raise SettingsError("SocialCrawl keys must start with sc_ and use the expected key format")
    return key


def _replace_env_line(text: str, name: str, value: str | None) -> str:
    output: list[str] = []
    replaced = False
    pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(name)}\s*=")
    for line in text.splitlines():
        if pattern.match(line):
            if value is not None and not replaced:
                output.append(f"{name}={value}")
                replaced = True
            continue
        output.append(line)
    if value is not None and not replaced:
        if output and output[-1].strip():
            output.append("")
        output.append(f"{name}={value}")
    return "\n".join(output).rstrip() + ("\n" if output else "")


def _atomic_write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        temporary_path = pathlib.Path(temporary)
        if temporary_path.exists():
            temporary_path.unlink()


def save_api_key(path: pathlib.Path, value: str) -> None:
    key = validate_key(value)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    _atomic_write(path, _replace_env_line(current, ENV_KEY, key))


def remove_api_key(path: pathlib.Path) -> None:
    if not path.exists():
        return
    current = path.read_text(encoding="utf-8")
    _atomic_write(path, _replace_env_line(current, ENV_KEY, None))
