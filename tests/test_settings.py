from __future__ import annotations

import pathlib
import stat
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sdsa.settings import SettingsError, credential_status, env_values, parse_env, remove_api_key, runtime_api_key, save_api_key


KEY_A = "sc_" + "abcdefghijklmnopqrstuvwxyz1234567890"
KEY_B = "sc_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321"


class SettingsTests(unittest.TestCase):
    def test_parse_env_accepts_comments_quotes_and_export(self) -> None:
        values = parse_env("# note\nexport A='one'\nB=\"two\"\n")
        self.assertEqual(values, {"A": "one", "B": "two"})

    def test_process_environment_has_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / ".env"
            path.write_text(f"SOCIALCRAWL_API_KEY={KEY_A}\n")
            key, source = runtime_api_key(path, {"SOCIALCRAWL_API_KEY": KEY_B})
        self.assertEqual((key, source), (KEY_B, "process"))

    def test_save_replace_remove_preserves_other_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / ".env"
            path.write_text("OTHER=value\n")
            save_api_key(path, KEY_A)
            self.assertEqual(env_values(path)["OTHER"], "value")
            self.assertEqual(env_values(path)["SOCIALCRAWL_API_KEY"], KEY_A)
            save_api_key(path, KEY_B)
            self.assertEqual(env_values(path)["SOCIALCRAWL_API_KEY"], KEY_B)
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)
            remove_api_key(path)
            self.assertNotIn("SOCIALCRAWL_API_KEY", env_values(path))
            self.assertEqual(env_values(path)["OTHER"], "value")

    def test_invalid_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SettingsError):
                save_api_key(pathlib.Path(directory) / ".env", "not-a-key")

    def test_status_never_contains_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / ".env"
            save_api_key(path, KEY_A)
            status = credential_status(path, {})
        self.assertEqual(status, {"configured": True, "source": "env_file"})
        self.assertNotIn(KEY_A, repr(status))
