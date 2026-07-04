from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release_audit import audit


class ReleaseTests(unittest.TestCase):
    def test_repository_audit_passes(self) -> None:
        result = audit(ROOT, ["legacy-" + "brand-marker"])
        self.assertTrue(result["ok"], result["failures"])

    def test_frontend_has_error_empty_and_populated_contracts(self) -> None:
        html = (ROOT / "assets/index.html").read_text()
        js = (ROOT / "assets/app.js").read_text()
        self.assertIn("error-banner", html)
        self.assertIn("No signals in the current workspace", js)
        self.assertIn("renderSignal", js)
        self.assertIn("setup-view", html)
        self.assertIn("Ready to Listen", html)
        self.assertIn("Get a SocialCrawl key", html)
        self.assertIn("clientErrors", js)
        self.assertIn("updateCollectAvailability", js)
        self.assertIn('demo ? "Fixture"', js)
        self.assertIn('demo ? "Demo ready"', js)

    def test_frontend_has_accessible_setup_contracts(self) -> None:
        html = (ROOT / "assets/index.html").read_text()
        self.assertIn('aria-label="Listening readiness"', html)
        self.assertIn('role="alert"', html)
        self.assertIn('type="password"', html)
        self.assertIn('autocomplete="off"', html)


if __name__ == "__main__":
    unittest.main()
