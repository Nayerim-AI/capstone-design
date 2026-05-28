import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from telegram_bot import format_measurement_dashboard, format_status_dashboard  # noqa: E402


def config():
    return SimpleNamespace(
        default_freq_mhz=514.0,
        calibration_offset_db=0.0,
        gps_enabled=True,
        gps_port="/dev/ttyUSB0",
        gps_baudrate=4800,
    )


def rf_result(**overrides):
    data = {
        "frequency_mhz": 514.0,
        "sample_rate_msps": 2.048,
        "measurement_bw_mhz": 1.8,
        "gain_db": 19.7,
        "average_bandpower_db": 50.26,
        "std_deviation_db": 0.03,
        "field_strength_dbuvm_est": 50.26,
        "signal_quality": "Cukup",
    }
    data.update(overrides)
    return data


def gps_result(status="Valid", **overrides):
    data = {
        "enabled": True,
        "available": True,
        "has_fix": status == "Valid",
        "status": status,
        "latitude": -7.123456 if status == "Valid" else None,
        "longitude": 109.123456 if status == "Valid" else None,
        "gps_time": "12:35:19 UTC" if status == "Valid" else None,
        "maps_url": "https://maps.google.com/?q=-7.123456,109.123456"
        if status == "Valid"
        else None,
        "raw_type": "GPRMC",
        "message": "GPS fix valid",
    }
    data.update(overrides)
    return data


class TelegramFormatTest(unittest.TestCase):
    def test_measurement_dashboard_with_valid_gps_and_complete_rf(self):
        message = format_measurement_dashboard(rf_result(), gps_result(), config())

        self.assertIn("📡 DVB-T2 Coverage Analyzer", message)
        self.assertIn("Frekuensi              : 514.000 MHz", message)
        self.assertIn("Bandpower Relatif     : 50.26 dB", message)
        self.assertIn("Estimasi Field Strength: 50.26 dBµV/m", message)
        self.assertIn("Kualitas Sinyal       : Cukup", message)
        self.assertIn("Sample Rate           : 2.048 MS/s", message)
        self.assertIn("Bandwidth Ukur        : 1.800 MHz", message)
        self.assertIn("Gain SDR              : 19.7 dB", message)
        self.assertIn("Std Deviasi           : 0.03 dB", message)
        self.assertIn("Status                : Valid", message)
        self.assertIn("Latitude              : -7.123456", message)
        self.assertIn("Longitude             : 109.123456", message)
        self.assertIn("Waktu GPS             : 12:35:19 UTC", message)
        self.assertIn("Maps                  : https://maps.google.com/?q=-7.123456,109.123456", message)

    def test_measurement_dashboard_with_gps_no_fix(self):
        message = format_measurement_dashboard(rf_result(), gps_result("Belum Fix"), config())

        self.assertIn("Status                : Belum Fix", message)
        self.assertIn("Latitude              : Tidak tersedia", message)
        self.assertIn("Longitude             : Tidak tersedia", message)
        self.assertIn("Waktu GPS             : Tidak tersedia", message)
        self.assertIn("Maps                  : Tidak tersedia", message)

    def test_measurement_dashboard_with_disabled_gps(self):
        cfg = config()
        cfg.gps_enabled = False
        gps = gps_result(
            "Nonaktif",
            enabled=False,
            available=False,
            raw_type="NONE",
            message="GPS dinonaktifkan",
        )

        message = format_measurement_dashboard(rf_result(), gps, cfg)

        self.assertIn("Status                : Nonaktif", message)
        self.assertIn("Latitude              : Tidak tersedia", message)
        self.assertIn("Maps                  : Tidak tersedia", message)

    def test_measurement_dashboard_with_gps_port_unavailable(self):
        gps = gps_result(
            "Tidak Tersedia",
            available=False,
            raw_type="NONE",
            message="GPS tidak tersedia",
        )

        message = format_measurement_dashboard(rf_result(), gps, config())

        self.assertIn("Status                : Tidak Tersedia", message)
        self.assertIn("Latitude              : Tidak tersedia", message)
        self.assertIn("Maps                  : Tidak tersedia", message)

    def test_measurement_dashboard_with_rf_error(self):
        message = format_measurement_dashboard(
            rf_result(
                average_bandpower_db=None,
                field_strength_dbuvm_est=None,
                std_deviation_db=None,
                signal_quality="Error",
                error="RTL-SDR tidak ditemukan",
            ),
            gps_result("Belum Fix"),
            config(),
        )

        self.assertIn("RTL-SDR               : Error", message)
        self.assertIn("RF Error              : RTL-SDR tidak ditemukan", message)
        self.assertIn("Bandpower Relatif     : Tidak tersedia dB", message)

    def test_status_dashboard(self):
        message = format_status_dashboard(
            {"rtl_sdr": "OK", "mode": "Telegram Polling"},
            gps_result("Belum Fix"),
            config(),
        )

        self.assertIn("✅ Sistem Aktif", message)
        self.assertIn("RTL-SDR        : OK", message)
        self.assertIn("GPS            : Belum Fix", message)
        self.assertIn("GPS Baudrate   : 4800", message)
        self.assertIn("Frekuensi      : 514.000 MHz", message)
        self.assertIn("Kalibrasi      : 0.00 dB", message)


if __name__ == "__main__":
    unittest.main()
