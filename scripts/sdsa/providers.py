from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request
from typing import Any


SOCIALCRAWL_BASE = "https://www.socialcrawl.dev/v1"


class ProviderError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def stable_id(platform: str, url: str, text: str) -> str:
    payload = f"{platform}|{url}|{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


def normalize_record(record: dict[str, Any], source_type: str, data_label: str) -> dict[str, Any] | None:
    content = record.get("content") if isinstance(record.get("content"), dict) else {}
    author = record.get("author") if isinstance(record.get("author"), dict) else {}
    text = first_present(
        record.get("text"),
        content.get("text"),
        record.get("title"),
        record.get("description"),
        record.get("snippet"),
    )
    if not isinstance(text, str) or len(text.strip().split()) < 3:
        return None
    platform = str(first_present(record.get("platform"), source_type, "unknown") or "unknown")
    url = str(first_present(record.get("url"), record.get("source_url"), "") or "")
    return {
        "id": str(first_present(record.get("id"), stable_id(platform, url, text))),
        "source_type": source_type,
        "data_label": data_label,
        "platform": platform,
        "source_url": url,
        "author": str(first_present(author.get("username"), author.get("display_name"), record.get("author"), "unknown") or "unknown"),
        "published_at": str(first_present(record.get("published_at"), record.get("created_at"), "") or ""),
        "query": str(record.get("query") or ""),
        "text": text.strip(),
        "raw": record,
    }


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def extract_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("items", "results", "mentions", "posts", "comments"):
        if isinstance(data.get(key), list):
            return [item for item in data[key] if isinstance(item, dict)]
    flattened: list[dict[str, Any]] = []
    for value in data.values():
        if isinstance(value, list):
            flattened.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            flattened.extend(extract_items(value))
    return flattened


def extract_everywhere_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    records: list[dict[str, Any]] = []
    for item in data.get("items", []):
        if not isinstance(item, dict):
            continue
        source_items = item.get("source_items")
        if not isinstance(source_items, list):
            records.append(item)
            continue
        for source in source_items:
            if not isinstance(source, dict):
                continue
            record = dict(source)
            record.setdefault("text", first_present(item.get("text"), item.get("title"), item.get("snippet")))
            record.setdefault("query", payload.get("query", ""))
            records.append(record)
    return records


def load_json_records(path: pathlib.Path, data_label: str = "observed") -> list[dict[str, Any]]:
    if not path.exists():
        raise ProviderError(f"Input file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Input file is not valid JSON: {exc}") from exc
    records = payload if isinstance(payload, list) else extract_items(payload)
    normalized = [normalize_record(item, "json", data_label) for item in records]
    return [item for item in normalized if item]


def socialcrawl_request(
    path: str,
    api_key: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    url = f"{SOCIALCRAWL_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"x-api-key": api_key, "accept": "application/json"}
    if payload is not None:
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ProviderError(f"Live provider request failed: {type(exc).__name__}") from exc


def collect_socialcrawl(
    api_key: str,
    queries: list[str],
    platforms: list[str],
    max_items: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not api_key:
        raise ProviderError("SOCIALCRAWL_API_KEY is required for live collection")
    signals: list[dict[str, Any]] = []
    logs: list[str] = []
    for query in queries:
        payload = socialcrawl_request(
            "/search/everywhere",
            api_key,
            params={"query": query, "sources": ",".join("x" if item.lower() == "twitter" else item.lower() for item in platforms)},
        )
        records = extract_everywhere_records(payload)
        for record in records:
            record.setdefault("platform", first_present(record.get("source"), payload.get("platform"), "socialcrawl"))
            record.setdefault("query", query)
            normalized = normalize_record(record, "socialcrawl", "observed")
            if normalized and normalized.get("source_url"):
                signals.append(normalized)
        logs.append(f"query {query!r}: {len(records)} record(s)")
    return dedupe(signals)[:max_items], logs


def test_socialcrawl(api_key: str) -> dict[str, Any]:
    if not api_key:
        raise ProviderError("SOCIALCRAWL_API_KEY is required for a connection test")
    payload = socialcrawl_request("/credits/balance", api_key, timeout=15)
    return {
        "connected": bool(payload.get("success", True)),
        "message": "SocialCrawl accepted the saved credential.",
    }


def dedupe(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for signal in signals:
        identity = str(signal.get("source_url") or signal.get("id"))
        key = (str(signal.get("platform")), identity)
        if key in seen:
            continue
        seen.add(key)
        output.append(signal)
    return output
