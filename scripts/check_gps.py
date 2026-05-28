import argparse
import os
import subprocess
import time
from pathlib import Path

import serial

try:
    import pynmea2
except ImportError:
    pynmea2 = None


DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUDRATE = 9600
DEFAULT_DURATION = 20
SCAN_BAUDRATES = [4800, 9600, 19200, 38400, 57600, 115200]
NMEA_PREFIXES = ("$GPGGA", "$GNGGA", "$GPRMC", "$GNRMC")
MAX_SAMPLE_LINES = 10


def check_port_exists(port):
    return Path(port).exists()


def check_permission(port):
    return os.access(port, os.R_OK | os.W_OK)


def check_port_busy(port):
    try:
        result = subprocess.run(
            ["fuser", "-v", port],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except FileNotFoundError:
        return False, "fuser tidak tersedia; status busy tidak bisa dicek otomatis."
    except subprocess.TimeoutExpired:
        return False, "fuser timeout; status busy tidak bisa dicek otomatis."

    output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    return result.returncode == 0, output


def read_serial_lines(port, baudrate, duration):
    deadline = time.monotonic() + duration
    lines = []
    byte_count = 0

    with serial.Serial(port=port, baudrate=baudrate, timeout=0, write_timeout=1) as ser:
        ser.reset_input_buffer()
        buffer = bytearray()

        while time.monotonic() < deadline:
            waiting = ser.in_waiting
            chunk = ser.read(waiting or 1)
            if not chunk:
                time.sleep(0.05)
                continue

            byte_count += len(chunk)
            buffer.extend(chunk)

            while b"\n" in buffer or b"\r" in buffer:
                split_positions = [pos for pos in (buffer.find(b"\n"), buffer.find(b"\r")) if pos >= 0]
                split_at = min(split_positions)
                raw_line = bytes(buffer[:split_at])
                del buffer[: split_at + 1]

                line = raw_line.decode("ascii", errors="replace").strip()
                if line:
                    lines.append(line)
                    if len(lines) >= 100:
                        return lines, byte_count

        if buffer:
            line = bytes(buffer).decode("ascii", errors="replace").strip()
            if line:
                lines.append(line)

    return lines, byte_count


def detect_nmea(lines):
    return [line for line in lines if line.startswith(NMEA_PREFIXES)]


def parse_gps_fix(lines):
    if pynmea2 is None:
        return {
            "parser_available": False,
            "has_nmea": bool(detect_nmea(lines)),
            "has_fix": False,
            "fix_status": "NMEA terdeteksi, tetapi pynmea2 belum terinstall.",
        }

    has_nmea = False
    last_status = "NMEA tidak terdeteksi."

    for line in lines:
        if not line.startswith(NMEA_PREFIXES):
            continue

        has_nmea = True
        try:
            msg = pynmea2.parse(line)
        except pynmea2.ParseError:
            last_status = "NMEA terdeteksi, tetapi checksum/format tidak valid."
            continue

        sentence_type = getattr(msg, "sentence_type", "")
        latitude = getattr(msg, "latitude", None)
        longitude = getattr(msg, "longitude", None)
        timestamp = getattr(msg, "timestamp", None)

        if sentence_type == "RMC":
            status_value = getattr(msg, "status", "")
            if status_value == "A" and latitude and longitude:
                return {
                    "parser_available": True,
                    "has_nmea": True,
                    "has_fix": True,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": timestamp,
                    "fix_status": "RMC status A, fix valid.",
                }
            if status_value == "V":
                last_status = "RMC status V, GPS belum fix."

        if sentence_type == "GGA":
            fix_quality = str(getattr(msg, "gps_qual", "0"))
            if fix_quality != "0" and latitude and longitude:
                return {
                    "parser_available": True,
                    "has_nmea": True,
                    "has_fix": True,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": timestamp,
                    "fix_status": f"GGA fix_quality {fix_quality}, fix valid.",
                }
            if fix_quality == "0":
                last_status = "GGA fix_quality 0, GPS belum fix."

    return {
        "parser_available": True,
        "has_nmea": has_nmea,
        "has_fix": False,
        "fix_status": last_status,
    }


def print_header(port, baudrate, duration):
    print("=== GPS Serial Diagnostic ===")
    print(f"Port      : {port}")
    print(f"Baudrate  : {baudrate}")
    print(f"Duration  : {duration:g}s")


def print_manual_help(port, baudrate):
    print("")
    print("Manual test:")
    print(f"stty -F {port} {baudrate} cs8 -cstopb -parenb raw -echo")
    print(f"timeout 20 cat {port}")
    print("")
    print("Wiring reminder:")
    print("GPS VCC -> 3.3V/5V sesuai modul")
    print("GPS GND -> GND PL2303")
    print("GPS TX  -> RX PL2303")
    print("GPS RX  -> TX PL2303 opsional")


def print_no_data_notes():
    print("Catatan   : Port bisa dibuka, tetapi tidak ada data serial masuk.")
    print("Kemungkinan:")
    print("- PL2303 terdeteksi tetapi belum tersambung ke modul GPS.")
    print("- TX GPS belum masuk ke RX PL2303.")
    print("- GPS belum mendapat power.")
    print("- Baudrate GPS berbeda.")
    print("- Device ini hanya USB-to-Serial, bukan GPS USB langsung.")


def print_sample_lines(title, lines):
    if not lines:
        return
    print(title)
    for line in lines[:MAX_SAMPLE_LINES]:
        print(line)


def diagnose_port(port, baudrate, duration, show_header=True, show_manual=True):
    if show_header:
        print_header(port, baudrate, duration)

    if not check_port_exists(port):
        print("Status    : PORT_NOT_FOUND")
        print("Catatan   : Device serial tidak ditemukan.")
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "PORT_NOT_FOUND"

    if not check_permission(port):
        print("Status    : PERMISSION_DENIED")
        print("Catatan   : User saat ini tidak punya akses baca/tulis ke port serial.")
        print("Solusi    : sudo usermod -aG dialout $USER")
        print("           Lalu logout/login atau reboot.")
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "PERMISSION_DENIED"

    is_busy, busy_detail = check_port_busy(port)
    if is_busy:
        print("Status    : PORT_BUSY")
        print("Catatan   : Port sedang dipakai proses lain.")
        if busy_detail:
            print(busy_detail)
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "PORT_BUSY"
    if busy_detail:
        print(f"Warning   : {busy_detail}")

    try:
        lines, byte_count = read_serial_lines(port, baudrate, duration)
    except serial.SerialException as exc:
        message = str(exc)
        if "Permission denied" in message:
            print("Status    : PERMISSION_DENIED")
            print("Catatan   : SerialException permission denied.")
            print("Solusi    : sudo usermod -aG dialout $USER")
            print("           Lalu logout/login atau reboot.")
            if show_manual:
                print_manual_help(port, baudrate)
            return 1, "PERMISSION_DENIED"

        print("Status    : SERIAL_OPEN_ERROR")
        print(f"Catatan   : {exc}")
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "SERIAL_OPEN_ERROR"

    if byte_count == 0 and not lines:
        print("Status    : PORT_OPEN_NO_DATA")
        print_no_data_notes()
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "PORT_OPEN_NO_DATA"

    nmea_lines = detect_nmea(lines)
    if not nmea_lines:
        print("Status    : SERIAL_DATA_NOT_NMEA")
        print("Catatan   : Ada data serial masuk, tetapi bukan kalimat NMEA GPS yang dikenali.")
        print(f"Bytes     : {byte_count}")
        print_sample_lines("Sample raw data:", lines)
        if show_manual:
            print_manual_help(port, baudrate)
        return 1, "SERIAL_DATA_NOT_NMEA"

    print_sample_lines("Sample NMEA:", nmea_lines)
    parsed = parse_gps_fix(nmea_lines)

    if not parsed["parser_available"]:
        print("Status    : NMEA_DETECTED_PARSER_MISSING")
        print("Catatan   : NMEA terdeteksi, tetapi pynmea2 tidak tersedia untuk parsing fix.")
        print("Install   : pip3 install pynmea2")
        if show_manual:
            print_manual_help(port, baudrate)
        return 0, "NMEA_DETECTED_PARSER_MISSING"

    if parsed["has_fix"]:
        print("Status    : GPS_FIX_VALID")
        print(f"Latitude  : {parsed['latitude']:.6f}")
        print(f"Longitude : {parsed['longitude']:.6f}")
        print(f"Timestamp : {parsed.get('timestamp')}")
        print(f"Fix status: {parsed['fix_status']}")
        if show_manual:
            print_manual_help(port, baudrate)
        return 0, "GPS_FIX_VALID"

    print("Status    : NMEA_NO_FIX")
    print(f"Fix status: {parsed['fix_status']}")
    print("Catatan   : NMEA valid terbaca, tetapi GPS belum mendapat fix koordinat.")
    if show_manual:
        print_manual_help(port, baudrate)
    return 0, "NMEA_NO_FIX"


def scan_baudrates(port, duration):
    print("=== GPS Serial Diagnostic ===")
    print(f"Port      : {port}")
    print(f"Scan      : {', '.join(str(rate) for rate in SCAN_BAUDRATES)}")
    print(f"Duration  : {duration:g}s per baudrate")

    final_code = 1
    final_status = "PORT_OPEN_NO_DATA"
    for baudrate in SCAN_BAUDRATES:
        print("")
        print(f"--- Baudrate {baudrate} ---")
        code, status = diagnose_port(
            port,
            baudrate,
            duration,
            show_header=False,
            show_manual=False,
        )
        final_status = status
        if code == 0:
            final_code = 0
            break
        if status in {"PORT_NOT_FOUND", "PERMISSION_DENIED", "PORT_BUSY"}:
            final_code = 1
            break

    print("")
    print(f"Scan result: {final_status}")
    print_manual_help(port, DEFAULT_BAUDRATE)
    return final_code


def main():
    parser = argparse.ArgumentParser(description="Diagnostik GPS serial/NMEA.")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baudrate", type=int, default=None)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    parser.add_argument("--scan", action="store_true", help="Scan baudrate umum GPS.")
    args = parser.parse_args()

    try:
        if args.scan or args.baudrate is None:
            return scan_baudrates(args.port, args.duration)

        code, _status = diagnose_port(args.port, args.baudrate, args.duration)
        return code
    except KeyboardInterrupt:
        print("")
        print("Status    : INTERRUPTED")
        print("Catatan   : Dihentikan manual oleh pengguna.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
