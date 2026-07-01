from __future__ import annotations

import copy
import json
import os
import pathlib
import shutil
import tempfile
from typing import Any


SCHEMA_VERSION = 2
PROFILE_STATUSES = {"setup", "demo", "ready"}
REQUIRED_PATHS = (
    "schema_version",
    "profile_status",
    "company.name",
    "company.industry",
    "company.product",
    "company.description",
    "company.website",
    "audience.description",
    "audience.pain_points",
    "audience.intent_signals",
    "offer.summary",
    "offer.cta_url",
    "voice.attributes",
    "disclosure",
    "claims.approved",
    "claims.forbidden",
    "safety.exclusions",
    "safety.escalation_terms",
    "safety.max_responses_per_author_24h",
    "listening.queries",
    "listening.platforms",
    "listening.freshness_minutes",
    "listening.max_items",
    "response_families",
    "experiment.primary_event",
    "experiment.guardrail_event",
    "experiment.minimum_sample_size",
)
LIST_PATHS = (
    "audience.pain_points",
    "audience.intent_signals",
    "voice.attributes",
    "claims.approved",
    "claims.forbidden",
    "safety.exclusions",
    "safety.escalation_terms",
    "listening.queries",
    "listening.platforms",
)


class ConfigError(ValueError):
    pass


def read_profile(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Profile not found: {path}")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Profile is not valid JSON: {exc}") from exc
    if not isinstance(profile, dict):
        raise ConfigError("Profile root must be an object")
    return profile


def load_profile(path: pathlib.Path) -> dict[str, Any]:
    profile = read_profile(path)
    validate_profile(profile)
    return profile


def get_path(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validation_errors(profile: dict[str, Any], require_ready: bool = False) -> list[str]:
    errors: list[str] = []
    for dotted_path in REQUIRED_PATHS:
        value = get_path(profile, dotted_path)
        if value is None or value == "" or value == []:
            errors.append(f"Missing required field: {dotted_path}")

    for dotted_path in LIST_PATHS:
        value = get_path(profile, dotted_path)
        if value is not None and not isinstance(value, list):
            errors.append(f"Field must be a list: {dotted_path}")
        elif isinstance(value, list) and any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"List entries must be non-empty text: {dotted_path}")

    version = profile.get("schema_version")
    if version is not None and (not isinstance(version, int) or version != SCHEMA_VERSION):
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    for dotted_path in ("company.website", "offer.cta_url"):
        url = str(get_path(profile, dotted_path) or "")
        if url and not url.startswith(("https://", "http://")):
            errors.append(f"{dotted_path} must start with http:// or https://")

    for dotted_path in (
        "safety.max_responses_per_author_24h",
        "listening.freshness_minutes",
        "listening.max_items",
        "experiment.minimum_sample_size",
    ):
        value = get_path(profile, dotted_path)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 1):
            errors.append(f"{dotted_path} must be a positive integer")

    families = profile.get("response_families")
    if families is not None:
        if not isinstance(families, list) or not families:
            errors.append("response_families must be a non-empty list")
        else:
            for index, family in enumerate(families):
                if not isinstance(family, dict):
                    errors.append(f"response_families[{index}] must be an object")
                    continue
                for key in ("name", "signals", "hypothesis_a", "hypothesis_b"):
                    if not family.get(key):
                        errors.append(f"response_families[{index}].{key} is required")
                if family.get("signals") is not None and not isinstance(family.get("signals"), list):
                    errors.append(f"response_families[{index}].signals must be a list")

    primary = get_path(profile, "experiment.primary_event")
    guardrail = get_path(profile, "experiment.guardrail_event")
    if primary and guardrail and primary == guardrail:
        errors.append("Primary and guardrail events must be different")

    status = profile.get("profile_status")
    if status not in PROFILE_STATUSES:
        errors.append("profile_status must be setup, demo, or ready")
    if require_ready and status != "ready":
        errors.append("Profile status is not ready")
    if require_ready or status == "ready":
        placeholders = find_placeholders(profile)
        if placeholders:
            errors.append("Ready profiles cannot contain onboarding placeholders")
    return errors


def validate_profile(profile: dict[str, Any], require_ready: bool = False) -> None:
    errors = validation_errors(profile, require_ready=require_ready)
    if errors:
        raise ConfigError("Profile validation failed:\n- " + "\n- ".join(errors))


def require_live_ready(profile: dict[str, Any]) -> None:
    validate_profile(profile, require_ready=True)


def find_placeholders(value: Any) -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            matches.extend(find_placeholders(child))
    elif isinstance(value, list):
        for child in value:
            matches.extend(find_placeholders(child))
    elif isinstance(value, str) and value.lower().startswith("replace with"):
        matches.append(value)
    return matches


def setup_status(profile: dict[str, Any], credential_configured: bool) -> dict[str, Any]:
    errors = validation_errors(profile, require_ready=False)
    placeholders = find_placeholders(profile)
    profile_ready = profile.get("profile_status") == "ready" and not errors and not placeholders
    return {
        "profile_ready": profile_ready,
        "provider_ready": credential_configured,
        "ready_to_listen": profile_ready and credential_configured,
        "profile_status": str(profile.get("profile_status") or "setup"),
        "errors": errors,
        "placeholder_count": len(placeholders),
    }


def migrate_profile(profile: dict[str, Any]) -> tuple[dict[str, Any], bool, int]:
    migrated = copy.deepcopy(profile)
    previous = migrated.get("schema_version")
    old_version = previous if isinstance(previous, int) else 1
    changed = old_version != SCHEMA_VERSION
    company = migrated.setdefault("company", {})
    if "industry" not in company:
        company["industry"] = ""
        changed = True
    if "website" not in company:
        company["website"] = ""
        changed = True
    migrated["schema_version"] = SCHEMA_VERSION
    if changed and migrated.get("profile_status") != "setup":
        migrated["profile_status"] = "setup"
    return migrated, changed, old_version


def atomic_write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary_path = pathlib.Path(temporary)
        if temporary_path.exists():
            temporary_path.unlink()


def backup_profile(path: pathlib.Path, version: int | str = "current") -> pathlib.Path | None:
    if not path.exists():
        return None
    candidate = path.with_name(f"{path.stem}.v{version}.backup{path.suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}.v{version}.backup-{counter}{path.suffix}")
        counter += 1
    shutil.copyfile(path, candidate)
    return candidate


def ensure_profile(path: pathlib.Path, template_path: pathlib.Path) -> tuple[dict[str, Any], pathlib.Path | None]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, path)
    profile = read_profile(path)
    migrated, changed, old_version = migrate_profile(profile)
    backup = None
    if changed:
        backup = backup_profile(path, old_version)
        atomic_write_json(path, migrated)
    return migrated, backup


def save_profile(path: pathlib.Path, profile: dict[str, Any], complete: bool = False) -> dict[str, Any]:
    migrated, _, _ = migrate_profile(profile)
    migrated["profile_status"] = "ready" if complete else "setup"
    if complete:
        validate_profile(migrated, require_ready=True)
    atomic_write_json(path, migrated)
    return migrated


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "company": get_path(profile, "company.name") or "Setup required",
        "industry": get_path(profile, "company.industry") or "",
        "product": get_path(profile, "company.product") or "",
        "audience": get_path(profile, "audience.description") or "",
        "queries": len(get_path(profile, "listening.queries") or []),
        "platforms": get_path(profile, "listening.platforms") or [],
        "primary_event": get_path(profile, "experiment.primary_event") or "qualified_action",
        "guardrail_event": get_path(profile, "experiment.guardrail_event") or "negative_feedback",
    }
