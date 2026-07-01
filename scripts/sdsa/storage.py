from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import sqlite3
from typing import Any


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    data_label TEXT NOT NULL,
    platform TEXT NOT NULL,
    source_url TEXT NOT NULL,
    author TEXT NOT NULL,
    published_at TEXT NOT NULL,
    query TEXT NOT NULL,
    text TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    route TEXT NOT NULL,
    route_reasons_json TEXT NOT NULL,
    message_family TEXT NOT NULL,
    assigned_variant TEXT NOT NULL,
    agent_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    signal_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    body TEXT NOT NULL,
    rationale TEXT NOT NULL,
    guardrails_json TEXT NOT NULL,
    data_label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(signal_id, variant),
    FOREIGN KEY(signal_id) REFERENCES signals(id)
);
CREATE TABLE IF NOT EXISTS reviews (
    signal_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    final_body TEXT NOT NULL,
    reviewer_note TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    FOREIGN KEY(signal_id) REFERENCES signals(id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data_label TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY(signal_id) REFERENCES signals(id)
);
"""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def upsert_signals(self, rows: list[dict[str, Any]]) -> int:
        for row in rows:
            self.connection.execute(
                """INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  source_type=excluded.source_type, data_label=excluded.data_label,
                  platform=excluded.platform, source_url=excluded.source_url,
                  author=excluded.author, published_at=excluded.published_at,
                  query=excluded.query, text=excluded.text, raw_json=excluded.raw_json,
                  relevance_score=excluded.relevance_score, route=excluded.route,
                  route_reasons_json=excluded.route_reasons_json,
                  message_family=excluded.message_family,
                  assigned_variant=excluded.assigned_variant,
                  agent_status=excluded.agent_status""",
                (
                    row["id"], row["source_type"], row["data_label"], row["platform"],
                    row.get("source_url", ""), row.get("author", "unknown"),
                    row.get("published_at", ""), row.get("query", ""), row["text"],
                    json.dumps(row.get("raw", {}), ensure_ascii=True), utc_now(),
                    row["relevance_score"], row["route"],
                    json.dumps(row["route_reasons"], ensure_ascii=True),
                    row["message_family"], row["assigned_variant"], row["agent_status"],
                ),
            )
        self.connection.commit()
        return len(rows)

    def import_drafts(self, drafts: list[dict[str, Any]]) -> int:
        count = 0
        for item in drafts:
            signal_id = str(item.get("signal_id") or "")
            action = str(item.get("action") or "draft")
            variants = item.get("variants") or {}
            if not signal_id:
                raise ValueError("Each result needs signal_id")
            signal = self.connection.execute(
                "SELECT route FROM signals WHERE id = ?", (signal_id,)
            ).fetchone()
            if not signal:
                raise ValueError(f"Unknown signal_id: {signal_id}")
            if signal["route"] != "review":
                raise ValueError(f"Drafts are not allowed for routed signal: {signal_id}")
            if action in {"suppress", "escalate"}:
                self.connection.execute(
                    "UPDATE signals SET route = ?, agent_status = 'complete' WHERE id = ?",
                    (action, signal_id),
                )
                continue
            if action != "draft" or not isinstance(variants, dict):
                raise ValueError(f"Action for {signal_id} must be draft, suppress, or escalate")
            for variant in ("a", "b"):
                draft = variants.get(variant)
                if not isinstance(draft, dict) or not str(draft.get("body") or "").strip():
                    raise ValueError(f"Missing variant {variant} for {signal_id}")
                self.connection.execute(
                    """INSERT INTO drafts VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(signal_id, variant) DO UPDATE SET
                      body=excluded.body, rationale=excluded.rationale,
                      guardrails_json=excluded.guardrails_json,
                      data_label=excluded.data_label, created_at=excluded.created_at""",
                    (
                        signal_id, variant, str(draft["body"]).strip(),
                        str(draft.get("rationale") or ""),
                        json.dumps(draft.get("guardrails") or [], ensure_ascii=True),
                        str(item.get("data_label") or "agent_generated"), utc_now(),
                    ),
                )
                count += 1
            self.connection.execute(
                "UPDATE signals SET agent_status = 'complete' WHERE id = ?", (signal_id,)
            )
        self.connection.commit()
        return count

    def review(self, signal_id: str, decision: str, final_body: str = "", note: str = "") -> None:
        allowed = {"approved", "rejected", "escalated"}
        if decision not in allowed:
            raise ValueError(f"Decision must be one of: {', '.join(sorted(allowed))}")
        signal = self.connection.execute(
            "SELECT assigned_variant, route FROM signals WHERE id = ?", (signal_id,)
        ).fetchone()
        if not signal:
            raise ValueError(f"Unknown signal_id: {signal_id}")
        if decision == "approved" and signal["route"] != "review":
            raise ValueError("Only review-routed signals can be approved")
        if decision == "approved" and not final_body:
            draft = self.connection.execute(
                "SELECT body FROM drafts WHERE signal_id = ? AND variant = ?",
                (signal_id, signal["assigned_variant"]),
            ).fetchone()
            if not draft:
                raise ValueError("Assigned draft must exist before approval")
            final_body = str(draft["body"])
        self.connection.execute(
            """INSERT INTO reviews VALUES (?,?,?,?,?)
            ON CONFLICT(signal_id) DO UPDATE SET decision=excluded.decision,
              final_body=excluded.final_body, reviewer_note=excluded.reviewer_note,
              reviewed_at=excluded.reviewed_at""",
            (signal_id, decision, final_body, note, utc_now()),
        )
        self.connection.commit()

    def record_event(
        self,
        signal_id: str,
        event_type: str,
        data_label: str = "reviewer_entered",
        metadata: dict[str, Any] | None = None,
        max_responses_per_author_24h: int = 1,
    ) -> None:
        signal = self.connection.execute("SELECT data_label FROM signals WHERE id = ?", (signal_id,)).fetchone()
        if not signal:
            raise ValueError(f"Unknown signal_id: {signal_id}")
        if signal["data_label"] == "fixture":
            data_label = "fixture"
        review = self.connection.execute(
            "SELECT decision FROM reviews WHERE signal_id = ?", (signal_id,)
        ).fetchone()
        if not review or review["decision"] != "approved":
            raise ValueError("Outcome events require an approved human review")
        if event_type != "posted" and not self.connection.execute(
            "SELECT 1 FROM events WHERE signal_id = ? AND event_type = 'posted'", (signal_id,)
        ).fetchone():
            raise ValueError("Record posted before downstream outcome events")
        if self.connection.execute(
            "SELECT 1 FROM events WHERE signal_id = ? AND event_type = ? AND data_label = ?",
            (signal_id, event_type, data_label),
        ).fetchone():
            return
        if event_type == "posted" and signal["data_label"] != "fixture":
            author = self.connection.execute("SELECT author FROM signals WHERE id = ?", (signal_id,)).fetchone()["author"]
            recent = self.connection.execute(
                """SELECT COUNT(*) FROM events e JOIN signals s ON s.id=e.signal_id
                   WHERE e.event_type='posted' AND s.author=?
                   AND datetime(e.occurred_at) >= datetime('now','-24 hours')""",
                (author,),
            ).fetchone()[0]
            if int(recent) >= max_responses_per_author_24h:
                raise ValueError("Configured per-author response frequency limit reached")
        self.connection.execute(
            "INSERT INTO events(signal_id,event_type,data_label,metadata_json,occurred_at) VALUES (?,?,?,?,?)",
            (signal_id, event_type, data_label, json.dumps(metadata or {}), utc_now()),
        )
        self.connection.commit()

    def agent_batch(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT id,platform,source_url,author,published_at,query,text,
                      relevance_score,route,message_family,assigned_variant,data_label
               FROM signals WHERE route = 'review' AND agent_status = 'pending'
               ORDER BY relevance_score DESC, ingested_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]

    def state(self, profile: dict[str, Any]) -> dict[str, Any]:
        signals = self.connection.execute(
            """SELECT s.*, r.decision, r.final_body, r.reviewer_note, r.reviewed_at
               FROM signals s LEFT JOIN reviews r ON r.signal_id=s.id
               ORDER BY s.relevance_score DESC, s.ingested_at DESC"""
        ).fetchall()
        output: list[dict[str, Any]] = []
        for row in signals:
            item = dict(row)
            item["route_reasons"] = json.loads(item.pop("route_reasons_json"))
            item.pop("raw_json", None)
            draft_rows = self.connection.execute(
                "SELECT variant,body,rationale,guardrails_json,data_label FROM drafts WHERE signal_id=?",
                (item["id"],),
            ).fetchall()
            item["drafts"] = {
                draft["variant"]: {
                    "body": draft["body"],
                    "rationale": draft["rationale"],
                    "guardrails": json.loads(draft["guardrails_json"]),
                    "data_label": draft["data_label"],
                }
                for draft in draft_rows
            }
            output.append(item)
        return {
            "profile": {
                "company": profile["company"]["name"],
                "product": profile["company"]["product"],
                "primary_event": profile["experiment"]["primary_event"],
                "guardrail_event": profile["experiment"]["guardrail_event"],
            },
            "signals": output,
            "summary": self.summary(),
            "experiments": self.experiment_report(profile),
        }

    def summary(self) -> dict[str, int]:
        row = self.connection.execute(
            """SELECT COUNT(*) total,
               SUM(CASE WHEN route='review' THEN 1 ELSE 0 END) reviewable,
               SUM(CASE WHEN route='escalate' THEN 1 ELSE 0 END) escalated,
               SUM(CASE WHEN agent_status='complete' THEN 1 ELSE 0 END) drafted
               FROM signals"""
        ).fetchone()
        approved = self.connection.execute(
            "SELECT COUNT(*) FROM reviews WHERE decision='approved'"
        ).fetchone()[0]
        return {key: int(row[key] or 0) for key in row.keys()} | {"approved": int(approved)}

    def experiment_report(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        primary = profile["experiment"]["primary_event"]
        guardrail = profile["experiment"]["guardrail_event"]
        minimum = int(profile["experiment"]["minimum_sample_size"])
        groups = self.connection.execute(
            """SELECT message_family, platform, assigned_variant,
                      SUM(CASE WHEN e.event_type='posted' AND e.data_label!='fixture' THEN 1 ELSE 0 END) exposures,
                      SUM(CASE WHEN e.event_type=? AND e.data_label!='fixture' THEN 1 ELSE 0 END) conversions,
                      SUM(CASE WHEN e.event_type=? AND e.data_label!='fixture' THEN 1 ELSE 0 END) guardrails
               FROM signals s LEFT JOIN events e ON e.signal_id=s.id
               WHERE s.route='review'
               GROUP BY message_family, platform, assigned_variant
               ORDER BY message_family, platform, assigned_variant""",
            (primary, guardrail),
        ).fetchall()
        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for row in groups:
            key = (row["message_family"], row["platform"])
            bucket = buckets.setdefault(key, {"message_family": key[0], "platform": key[1], "variants": {}})
            exposures = int(row["exposures"] or 0)
            conversions = int(row["conversions"] or 0)
            guardrails = int(row["guardrails"] or 0)
            bucket["variants"][row["assigned_variant"]] = {
                "exposures": exposures,
                "conversions": conversions,
                "guardrails": guardrails,
                "conversion_rate": round(conversions / exposures, 4) if exposures else 0.0,
                "guardrail_rate": round(guardrails / exposures, 4) if exposures else 0.0,
                "interval": wilson_interval(conversions, exposures),
            }
        reports: list[dict[str, Any]] = []
        for bucket in buckets.values():
            variants = bucket["variants"]
            a = variants.get("a", empty_variant())
            b = variants.get("b", empty_variant())
            leader = "tie"
            if a["conversion_rate"] > b["conversion_rate"]:
                leader = "a"
            elif b["conversion_rate"] > a["conversion_rate"]:
                leader = "b"
            status = "insufficient_data"
            winner = None
            if min(a["exposures"], b["exposures"]) >= minimum:
                status = "directional"
                a_low, a_high = a["interval"]
                b_low, b_high = b["interval"]
                guardrail_ok = abs(a["guardrail_rate"] - b["guardrail_rate"]) <= 0.02
                if guardrail_ok and (a_low > b_high or b_low > a_high):
                    status = "validated"
                    winner = leader if leader != "tie" else None
            reports.append(bucket | {"status": status, "directional_leader": leader, "winner": winner, "minimum_sample_size": minimum})
        return reports


def empty_variant() -> dict[str, Any]:
    return {"exposures": 0, "conversions": 0, "guardrails": 0, "conversion_rate": 0.0, "guardrail_rate": 0.0, "interval": [0.0, 1.0]}


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [0.0, 1.0]
    proportion = successes / total
    denominator = 1 + (z * z / total)
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((proportion * (1 - proportion) / total) + (z * z / (4 * total * total))) / denominator
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]
