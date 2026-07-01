from __future__ import annotations

import hashlib
import re
import datetime as dt
from typing import Any


def normalize_terms(items: list[Any]) -> list[str]:
    return [str(item).strip().lower() for item in items if str(item).strip()]


def lexical_score(text: str, terms: list[str]) -> float:
    lower = text.lower()
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if term in lower)
    return min(1.0, matches / max(1, min(3, len(terms))))


def route_signal(signal: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    text = str(signal.get("text") or "")
    pain_terms = normalize_terms(profile["audience"]["pain_points"])
    intent_terms = normalize_terms(profile["audience"]["intent_signals"])
    exclusion_terms = normalize_terms(profile["safety"]["exclusions"])
    escalation_terms = normalize_terms(profile["safety"]["escalation_terms"])

    exclusion_hits = [term for term in exclusion_terms if term in text.lower()]
    escalation_hits = [term for term in escalation_terms if term in text.lower()]
    pain_score = lexical_score(text, pain_terms)
    intent_score = lexical_score(text, intent_terms)
    relevance_score = round((pain_score * 0.55) + (intent_score * 0.45), 3)
    freshness_status = signal_freshness(signal, int(profile["listening"]["freshness_minutes"]))

    if signal.get("source_type") == "socialcrawl" and freshness_status != "fresh":
        route = "suppress"
    elif freshness_status == "stale":
        route = "suppress"
    elif escalation_hits:
        route = "escalate"
    elif exclusion_hits or relevance_score == 0:
        route = "suppress"
    else:
        route = "review"

    family = infer_message_family(text, profile)
    assigned_variant = assign_variant(str(signal["id"]), family)
    return {
        **signal,
        "relevance_score": relevance_score,
        "route": route,
        "route_reasons": {
            "exclusion_hits": exclusion_hits,
            "escalation_hits": escalation_hits,
            "pain_score": pain_score,
            "intent_score": intent_score,
            "freshness_status": freshness_status,
        },
        "message_family": family,
        "assigned_variant": assigned_variant,
        "agent_status": "pending" if route == "review" else "not_requested",
    }


def infer_message_family(text: str, profile: dict[str, Any]) -> str:
    families = profile.get("response_families") or []
    lower = text.lower()
    for family in families:
        if not isinstance(family, dict):
            continue
        terms = normalize_terms(family.get("signals") or [])
        if any(term in lower for term in terms):
            return slug(str(family.get("name") or "general"))
    return "general"


def assign_variant(signal_id: str, family: str) -> str:
    digest = hashlib.sha256(f"{family}|{signal_id}".encode("utf-8")).digest()
    return "a" if digest[0] % 2 == 0 else "b"


def signal_freshness(signal: dict[str, Any], limit_minutes: int) -> str:
    if signal.get("data_label") == "fixture":
        return "fixture"
    value = str(signal.get("published_at") or "").strip()
    if not value:
        return "unknown"
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        published = dt.datetime.fromisoformat(value)
    except ValueError:
        return "unknown"
    if published.tzinfo is None:
        published = published.replace(tzinfo=dt.timezone.utc)
    age = (dt.datetime.now(dt.timezone.utc) - published.astimezone(dt.timezone.utc)).total_seconds() / 60
    return "fresh" if age <= limit_minutes else "stale"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "general"


def process_signals(signals: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [route_signal(signal, profile) for signal in signals]
