import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

import database
import logger as measurement_logger
import main


class DatabaseStorageTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self._close_connection()
        database.DB_PATH = Path(self.tmpdir.name) / "capstone.db"
        database.init_db()

    def tearDown(self):
        self._close_connection()
        database.DB_PATH = self.original_db_path
        self.tmpdir.cleanup()

    @staticmethod
    def _close_connection():
        connection = getattr(database._local, "conn", None)
        if connection is not None:
            connection.close()
        database._local.conn = None

    def test_measurement_and_raw_readings_round_trip(self):
        measurement_id = database.insert_measurement(
            {
                "timestamp": "2026-07-30 18:00:00",
                "frequency_mhz": 570.0,
                "raw_bandpower_db": 32.57,
                "min_bandpower_db": 32.53,
                "max_bandpower_db": 32.60,
                "std_deviation_db": 0.03,
                "komdigi_category": "DALAM_RENTANG_ACUAN",
            },
            raw_measurements=[32.57, 32.60, 32.53],
        )

        stored = database.get_measurement_by_id(measurement_id)

        self.assertEqual(stored["frequency_mhz"], 570.0)
        self.assertEqual(stored["raw_measurements"], [32.57, 32.60, 32.53])
        self.assertEqual(database.get_stats()["total_measurements"], 1)
        self.assertEqual(database.get_stats()["total_raw_readings"], 3)

    def test_csv_category_alias_is_preserved_during_backfill_insert(self):
        measurement_id = database.insert_measurement(
            {
                "timestamp": "2026-07-30 18:05:00",
                "frequency_mhz": 570.0,
                "category": "DALAM_RENTANG_ACUAN",
            }
        )

        stored = database.get_measurement_by_id(measurement_id)

        self.assertEqual(stored["komdigi_category"], "DALAM_RENTANG_ACUAN")

    def test_missing_timestamp_uses_current_timestamp(self):
        measurement_id = database.insert_measurement({"frequency_mhz": 570.0})

        stored = database.get_measurement_by_id(measurement_id)

        self.assertRegex(stored["timestamp"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_invalid_raw_reading_rolls_back_measurement(self):
        with self.assertRaises(ValueError):
            database.insert_measurement(
                {
                    "timestamp": "2026-07-30 18:15:00",
                    "frequency_mhz": 570.0,
                },
                raw_measurements=[32.57, "invalid"],
            )

        self.assertEqual(database.get_stats()["total_measurements"], 0)
        self.assertEqual(database.get_stats()["total_raw_readings"], 0)


class DatabaseLoggerTest(unittest.TestCase):
    def test_database_schema_is_initialized_before_insert(self):
        with (
            patch.object(measurement_logger, "_db_init") as init_db,
            patch.object(measurement_logger, "_db_insert", return_value=7) as insert,
        ):
            result = measurement_logger.log_measurement_to_db(
                {"timestamp": "2026-07-30 18:10:00", "frequency_mhz": 570.0},
                [32.57],
            )

        self.assertEqual(result, 7)
        init_db.assert_called_once_with()
        insert.assert_called_once()


class CliDatabaseMappingTest(unittest.TestCase):
    def test_cli_passes_measurement_statistics_and_categories_to_database(self):
        result = {
            "average_bandpower_db": 32.57,
            "min_bandpower_db": 32.53,
            "max_bandpower_db": 32.60,
            "std_deviation_db": 0.03,
            "actual_gain_db": 19.7,
            "total_correction_db": 26.4,
            "field_strength_dbuvm_est": 58.97,
            "komdigi_category": "DALAM_RENTANG_ACUAN",
            "signal_quality": "Baik",
            "raw_measurements": [32.57, 32.60, 32.53],
        }
        app_config = SimpleNamespace(
            sdr_gain_db=19.7,
            sample_rate_hz=2_048_000,
            measurement_bandwidth_hz=1_800_000,
            measurement_mode="center_bandpower_1p8mhz",
            calibration_mode="reference_instrument_calibrated",
            calibration_offset_db=26.4,
            calibration_source="HD Ranger",
            antenna_factor_db_per_m=None,
            cable_loss_db=0.0,
            rx_antenna_height_m=1.5,
            komdigi_lower_dbuvm=39.5,
            komdigi_upper_dbuvm=76.2,
        )
        args = SimpleNamespace(repeat=3)
        channel = {
            "uhf_channel": 33,
            "network": "Referensi",
            "scan_priority": "single",
        }

        with (
            patch.object(main, "build_sdr_config", return_value=object()),
            patch.object(main, "run_single_measurement", return_value=result),
            patch.object(main, "print_measurement_result"),
            patch.object(main, "log_measurement_data"),
            patch.object(main, "log_field_scan_data"),
            patch.object(main, "log_measurement_to_db") as log_db,
        ):
            exit_code = main._run_one(
                app_config,
                570.0,
                "UHF33",
                channel=channel,
                args=args,
            )

        row, raw_readings = log_db.call_args.args
        self.assertEqual(exit_code, 0)
        self.assertEqual(row["min_bandpower_db"], 32.53)
        self.assertEqual(row["max_bandpower_db"], 32.60)
        self.assertEqual(row["std_deviation_db"], 0.03)
        self.assertEqual(row["komdigi_category"], "DALAM_RENTANG_ACUAN")
        self.assertEqual(row["signal_quality"], "Baik")
        self.assertEqual(raw_readings, [32.57, 32.60, 32.53])


if __name__ == "__main__":
    unittest.main()
