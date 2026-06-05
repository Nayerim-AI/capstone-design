import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_channel_map, load_test_locations


class FieldTestLocationPlanTest(unittest.TestCase):
    def test_required_jakarta_test_points_exist(self):
        locations = load_test_locations()
        self.assertEqual(
            set(locations),
            {"monas", "bundaran_hi", "cp_taman_anggrek", "stasiun_juanda", "indomaret_tomang"},
        )

    def test_each_location_has_route_order_and_reference_placeholder(self):
        locations = load_test_locations()
        self.assertEqual(
            {k: v["route_order"] for k, v in locations.items()},
            {"stasiun_juanda": 1, "monas": 2, "bundaran_hi": 3, "indomaret_tomang": 4, "cp_taman_anggrek": 5},
        )
        for key, loc in locations.items():
            self.assertEqual(loc["rx_antenna_height_m"], 1.5, key)
            self.assertIsNone(loc["radio_planner_dbuvm"], key)
            self.assertIsNotNone(loc["initial_lat"], key)
            self.assertIsNotNone(loc["initial_lon"], key)

    def test_legacy_radioplanner_channel_still_present(self):
        channels = load_channel_map()
        self.assertIn("TVRI_JOGLO_514MHZ", channels)
        self.assertEqual(channels["TVRI_JOGLO_514MHZ"]["frequency_mhz"], 514.0)
        self.assertEqual(channels["TVRI_JOGLO_514MHZ"]["bandwidth_mhz"], 8.0)


if __name__ == "__main__":
    unittest.main()
