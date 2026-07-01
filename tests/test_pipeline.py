from __future__ import annotations

import json
import datetime as dt
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.pipeline import assign_variant, route_signal


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((ROOT / "assets/fixtures/demo-profile.json").read_text())

    def signal(self, text: str, signal_id: str = "signal-1") -> dict:
        return {"id": signal_id, "text": text, "source_type": "json", "data_label": "observed", "platform": "forum", "source_url": "", "author": "a", "published_at": "", "query": "", "raw": {}}

    def test_routes_relevant_signal_to_review(self) -> None:
        result = route_signal(self.signal("Our support queue keeps growing and we need a shared inbox"), self.profile)
        self.assertEqual(result["route"], "review")

    def test_hard_escalation_wins(self) -> None:
        result = route_signal(self.signal("The support queue keeps growing after a security breach"), self.profile)
        self.assertEqual(result["route"], "escalate")

    def test_exclusion_suppresses(self) -> None:
        result = route_signal(self.signal("Student assignment about manual ticket triage"), self.profile)
        self.assertEqual(result["route"], "suppress")

    def test_assignment_is_stable(self) -> None:
        self.assertEqual(assign_variant("abc", "general"), assign_variant("abc", "general"))

    def test_stale_live_signal_is_suppressed(self) -> None:
        item = self.signal("Our support queue keeps growing and we need a shared inbox")
        item["source_type"] = "socialcrawl"
        item["published_at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).isoformat()
        result = route_signal(item, self.profile)
        self.assertEqual(result["route"], "suppress")
        self.assertEqual(result["route_reasons"]["freshness_status"], "stale")


if __name__ == "__main__":
    unittest.main()
