from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.providers import collect_socialcrawl, dedupe, load_json_records, normalize_record


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class ProviderTests(unittest.TestCase):
    def test_normalize_common_record(self) -> None:
        row = normalize_record({"platform": "forum", "url": "https://example.com/1", "text": "I need a better workflow today"}, "json", "observed")
        self.assertEqual(row["platform"], "forum")
        self.assertEqual(row["data_label"], "observed")
        self.assertTrue(row["id"])

    def test_json_loader_accepts_result_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "records.json"
            path.write_text(json.dumps({"results": [{"platform": "forum", "text": "Need a shared queue for customer messages"}]}))
            rows = load_json_records(path)
        self.assertEqual(len(rows), 1)

    def test_dedupe_uses_platform_and_source_identity(self) -> None:
        rows = [
            {"platform": "forum", "source_url": "https://example.com/1", "id": "1"},
            {"platform": "forum", "source_url": "https://example.com/1", "id": "2"},
        ]
        self.assertEqual(len(dedupe(rows)), 1)

    @mock.patch("urllib.request.urlopen")
    def test_socialcrawl_contract(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = FakeResponse({
            "platform": "forum",
            "data": {"items": [{"id": "live-1", "url": "https://example.com/live-1", "text": "Looking for a better shared support queue"}]},
        })
        rows, logs = collect_socialcrawl("test-key", ["shared support queue"], ["forum"], 10)
        self.assertEqual(rows[0]["source_type"], "socialcrawl")
        self.assertEqual(rows[0]["data_label"], "observed")
        self.assertTrue(logs)

    @mock.patch("urllib.request.urlopen")
    def test_socialcrawl_drops_records_without_source_url(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = FakeResponse({
            "platform": "forum",
            "data": {"items": [{"id": "summary-only", "text": "Looking for a better shared support queue"}]},
        })
        rows, _ = collect_socialcrawl("test-key", ["shared support queue"], ["forum"], 10)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
