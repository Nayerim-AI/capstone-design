import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gps_reader import GPSReader, disabled_gps_result  # noqa: E402


EXPECTED_KEYS = {
    "enabled",
    "available",
    "has_fix",
    "status",
    "latitude",
    "longitude",
    "gps_time",
    "maps_url",
    "raw_type",
    "message",
}


class GPSResultSchemaTest(unittest.TestCase):
    def test_default_reader_snapshot_has_consistent_keys(self):
        result = GPSReader(baudrate=4800).get_current_location()

        self.assertEqual(set(result.keys()), EXPECTED_KEYS)
        self.assertEqual(result["status"], "Belum Fix")

    def test_disabled_snapshot_has_consistent_keys(self):
        result = disabled_gps_result()

        self.assertEqual(set(result.keys()), EXPECTED_KEYS)
        self.assertEqual(result["status"], "Nonaktif")


if __name__ == "__main__":
    unittest.main()
