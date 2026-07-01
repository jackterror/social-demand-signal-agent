from __future__ import annotations

import json
import pathlib
from typing import Any


REQUIRED_PATHS = (
    "profile_status",
    "company.name",
    "company.product",
    "company.description",
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


class ConfigError(ValueError):
    pass


def load_profile(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Profile not found: {path}")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Profile is not valid JSON: {exc}") from exc
    if not isinstance(profile, dict):
        raise ConfigError("Profile root must be an object")
    validate_profile(profile)
    return profile


def get_path(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_profile(profile: dict[str, Any]) -> None:
    errors: list[str] = []
    for dotted_path in REQUIRED_PATHS:
        value = get_path(profile, dotted_path)
        if value is None or value == "" or value == []:
            errors.append(f"missing required field: {dotted_path}")

    for dotted_path in (
        "audience.pain_points",
        "audience.intent_signals",
        "voice.attributes",
        "claims.approved",
        "claims.forbidden",
        "safety.exclusions",
        "safety.escalation_terms",
        "listening.queries",
        "listening.platforms",
    ):
        value = get_path(profile, dotted_path)
        if value is not None and not isinstance(value, list):
            errors.append(f"field must be a list: {dotted_path}")

    cta = str(get_path(profile, "offer.cta_url") or "")
    if cta and not cta.startswith(("https://", "http://")):
        errors.append("offer.cta_url must start with http:// or https://")

    minimum = get_path(profile, "experiment.minimum_sample_size")
    if minimum is not None and (not isinstance(minimum, int) or minimum < 1):
        errors.append("experiment.minimum_sample_size must be a positive integer")
    frequency = get_path(profile, "safety.max_responses_per_author_24h")
    if frequency is not None and (not isinstance(frequency, int) or frequency < 1):
        errors.append("safety.max_responses_per_author_24h must be a positive integer")
    for dotted_path in ("listening.freshness_minutes", "listening.max_items"):
        value = get_path(profile, dotted_path)
        if value is not None and (not isinstance(value, int) or value < 1):
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

    primary = get_path(profile, "experiment.primary_event")
    guardrail = get_path(profile, "experiment.guardrail_event")
    if primary and guardrail and primary == guardrail:
        errors.append("primary and guardrail events must be different")

    status = profile.get("profile_status")
    if status not in {"demo", "ready"}:
        errors.append("profile_status must be demo or ready")
    if status == "ready":
        placeholders = find_placeholders(profile)
        if placeholders:
            errors.append("ready profiles cannot contain onboarding placeholders")

    if errors:
        raise ConfigError("Profile validation failed:\n- " + "\n- ".join(errors))


def require_live_ready(profile: dict[str, Any]) -> None:
    validate_profile(profile)
    if profile.get("profile_status") != "ready":
        raise ConfigError("Live collection is blocked until profile_status is set to ready")


def find_placeholders(value: Any) -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            matches.extend(find_placeholders(child))
    elif isinstance(value, list):
        for child in value:
            matches.extend(find_placeholders(child))
    elif isinstance(value, str) and "replace with" in value.lower():
        matches.append(value)
    return matches


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "company": profile["company"]["name"],
        "product": profile["company"]["product"],
        "audience": profile["audience"]["description"],
        "queries": len(profile["listening"]["queries"]),
        "platforms": profile["listening"]["platforms"],
        "primary_event": profile["experiment"]["primary_event"],
        "guardrail_event": profile["experiment"]["guardrail_event"],
    }
