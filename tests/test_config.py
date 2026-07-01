from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.config import (
    ConfigError,
    SCHEMA_VERSION,
    ensure_profile,
    migrate_profile,
    require_live_ready,
    save_profile,
    setup_status,
    validate_profile,
)


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

    def test_industry_and_website_are_required(self) -> None:
        self.profile["profile_status"] = "ready"
        self.profile["company"]["industry"] = ""
        with self.assertRaises(ConfigError):
            require_live_ready(self.profile)
        self.profile["company"]["industry"] = "Software"
        self.profile["company"]["website"] = "not-a-url"
        with self.assertRaises(ConfigError):
            require_live_ready(self.profile)

    def test_old_ready_profile_migrates_back_to_setup(self) -> None:
        old = copy.deepcopy(self.profile)
        old.pop("schema_version")
        old["company"].pop("industry")
        old["company"].pop("website")
        old["profile_status"] = "ready"
        migrated, changed, version = migrate_profile(old)
        self.assertTrue(changed)
        self.assertEqual(version, 1)
        self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
        self.assertEqual(migrated["profile_status"], "setup")

    def test_old_demo_profile_migrates_back_to_setup(self) -> None:
        old = copy.deepcopy(self.profile)
        old.pop("schema_version")
        old["company"].pop("industry")
        old["company"].pop("website")
        migrated, changed, _ = migrate_profile(old)
        self.assertTrue(changed)
        self.assertEqual(migrated["profile_status"], "setup")

    def test_file_migration_writes_backup(self) -> None:
        old = copy.deepcopy(self.profile)
        old.pop("schema_version")
        old["company"].pop("industry")
        old["company"].pop("website")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "profile.json"
            path.write_text(json.dumps(old))
            migrated, backup = ensure_profile(path, ROOT / "assets/company-profile.example.json")
            self.assertIsNotNone(backup)
            self.assertTrue(backup.exists())
            self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)

    def test_partial_save_stays_setup_and_complete_save_becomes_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "profile.json"
            partial = copy.deepcopy(self.profile)
            partial["company"]["name"] = ""
            saved = save_profile(path, partial, complete=False)
            self.assertEqual(saved["profile_status"], "setup")
            with self.assertRaises(ConfigError):
                save_profile(path, partial, complete=True)
            ready = save_profile(path, self.profile, complete=True)
            self.assertEqual(ready["profile_status"], "ready")

    def test_setup_status_separates_profile_and_provider(self) -> None:
        self.profile["profile_status"] = "ready"
        status = setup_status(self.profile, credential_configured=False)
        self.assertTrue(status["profile_ready"])
        self.assertFalse(status["provider_ready"])
        self.assertFalse(status["ready_to_listen"])


if __name__ == "__main__":
    unittest.main()
