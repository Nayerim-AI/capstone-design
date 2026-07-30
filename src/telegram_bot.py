from datetime import datetime, timedelta, timezone
import time as _time

from telegram import Update
from telegram.error import NetworkError, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from config import load_channel_map, load_test_locations
from dvbt2_core import (
    Dvbt2SdrConfig,
    RtlSdr,
    classify_komdigi_reference,
    get_calibration_disclaimer,
    run_single_measurement,
)
from gps_reader import disabled_gps_result
from logger import log_field_scan_data, log_measurement_data, log_measurement_to_db, system_logger


WIB = timezone(timedelta(hours=7))


def _fmt_number(value, digits=2, fallback="Tidak tersedia"):
    if value is None:
        return fallback
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return fallback


def _fmt_status(value, fallback="Tidak tersedia"):
    return value if value not in (None, "") else fallback


def _status_rf(rf_result):
    if not rf_result:
        return "Error"
    if rf_result.get("error"):
        return "Error"
    return "OK"


def _gps_result_for_config(config):
    if not config.gps_enabled:
        return disabled_gps_result()
    return {
        "enabled": True,
        "available": False,
        "has_fix": False,
        "status": "Tidak Tersedia",
        "latitude": None,
        "longitude": None,
        "gps_time": None,
        "maps_url": None,
        "raw_type": "NONE",
        "message": "GPS reader belum tersedia",
    }


def format_measurement_dashboard(rf_result, gps_result, config):
    rf_result = rf_result or {}
    gps_result = gps_result or _gps_result_for_config(config)
    now_wib = datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
    gps_has_fix = bool(gps_result.get("has_fix"))
    gps_time = gps_result.get("gps_time") if gps_has_fix else None
    maps_url = gps_result.get("maps_url") if gps_has_fix else None

    channel_name = rf_result.get("channel_name", config.channel_name if hasattr(config, "channel_name") else "unknown")
    frequency_display = f"{channel_name} / {_fmt_number(rf_result.get('frequency_mhz'), 3)} MHz"
    calibration_mode = rf_result.get("calibration_mode") or config.calibration_mode if hasattr(config, "calibration_mode") else "raw"
    measurement_mode = rf_result.get("measurement_mode") or config.measurement_mode if hasattr(config, "measurement_mode") else "unknown"
    disclaimer = get_calibration_disclaimer(calibration_mode)

    lines = [
        "📡 DVB-T2 Coverage Analyzer",
        "",
        "🕒 Waktu Sistem:",
        now_wib,
        "",
        "📻 Pengukuran RF",
        f"Kanal                  : {frequency_display}",
        f"Frekuensi              : {_fmt_number(rf_result.get('frequency_mhz'), 3)} MHz",
        f"Bandpower Relatif     : {_fmt_number(rf_result.get('average_bandpower_db'))} dB",
        (
            "Estimasi Field Strength: "
            f"{_fmt_number(rf_result.get('field_strength_dbuvm_est', rf_result.get('field_strength_est_dbuvm')))} dBµV/m"
        ),
        f"Kategori Acuan        : {_fmt_status(rf_result.get('komdigi_category', rf_result.get('category')))}",
        f"Kualitas Sinyal       : {_fmt_status(rf_result.get('signal_quality'))}",
        f"Sample Rate           : {_fmt_number(rf_result.get('sample_rate_msps'), 3)} MS/s",
        f"Bandwidth Ukur        : {_fmt_number(rf_result.get('measurement_bw_mhz'), 3)} MHz",
        f"Gain SDR              : {_fmt_number(rf_result.get('actual_gain_db', rf_result.get('gain_db')), 1)} dB",
        f"Std Deviasi           : {_fmt_number(rf_result.get('std_deviation_db'))} dB",
        "",
        "📍 GPS",
        f"Status                : {_fmt_status(gps_result.get('status'))}",
        f"Latitude              : {_fmt_number(gps_result.get('latitude'), 6)}",
        f"Longitude             : {_fmt_number(gps_result.get('longitude'), 6)}",
        f"Waktu GPS             : {_fmt_status(gps_time)}",
        f"Maps                  : {_fmt_status(maps_url)}",
        "",
        "⚙️ Sistem",
        f"RTL-SDR               : {_status_rf(rf_result)}",
        f"GPS Port              : {config.gps_port}",
        f"GPS Baudrate          : {config.gps_baudrate}",
        f"Kalibrasi Mode        : {calibration_mode}",
        f"Kalibrasi Offset      : {_fmt_number(rf_result.get('calibration_offset_db'))} dB",
        f"Mode Ukur             : {measurement_mode}",
        "",
        "⚠️ Catatan",
        f"Field strength: {disclaimer}.",
        "Bandwidth ukur: 1.8 MHz (center-bandpower estimation, bukan full 8 MHz).",
    ]

    if rf_result.get("error"):
        lines.extend(["", f"RF Error              : {rf_result['error']}"])

    return "\n".join(lines)


def format_status_dashboard(system_status, gps_result, config):
    system_status = system_status or {}
    gps_result = gps_result or _gps_result_for_config(config)
    rtl_sdr_status = system_status.get("rtl_sdr", "Error")
    mode = system_status.get("mode", "Telegram Polling")

    return "\n".join(
        [
            "✅ Sistem Aktif",
            "",
            f"RTL-SDR        : {rtl_sdr_status}",
            f"GPS            : {_fmt_status(gps_result.get('status'))}",
            f"GPS Port       : {config.gps_port}",
            f"GPS Baudrate   : {config.gps_baudrate}",
            f"Frekuensi      : {getattr(config, 'frequency_mhz', getattr(config, 'default_freq_mhz', 0.0)):.3f} MHz",
            f"Kalibrasi Mode : {getattr(config, 'calibration_mode', 'raw')}",
            f"Kalibrasi      : {config.calibration_offset_db:.2f} dB",
            f"Mode Ukur      : {getattr(config, 'measurement_mode', 'unknown')}",
            f"Mode           : {mode}",
        ]
    )


def format_measurement_message(result, location=None):
    class _CompatConfig:
        gps_enabled = bool(location or {})
        gps_port = "/dev/ttyUSB0"
        gps_baudrate = 4800
        calibration_offset_db = result.get("calibration_offset_db", 0.0) if result else 0.0
        calibration_mode = result.get("calibration_mode", "raw") if result else "raw"
        measurement_mode = result.get("measurement_mode", "center_bandpower_1p8mhz") if result else "center_bandpower_1p8mhz"
        channel_name = result.get("channel_name", "unknown") if result else "unknown"
        frequency_mhz = result.get("frequency_mhz", 0.0) if result else 0.0

    return format_measurement_dashboard(result, location, _CompatConfig())


def _ordered_channels_for_scan(scan_mode, channel_id=None):
    channels = load_channel_map()
    if scan_mode == "single":
        if not channel_id:
            return []
        if channel_id not in channels:
            raise ValueError(f"Channel {channel_id!r} tidak ada")
        return [(channel_id, dict(channels[channel_id]))]
    wanted = {"baseline"} if scan_mode == "baseline" else {"optional"} if scan_mode == "optional" else {"baseline", "optional"}
    picked = [(key, dict(ch)) for key, ch in channels.items() if str(ch.get("scan_priority", "")).lower() in wanted]
    return sorted(picked, key=lambda item: (item[1].get("scan_priority") != "baseline", float(item[1].get("frequency_mhz", 0))))


def format_locations_message(route_order=False):
    items = list(load_test_locations().items())
    if route_order:
        items.sort(key=lambda kv: int(kv[1].get("route_order", 999)))
    lines = ["📍 Lokasi Uji DVB-T2"]
    for key, loc in items:
        lines.append(f"{loc.get('route_order', '-')}. {key} — {loc.get('name')}")
        lines.append(f"   awal: {loc.get('initial_lat')}, {loc.get('initial_lon')}")
    return "\n".join(lines)


def format_channels_message():
    lines = ["📡 Channel/MUX Jabodetabek"]
    for key, ch in _ordered_channels_for_scan("all"):
        lines.append(f"- {key}: UHF {ch.get('uhf_channel')} / {ch.get('frequency_mhz')} MHz / {ch.get('network')} / {ch.get('scan_priority')}")
    return "\n".join(lines)


def format_scan_help_message():
    return "\n".join([
        "📡 Perintah Field Scan",
        "",
        "/locations - daftar titik uji",
        "/route - urutan rute",
        "/channels - daftar MUX/frekuensi",
        "/scan <lokasi> baseline - scan 6 MUX wajib",
        "/scan <lokasi> optional - scan 514/690 MHz",
        "/scan <lokasi> all - scan baseline + optional",
        "/scan <lokasi> single <channel_id> - scan satu MUX",
        "",
        "Contoh:",
        "/scan monas baseline",
        "/scan bundaran_hi single UHF24_EMTEK",
        "",
        "Catatan: lock/SNR/MER/BER/PER masih unknown karena flow RTL-SDR belum decoder DVB-T2.",
    ])


class TelegramBot:
    def __init__(self, app_config, gps_reader=None):
        self.config = app_config
        self.gps_reader = gps_reader

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📡 DVB-T2 Coverage Analyzer Portable\n"
            "Perintah tersedia:\n"
            "/status - status sistem\n"
            "/measure - pengukuran RF dan status GPS\n"
            "/measure <freq> - pengukuran pada frekuensi tertentu\n"
            "/locations - daftar titik uji\n"
            "/route - urutan rute lapangan\n"
            "/channels - daftar MUX/frekuensi\n"
            "/scanhelp - bantuan scan lapangan\n"
            "/scan <lokasi> baseline - scan 6 MUX wajib"
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        gps_result = self._read_gps()
        system_status = {
            "rtl_sdr": "OK" if RtlSdr is not None else "Error",
            "mode": "Telegram Polling",
        }
        await update.message.reply_text(
            format_status_dashboard(system_status, gps_result, self.config)
        )

    async def measure(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        freq_mhz = self.config.frequency_mhz
        if context.args:
            try:
                freq_mhz = float(context.args[0])
            except ValueError:
                await update.message.reply_text("Format frekuensi tidak valid. Contoh: /measure 514")
                return

        await update.message.reply_text("Pengukuran dimulai...")

        import time as _time
        t0 = _time.time()
        sdr_config = Dvbt2SdrConfig(
            calibration_offset_db=self.config.calibration_offset_db,
            calibration_mode=self.config.calibration_mode,
            cable_loss_db=self.config.cable_loss_db,
            antenna_factor_db_per_m=self.config.antenna_factor_db_per_m,
            komdigi_lower_dbuvm=self.config.komdigi_lower_dbuvm,
            komdigi_upper_dbuvm=self.config.komdigi_upper_dbuvm,
            gain_db=self.config.sdr_gain_db,
        )
        result = run_single_measurement(freq_mhz=freq_mhz, repeat=5, config=sdr_config)
        t_elapsed = _time.time() - t0

        if result.get("error"):
            system_logger.error("RTL-SDR measurement error: %s", result["error"])

        result.update({
            "channel_name": self.config.channel_name,
            "measurement_mode": self.config.measurement_mode,
            "calibration_mode": self.config.calibration_mode,
            "calibration_source": self.config.calibration_source,
            "komdigi_lower_dbuvm": self.config.komdigi_lower_dbuvm,
            "komdigi_upper_dbuvm": self.config.komdigi_upper_dbuvm,
        })

        gps_result = self._read_gps()
        telegram_status = "FAILED" if result.get("error") else "OK"

        # Log measurement ke CSV + SQLite DB (tetap jalan walau Telegram gagal)
        measurement_row = {
            "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": gps_result.get("latitude"),
            "longitude": gps_result.get("longitude"),
            "gps_fix": gps_result.get("has_fix", False),
            "gps_satellites": None,
            "channel_name": self.config.channel_name,
            "frequency_mhz": freq_mhz,
            "sdr_gain_db": result.get("actual_gain_db", self.config.sdr_gain_db),
            "sample_rate_hz": int(self.config.sample_rate_hz),
            "measurement_bandwidth_hz": int(self.config.measurement_bandwidth_hz),
            "measurement_mode": self.config.measurement_mode,
            "raw_bandpower_db": result.get("average_bandpower_db"),
            "min_bandpower_db": result.get("min_bandpower_db"),
            "max_bandpower_db": result.get("max_bandpower_db"),
            "std_deviation_db": result.get("std_deviation_db"),
            "calibration_mode": self.config.calibration_mode,
            "calibration_offset_db": self.config.calibration_offset_db,
            "calibration_source": self.config.calibration_source,
            "antenna_factor_db_per_m": self.config.antenna_factor_db_per_m,
            "cable_loss_db": self.config.cable_loss_db,
            "rx_antenna_height_m": self.config.rx_antenna_height_m,
            "total_correction_db": result.get("total_correction_db"),
            "field_strength_est_dbuvm": result.get("field_strength_dbuvm_est"),
            "komdigi_lower_dbuvm": self.config.komdigi_lower_dbuvm,
            "komdigi_upper_dbuvm": self.config.komdigi_upper_dbuvm,
            "komdigi_category": result.get("komdigi_category"),
            "category": result.get("komdigi_category"),
            "signal_quality": result.get("signal_quality"),
            "telegram_status": telegram_status,
            "telegram_delay_s": round(t_elapsed, 2),
            "notes": result.get("error") or "",
        }
        log_measurement_data(measurement_row)
        log_measurement_to_db(measurement_row, result.get("raw_measurements"))

        await update.message.reply_text(
            format_measurement_dashboard(result, gps_result, self.config)
        )


    async def locations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_locations_message(route_order=False))

    async def route(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_locations_message(route_order=True))

    async def channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_channels_message())

    async def scanhelp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_scan_help_message())

    async def scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text(format_scan_help_message())
            return
        location_id = context.args[0]
        scan_mode = context.args[1].lower()
        channel_id = context.args[2] if len(context.args) >= 3 else None
        if scan_mode not in {"baseline", "optional", "all", "single"}:
            await update.message.reply_text("Mode scan tidak valid. Pakai: baseline, optional, all, single")
            return
        locations = load_test_locations()
        if location_id not in locations:
            await update.message.reply_text(f"Lokasi tidak ditemukan: {location_id}. Cek /locations")
            return
        location = dict(locations[location_id])
        location["id"] = location_id
        try:
            channels = _ordered_channels_for_scan(scan_mode, channel_id)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return
        if not channels:
            await update.message.reply_text("Tidak ada channel untuk scan. Cek /channels")
            return

        await update.message.reply_text(f"Scan dimulai: {location_id} / {scan_mode} / {len(channels)} channel")
        summary = [f"📡 Hasil Scan {location.get('name')} ({scan_mode})"]
        sdr_config = Dvbt2SdrConfig(
            calibration_offset_db=self.config.calibration_offset_db,
            calibration_mode=self.config.calibration_mode,
            cable_loss_db=self.config.cable_loss_db,
            antenna_factor_db_per_m=self.config.antenna_factor_db_per_m,
            komdigi_lower_dbuvm=self.config.komdigi_lower_dbuvm,
            komdigi_upper_dbuvm=self.config.komdigi_upper_dbuvm,
            gain_db=self.config.sdr_gain_db,
        )
        gps_result = self._read_gps()
        for key, channel in channels:
            freq_mhz = float(channel.get("frequency_mhz"))
            result = run_single_measurement(freq_mhz=freq_mhz, repeat=5, config=sdr_config)
            result.update({
                "channel_name": channel.get("channel_name", key),
                "measurement_mode": self.config.measurement_mode,
                "calibration_mode": self.config.calibration_mode,
                "calibration_source": self.config.calibration_source,
                "komdigi_lower_dbuvm": self.config.komdigi_lower_dbuvm,
                "komdigi_upper_dbuvm": self.config.komdigi_upper_dbuvm,
            })
            status = "ERR" if result.get("error") else "OK"
            summary.append(
                f"UHF {channel.get('uhf_channel')} {freq_mhz:.0f} MHz {channel.get('network')}: "
                f"{status}, {result.get('komdigi_category')}, { _fmt_number(result.get('average_bandpower_db')) } dB"
            )
            log_field_scan_data({
                "site_id": location_id,
                "site_name": location.get("name"),
                "initial_lat": location.get("initial_lat"),
                "initial_lon": location.get("initial_lon"),
                "lat": gps_result.get("latitude"),
                "lon": gps_result.get("longitude"),
                "uhf_channel": channel.get("uhf_channel"),
                "frequency_mhz": freq_mhz,
                "channel_name": channel.get("channel_name", key),
                "network": channel.get("network"),
                "scan_priority": channel.get("scan_priority"),
                "lock_status": "unknown",
                "signal_strength": result.get("average_bandpower_db"),
                "field_strength_est_dbuvm": result.get("field_strength_dbuvm_est"),
                "antenna_type": "capung",
                "antenna_height_m": location.get("rx_antenna_height_m", self.config.rx_antenna_height_m),
                "receiver_gain_db": result.get("actual_gain_db", self.config.sdr_gain_db),
                "calibration_mode": self.config.calibration_mode,
                "radio_planner_dbuvm": location.get("radio_planner_dbuvm"),
                "measurement_mode": self.config.measurement_mode,
                "notes": result.get("error") or "Telegram /scan; lock/SNR/MER/BER/PER belum tersedia dari RTL-SDR flow",
            })
        summary.append("\n⚠️ Estimasi SDR relatif. Bukan kalibrasi absolut.")
        await update.message.reply_text("\n".join(summary[:35]))

    def _read_gps(self):
        if not self.config.gps_enabled:
            return disabled_gps_result()
        if self.gps_reader is None:
            return _gps_result_for_config(self.config)
        return self.gps_reader.read_location(timeout_s=1.0, max_lines=8)


def run_telegram_bot(app_config, gps_reader=None):
    if not app_config.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN kosong. Isi token di file .env.")

    bot = TelegramBot(app_config, gps_reader)
    application = Application.builder().token(app_config.telegram_token).build()
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("status", bot.status))
    application.add_handler(CommandHandler("measure", bot.measure))
    application.add_handler(CommandHandler("locations", bot.locations))
    application.add_handler(CommandHandler("route", bot.route))
    application.add_handler(CommandHandler("channels", bot.channels))
    application.add_handler(CommandHandler("scanhelp", bot.scanhelp))
    application.add_handler(CommandHandler("scan", bot.scan))

    system_logger.info("Bot Telegram berjalan dengan polling.")
    try:
        application.run_polling()
    except NetworkError as exc:
        raise RuntimeError("Koneksi internet gagal saat menjalankan Telegram bot.") from exc
    except TelegramError as exc:
        raise RuntimeError(f"Telegram error: {exc}") from exc
