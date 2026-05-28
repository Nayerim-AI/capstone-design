# Quickstart DVB-T2 Coverage Analyzer Portable

Panduan cepat untuk menjalankan project di Orange Pi Zero 3.

## 1. Masuk ke Repo

```bash
cd ~/capstone-design-repo
```

## 2. Install Dependency

```bash
pip3 install -r requirements.txt
```

## 3. Buat File Konfigurasi

```bash
cp .env.example .env
nano .env
```

Isi minimal:

```env
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
DEFAULT_FREQ_MHZ=514.0
CALIBRATION_OFFSET_DB=0.0
GPS_ENABLED=true
GPS_PORT=/dev/ttyUSB0
GPS_BAUDRATE=4800
```

Catatan:
- Jangan hardcode token Telegram di source code.
- GPS project ini terbaca NMEA pada `4800` baud.
- Field strength masih estimasi relatif, bukan hasil ukur absolut tersertifikasi.

## 4. Cek Hardware USB

```bash
lsusb
```

Pastikan muncul perangkat seperti:

```text
Realtek Semiconductor Corp. RTL2838 DVB-T
Prolific Technology, Inc. PL2303 Serial Port
```

Pastikan serial GPS muncul:

```bash
ls -l /dev/ttyUSB0
```

Jika permission denied, tambahkan user ke grup `dialout`:

```bash
sudo usermod -aG dialout $USER
```

Lalu logout/login atau reboot.

## 5. Tes GPS

```bash
python3 scripts/check_gps.py --port /dev/ttyUSB0 --baudrate 4800 --duration 30
```

Jika GPS belum mendapat satelit, status `NMEA_NO_FIX` masih normal. Artinya data NMEA sudah masuk, tetapi koordinat belum valid.

Jika ingin scan baudrate:

```bash
python3 scripts/check_gps.py --port /dev/ttyUSB0 --duration 10 --scan
```

Manual test:

```bash
stty -F /dev/ttyUSB0 4800 cs8 -cstopb -parenb raw -echo
timeout 20 cat /dev/ttyUSB0
```

## 6. Tes RTL-SDR via CLI

```bash
python3 main.py --mode cli --freq 514 --repeat 5
```

Jika RTL-SDR tidak terbuka, cek:
- Dongle RTL-SDR terpasang.
- Tidak sedang dipakai proses lain.
- Driver DVB bawaan Linux tidak mengunci device.

## 7. Jalankan Telegram Bot

Pastikan `.env` sudah berisi `TELEGRAM_TOKEN`.

```bash
python3 main.py --mode telegram
```

Di Telegram, kirim:

```text
/start
/status
/measure
```

## 8. Interpretasi GPS di Telegram

Status GPS:
- `Valid`: koordinat valid dan Maps tersedia.
- `Belum Fix`: NMEA terbaca, tetapi satelit belum fix. Pengukuran RTL-SDR tetap dikirim.
- `Nonaktif`: `GPS_ENABLED=false`.
- `Tidak Tersedia`: port GPS tidak bisa dibuka atau device tidak tersedia.

## 9. Autostart systemd

Gunakan systemd jika device akan dipakai headless. Saat Orange Pi dinyalakan, service akan menjalankan:

```bash
python3 main.py --mode telegram
```

Pengukuran tetap hanya berjalan saat user mengirim `/measure` di Telegram.

Jalankan preflight:

```bash
./scripts/preflight_check.sh
```

Install service tanpa langsung start:

```bash
chmod +x scripts/install_service.sh scripts/uninstall_service.sh scripts/service_status.sh scripts/preflight_check.sh
./scripts/install_service.sh
```

Install dan langsung start:

```bash
./scripts/install_service.sh --start
```

Cek status dan log:

```bash
sudo systemctl status dvbt2-analyzer.service
journalctl -u dvbt2-analyzer.service -f
```

Atau:

```bash
./scripts/service_status.sh
```

Stop service untuk debugging manual:

```bash
sudo systemctl stop dvbt2-analyzer.service
python3 main.py --mode telegram
```

Jangan menjalankan mode Telegram manual ketika service masih aktif, karena Telegram polling bisa conflict `getUpdates`.

Disable service:

```bash
./scripts/uninstall_service.sh
```

Dokumen detail: `docs/deployment.md`.

## 10. Perintah Validasi Developer

```bash
python3 -m py_compile main.py src/*.py scripts/*.py
python3 -m unittest discover -s test
python3 main.py --help
```
