from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.server import build_handler


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.profile = pathlib.Path(self.temp.name) / "profile.json"
        self.database = pathlib.Path(self.temp.name) / "state.sqlite3"
        self.profile.write_text((ROOT / "assets/fixtures/demo-profile.json").read_text())
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.profile, self.database))
        except PermissionError:
            self.temp.cleanup()
            self.skipTest("localhost binding is unavailable in this sandbox")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get_json(self, path: str) -> dict:
        with urllib.request.urlopen(self.base + path) as response:
            return json.loads(response.read())

    def post_json(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_empty_loading_and_populated_states(self) -> None:
        empty = self.get_json("/api/state")
        self.assertEqual(empty["summary"]["total"], 0)
        result = self.post_json("/api/collect", {"provider": "fixture"})
        self.assertEqual(result["stored"], 5)
        populated = self.get_json("/api/state")
        self.assertEqual(populated["summary"]["total"], 5)

    def test_application_assets_load(self) -> None:
        with urllib.request.urlopen(self.base + "/") as response:
            html = response.read().decode()
        self.assertIn("Review Queue", html)
        self.assertIn("error-banner", html)
        self.assertIn("experiment-body", html)

    def test_export_endpoint_creates_agent_batch(self) -> None:
        self.post_json("/api/collect", {"provider": "fixture"})
        result = self.post_json("/api/export", {})
        self.assertEqual(result["exported"], 3)


if __name__ == "__main__":
    unittest.main()
