from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.config import ConfigError
from sdsa.server import build_handler, run_server


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.profile = pathlib.Path(self.temp.name) / "profile.json"
        self.database = pathlib.Path(self.temp.name) / "state.sqlite3"
        self.env = pathlib.Path(self.temp.name) / ".env"
        self.profile.write_text((ROOT / "assets/fixtures/demo-profile.json").read_text())
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.profile, self.database, self.env))
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
        request = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "X-SDSA-Request": "local"}, method="POST")
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

    def test_setup_payload_never_returns_secret(self) -> None:
        secret = "sc_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        self.env.write_text(f"SOCIALCRAWL_API_KEY={secret}\n")
        result = self.get_json("/api/setup")
        self.assertTrue(result["provider"]["credential_configured"])
        self.assertNotIn(secret, json.dumps(result))

    def test_setup_can_save_progress_and_complete(self) -> None:
        template = json.loads((ROOT / "assets/company-profile.example.json").read_text())
        progress = self.post_json("/api/setup/save", {"profile": template, "complete": False})
        self.assertEqual(progress["profile_status"], "setup")
        complete = json.loads((ROOT / "assets/fixtures/demo-profile.json").read_text())
        complete["profile_status"] = "setup"
        result = self.post_json("/api/setup/save", {"profile": complete, "complete": True})
        self.assertEqual(result["profile_status"], "ready")

    def test_credential_lifecycle_is_redacted(self) -> None:
        secret = "sc_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        saved = self.post_json("/api/credential", {"action": "save", "api_key": secret})
        self.assertNotIn(secret, json.dumps(saved))
        self.assertIn(secret, self.env.read_text())
        removed = self.post_json("/api/credential", {"action": "remove"})
        self.assertFalse(removed["provider"]["credential_configured"])

    @mock.patch("sdsa.server.test_socialcrawl")
    def test_provider_connection_state(self, test_connection: mock.Mock) -> None:
        secret = "sc_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        self.post_json("/api/credential", {"action": "save", "api_key": secret})
        test_connection.return_value = {"connected": True, "message": "connected"}
        result = self.post_json("/api/provider/test", {})
        self.assertEqual(result["provider"]["connection_state"], "connected")

    def test_mutation_requires_local_header(self) -> None:
        request = urllib.request.Request(self.base + "/api/reset/demo", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 400)

    def test_reset_setup_and_demo_are_separate(self) -> None:
        result = self.post_json("/api/reset/setup", {})
        self.assertEqual(result["setup"]["readiness"]["profile_status"], "setup")
        result = self.post_json("/api/reset/demo", {})
        self.assertEqual(result["setup"]["readiness"]["profile_status"], "demo")
        self.assertEqual(result["signals"], 5)


class ServerBoundaryTests(unittest.TestCase):
    def test_server_rejects_non_loopback_host_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with self.assertRaises(ConfigError):
                run_server(root / "profile.json", root / "state.sqlite3", root / ".env", "0.0.0.0", 8766, True)


if __name__ == "__main__":
    unittest.main()
