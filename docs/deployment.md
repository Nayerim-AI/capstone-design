# Deployment Autostart systemd

Dokumen ini menjelaskan mode deployment headless untuk Orange Pi Zero 3.

Alur deployment:

```text
Power ON -> Linux boot -> network ready -> systemd service jalan -> Telegram bot aktif
```

Service hanya menjalankan bot Telegram:

```bash
python3 main.py --mode telegram
```

Pengukuran tetap by-command dari Telegram:

```text
/status
/measure
```

Service tidak melakukan pengukuran otomatis terus-menerus.

## Persiapan

Pastikan `.env` sudah ada dan benar:

```bash
cd ~/capstone-design-repo
cp .env.example .env
nano .env
```

GPS yang sudah teruji pada project ini:

```env
GPS_ENABLED=true
GPS_PORT=/dev/ttyUSB0
GPS_BAUDRATE=4800
DEFAULT_FREQ_MHZ=514.0
CALIBRATION_OFFSET_DB=0.0
```

Jangan hardcode token Telegram di source code. Simpan token hanya di `.env`.

## Permission GPS

GPS `/dev/ttyUSB0` biasanya butuh user `orangepi` masuk grup `dialout`:

```bash
sudo usermod -aG dialout orangepi
sudo reboot
```

## Preflight Check

Jalankan cek ringan tanpa measurement penuh:

```bash
./scripts/preflight_check.sh
```

Preflight mengecek:
- `python3`
- `.env`
- `main.py`
- konfigurasi GPS dari `.env`
- device GPS jika `GPS_ENABLED=true`
- RTL-SDR via `lsusb` `0bda:2838`
- command `rtl_test`

## Install Service

Aktifkan executable bit:

```bash
chmod +x scripts/install_service.sh scripts/uninstall_service.sh scripts/service_status.sh scripts/preflight_check.sh
```

Install dan enable service tanpa langsung start:

```bash
./scripts/install_service.sh
```

Install lalu langsung start:

```bash
./scripts/install_service.sh --start
```

## Cek Status dan Log

```bash
sudo systemctl status dvbt2-analyzer.service
journalctl -u dvbt2-analyzer.service -f
```

Atau helper:

```bash
./scripts/service_status.sh
```

## Stop untuk Debugging Manual

Stop service dulu:

```bash
sudo systemctl stop dvbt2-analyzer.service
```

Lalu jalankan manual:

```bash
python3 main.py --mode telegram
```

Peringatan: jangan menjalankan manual mode Telegram ketika service masih aktif. Telegram akan mengalami conflict `getUpdates` karena ada dua polling bot dengan token yang sama.

## Disable dan Uninstall Service

```bash
./scripts/uninstall_service.sh
```

Script ini akan stop service jika aktif, disable service, hapus unit systemd, dan reload systemd. Repo dan `.env` tidak dihapus.

## Troubleshooting RTL-SDR

Sebelum test manual, stop service:

```bash
sudo systemctl stop dvbt2-analyzer.service
```

Cek USB:

```bash
lsusb
```

Cek tool RTL-SDR:

```bash
rtl_test
```

Jika RTL-SDR permission error atau device busy, pastikan tidak ada proses lain yang memakai dongle dan cek konfigurasi driver RTL-SDR di sistem.
