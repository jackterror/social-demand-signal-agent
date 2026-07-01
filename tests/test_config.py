from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.config import ConfigError, require_live_ready, validate_profile


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((ROOT / "assets/fixtures/demo-profile.json").read_text())

    def test_demo_profile_validates_but_is_not_live_ready(self) -> None:
        validate_profile(self.profile)
        with self.assertRaises(ConfigError):
            require_live_ready(self.profile)

    def test_ready_profile_passes(self) -> None:
        self.profile["profile_status"] = "ready"
        require_live_ready(self.profile)

    def test_missing_required_field_fails(self) -> None:
        broken = copy.deepcopy(self.profile)
        broken["audience"]["pain_points"] = []
        with self.assertRaises(ConfigError):
            validate_profile(broken)

    def test_ready_profile_rejects_onboarding_placeholder(self) -> None:
        template = json.loads((ROOT / "assets/company-profile.example.json").read_text())
        template["profile_status"] = "ready"
        with self.assertRaises(ConfigError):
            validate_profile(template)


if __name__ == "__main__":
    unittest.main()
