import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_test_locations, load_channel_map, load_config


class FieldTestLocationPlanTest(unittest.TestCase):
    def test_required_jakarta_test_points_exist(self):
        locations = load_test_locations()
        self.assertEqual(
            set(locations),
            {"monas", "bundaran_hi", "cp_taman_anggrek", "stasiun_juanda", "indomaret_tomang"},
        )

    def test_each_location_is_model_aligned_placeholder(self):
        locations = load_test_locations()
        for key, loc in locations.items():
            self.assertEqual(loc["frequency_mhz"], 514.0, key)
            self.assertEqual(loc["channel_name"], "TVRI_JOGLO_514MHZ", key)
            self.assertEqual(loc["rx_antenna_height_m"], 1.5, key)
            self.assertIsNone(loc["radio_planner_dbuvm"], key)
            self.assertIn("isi koordinat GPS aktual", loc["notes"], key)

    def test_channel_defaults_to_radioplanner_band(self):
        cfg = load_config()
        channels = load_channel_map()
        self.assertEqual(cfg.channel_name, "TVRI_JOGLO_514MHZ")
        self.assertIn("TVRI_JOGLO_514MHZ", channels)
        self.assertEqual(channels["TVRI_JOGLO_514MHZ"]["frequency_mhz"], 514.0)
        self.assertEqual(channels["TVRI_JOGLO_514MHZ"]["bandwidth_mhz"], 8.0)


if __name__ == "__main__":
    unittest.main()
