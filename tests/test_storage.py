from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.storage import Store


def signal(signal_id: str, variant: str = "a", label: str = "observed", family: str = "general", platform: str = "forum") -> dict:
    return {
        "id": signal_id, "source_type": "json", "data_label": label,
        "platform": platform, "source_url": f"https://example.com/{signal_id}",
        "author": "person", "published_at": "", "query": "", "text": "Need a better shared queue now",
        "raw": {}, "relevance_score": 1.0, "route": "review", "route_reasons": {},
        "message_family": family, "assigned_variant": variant, "agent_status": "pending",
    }


def result(signal_id: str, action: str = "draft") -> dict:
    value = {"signal_id": signal_id, "action": action, "data_label": "agent_generated"}
    if action == "draft":
        value["variants"] = {
            "a": {"body": "A disclosed response", "rationale": "A", "guardrails": []},
            "b": {"body": "B disclosed response", "rationale": "B", "guardrails": []},
        }
    return value


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(pathlib.Path(self.temp.name) / "test.sqlite3")
        self.profile = json.loads((ROOT / "assets/fixtures/demo-profile.json").read_text())

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_draft_import_and_review_use_assigned_variant(self) -> None:
        self.store.upsert_signals([signal("s1", "b")])
        self.assertEqual(self.store.import_drafts([result("s1")]), 2)
        self.store.review("s1", "approved")
        row = self.store.connection.execute("SELECT final_body FROM reviews WHERE signal_id='s1'").fetchone()
        self.assertEqual(row["final_body"], "B disclosed response")

    def test_agent_can_suppress_candidate(self) -> None:
        self.store.upsert_signals([signal("s1")])
        self.store.import_drafts([result("s1", "suppress")])
        row = self.store.connection.execute("SELECT route,agent_status FROM signals WHERE id='s1'").fetchone()
        self.assertEqual((row["route"], row["agent_status"]), ("suppress", "complete"))

    def test_fixture_events_do_not_change_real_metrics(self) -> None:
        self.store.upsert_signals([signal("s1", "a", "fixture")])
        self.store.import_drafts([result("s1")])
        self.store.review("s1", "approved")
        self.store.record_event("s1", "posted", "reviewer_entered")
        self.store.record_event("s1", "qualified_action", "reviewer_entered")
        labels = [row[0] for row in self.store.connection.execute("SELECT data_label FROM events").fetchall()]
        self.assertEqual(labels, ["fixture", "fixture"])
        report = self.store.experiment_report(self.profile)[0]
        self.assertEqual(report["variants"]["a"]["exposures"], 0)

    def test_observed_events_are_grouped_by_family_platform_variant(self) -> None:
        self.store.upsert_signals([signal("s1", "a"), signal("s2", "b")])
        for signal_id in ("s1", "s2"):
            self.store.import_drafts([result(signal_id)])
            self.store.review(signal_id, "approved")
            self.store.record_event(signal_id, "posted", max_responses_per_author_24h=10)
        self.store.record_event("s1", "qualified_action")
        report = self.store.experiment_report(self.profile)[0]
        self.assertEqual(report["variants"]["a"]["conversion_rate"], 1.0)
        self.assertEqual(report["variants"]["b"]["conversion_rate"], 0.0)
        self.assertEqual(report["status"], "insufficient_data")

    def test_events_require_approval_and_are_idempotent(self) -> None:
        self.store.upsert_signals([signal("s1")])
        with self.assertRaises(ValueError):
            self.store.record_event("s1", "posted")
        self.store.import_drafts([result("s1")])
        self.store.review("s1", "approved")
        self.store.record_event("s1", "posted")
        self.store.record_event("s1", "posted")
        count = self.store.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(count, 1)

    def test_per_author_frequency_limit_is_enforced(self) -> None:
        self.store.upsert_signals([signal("s1", "a"), signal("s2", "b")])
        for signal_id in ("s1", "s2"):
            self.store.import_drafts([result(signal_id)])
            self.store.review(signal_id, "approved")
        self.store.record_event("s1", "posted", max_responses_per_author_24h=1)
        with self.assertRaises(ValueError):
            self.store.record_event("s2", "posted", max_responses_per_author_24h=1)


if __name__ == "__main__":
    unittest.main()
