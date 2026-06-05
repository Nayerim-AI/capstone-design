import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import load_config
from dvbt2_core import Dvbt2SdrConfig, list_sdr_available_gains, print_measurement_result, run_single_measurement
from gps_reader import GPSReader
from logger import system_logger, log_measurement_data
from telegram_bot import run_telegram_bot


def parse_args():
    parser = argparse.ArgumentParser(description="DVB-T2 Coverage Analyzer Portable")
    parser.add_argument("--mode", choices=["cli", "telegram"], default="cli")
    parser.add_argument("--freq", type=float, default=None, help="Frekuensi center dalam MHz.")
    parser.add_argument("--repeat", type=int, default=5, help="Jumlah pengulangan pengukuran CLI.")
    parser.add_argument("--list-gains", action="store_true", help="Tampilkan gain RTL-SDR yang tersedia.")
    return parser.parse_args()


def build_sdr_config(app_config):
    return Dvbt2SdrConfig(
        sample_rate=float(app_config.sample_rate_hz),
        measurement_bw_hz=float(app_config.measurement_bandwidth_hz),
        gain_db=float(app_config.sdr_gain_db),
        calibration_offset_db=app_config.calibration_offset_db,
        calibration_mode=app_config.calibration_mode,
        cable_loss_db=app_config.cable_loss_db,
        antenna_factor_db_per_m=app_config.antenna_factor_db_per_m,
        komdigi_lower_dbuvm=app_config.komdigi_lower_dbuvm,
        komdigi_upper_dbuvm=app_config.komdigi_upper_dbuvm,
        rx_antenna_height_m=app_config.rx_antenna_height_m,
    )


def run_cli(app_config, args):
    freq_mhz = args.freq if args.freq is not None else app_config.frequency_mhz
    system_logger.info("Mode CLI, frekuensi %.3f MHz, repeat %s", freq_mhz, args.repeat)
    result = run_single_measurement(
        freq_mhz=freq_mhz,
        repeat=args.repeat,
        config=build_sdr_config(app_config),
    )
    result.update({
        "channel_name": app_config.channel_name,
        "measurement_mode": app_config.measurement_mode,
        "calibration_mode": app_config.calibration_mode,
        "calibration_source": app_config.calibration_source,
        "komdigi_lower_dbuvm": app_config.komdigi_lower_dbuvm,
        "komdigi_upper_dbuvm": app_config.komdigi_upper_dbuvm,
    })
    print_measurement_result(result)
    log_measurement_data({
        "latitude": None,
        "longitude": None,
        "gps_fix": False,
        "gps_satellites": None,
        "channel_name": app_config.channel_name,
        "frequency_mhz": freq_mhz,
        "sdr_gain_db": result.get("actual_gain_db", app_config.sdr_gain_db),
        "sample_rate_hz": int(app_config.sample_rate_hz),
        "measurement_bandwidth_hz": int(app_config.measurement_bandwidth_hz),
        "measurement_mode": app_config.measurement_mode,
        "raw_bandpower_db": result.get("average_bandpower_db"),
        "calibration_mode": app_config.calibration_mode,
        "calibration_offset_db": app_config.calibration_offset_db,
        "calibration_source": app_config.calibration_source,
        "antenna_factor_db_per_m": app_config.antenna_factor_db_per_m,
        "cable_loss_db": app_config.cable_loss_db,
        "rx_antenna_height_m": app_config.rx_antenna_height_m,
        "total_correction_db": result.get("total_correction_db"),
        "field_strength_est_dbuvm": result.get("field_strength_dbuvm_est"),
        "komdigi_lower_dbuvm": app_config.komdigi_lower_dbuvm,
        "komdigi_upper_dbuvm": app_config.komdigi_upper_dbuvm,
        "category": result.get("komdigi_category"),
        "telegram_status": "N/A_CLI",
        "telegram_delay_s": None,
        "notes": result.get("error") or "CLI measurement; GPS not attached to CLI path",
    })
    if result.get("error"):
        return 1
    return 0


def run_telegram(app_config):
    if not app_config.telegram_token:
        system_logger.error("TELEGRAM_TOKEN kosong. Isi token di file .env.")
        return 1

    gps = None
    if app_config.gps_enabled:
        gps = GPSReader(
            port=app_config.gps_port,
            baudrate=app_config.gps_baudrate,
            enabled=app_config.gps_enabled,
        )
        gps_ready = gps.connect()
        if not gps_ready:
            system_logger.warning("GPS tidak tersedia. Bot tetap berjalan tanpa koordinat GPS.")
    else:
        system_logger.info("GPS nonaktif melalui GPS_ENABLED=false.")

    try:
        run_telegram_bot(app_config, gps)
        return 0
    except RuntimeError as exc:
        system_logger.error("%s", exc)
        return 1
    finally:
        if gps is not None:
            gps.stop()


def main():
    args = parse_args()

    try:
        app_config = load_config()
    except ValueError as exc:
        system_logger.error("%s", exc)
        return 1

    if args.list_gains:
        gains = list_sdr_available_gains()
        if gains is None:
            print("Available gains tidak bisa dibaca. Cek RTL-SDR/pyrtlsdr.")
            return 1
        print("Available RTL-SDR gain values (dB):")
        print(", ".join(str(g) for g in gains))
        return 0

    if not app_config.env_exists:
        system_logger.warning(".env belum dibuat. Menggunakan default dan environment saat ini.")
        system_logger.warning("Buat dari template: cp .env.example .env")

    if args.mode == "cli":
        return run_cli(app_config, args)
    if args.mode == "telegram":
        return run_telegram(app_config)

    system_logger.error("Mode operasi tidak dikenal: %s", args.mode)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
