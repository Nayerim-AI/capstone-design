import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"


@dataclass(frozen=True)
class AppConfig:
    telegram_token: str
    telegram_chat_id: str
    default_freq_mhz: float
    calibration_offset_db: float
    gps_enabled: bool
    gps_port: str
    gps_baudrate: int
    env_exists: bool


def _get_float(name, default):
    value = os.getenv(name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Nilai {name} harus berupa angka. Nilai saat ini: {value}") from exc


def _get_int(name, default):
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Nilai {name} harus berupa integer. Nilai saat ini: {value}") from exc


def _get_bool(name, default):
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Nilai {name} harus true atau false. Nilai saat ini: {value}")


def load_config(env_path=ENV_FILE):
    env_path = Path(env_path)
    env_exists = env_path.exists()
    if env_exists:
        if load_dotenv is not None:
            load_dotenv(env_path)
        else:
            _load_simple_env(env_path)

    return AppConfig(
        telegram_token=os.getenv("TELEGRAM_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        default_freq_mhz=_get_float("DEFAULT_FREQ_MHZ", 514.0),
        calibration_offset_db=_get_float("CALIBRATION_OFFSET_DB", 0.0),
        gps_enabled=_get_bool("GPS_ENABLED", True),
        gps_port=os.getenv("GPS_PORT", "/dev/ttyUSB0").strip(),
        gps_baudrate=_get_int("GPS_BAUDRATE", 4800),
        env_exists=env_exists,
    )


def _load_simple_env(env_path):
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
