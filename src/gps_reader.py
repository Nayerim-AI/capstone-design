import threading
import time

import pynmea2
import serial

from logger import log_gps_data, system_logger


NMEA_PREFIXES = ("$GPGGA", "$GNGGA", "$GPRMC", "$GNRMC")


def _base_gps_result(enabled=True, available=False, status="Tidak Tersedia", message=None):
    return {
        "enabled": bool(enabled),
        "available": bool(available),
        "has_fix": False,
        "status": status,
        "latitude": None,
        "longitude": None,
        "gps_time": None,
        "maps_url": None,
        "raw_type": "NONE",
        "message": message or "",
    }


def disabled_gps_result():
    return _base_gps_result(
        enabled=False,
        available=False,
        status="Nonaktif",
        message="GPS dinonaktifkan melalui konfigurasi",
    )


class GPSReader:
    def __init__(self, port="/dev/ttyUSB0", baudrate=4800, enabled=True):
        self.port = port
        self.baudrate = baudrate
        self.enabled = enabled
        self.serial_conn = None
        self.is_running = False
        self.thread = None

        self.current_result = _base_gps_result(
            enabled=enabled,
            available=False,
            status="Belum Fix" if enabled else "Nonaktif",
            message="GPS belum dibaca" if enabled else "GPS dinonaktifkan melalui konfigurasi",
        )
        self.lock = threading.Lock()

    def connect(self):
        if not self.enabled:
            with self.lock:
                self.current_result = disabled_gps_result()
            return False

        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.2)
            with self.lock:
                self.current_result = _base_gps_result(
                    enabled=True,
                    available=True,
                    status="Belum Fix",
                    message="Port GPS terbuka, menunggu NMEA",
                )
            system_logger.info("Berhasil terhubung ke GPS di port %s @ %s baud", self.port, self.baudrate)
            return True
        except serial.SerialException as exc:
            message = f"GPS tidak tersedia di {self.port}: {exc}"
            with self.lock:
                self.current_result = _base_gps_result(
                    enabled=True,
                    available=False,
                    status="Tidak Tersedia",
                    message=message,
                )
            system_logger.warning(message)
            return False

    def start(self):
        if not self.enabled:
            with self.lock:
                self.current_result = disabled_gps_result()
            return False

        if self.is_running:
            return True

        if not self.serial_conn and not self.connect():
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        system_logger.info("Thread GPS Reader dimulai.")
        return True

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        system_logger.info("GPS Reader dihentikan.")

    def _read_loop(self):
        while self.is_running:
            try:
                line = self.serial_conn.readline().decode("ascii", errors="replace").strip()
                if line:
                    self.parse_nmea_line(line)
            except Exception as exc:
                message = f"Error pembacaan GPS: {exc}"
                with self.lock:
                    self.current_result = _base_gps_result(
                        enabled=True,
                        available=False,
                        status="Tidak Tersedia",
                        message=message,
                    )
                system_logger.warning(message)
                time.sleep(1)

    def parse_nmea_line(self, line):
        if not line.startswith(NMEA_PREFIXES):
            return False

        raw_type = line[1:6]
        try:
            msg = pynmea2.parse(line)
        except pynmea2.ParseError:
            with self.lock:
                self.current_result = _base_gps_result(
                    enabled=True,
                    available=True,
                    status="Belum Fix",
                    message="NMEA terbaca tetapi format/checksum belum valid",
                )
                self.current_result["raw_type"] = raw_type
            return False

        result = self._result_from_message(msg, raw_type)
        with self.lock:
            self.current_result = result

        if result["has_fix"]:
            log_gps_data(result["latitude"], result["longitude"])
            system_logger.debug("GPS fix: %s, %s", result["latitude"], result["longitude"])
            return True

        system_logger.info("NMEA terbaca tetapi GPS belum fix")
        return False

    def _result_from_message(self, msg, raw_type):
        latitude = getattr(msg, "latitude", None)
        longitude = getattr(msg, "longitude", None)
        gps_time = _format_gps_time(getattr(msg, "timestamp", None))
        sentence_type = getattr(msg, "sentence_type", "")

        has_fix = False
        message = "NMEA terbaca tetapi GPS belum fix"

        if sentence_type == "RMC":
            status_value = getattr(msg, "status", "")
            has_fix = status_value == "A" and bool(latitude) and bool(longitude)
            if status_value == "V":
                message = "RMC status V, GPS belum fix"
        elif sentence_type == "GGA":
            fix_quality = str(getattr(msg, "gps_qual", "0"))
            has_fix = fix_quality != "0" and bool(latitude) and bool(longitude)
            if fix_quality == "0":
                message = "GGA fix_quality 0, GPS belum fix"

        if has_fix:
            maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
            return {
                "enabled": True,
                "available": True,
                "has_fix": True,
                "status": "Valid",
                "latitude": latitude,
                "longitude": longitude,
                "gps_time": gps_time,
                "maps_url": maps_url,
                "raw_type": raw_type,
                "message": "GPS fix valid",
            }

        result = _base_gps_result(
            enabled=True,
            available=True,
            status="Belum Fix",
            message=message,
        )
        result["raw_type"] = raw_type
        return result

    def read_location(self, timeout_s=1.0, max_lines=8):
        if not self.enabled:
            return disabled_gps_result()

        if not self.serial_conn:
            if not self.connect():
                return self.get_current_location()

        deadline = time.monotonic() + timeout_s
        lines_read = 0
        while time.monotonic() < deadline and lines_read < max_lines:
            try:
                raw = self.serial_conn.readline()
            except serial.SerialException as exc:
                message = f"GPS tidak tersedia di {self.port}: {exc}"
                with self.lock:
                    self.current_result = _base_gps_result(
                        enabled=True,
                        available=False,
                        status="Tidak Tersedia",
                        message=message,
                    )
                system_logger.warning(message)
                break

            if not raw:
                continue

            lines_read += 1
            line = raw.decode("ascii", errors="replace").strip()
            self.parse_nmea_line(line)
            snapshot = self.get_current_location()
            if snapshot["has_fix"]:
                return snapshot

        return self.get_current_location()

    def get_current_location(self):
        with self.lock:
            return dict(self.current_result)


def _format_gps_time(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return f"{value.strftime('%H:%M:%S')} UTC"
    return f"{value} UTC"
