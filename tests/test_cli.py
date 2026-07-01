from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "signal_agent.py"
DEMO = ROOT / "assets" / "fixtures" / "demo-profile.json"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        directory = pathlib.Path(self.temp.name)
        self.profile = directory / "profile.json"
        self.database = directory / "state.sqlite3"
        self.env_file = directory / ".env"
        self.environment = os.environ.copy()
        self.environment.pop("SOCIALCRAWL_API_KEY", None)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--profile", str(self.profile), "--database", str(self.database), "--env-file", str(self.env_file), *arguments],
            cwd=ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_and_setup_status_need_no_json_edit(self) -> None:
        self.assertEqual(self.run_cli("init").returncode, 0)
        result = self.run_cli("setup-status")
        self.assertEqual(result.returncode, 0)
        status = json.loads(result.stdout)
        self.assertEqual(status["profile_status"], "setup")
        self.assertFalse(status["ready_to_listen"])

    def test_live_collection_is_blocked_without_key(self) -> None:
        profile = json.loads(DEMO.read_text())
        profile["profile_status"] = "ready"
        self.profile.write_text(json.dumps(profile))
        result = self.run_cli("collect", "--provider", "socialcrawl")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SOCIALCRAWL_API_KEY is required", result.stderr)

    def test_profile_export_contains_no_credential(self) -> None:
        self.assertEqual(self.run_cli("profile-import", "--input", str(DEMO)).returncode, 0)
        output = pathlib.Path(self.temp.name) / "export.json"
        self.assertEqual(self.run_cli("profile-export", "--output", str(output)).returncode, 0)
        text = output.read_text()
        self.assertNotIn("SOCIALCRAWL_API_KEY", text)
        self.assertNotIn("api_key", text.lower())

    def test_doctor_reports_separate_readiness_checks(self) -> None:
        self.assertEqual(self.run_cli("init").returncode, 0)
        result = self.run_cli("doctor", "--port", "0")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertIn("profile_ready", payload["checks"])
        self.assertIn("provider_ready", payload["checks"])
        self.assertIn("port_available", payload["checks"])


if __name__ == "__main__":
    unittest.main()
