import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import load_config, load_measurement_config, load_channel_map
from dvbt2_core import (
    Dvbt2SdrConfig,
    calculate_total_correction_db,
    classify_komdigi_reference,
    estimate_field_strength,
)
from logger import MEASUREMENT_LOG_HEADER, log_measurement_data
from telegram_bot import format_measurement_dashboard


class P0MeasurementPipelineTest(unittest.TestCase):
    def test_measurement_config_can_be_read(self):
        cfg = load_config()
        self.assertEqual(cfg.measurement_mode, "center_bandpower_1p8mhz")
        self.assertEqual(cfg.calibration_mode, "raw")
        self.assertEqual(cfg.calibration_offset_db, 0.0)
        self.assertEqual(cfg.calibration_source, "none")
        self.assertEqual(cfg.komdigi_lower_dbuvm, 39.5)
        self.assertEqual(cfg.komdigi_upper_dbuvm, 76.2)
        self.assertEqual(cfg.rx_antenna_height_m, 1.5)
        self.assertIsNone(cfg.antenna_factor_db_per_m)
        self.assertGreater(cfg.sdr_gain_db, 0)

    def test_channel_map_can_be_read_without_invented_local_frequency(self):
        channels = load_channel_map()
        self.assertIn("TEST_CH", channels)
        self.assertEqual(channels["TEST_CH"]["frequency_mhz"], 0.0)
        self.assertEqual(channels["TEST_CH"]["bandwidth_mhz"], 8.0)

    def test_csv_header_is_required_schema(self):
        self.assertEqual(MEASUREMENT_LOG_HEADER, [
            "timestamp","latitude","longitude","gps_fix","gps_satellites","channel_name","frequency_mhz","sdr_gain_db","sample_rate_hz","measurement_bandwidth_hz","measurement_mode","raw_bandpower_db","calibration_mode","calibration_offset_db","calibration_source","antenna_factor_db_per_m","cable_loss_db","rx_antenna_height_m","total_correction_db","field_strength_est_dbuvm","komdigi_lower_dbuvm","komdigi_upper_dbuvm","category","telegram_status","telegram_delay_s","notes"
        ])

    def test_komdigi_category_thresholds(self):
        self.assertEqual(classify_komdigi_reference(39.49, 39.5, 76.2), "DI_BAWAH_ACUAN")
        self.assertEqual(classify_komdigi_reference(39.5, 39.5, 76.2), "DALAM_RENTANG_ACUAN")
        self.assertEqual(classify_komdigi_reference(76.2, 39.5, 76.2), "DALAM_RENTANG_ACUAN")
        self.assertEqual(classify_komdigi_reference(76.21, 39.5, 76.2), "DI_ATAS_ACUAN")

    def test_field_strength_estimate_uses_raw_plus_total_correction(self):
        total = calculate_total_correction_db(3.0, cable_loss_db=1.5, antenna_factor_db_per_m=12.0)
        self.assertEqual(total, 16.5)
        self.assertEqual(estimate_field_strength(40.0, total), 56.5)

    def test_unknown_antenna_factor_is_not_forced(self):
        total = calculate_total_correction_db(2.0, cable_loss_db=1.0, antenna_factor_db_per_m=None)
        self.assertEqual(total, 3.0)

    def test_offset_script_computes_radioplanner_model_aligned_offset(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "compute_model_aligned_offset.py"
        result = subprocess.run(
            [sys.executable, str(script), "--raw-bandpower-db", "42.5", "--radioplanner-dbuvm", "55.0"],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("offset_model_db = 12.50 dB", result.stdout)
        self.assertIn("CALIBRATION_OFFSET_DB=12.50", result.stdout)
        self.assertIn("bukan kalibrasi absolut", result.stdout)

    def test_telegram_message_contains_p0_fields_and_disclaimer(self):
        cfg = SimpleNamespace(
            gps_enabled=True, gps_port="/dev/ttyUSB0", gps_baudrate=4800,
            calibration_offset_db=0.0, calibration_mode="raw", measurement_mode="center_bandpower_1p8mhz",
        )
        rf = {
            "timestamp": "2026-06-04 14:00:00 WIB",
            "channel_name": "TEST_CH", "frequency_mhz": 514.0,
            "field_strength_est_dbuvm": 50.0, "category": "DALAM_RENTANG_ACUAN",
            "actual_gain_db": 19.7, "sdr_gain_db": 19.7,
            "measurement_mode": "center_bandpower_1p8mhz", "calibration_mode": "raw",
            "average_bandpower_db": 50.0, "std_deviation_db": 0.1,
            "sample_rate_msps": 2.048, "measurement_bw_mhz": 1.8,
        }
        gps = {"has_fix": True, "status": "Valid", "latitude": -6.1, "longitude": 106.8, "gps_time": "01:00:00 UTC", "maps_url": "https://maps.google.com/?q=-6.1,106.8"}
        msg = format_measurement_dashboard(rf, gps, cfg)
        self.assertIn("TEST_CH / 514.000 MHz", msg)
        self.assertIn("50.00 dBµV/m", msg)
        self.assertIn("DALAM_RENTANG_ACUAN", msg)
        self.assertIn("-6.100000", msg)
        self.assertIn("Gain SDR", msg)
        self.assertIn("Kalibrasi Mode", msg)
        self.assertIn("center_bandpower_1p8mhz", msg)
        self.assertIn("bukan kalibrasi absolut", msg)

    def test_pipeline_does_not_crash_if_gps_no_fix_and_logs_measurement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "measurement_log.csv"
            row = log_measurement_data({
                "latitude": None, "longitude": None, "gps_fix": False, "gps_satellites": None,
                "channel_name": "TEST_CH", "frequency_mhz": 514.0, "sdr_gain_db": 19.7,
                "sample_rate_hz": 2048000, "measurement_bandwidth_hz": 1800000,
                "measurement_mode": "center_bandpower_1p8mhz", "raw_bandpower_db": 42.0,
                "calibration_mode": "raw", "calibration_offset_db": 0.0, "calibration_source": "none",
                "antenna_factor_db_per_m": None, "cable_loss_db": 0.0, "rx_antenna_height_m": 1.5,
                "total_correction_db": 0.0, "field_strength_est_dbuvm": 42.0,
                "komdigi_lower_dbuvm": 39.5, "komdigi_upper_dbuvm": 76.2,
                "category": "DALAM_RENTANG_ACUAN", "telegram_status": "FAILED",
                "telegram_delay_s": None, "notes": "GPS belum fix",
            }, csv_path=path)
            self.assertFalse(row["gps_fix"])
            rows = list(csv.DictReader(path.open()))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["telegram_status"], "FAILED")
            self.assertEqual(rows[0]["notes"], "GPS belum fix")


if __name__ == "__main__":
    unittest.main()
