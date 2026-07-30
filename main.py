import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import load_channel_map, load_config, load_test_locations
from dvbt2_core import Dvbt2SdrConfig, list_sdr_available_gains, print_measurement_result, run_single_measurement
from gps_reader import GPSReader
from logger import log_field_scan_data, log_measurement_data, log_measurement_to_db, system_logger
from telegram_bot import run_telegram_bot


def parse_args():
    parser = argparse.ArgumentParser(description="DVB-T2 Coverage Analyzer Portable")
    parser.add_argument("--mode", choices=["cli", "telegram"], default="cli")
    parser.add_argument("--freq", type=float, default=None, help="Frekuensi center dalam MHz untuk scan single/manual.")
    parser.add_argument("--repeat", type=int, default=5, help="Jumlah pengulangan per frekuensi CLI.")
    parser.add_argument("--location", default=None, help="ID lokasi dari config/test_locations.yaml, contoh: monas")
    parser.add_argument("--scan", choices=["single", "baseline", "optional", "all"], default="single", help="Profil scan CLI.")
    parser.add_argument("--channel", default=None, help="Channel ID dari config/dvbt2_channels.yaml untuk scan single.")
    parser.add_argument("--list-locations", action="store_true", help="Tampilkan daftar lokasi uji dan keluar.")
    parser.add_argument("--list-channels", action="store_true", help="Tampilkan daftar channel/MUX dan keluar.")
    parser.add_argument("--route-order", action="store_true", help="Tampilkan urutan rute yang disarankan dan keluar.")
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


def _resolve_location(args):
    if not args.location:
        return None
    locations = load_test_locations()
    if args.location not in locations:
        raise ValueError(f"Lokasi {args.location!r} tidak ada di config/test_locations.yaml")
    loc = dict(locations[args.location])
    loc["id"] = args.location
    return loc


def _ordered_channels(scan_mode, channel_id=None):
    channels = load_channel_map()
    if scan_mode == "single":
        if channel_id:
            if channel_id not in channels:
                raise ValueError(f"Channel {channel_id!r} tidak ada di config/dvbt2_channels.yaml")
            return [(channel_id, dict(channels[channel_id]))]
        return []

    wanted = {"baseline"} if scan_mode == "baseline" else {"optional"} if scan_mode == "optional" else {"baseline", "optional"}
    picked = []
    for key, channel in channels.items():
        priority = str(channel.get("scan_priority", "")).lower()
        if priority in wanted:
            picked.append((key, dict(channel)))
    return sorted(picked, key=lambda item: (item[1].get("scan_priority") != "baseline", float(item[1].get("frequency_mhz", 0))))


def _measurement_note(location, channel, error=None):
    if error:
        return error
    parts = []
    if location:
        parts.extend([
            f"location_id={location.get('id')}",
            f"site_name={location.get('name')}",
            f"initial_lat={location.get('initial_lat')}",
            f"initial_lon={location.get('initial_lon')}",
            f"route_order={location.get('route_order')}",
        ])
    if channel:
        parts.extend([
            f"uhf_channel={channel.get('uhf_channel')}",
            f"network={channel.get('network')}",
            f"scan_priority={channel.get('scan_priority')}",
        ])
    parts.append("GPS aktual belum diambil di CLI path; isi dari GPS/HP saat lapangan")
    parts.append("relative SDR center-bandpower; bukan kalibrasi absolut")
    return "; ".join(str(p) for p in parts if p is not None)


def _run_one(app_config, freq_mhz, channel_name, location=None, channel=None, args=None):
    result = run_single_measurement(
        freq_mhz=freq_mhz,
        repeat=args.repeat if args else 5,
        config=build_sdr_config(app_config),
    )
    result.update({
        "channel_name": channel_name,
        "measurement_mode": app_config.measurement_mode,
        "calibration_mode": app_config.calibration_mode,
        "calibration_source": app_config.calibration_source,
        "komdigi_lower_dbuvm": app_config.komdigi_lower_dbuvm,
        "komdigi_upper_dbuvm": app_config.komdigi_upper_dbuvm,
    })
    print_measurement_result(result)

    common = {
        "latitude": location.get("latitude") if location else None,
        "longitude": location.get("longitude") if location else None,
        "gps_fix": False,
        "gps_satellites": None,
        "channel_name": channel_name,
        "frequency_mhz": freq_mhz,
        "sdr_gain_db": result.get("actual_gain_db", app_config.sdr_gain_db),
        "sample_rate_hz": int(app_config.sample_rate_hz),
        "measurement_bandwidth_hz": int(app_config.measurement_bandwidth_hz),
        "measurement_mode": app_config.measurement_mode,
        "raw_bandpower_db": result.get("average_bandpower_db"),
        "min_bandpower_db": result.get("min_bandpower_db"),
        "max_bandpower_db": result.get("max_bandpower_db"),
        "std_deviation_db": result.get("std_deviation_db"),
        "calibration_mode": app_config.calibration_mode,
        "calibration_offset_db": app_config.calibration_offset_db,
        "calibration_source": app_config.calibration_source,
        "antenna_factor_db_per_m": app_config.antenna_factor_db_per_m,
        "cable_loss_db": app_config.cable_loss_db,
        "rx_antenna_height_m": location.get("rx_antenna_height_m", app_config.rx_antenna_height_m) if location else app_config.rx_antenna_height_m,
        "total_correction_db": result.get("total_correction_db"),
        "field_strength_est_dbuvm": result.get("field_strength_dbuvm_est"),
        "komdigi_lower_dbuvm": app_config.komdigi_lower_dbuvm,
        "komdigi_upper_dbuvm": app_config.komdigi_upper_dbuvm,
        "komdigi_category": result.get("komdigi_category"),
        "category": result.get("komdigi_category"),
        "signal_quality": result.get("signal_quality"),
        "telegram_status": "N/A_CLI",
        "telegram_delay_s": None,
        "notes": _measurement_note(location, channel, result.get("error")),
    }
    log_measurement_data(common)
    log_measurement_to_db(common, result.get("raw_measurements"))
    log_field_scan_data({
        "site_id": location.get("id") if location else None,
        "site_name": location.get("name") if location else None,
        "initial_lat": location.get("initial_lat") if location else None,
        "initial_lon": location.get("initial_lon") if location else None,
        "lat": location.get("latitude") if location else None,
        "lon": location.get("longitude") if location else None,
        "uhf_channel": channel.get("uhf_channel") if channel else None,
        "frequency_mhz": freq_mhz,
        "channel_name": channel_name,
        "network": channel.get("network") if channel else None,
        "scan_priority": channel.get("scan_priority") if channel else None,
        "lock_status": "unknown",
        "signal_strength": result.get("average_bandpower_db"),
        "field_strength_est_dbuvm": result.get("field_strength_dbuvm_est"),
        "signal_quality": None,
        "snr_mer_db": None,
        "ber": None,
        "per": None,
        "antenna_type": "capung",
        "antenna_height_m": location.get("rx_antenna_height_m", app_config.rx_antenna_height_m) if location else app_config.rx_antenna_height_m,
        "antenna_direction_deg": None,
        "receiver_gain_db": result.get("actual_gain_db", app_config.sdr_gain_db),
        "calibration_mode": app_config.calibration_mode,
        "radio_planner_dbuvm": location.get("radio_planner_dbuvm") if location else None,
        "radio_planner_margin_db": None,
        "delta_vs_radioplanner_db": None,
        "measurement_mode": app_config.measurement_mode,
        "notes": _measurement_note(location, channel, result.get("error")),
    })
    return 1 if result.get("error") else 0


def run_cli(app_config, args):
    location = _resolve_location(args)
    channels = _ordered_channels(args.scan, args.channel)

    if args.scan == "single" and not channels:
        freq_mhz = args.freq if args.freq is not None else app_config.frequency_mhz
        channel_name = app_config.channel_name
        channel = {"channel_name": channel_name, "frequency_mhz": freq_mhz, "scan_priority": "single"}
        channels = [(channel_name, channel)]

    system_logger.info("Mode CLI, lokasi %s, scan %s, jumlah channel %s", location.get("id") if location else "manual", args.scan, len(channels))
    exit_code = 0
    for channel_id, channel in channels:
        freq_mhz = args.freq if args.scan == "single" and args.freq is not None else float(channel.get("frequency_mhz"))
        channel_name = channel.get("channel_name", channel_id)
        print(f"\n=== Scan {channel_name} / UHF {channel.get('uhf_channel')} / {freq_mhz:.3f} MHz ===")
        exit_code = max(exit_code, _run_one(app_config, freq_mhz, channel_name, location, channel, args))
    return exit_code


def run_telegram(app_config):
    if not app_config.telegram_token:
        system_logger.error("TELEGRAM_TOKEN kosong. Isi token di file .env.")
        return 1
    gps = None
    if app_config.gps_enabled:
        gps = GPSReader(port=app_config.gps_port, baudrate=app_config.gps_baudrate, enabled=app_config.gps_enabled)
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


def _print_locations(route_order=False):
    items = list(load_test_locations().items())
    if route_order:
        items.sort(key=lambda kv: int(kv[1].get("route_order", 999)))
    print("Daftar lokasi uji:")
    for key, loc in items:
        print(f"- {key}: {loc.get('name')} | initial={loc.get('initial_lat')},{loc.get('initial_lon')} | order={loc.get('route_order')} | rp={loc.get('radio_planner_dbuvm')}")


def _print_channels():
    print("Daftar channel/MUX:")
    for key, ch in _ordered_channels("all"):
        print(f"- {key}: UHF {ch.get('uhf_channel')} | {ch.get('frequency_mhz')} MHz | {ch.get('network')} | {ch.get('scan_priority')}")


def main():
    args = parse_args()
    try:
        app_config = load_config()
    except ValueError as exc:
        system_logger.error("%s", exc)
        return 1

    if args.list_locations or args.route_order:
        _print_locations(route_order=args.route_order)
        return 0
    if args.list_channels:
        _print_channels()
        return 0
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
        try:
            return run_cli(app_config, args)
        except ValueError as exc:
            system_logger.error("%s", exc)
            return 1
    if args.mode == "telegram":
        return run_telegram(app_config)
    system_logger.error("Mode operasi tidak dikenal: %s", args.mode)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
