# BAB V — PENGUJIAN SISTEM
## LANGKAH RUNNING PROGRAM

### 1. Verifikasi RTL-SDR Blog V3 Terdeteksi oleh Sistem

**Deskripsi:**
Sebelum menjalankan program, diperlukan verifikasi bahwa RTL-SDR Blog V3 terdeteksi oleh sistem Linux. Dongle ini menggunakan chip RTL2832U dengan USB ID `0bda:2838`. Jika terdeteksi, proceed ke langkah berikutnya.

**Langkah-Langkah:**

1. **Cek USB Devices**
   ```bash
   lsusb
   ```
   
   **Output yang diharapkan:**
   ```
   Bus 001 Device 002: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T
   Bus 001 Device 003: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T
   ```

2. **Cek Device File**
   ```bash
   ls -l /dev/bus/usb/001/
   ```
   
   **Output yang diharapkan:**
   ```
   crw-rw-r+ 1 root root 189, 512 May 28 12:00 001/002
   crw-rw-r+ 1 root 189, 515 May 28 12:00 001/003
   ```

3. **(Opsional) Tes dengan rtl_test**
   ```bash
   rtl_test -t
   ```
   
   **Output yang diharapkan:**
   ```
   Found 1 device(s):
   Found Realtek Semiconductor Corp. RTL2838DU-stick at 0x1a.
   ```

**Penjelasan:**
- `lsusb` menampilkan semua USB devices yang terhubung.
- `0bda:2838` adalah USB ID standar RTL-SDR Blog V3.
- Jika tidak muncul, coba reboot atau cek kabel USB.
- `rtl_test` adalah tool dari package `rtl-sdr` untuk verifikasi tambahan.

---

### 2. Verifikasi Modul GPS Terdeteksi sebagai Perangkat Serial

**Deskripsi:**
Modul GPS (PL2303/MA-8910P) terdeteksi sebagai device serial `/dev/ttyUSB0`. Perlu dicek apakah device tersedia dan memiliki permission yang benar untuk dibaca oleh user.

**Langkah-Langkah:**

1. **Cek USB Serial Devices**
   ```bash
   ls -l /dev/ttyUSB*
   ```
   
   **Output yang diharapkan:**
   ```
   crw-rw---- 1 root dialout 188, 0 May 28 12:00 /dev/ttyUSB0
   ```

2. **Cek lsusb**
   ```bash
   lsusb | grep -i prolific
   ```
   
   **Output yang diharapkan:**
   ```
   Bus 001 Device 004: ID 067b:2303 Prolific Technology, Inc. PL2303 Serial Port
   ```

3. **Tambah User ke Grup dialout**
   Jika permission denied, tambahkan user ke grup dialout:
   ```bash
   sudo usermod -aG dialout $USER
   ```
   
   затем logout dan login ulang, atau:
   ```bash
   sudo chmod a+rw /dev/ttyUSB0
   ```

4. **Tes GPS dengan scripts/check_gps.py**
   ```bash
   python3 scripts/check_gps.py --port /dev/ttyUSB0 --baudrate 4800 --duration 30
   ```
   
   **Output yang diharapkan:**
   ```
   [INFO] GPS Reader started on /dev/ttyUSB0 @ 4800 baud
   [INFO] NMEA terbaca: $GPGGA,...
   [INFO] GPS fix: -6.229747, 106.829507
   ```

5. **(Opsional) Scan Baudrate Otomatis**
   Jika tidak yakin baudrate:
   ```bash
   python3 scripts/check_gps.py --port /dev/ttyUSB0 --duration 10 --scan
   ```

**Penjelasan:**
- `/dev/ttyUSB0` adalah device file untuk USB Serial (GPS).
- `ID 067b:2303` adalah USB ID Prolific PL2303.
- Grup `dialout` diperlukan untuk mengakses serial port.
- `check_gps.py` adalah script utility untuk testing GPS.

---

### 3. Menjalankan Program Secara Manual

**Deskripsi:**
Mode CLI digunakan untuk pengembangan dan debugging. Program dijalankan langsung dari terminal, hasil pengukuran ditampilkan ke stdout.

**Langkah-Langkah:**

1. **Pastikan Dependensi Terinstall**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Buat File Konfigurasi**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Isi minimal:
   ```env
   TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   DEFAULT_FREQ_MHZ=514.0
   CALIBRATION_OFFSET_DB=0.0
   GPS_ENABLED=true
   GPS_PORT=/dev/ttyUSB0
   GPS_BAUDRATE=4800
   ```

3. **Jalankan Program (CLI Mode)**
   ```bash
   python3 main.py --mode cli --freq 514 --repeat 5
   ```

   **Output yang diharapkan:**
   ```
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

4. **Jalankan Program (Telegram Mode)**
   ```bash
   python3 main.py --mode telegram
   ```
   
   **Output yang diharapkan:**
   ```
   2026-05-28 12:00:00 - CapstoneDvbT2 - INFO - Berhasil terhubung ke GPS di port /dev/ttyUSB0 @ 4800 baud
   2026-05-28 12:00:00 - CapstoneDvbT2 - INFO - Bot Telegram berjalan dengan polling.
   ```

5. **Kirim Perintah dari Telegram**
   ```
   /start
   /status
   /measure
   /measure 650
   ```

**Penjelasan:**
- `--mode cli` untuk command-line interface.
- `--freq 514` adalah frekuensi center dalam MHz (default 514 MHz).
- `--repeat 5` adalah jumlah pengulangan (default 5).
- Mode Telegram memerlukan internet dan token valid.

---

### 4. Menjalankan Program Secara Otomatis (Systemd Service)

**Deskripsi:**
Untuk deployment headless (tanpa monitor), program dijalankan sebagai systemd service. Saat Orange Pi dinyalakan, service otomatis berjalan dan Telegram bot siap menerima command.

**Langkah-Langkah:**

1. **Jalankan Preflight Check**
   ```bash
   chmod +x scripts/preflight_check.sh
   ./scripts/preflight_check.sh
   ```
   
   **Output yang diharapkan:**
   ```
   === DVB-T2 Analyzer Preflight Check ===
   OK    : python3 tersedia: /usr/bin/python3
   OK    : .env ditemukan
   OK    : main.py ditemukan
   OK    : GPS device ditemukan: /dev/ttyUSB0
   OK    : RTL-SDR USB terdeteksi: 0bda:2838
   Preflight result: OK
   ```

2. **Install Service**
   ```bash
   chmod +x scripts/install_service.sh scripts/uninstall_service.sh scripts/service_status.sh
   ./scripts/install_service.sh
   ```
   
   Atau langsung start:
   ```bash
   ./scripts/install_service.sh --start
   ```

3. **Cek Status Service**
   ```bash
   sudo systemctl status dvbt2-analyzer.service
   ```
   
   **Output yang diharapkan:**
   ```
   ● dvbt2-analyzer.service - DVB-T2 Coverage Analyzer Telegram Service
      Loaded: loaded (/home/orangepi/capstone-design-repo/deployment/dvbt2-analyzer.service; enabled)
      Active: active (running) since Thu 2026-05-28 12:00:00 WITA; 1min ago
   ```

4. **Cek Log Real-time**
   ```bash
   journalctl -u dvbt2-analyzer.service -f
   ```
   
   Atau gunakan helper:
   ```bash
   ./scripts/service_status.sh
   ```

5. **Stop Service (untuk Debugging)**
   ```bash
   sudo systemctl stop dvbt2-analyzer.service
   python3 main.py --mode telegram
   ```

6. **Uninstall Service**
   ```bash
   ./scripts/uninstall_service.sh
   ```

**Penjelasan:**
- **Systemd service** memastikan program otomatis start saat boot.
- File service: `deployment/dvbt2-analyzer.service`.
- `ExecStartPre=/bin/sleep 10` menunggu network ready.
- `Restart=on-failure` restart otomatis jika crash.
- `journalctl` untuk melihat log real-time.

---

## RINGKASAN PENGUJIAN

| No. | Tahap Pengujian | Hasil yang Diharapkan |
|-----|-----------------|----------------------|
| 1 | Verifikasi RTL-SDR | `lsusb` menampilkan `0bda:2838` |
| 2 | Verifikasi GPS | `/dev/ttyUSB0` tersedia, `check_gps.py` berhasil |
| 3 | Running Manual (CLI) | Output pengukuran muncul di terminal |
| 4 | Running Manual (Telegram) | Bot menerima `/start`, `/status`, `/measure` |
| 5 | Running Otomatis (Systemd) | Service aktif, bot menerima command setelah reboot |

---

## TROUBLESHOOTING

| Masalah | Solusi |
|---------|--------|
| RTL-SDR tidak terdeteksi | `lsusb`, cek kabel USB, cek driver `rtl2832u` |
| GPS permission denied | `sudo usermod -aG dialout $USER`, reboot |
| Telegram token error | Cek `TELEGRAM_TOKEN` di `.env`, pastikan token valid |
| Service tidak start | `journalctl -u dvbt2-analyzer.service`, cek log error |
| GPS belum fix | Pindahkan antenna GPS ke outdoor, tunggu 1-2 menit |
| Field strength tidak masuk akal | Sesuaikan `CALIBRATION_OFFSET_DB` dengan alat pembanding |