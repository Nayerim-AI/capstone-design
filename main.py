import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import ENV_FILE, load_config
from dvbt2_core import Dvbt2SdrConfig, print_measurement_result, run_single_measurement
from gps_reader import GPSReader
from logger import system_logger
from telegram_bot import run_telegram_bot


def parse_args():
    parser = argparse.ArgumentParser(description="DVB-T2 Coverage Analyzer Portable")
    parser.add_argument("--mode", choices=["cli", "telegram"], default="cli")
    parser.add_argument("--freq", type=float, default=None, help="Frekuensi center dalam MHz.")
    parser.add_argument("--repeat", type=int, default=5, help="Jumlah pengulangan pengukuran CLI.")
    return parser.parse_args()


def build_sdr_config(app_config):
    return Dvbt2SdrConfig(calibration_offset_db=app_config.calibration_offset_db)


def run_cli(app_config, args):
    freq_mhz = args.freq if args.freq is not None else app_config.default_freq_mhz
    system_logger.info("Mode CLI, frekuensi %.3f MHz, repeat %s", freq_mhz, args.repeat)
    result = run_single_measurement(
        freq_mhz=freq_mhz,
        repeat=args.repeat,
        config=build_sdr_config(app_config),
    )
    print_measurement_result(result)
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
