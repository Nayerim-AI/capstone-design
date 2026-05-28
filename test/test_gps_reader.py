import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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


class GPSReaderTest(unittest.TestCase):
    def assert_schema(self, result):
        self.assertEqual(set(result.keys()), EXPECTED_KEYS)

    def test_valid_gga_sentence_updates_schema_with_fix(self):
        reader = GPSReader(baudrate=4800)
        sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"

        with patch("gps_reader.log_gps_data"):
            parsed = reader.parse_nmea_line(sentence)

        result = reader.get_current_location()
        self.assertTrue(parsed)
        self.assert_schema(result)
        self.assertTrue(result["has_fix"])
        self.assertEqual(result["status"], "Valid")
        self.assertAlmostEqual(result["latitude"], 48.1173, places=4)
        self.assertAlmostEqual(result["longitude"], 11.5166667, places=4)
        self.assertEqual(result["gps_time"], "12:35:19 UTC")
        self.assertEqual(result["raw_type"], "GPGGA")

    def test_gga_no_fix_is_not_error(self):
        reader = GPSReader(baudrate=4800)
        sentence = "$GPGGA,123519,,,,,0,00,99.99,,,,,,*45"

        parsed = reader.parse_nmea_line(sentence)
        result = reader.get_current_location()

        self.assertFalse(parsed)
        self.assert_schema(result)
        self.assertTrue(result["available"])
        self.assertFalse(result["has_fix"])
        self.assertEqual(result["status"], "Belum Fix")
        self.assertIsNone(result["gps_time"])
        self.assertIn("belum fix", result["message"].lower())

    def test_disabled_result_schema(self):
        result = disabled_gps_result()

        self.assert_schema(result)
        self.assertFalse(result["enabled"])
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "Nonaktif")

    def test_port_error_result_schema(self):
        reader = GPSReader(port="/tmp/port-tidak-ada", baudrate=4800)

        reader.connect()
        result = reader.get_current_location()

        self.assert_schema(result)
        self.assertTrue(result["enabled"])
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "Tidak Tersedia")


if __name__ == "__main__":
    unittest.main()
