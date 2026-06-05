import csv
import logging
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"
MEASUREMENT_LOG_PATH = DATA_DIR / "measurement_log.csv"
FIELD_SCAN_LOG_PATH = DATA_DIR / "field_scan_log.csv"

MEASUREMENT_LOG_HEADER = [
    "timestamp",
    "latitude",
    "longitude",
    "gps_fix",
    "gps_satellites",
    "channel_name",
    "frequency_mhz",
    "sdr_gain_db",
    "sample_rate_hz",
    "measurement_bandwidth_hz",
    "measurement_mode",
    "raw_bandpower_db",
    "calibration_mode",
    "calibration_offset_db",
    "calibration_source",
    "antenna_factor_db_per_m",
    "cable_loss_db",
    "rx_antenna_height_m",
    "total_correction_db",
    "field_strength_est_dbuvm",
    "komdigi_lower_dbuvm",
    "komdigi_upper_dbuvm",
    "category",
    "telegram_status",
    "telegram_delay_s",
    "notes",
]

FIELD_SCAN_HEADER = [
    "timestamp",
    "site_id",
    "site_name",
    "initial_lat",
    "initial_lon",
    "lat",
    "lon",
    "uhf_channel",
    "frequency_mhz",
    "channel_name",
    "network",
    "scan_priority",
    "lock_status",
    "signal_strength",
    "field_strength_est_dbuvm",
    "signal_quality",
    "snr_mer_db",
    "ber",
    "per",
    "antenna_type",
    "antenna_height_m",
    "antenna_direction_deg",
    "receiver_gain_db",
    "calibration_mode",
    "radio_planner_dbuvm",
    "radio_planner_margin_db",
    "delta_vs_radioplanner_db",
    "measurement_mode",
    "notes",
]


def setup_logger(name="CapstoneDvbT2", level=logging.INFO):
    LOG_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(LOG_DIR / "system.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


system_logger = setup_logger()


def _now_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return value


def _append_csv(header, data, csv_path):
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    row = {key: _normalize_value(data.get(key)) for key in header}
    row["timestamp"] = row.get("timestamp") or _now_timestamp()
    file_exists = csv_path.is_file()
    try:
        with csv_path.open(mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        return row
    except Exception as exc:
        system_logger.error("Gagal menulis CSV %s: %s", csv_path.name, exc)
        raise


def log_measurement_data(measurement, csv_path=MEASUREMENT_LOG_PATH):
    DATA_DIR.mkdir(exist_ok=True)
    return _append_csv(MEASUREMENT_LOG_HEADER, measurement, csv_path)


def log_field_scan_data(scan_data, csv_path=FIELD_SCAN_LOG_PATH):
    DATA_DIR.mkdir(exist_ok=True)
    return _append_csv(FIELD_SCAN_HEADER, scan_data, csv_path)


def log_gps_data(latitude, longitude, altitude=None, speed=None):
    DATA_DIR.mkdir(exist_ok=True)
    csv_path = DATA_DIR / "gps_log.csv"
    file_exists = csv_path.is_file()
    try:
        with csv_path.open(mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Timestamp", "Latitude", "Longitude", "Altitude", "Speed"])
            writer.writerow([_now_timestamp(), latitude, longitude, altitude, speed])
    except Exception as exc:
        system_logger.error("Gagal menulis log GPS ke CSV: %s", exc)
