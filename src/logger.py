import csv
import logging
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"


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


def log_gps_data(latitude, longitude, altitude=None, speed=None):
    DATA_DIR.mkdir(exist_ok=True)
    csv_path = DATA_DIR / "gps_log.csv"
    file_exists = csv_path.is_file()

    try:
        with csv_path.open(mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Timestamp", "Latitude", "Longitude", "Altitude", "Speed"])

            writer.writerow(
                [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    latitude,
                    longitude,
                    altitude,
                    speed,
                ]
            )
    except Exception as exc:
        system_logger.error("Gagal menulis log GPS ke CSV: %s", exc)
