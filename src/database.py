"""
Database module for DVB-T2 Capstone Design measurements.

Stores measurement data and raw field strength readings in SQLite.
Database file: data/capstone.db

Tables:
  - measurements: one row per measurement scan
  - raw_measurements: individual raw bandpower readings (one row per reading)
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import logging

logger = logging.getLogger("CapstoneDvbT2.DB")

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "capstone.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_type    TEXT NOT NULL DEFAULT 'cli',
            location_id     TEXT,
            location_name   TEXT,
            scan_mode       TEXT,
            started_at      TEXT NOT NULL,
            ended_at        TEXT,
            notes           TEXT
        );

        CREATE TABLE IF NOT EXISTS measurements (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id              INTEGER REFERENCES scan_sessions(id),

            -- Timestamp & location
            timestamp               TEXT NOT NULL,
            latitude                REAL,
            longitude               REAL,
            gps_fix                 INTEGER,
            gps_satellites          INTEGER,

            -- Channel / frequency
            channel_name            TEXT,
            frequency_mhz           REAL NOT NULL,
            uhf_channel             INTEGER,
            network                 TEXT,
            scan_priority           TEXT,

            -- SDR configuration
            sdr_gain_db             REAL,
            sample_rate_hz          INTEGER,
            measurement_bandwidth_hz INTEGER,
            measurement_mode        TEXT,

            -- Raw bandpower (average of raw_measurements)
            raw_bandpower_db        REAL,
            min_bandpower_db        REAL,
            max_bandpower_db        REAL,
            std_deviation_db        REAL,

            -- Calibration corrections
            calibration_mode        TEXT,
            calibration_offset_db   REAL,
            calibration_source      TEXT,
            antenna_factor_db_per_m REAL,
            cable_loss_db           REAL,
            rx_antenna_height_m     REAL,
            total_correction_db     REAL,

            -- Final field strength estimate
            field_strength_est_dbuvm REAL,
            komdigi_lower_dbuvm     REAL,
            komdigi_upper_dbuvm     REAL,
            komdigi_category        TEXT,
            signal_quality          TEXT,

            -- Telegram delivery
            telegram_status         TEXT,
            telegram_delay_s        REAL,

            -- Site info (from field scan)
            site_id                 TEXT,
            site_name               TEXT,
            initial_lat             REAL,
            initial_lon             REAL,
            antenna_type            TEXT,
            antenna_direction_deg   REAL,
            radio_planner_dbuvm     REAL,
            radio_planner_margin_db REAL,
            delta_vs_radioplanner_db REAL,
            snr_mer_db              REAL,
            ber                     REAL,
            per                     REAL,

            -- Error / notes
            error                   TEXT,
            notes                   TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_measurements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            measurement_id  INTEGER NOT NULL REFERENCES measurements(id) ON DELETE CASCADE,
            reading_index   INTEGER NOT NULL,
            bandpower_db    REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_measurements_timestamp
            ON measurements(timestamp);
        CREATE INDEX IF NOT EXISTS idx_measurements_session
            ON measurements(session_id);
        CREATE INDEX IF NOT EXISTS idx_raw_measurements_meas
            ON raw_measurements(measurement_id);
    """)
    conn.commit()


def _now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# All SQL binding parameters for the measurements table
_MEASUREMENT_PARAMS = [
    "session_id",
    "timestamp",
    "latitude",
    "longitude",
    "gps_fix",
    "gps_satellites",
    "channel_name",
    "frequency_mhz",
    "uhf_channel",
    "network",
    "scan_priority",
    "sdr_gain_db",
    "sample_rate_hz",
    "measurement_bandwidth_hz",
    "measurement_mode",
    "raw_bandpower_db",
    "min_bandpower_db",
    "max_bandpower_db",
    "std_deviation_db",
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
    "komdigi_category",
    "signal_quality",
    "telegram_status",
    "telegram_delay_s",
    "site_id",
    "site_name",
    "initial_lat",
    "initial_lon",
    "antenna_type",
    "antenna_direction_deg",
    "radio_planner_dbuvm",
    "radio_planner_margin_db",
    "delta_vs_radioplanner_db",
    "snr_mer_db",
    "ber",
    "per",
    "error",
    "notes",
]

# Columns that should be stored as REAL (float)
_FLOAT_COLUMNS = {
    "latitude", "longitude", "frequency_mhz", "sdr_gain_db",
    "raw_bandpower_db", "min_bandpower_db", "max_bandpower_db",
    "std_deviation_db", "calibration_offset_db", "antenna_factor_db_per_m",
    "cable_loss_db", "rx_antenna_height_m", "total_correction_db",
    "field_strength_est_dbuvm", "komdigi_lower_dbuvm", "komdigi_upper_dbuvm",
    "telegram_delay_s", "initial_lat", "initial_lon",
    "antenna_direction_deg", "radio_planner_dbuvm", "radio_planner_margin_db",
    "delta_vs_radioplanner_db", "snr_mer_db", "ber", "per",
}

# Columns that should be stored as INTEGER
_INT_COLUMNS = {
    "gps_fix", "gps_satellites", "sample_rate_hz", "measurement_bandwidth_hz",
    "uhf_channel",
}


def _coerce(key: str, value) -> object:
    """Coerce a value to the appropriate type for SQLite."""
    if value is None:
        return None
    if key in _INT_COLUMNS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if key in _FLOAT_COLUMNS:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return str(value)


def _build_insert_data(data: dict, session_id: int = None) -> dict:
    """Build a complete data dict with all SQL parameters coerced correctly."""
    data = dict(data)
    if "komdigi_category" not in data and "category" in data:
        data["komdigi_category"] = data["category"]
    prepared = {}
    for param in _MEASUREMENT_PARAMS:
        if param == "session_id":
            prepared[param] = session_id
        elif param == "timestamp" and not data.get(param):
            prepared[param] = _now_timestamp()
        elif param in data:
            prepared[param] = _coerce(param, data[param])
        else:
            prepared[param] = None
    return prepared


def insert_measurement(
    data: dict,
    raw_measurements: list = None,
    session_id: int = None,
) -> int:
    """Insert a measurement row and its raw bandpower readings.

    Args:
        data: Dictionary with measurement fields (same keys as CSV headers).
        raw_measurements: List of individual raw bandpower_db readings.
        session_id: Optional scan session ID for grouping.

    Returns:
        The new measurement row ID.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        prepared = _build_insert_data(data, session_id)

        cur.execute("""
        INSERT INTO measurements (
            session_id, timestamp, latitude, longitude, gps_fix, gps_satellites,
            channel_name, frequency_mhz, uhf_channel, network, scan_priority,
            sdr_gain_db, sample_rate_hz, measurement_bandwidth_hz, measurement_mode,
            raw_bandpower_db, min_bandpower_db, max_bandpower_db, std_deviation_db,
            calibration_mode, calibration_offset_db, calibration_source,
            antenna_factor_db_per_m, cable_loss_db, rx_antenna_height_m, total_correction_db,
            field_strength_est_dbuvm, komdigi_lower_dbuvm, komdigi_upper_dbuvm,
            komdigi_category, signal_quality,
            telegram_status, telegram_delay_s,
            site_id, site_name, initial_lat, initial_lon,
            antenna_type, antenna_direction_deg,
            radio_planner_dbuvm, radio_planner_margin_db, delta_vs_radioplanner_db,
            snr_mer_db, ber, per,
            error, notes
        ) VALUES (
            :session_id, :timestamp, :latitude, :longitude, :gps_fix, :gps_satellites,
            :channel_name, :frequency_mhz, :uhf_channel, :network, :scan_priority,
            :sdr_gain_db, :sample_rate_hz, :measurement_bandwidth_hz, :measurement_mode,
            :raw_bandpower_db, :min_bandpower_db, :max_bandpower_db, :std_deviation_db,
            :calibration_mode, :calibration_offset_db, :calibration_source,
            :antenna_factor_db_per_m, :cable_loss_db, :rx_antenna_height_m, :total_correction_db,
            :field_strength_est_dbuvm, :komdigi_lower_dbuvm, :komdigi_upper_dbuvm,
            :komdigi_category, :signal_quality,
            :telegram_status, :telegram_delay_s,
            :site_id, :site_name, :initial_lat, :initial_lon,
            :antenna_type, :antenna_direction_deg,
            :radio_planner_dbuvm, :radio_planner_margin_db, :delta_vs_radioplanner_db,
            :snr_mer_db, :ber, :per,
            :error, :notes
        )
        """, prepared)

        measurement_id = cur.lastrowid

        if raw_measurements:
            rows = [
                (measurement_id, i, float(val))
                for i, val in enumerate(raw_measurements)
            ]
            cur.executemany(
                "INSERT INTO raw_measurements (measurement_id, reading_index, bandpower_db) VALUES (?, ?, ?)",
                rows,
            )

        conn.commit()
        return measurement_id
    except Exception:
        conn.rollback()
        raise


def create_session(session_type: str = "cli", location_id: str = None,
                   location_name: str = None, scan_mode: str = None,
                   notes: str = None) -> int:
    """Create a new scan session and return its ID."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scan_sessions (session_type, location_id, location_name, scan_mode, started_at, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_type, location_id, location_name, scan_mode, _now_timestamp(), notes))
    conn.commit()
    return cur.lastrowid


def close_session(session_id: int):
    """Mark a scan session as ended."""
    conn = _get_conn()
    conn.execute("UPDATE scan_sessions SET ended_at = ? WHERE id = ?",
                 (_now_timestamp(), session_id))
    conn.commit()


def get_recent_measurements(limit: int = 20, offset: int = 0) -> list:
    """Get recent measurements with their raw data counts."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.*, COUNT(r.id) as raw_count
        FROM measurements m
        LEFT JOIN raw_measurements r ON r.measurement_id = m.id
        GROUP BY m.id
        ORDER BY m.timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    return [dict(row) for row in cur.fetchall()]


def get_measurement_by_id(measurement_id: int) -> dict:
    """Get a single measurement with its raw readings."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM measurements WHERE id = ?", (measurement_id,))
    row = cur.fetchone()
    if not row:
        return None
    result = dict(row)

    cur.execute(
        "SELECT bandpower_db FROM raw_measurements WHERE measurement_id = ? ORDER BY reading_index",
        (measurement_id,),
    )
    result["raw_measurements"] = [r["bandpower_db"] for r in cur.fetchall()]
    return result


def get_raw_measurements(measurement_id: int) -> list:
    """Get raw bandpower readings for a measurement."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT reading_index, bandpower_db FROM raw_measurements WHERE measurement_id = ? ORDER BY reading_index",
        (measurement_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def get_sessions(limit: int = 10) -> list:
    """Get recent scan sessions."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, COUNT(m.id) as measurement_count
        FROM scan_sessions s
        LEFT JOIN measurements m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.started_at DESC
        LIMIT ?
    """, (limit,))
    return [dict(row) for row in cur.fetchall()]


def get_stats() -> dict:
    """Get summary statistics from the database."""
    conn = _get_conn()
    cur = conn.cursor()
    stats = {}

    cur.execute("SELECT COUNT(*) FROM measurements")
    stats["total_measurements"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM scan_sessions")
    stats["total_sessions"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM raw_measurements")
    stats["total_raw_readings"] = cur.fetchone()[0]

    cur.execute("""
        SELECT MIN(timestamp), MAX(timestamp) FROM measurements
    """)
    row = cur.fetchone()
    stats["first_measurement"] = row[0]
    stats["last_measurement"] = row[1]

    cur.execute("""
        SELECT COUNT(DISTINCT channel_name) FROM measurements WHERE channel_name IS NOT NULL
    """)
    stats["unique_channels"] = cur.fetchone()[0]

    cur.execute("""
        SELECT komdigi_category, COUNT(*) as cnt
        FROM measurements
        WHERE komdigi_category IS NOT NULL
        GROUP BY komdigi_category
        ORDER BY cnt DESC
    """)
    stats["category_counts"] = {row["komdigi_category"]: row["cnt"] for row in cur.fetchall()}

    return stats


def export_measurement_json(measurement_id: int, output_path: str = None) -> str:
    """Export a single measurement as JSON (.measure file).

    This creates a self-contained .measure file with all raw data.
    """
    data = get_measurement_by_id(measurement_id)
    if not data:
        raise ValueError(f"Measurement {measurement_id} not found")

    for key in ("timestamp",):
        if key in data and data[key]:
            try:
                data[key] = datetime.strptime(str(data[key]), "%Y-%m-%d %H:%M:%S").isoformat()
            except ValueError:
                pass

    output = json.dumps(data, indent=2, default=str)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)

    return output
