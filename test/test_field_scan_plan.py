import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_channel_map, load_test_locations
from logger import FIELD_SCAN_HEADER, log_field_scan_data


class JabodetabekFieldScanPlanTest(unittest.TestCase):
    def test_baseline_mux_list_matches_reference(self):
        channels = load_channel_map()
        baseline = [ch for ch in channels.values() if ch.get("scan_priority") == "baseline"]
        pairs = sorted((int(ch["uhf_channel"]), float(ch["frequency_mhz"])) for ch in baseline)
        self.assertEqual(pairs, [(24, 498.0), (28, 530.0), (31, 554.0), (34, 578.0), (40, 626.0), (43, 650.0)])

    def test_optional_mux_are_separate_from_baseline(self):
        channels = load_channel_map()
        optional = sorted((int(ch["uhf_channel"]), float(ch["frequency_mhz"])) for ch in channels.values() if ch.get("scan_priority") == "optional")
        self.assertEqual(optional, [(25, 514.0), (48, 690.0)])

    def test_location_route_order_and_initial_coordinates(self):
        locations = load_test_locations()
        route = sorted((int(loc["route_order"]), key, float(loc["initial_lat"]), float(loc["initial_lon"])) for key, loc in locations.items())
        self.assertEqual([key for _, key, _, _ in route], ["stasiun_juanda", "monas", "bundaran_hi", "indomaret_tomang", "cp_taman_anggrek"])
        self.assertEqual((route[1][2], route[1][3]), (-6.1754, 106.8272))

    def test_field_scan_csv_schema_supports_reference_template(self):
        required = {
            "timestamp", "site_name", "lat", "lon", "uhf_channel", "frequency_mhz",
            "lock_status", "signal_strength", "signal_quality", "snr_mer_db", "ber", "per",
            "antenna_type", "antenna_height_m", "receiver_gain_db", "calibration_mode",
            "radio_planner_dbuvm", "delta_vs_radioplanner_db", "notes",
        }
        self.assertTrue(required.issubset(set(FIELD_SCAN_HEADER)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "field_scan_log.csv"
            log_field_scan_data({
                "site_name": "Monas",
                "uhf_channel": 24,
                "frequency_mhz": 498.0,
                "lock_status": "unknown",
                "signal_strength": 12.3,
                "calibration_mode": "raw",
            }, csv_path=path)
            with path.open() as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["site_name"], "Monas")
            self.assertEqual(rows[0]["uhf_channel"], "24")


if __name__ == "__main__":
    unittest.main()
