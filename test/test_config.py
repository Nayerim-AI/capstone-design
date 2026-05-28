import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_config  # noqa: E402


class ConfigTest(unittest.TestCase):
    def load_from_text(self, text):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(text)
            with patch.dict(os.environ, {}, clear=True):
                return load_config(env_path)

    def test_gps_baudrate_default_is_4800(self):
        cfg = self.load_from_text("")

        self.assertEqual(cfg.gps_baudrate, 4800)

    def test_gps_enabled_accepts_true_false_values(self):
        true_values = ["true", "1", "yes", "y", "on"]
        false_values = ["false", "0", "no", "n", "off"]

        for value in true_values:
            cfg = self.load_from_text(f"GPS_ENABLED={value}\n")
            self.assertTrue(cfg.gps_enabled, value)

        for value in false_values:
            cfg = self.load_from_text(f"GPS_ENABLED={value}\n")
            self.assertFalse(cfg.gps_enabled, value)


if __name__ == "__main__":
    unittest.main()
