# 📡 DVB-T2 Coverage Analyzer Portable

**Capstone Design** — Alat ukur portabel untuk menganalisis cakupan sinyal DVB-T2 menggunakan RTL-SDR, GPS, dan kontrol via Telegram Bot.

---

## 📋 Daftar Isi

- [Ringkasan](#-ringkasan-proyek)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Hardware Requirements](#-hardware-requirements)
- [Struktur Proyek](#-struktur-proyek)
- [Quick Start](#-quick-start)
- [Mode Operasi](#-mode-operasi)
  - [CLI Mode](#cli-mode)
  - [Telegram Bot](#telegram-bot)
- [Telegram Commands](#-telegram-commands)
- [Sistem Pengukuran](#-sistem-pengukuran)
- [GPS Reader](#-gps-reader)
- [Deployment systemd](#-deployment-systemd)
- [Dokumentasi Tambahan](#-dokumentasi-tambahan)
- [Testing](#-testing)
- [Developer Reference](#-developer-reference)

---

## 🎯 Ringkasan Proyek

**Tujuan:** Membangun alat ukur portabel berbasis Orange Pi Zero 3 untuk mengukur dan menganalisis cakupan sinyal siaran DVB-T2 Indonesia.

**Cara Kerja Umum:**

```text
RTL-SDR (USB) ──┐
                 ├──► Python (main.py)
GPS Serial ─────┘        │
                          ├──► CLI: cetak ke terminal
                          └──► Telegram Bot: /measure, /status
```

**Output:**
- **Bandpower relatif** (dB) dari FFT IQ samples
- **Estimasi field strength** (dBµV/m) dengan offset kalibrasi
- **Klasifikasi kualitas sinyal**: Sangat Baik / Baik / Cukup / Lemah / Sangat Lemah
- **Koordinat GPS** (latitude, longitude) + tautan Google Maps
- **Log GPS** ke CSV untuk analisis spasial

---

## 🏗️ Arsitektur Sistem

```text
┌─────────────────────────────────────────────────────────────┐
│                     Orange Pi Zero 3                        │
│                                                             │
│  ┌──────────────┐    ┌────────────────────────────────┐     │
│  │  RTL-SDR     │    │         Python App              │     │
│  │  (USB)       │◄──►│  ┌───────────┐ ┌────────────┐  │     │
│  │  0bda:2838   │    │  │dvbt2_core │ │gps_reader  │  │     │
│  └──────────────┘    │  │ - capture │ │ - NMEA parse│  │     │
│                      │  │ - FFT/PSD │ │ - serial IO │  │     │
│  ┌──────────────┐    │  │ - bandpower│ │ - CSV log   │  │     │
│  │  GPS Serial  │◄──►│  └─────┬─────┘ └──────┬──────┘  │     │
│  │  PL2303      │    │        │               │         │     │
│  │  /dev/ttyUSB0│    │  ┌─────▼───────────────▼──────┐  │     │
│  └──────────────┘    │  │      telegram_bot.py       │  │     │
│                      │  │  /start /status /measure   │  │     │
│  ┌──────────────┐    │  └───────────┬────────────────┘  │     │
│  │  Internet    │◄──►│              │                    │     │
│  │  (WiFi/ETH)  │    │              ▼                    │     │
│  └──────────────┘    │      Telegram API                │     │
│                      └──────────────────────────────────┘     │
│                                                             │
│  ┌──────────────┐    ┌────────────────────────────────┐     │
│  │  config.py   │    │        logger.py               │     │
│  │  .env →      │    │  system.log + gps_log.csv      │     │
│  │  AppConfig   │    └────────────────────────────────┘     │
│  └──────────────┘                                           │
│                                                             │
│  systemd: dvbt2-analyzer.service (autostart)                │
└─────────────────────────────────────────────────────────────┘
```

### Alur Data

```text
RTL-SDR IQ Samples
    │
    ▼
dvbt2_core.capture_iq_samples()
    │
    ▼
dvbt2_core.compute_psd() ──► Hann window → FFT → Welch averaging
    │
    ▼
dvbt2_core.calculate_bandpower() ──► Exclude DC spike
    │
    ▼
dvbt2_core.estimate_field_strength() ──► + calibration_offset_db
    │
    ▼
dvbt2_core.classify_signal_quality()
    │
    ▼
Telegram / CLI ──► Dashboard / terminal output
```

---

## 🔧 Hardware Requirements

| Komponen | Spesifikasi | Catatan |
|----------|------------|---------|
| **Single Board Computer** | Orange Pi Zero 3 (atau Linux SBC) | ARM64, USB, WiFi |
| **RTL-SDR Dongle** | RTL2838 (0bda:2838) | Receiver DVB-T2 |
| **GPS Receiver** | USB Serial NMEA (PL2303, MA-8910P) | Baudrate 4800 |
| **Antena GPS** | Aktif dengan baterai internal | Outdoor untuk fix cepat |
| **Antena UHF** | 470–700 MHz | Untuk DVB-T2 |
| **Power** | USB-C 5V/3A | Orange Pi Zero 3 |
| **Internet** | WiFi / Ethernet | Untuk Telegram Bot |

---

## 📁 Struktur Proyek

```
capstone-design/
│
├── main.py                         # Entry point: CLI / Telegram
├── requirements.txt                # Python dependencies
├── .env.example                    # Template konfigurasi (.env)
├── .gitignore                      # Git ignore rules
│
├── src/                            # Source code utama
│   ├── dvbt2_core.py               # RTL-SDR capture + FFT + bandpower + field strength
│   ├── gps_reader.py               # GPS serial reader (NMEA), threaded
│   ├── telegram_bot.py             # Telegram bot handler (/start, /status, /measure)
│   ├── config.py                   # Konfigurasi dari .env (AppConfig dataclass)
│   └── logger.py                   # Logging + GPS CSV writer
│
├── test/                           # Unit tests
│   ├── test_config.py              # Config loading & parsing tests
│   ├── test_dvbt2_core.py          # PSD, bandpower, signal quality tests
│   ├── test_gps_reader.py          # GPS NMEA parsing tests
│   ├── test_gps_result_schema.py   # GPS result dict schema validation
│   └── test_telegram_format.py     # Telegram message formatting tests
│
├── scripts/                        # Shell scripting & utilities
│   ├── preflight_check.sh          # Pre-deployment hardware & config check
│   ├── check_gps.py                # GPS test tool (scan baudrate, read NMEA)
│   ├── install_service.sh          # Install systemd service
│   ├── uninstall_service.sh        # Remove systemd service
│   └── service_status.sh           # Check service status & journal
│
├── deployment/                     # Deployment config
│   └── dvbt2-analyzer.service      # systemd unit file for autostart
│
├── docs/                           # Dokumentasi
│   ├── QUICKSTART.md               # Panduan cepat setup & running
│   ├── Panduan_Penggunaan.md       # Panduan penggunaan Telegram bot
│   ├── SOP_Pengukuran.md           # SOP pengujian lapangan
│   ├── deployment.md               # Deployment systemd headless
│   └── legacy/                     # Legacy utilities (deprecated)
│       ├── bot_handler.py
│       ├── gps_reader.py
│       └── logger.py
│
├── config/                         # Direktori konfigurasi (kosong, untuk expansi)
├── data/                           # Runtime data output (gps_log.csv)
├── logs/                           # System logs (system.log)
└── .env                            # Konfigurasi lokal (tidak di-commit)
```

---

## 🚀 Quick Start

```bash
# 1. Clone & masuk direktori
git clone https://github.com/Nayerim-AI/capstone-design.git
cd capstone-design

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Buat konfigurasi
cp .env.example .env
nano .env
# Isi: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DEFAULT_FREQ_MHZ=514.0

# 4. Cek hardware
lsusb                    # Harus ada 0bda:2838 (RTL-SDR)
ls -l /dev/ttyUSB0       # GPS serial port

# 5. Tes GPS (30 detik)
python3 scripts/check_gps.py --port /dev/ttyUSB0 --baudrate 4800 --duration 30

# 6. Tes CLI
python3 main.py --mode cli --freq 514 --repeat 5

# 7. Jalankan Telegram Bot
python3 main.py --mode telegram
```

Lihat [QUICKSTART.md](docs/QUICKSTART.md) untuk panduan lengkap.

---

## 🎮 Mode Operasi

### CLI Mode

Pengukuran satu kali dengan output ke terminal:

```bash
# Pengukuran default (514 MHz, 5 repeat)
python3 main.py --mode cli

# Frekuensi kustom
python3 main.py --mode cli --freq 650 --repeat 3

# Help
python3 main.py --help
```

Output contoh:

```text
=== DVB-T2 CORE MEASUREMENT ===
Frequency              : 514.000 MHz
Sample rate            : 2.048 MS/s
Measurement bandwidth  : 1.800 MHz
Gain                   : 19.7 dB
Calibration offset     : 0.00 dB
Average bandpower      : -42.35 dB
Min bandpower          : -43.12 dB
Max bandpower          : -41.98 dB
Std deviation          : 0.47 dB
Power estimate         : -42.35 dB
Field strength est     : -42.35 dBuV/m
Signal quality         : Sangat Lemah
Raw measurements       : [-42.12, -43.05, -41.98, -42.56, -43.01]

Power dan field strength adalah estimasi relatif.
Gunakan calibration_offset_db dari alat pembanding untuk kalibrasi.
```

### Telegram Bot

Pengukuran dikontrol dari Telegram:

```bash
python3 main.py --mode telegram
```

Kirim perintah ke bot Telegram Anda:

| Perintah | Deskripsi |
|----------|-----------|
| `/start` | Menampilkan pesan sambutan & daftar perintah |
| `/status` | Status sistem: RTL-SDR, GPS, konfigurasi |
| `/measure` | Pengukuran RF + lokasi GPS |
| `/measure 650` | Pengukuran pada frekuensi kustom (MHz) |

---

## 🤖 Telegram Commands

### `/start`
```text
📡 DVB-T2 Coverage Analyzer Portable

Perintah tersedia:
/status - status sistem
/measure - pengukuran RF dan status GPS
```

### `/status`
```text
✅ Sistem Aktif

RTL-SDR        : OK
GPS            : Belum Fix
GPS Port       : /dev/ttyUSB0
GPS Baudrate   : 4800
Frekuensi      : 514.000 MHz
Kalibrasi      : 0.00 dB
Mode           : Telegram Polling
```

### `/measure`
```text
📡 DVB-T2 Coverage Analyzer

🕒 Waktu Sistem:
2026-05-27 21:30:00 WIB

📻 Pengukuran RF
Frekuensi              : 514.000 MHz
Bandpower Relatif     : -42.35 dB
Estimasi Field Strength: -42.35 dBµV/m
Kualitas Sinyal       : Sangat Lemah
...

📍 GPS
Status                : Valid
Latitude              : -6.229747
Longitude             : 106.829507
Waktu GPS             : 14:29:47 UTC
Maps                  : https://maps.google.com/?q=-6.229747,106.829507

⚙️ Sistem
RTL-SDR               : OK
GPS Port              : /dev/ttyUSB0
...
```

---

## 📻 Sistem Pengukuran

### dvbt2_core.py

Komponen inti pengukuran sinyal DVB-T2:

| Fungsi | Deskripsi |
|--------|-----------|
| `Dvbt2SdrConfig` | Data class konfigurasi: sample rate, FFT size, gain, bandwidth, kalibrasi |
| `initialize_sdr()` | Buka koneksi RTL-SDR, set frekuensi & gain |
| `capture_iq_samples()` | Ambil 256K IQ samples kompleks |
| `compute_psd()` | FFT dengan Hann window + Welch averaging → PSD relatif |
| `calculate_bandpower()` | Integrasi PSD pada measurement bandwidth (DC spike diexclude) |
| `estimate_field_strength()` | Bandpower + calibration offset → estimasi dBµV/m |
| `classify_signal_quality()` | Klasifikasi: Sangat Baik (>65) / Baik (55-65) / Cukup (48-55) / Lemah (35-48) / Sangat Lemah (<35) |
| `run_single_measurement()` | Orchestrator: warmup → repeat FFT → average → field strength |

**Pipeline sinyal:**

```text
IQ samples (complex64)
    │
    ▼
Remove DC bias (per segment)
    │
    ▼
Hann window → reduce spectral leakage
    │
    ▼
FFT (2048-point) → magnitude squared
    │
    ▼
Welch averaging (50% overlap) → reduce noise variance
    │
    ▼
FFT shift + 10*log10 → PSD (dB)
    │
    ▼
Integrate over ±1.8 MHz (exclude ±20 kHz DC)
    │
    ▼
+ calibration_offset → field strength estimate
    │
    ▼
Classify signal quality
```

**Keterangan:**
- Power dan field strength adalah **estimasi relatif**, bukan nilai absolut tersertifikasi.
- Gunakan `CALIBRATION_OFFSET_DB` dari alat pembanding untuk kalibrasi.
- DC spike RTL-SDR (±20 kHz) dibuang agar tidak mengganggu pengukuran.
- Default gain 19.7 dB, dapat disesuaikan via `dvbt2_core.py`.

---

## 📍 GPS Reader

### gps_reader.py

| Komponen | Deskripsi |
|----------|-----------|
| `GPSReader` | Class utama: threaded serial reader |
| `connect()` | Buka port serial `/dev/ttyUSB0` @ 4800 baud |
| `start()` | Jalankan background thread pembaca NMEA |
| `read_location()` | Blocking read dengan timeout (1 detik) |
| `get_current_location()` | Snapshot lokasi terkini (thread-safe) |
| `parse_nmea_line()` | Parse NMEA ($GPGGA, $GNGGA, $GPRMC, $GNRMC) |
| `_base_gps_result()` | Schema dictionary hasil GPS |

**GPS Result Schema:**

```python
{
    "enabled": bool,      # GPS_ENABLED dari .env
    "available": bool,    # Port serial terbuka
    "has_fix": bool,      # Koordinat valid
    "status": str,        # "Valid" | "Belum Fix" | "Nonaktif" | "Tidak Tersedia"
    "latitude": float,    # -7.0 s.d. -6.0
    "longitude": float,   # 106.0 s.d. 107.0
    "gps_time": str,      # HH:MM:SS UTC
    "maps_url": str,      # https://maps.google.com/?q=lat,lng
    "raw_type": str,      # "GPGGA" | "GNGGA" | "GPRMC" | "GNRMC"
    "message": str,       # Human-readable status message
}
```

**GPS Status pada Telegram:**

| Status | Arti | Tindakan |
|--------|------|----------|
| `Valid` | Koordinat valid, ada fix satelit | Maps URL tersedia |
| `Belum Fix` | NMEA terbaca tapi belum fix | Tunggu outdoor atau cek antena |
| `Nonaktif` | `GPS_ENABLED=false` | Jika perlu, aktifkan di `.env` |
| `Tidak Tersedia` | Port serial tidak bisa dibuka | Cek USB, permission `dialout` |

**GPS Logging:** Semua koordinat valid tercatat ke `data/gps_log.csv`:

```csv
Timestamp,Latitude,Longitude,Altitude,Speed
2026-05-27 21:30:00,-6.229747,106.829507,,
```

---

## ⚙️ Deployment systemd

Untuk deployment headless (Orange Pi menyala → bot langsung jalan):

### Persiapan

```bash
# Permission GPS
sudo usermod -aG dialout orangepi
sudo reboot

# Cek preflight
./scripts/preflight_check.sh
```

### Install

```bash
chmod +x scripts/*.sh

# Install tanpa start
./scripts/install_service.sh

# Install lalu start
./scripts/install_service.sh --start
```

### Manajemen

```bash
# Status
sudo systemctl status dvbt2-analyzer.service

# Log
journalctl -u dvbt2-analyzer.service -f

# Atau helper
./scripts/service_status.sh

# Stop (untuk debugging manual)
sudo systemctl stop dvbt2-analyzer.service

# Uninstall
./scripts/uninstall_service.sh
```

### systemd Service Unit

`deployment/dvbt2-analyzer.service`:

```ini
[Unit]
Description=DVB-T2 Coverage Analyzer Telegram Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=orangepi
WorkingDirectory=/home/orangepi/capstone-design-repo
EnvironmentFile=/home/orangepi/capstone-design-repo/.env
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 /home/orangepi/capstone-design-repo/main.py --mode telegram
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Catatan:**
- Service hanya menjalankan Telegram polling mode.
- Pengukuran tetap by-command (`/measure`).
- Delay 10 detik (`ExecStartPre=/bin/sleep 10`) menunggu network dan GPS ready.
- Jangan jalankan `main.py --mode telegram` manual saat service aktif (konflik polling).

---

## 📚 Dokumentasi Tambahan

| Dokumen | Konten |
|---------|--------|
| [QUICKSTART.md](docs/QUICKSTART.md) | Setup cepat dari awal sampai Telegram bot running |
| [Panduan_Penggunaan.md](docs/Panduan_Penggunaan.md) | Panduan interaksi Telegram bot untuk user |
| [SOP_Pengukuran.md](docs/SOP_Pengukuran.md) | Standar operasional prosedur pengujian lapangan |
| [deployment.md](docs/deployment.md) | Deploy systemd headless + troubleshooting |

---

## 🧪 Testing

```bash
# Compile check
python3 -m py_compile main.py src/*.py scripts/*.py

# Unit tests
python3 -m unittest discover -s test -v
```

**Test Coverage:**

| File | Tests |
|------|-------|
| `test_config.py` | Load config, parse boolean/int/float, GPS baudrate default |
| `test_dvbt2_core.py` | PSD computation, bandpower, field strength, signal quality classification |
| `test_gps_reader.py` | NMEA parsing ($GPGGA, $GPRMC), fix detection, error modes |
| `test_gps_result_schema.py` | GPS result dict schema validation |
| `test_telegram_format.py` | Dashboard message formatting, error states |

---

## 👨‍💻 Developer Reference

### Konfigurasi (.env)

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `TELEGRAM_TOKEN` | (wajib) | Bot token dari @BotFather |
| `TELEGRAM_CHAT_ID` | (wajib) | Chat ID untuk notifikasi |
| `DEFAULT_FREQ_MHZ` | 514.0 | Frekuensi center pengukuran (MHz) |
| `CALIBRATION_OFFSET_DB` | 0.0 | Offset kalibrasi field strength (dB) |
| `GPS_ENABLED` | true | Aktifkan/nonaktifkan GPS |
| `GPS_PORT` | /dev/ttyUSB0 | Port serial GPS |
| `GPS_BAUDRATE` | 4800 | Baudrate GPS NMEA |

### Entry Point

```bash
python3 main.py --mode {cli|telegram} [--freq MHZ] [--repeat N]
```

### Dependencies

```
numpy                       # FFT, array operations
pyrtlsdr                    # RTL-SDR interface
pyserial                    # Serial port (GPS)
pynmea2                     # NMEA sentence parser
python-telegram-bot         # Telegram Bot API (async)
python-dotenv               # .env file loader
```

### Script Helpers

```bash
# Cek GPS real-time
python3 scripts/check_gps.py --port /dev/ttyUSB0 --baudrate 4800 --duration 30

# Scan baudrate GPS otomatis
python3 scripts/check_gps.py --port /dev/ttyUSB0 --duration 10 --scan

# Preflight hardware/config check
./scripts/preflight_check.sh
```

---

## 📄 Lisensi

Proyek ini adalah bagian dari **Capstone Design** — Universitas/Lembaga terkait.

---

## 🔗 Links

- **Repository:** [https://github.com/Nayerim-AI/capstone-design](https://github.com/Nayerim-AI/capstone-design)
- **RTL-SDR:** [https://www.rtl-sdr.com](https://www.rtl-sdr.com)
- **Orange Pi Zero 3:** [http://www.orangepi.org](http://www.orangepi.org)
- **Python Telegram Bot:** [https://python-telegram-bot.org](https://python-telegram-bot.org)
