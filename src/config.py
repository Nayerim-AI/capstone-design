import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import yaml
except ImportError:
    yaml = None


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
MEASUREMENT_CONFIG_FILE = ROOT_DIR / "config" / "measurement_config.yaml"
CHANNEL_CONFIG_FILE = ROOT_DIR / "config" / "dvbt2_channels.yaml"
LOCATION_CONFIG_FILE = ROOT_DIR / "config" / "test_locations.yaml"


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
    sdr_gain_db: float
    sample_rate_hz: int
    measurement_bandwidth_hz: int
    measurement_mode: str
    channel_name: str
    frequency_mhz: float
    rx_antenna_height_m: float
    cable_loss_db: float
    antenna_factor_db_per_m: float | None
    calibration_mode: str
    calibration_source: str
    komdigi_lower_dbuvm: float
    komdigi_upper_dbuvm: float


def _get_float(name, default):
    value = os.getenv(name, str(default))
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Nilai {name} harus berupa angka. Nilai saat ini: {value}") from exc


def _get_optional_float(name, default):
    value = os.getenv(name, None)
    if value is None:
        return default
    value = value.strip()
    if value.lower() in {"", "none", "null"}:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Nilai {name} harus berupa angka/null. Nilai saat ini: {value}") from exc


def _get_int(name, default):
    value = os.getenv(name, str(default))
    try:
        return int(float(value))
    except ValueError as exc:
        raise ValueError(f"Nilai {name} harus berupa integer. Nilai saat ini: {value}") from exc


def _get_bool(name, default):
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Nilai {name} harus true atau false. Nilai saat ini: {value}")


def _load_simple_env(env_path):
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parse_simple_yaml(text):
    data = {}
    stack = [data]
    indent_stack = [0]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if ":" not in line:
            continue
        while indent_stack and indent < indent_stack[-1]:
            stack.pop(); indent_stack.pop()
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            new = {}
            stack[-1][key] = new
            stack.append(new)
            indent_stack.append(indent + 2)
        else:
            if value.lower() in {"null", "none"}:
                parsed = None
            elif value.lower() in {"true", "false"}:
                parsed = value.lower() == "true"
            else:
                parsed = value.strip('"').strip("'")
                try:
                    parsed = float(parsed) if "." in parsed else int(parsed)
                except ValueError:
                    pass
            stack[-1][key] = parsed
    return data


def _load_yaml_file(path):
    path = Path(path)
    if not path.exists():
        return {}
    if yaml is not None:
        loaded = yaml.safe_load(path.read_text())
        return loaded or {}
    return _parse_simple_yaml(path.read_text())


def load_measurement_config(config_path=MEASUREMENT_CONFIG_FILE):
    return _load_yaml_file(config_path)


def load_channel_map(channel_path=CHANNEL_CONFIG_FILE):
    data = _load_yaml_file(channel_path)
    channels = data.get("channels", data or {})
    return channels or {}


def load_test_locations(location_path=LOCATION_CONFIG_FILE):
    data = _load_yaml_file(location_path)
    locations = data.get("locations", data or {})
    return locations or {}


def _apply_measurement_config_to_env(measurement_config):
    for key, value in measurement_config.items():
        if value is None:
            os.environ.setdefault(key, "null")
        else:
            os.environ.setdefault(key, str(value))


def load_config(env_path=ENV_FILE, measurement_config_path=MEASUREMENT_CONFIG_FILE):
    env_path = Path(env_path)
    env_exists = env_path.exists()

    measurement_config = load_measurement_config(measurement_config_path)
    _apply_measurement_config_to_env(measurement_config)

    if env_exists:
        if load_dotenv is not None:
            load_dotenv(env_path)
        else:
            _load_simple_env(env_path)

    calibration_mode = os.getenv("CALIBRATION_MODE", "raw").strip()
    allowed_modes = {"raw", "radioplanner_model_aligned", "reference_instrument_calibrated"}
    if calibration_mode not in allowed_modes:
        raise ValueError(f"CALIBRATION_MODE harus salah satu dari {sorted(allowed_modes)}")

    frequency_mhz = _get_float("FREQUENCY_MHZ", _get_float("DEFAULT_FREQ_MHZ", 514.0))

    return AppConfig(
        telegram_token=os.getenv("TELEGRAM_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        default_freq_mhz=_get_float("DEFAULT_FREQ_MHZ", frequency_mhz),
        calibration_offset_db=_get_float("CALIBRATION_OFFSET_DB", 0.0),
        gps_enabled=_get_bool("GPS_ENABLED", True),
        gps_port=os.getenv("GPS_PORT", "/dev/ttyUSB0").strip(),
        gps_baudrate=_get_int("GPS_BAUDRATE", 4800),
        env_exists=env_exists,
        sdr_gain_db=_get_float("SDR_GAIN_DB", 19.7),
        sample_rate_hz=_get_int("SAMPLE_RATE_HZ", 2048000),
        measurement_bandwidth_hz=_get_int("MEASUREMENT_BANDWIDTH_HZ", 1800000),
        measurement_mode=os.getenv("MEASUREMENT_MODE", "center_bandpower_1p8mhz").strip(),
        channel_name=os.getenv("CHANNEL_NAME", "TEST_CH").strip(),
        frequency_mhz=frequency_mhz,
        rx_antenna_height_m=_get_float("RX_ANTENNA_HEIGHT_M", 1.5),
        cable_loss_db=_get_float("CABLE_LOSS_DB", 0.0),
        antenna_factor_db_per_m=_get_optional_float("ANTENNA_FACTOR_DB_PER_M", None),
        calibration_mode=calibration_mode,
        calibration_source=os.getenv("CALIBRATION_SOURCE", "none").strip(),
        komdigi_lower_dbuvm=_get_float("KOMDIGI_LOWER_DBUVM", 39.5),
        komdigi_upper_dbuvm=_get_float("KOMDIGI_UPPER_DBUVM", 76.2),
    )
