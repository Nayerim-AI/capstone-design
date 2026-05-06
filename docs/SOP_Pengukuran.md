# Standar Operasional Prosedur (SOP) Pengujian Lapangan

Dokumen ini berisi prosedur standar untuk melakukan pengujian dan pengukuran sistem GPS Logger menggunakan Telegram Bot.

## Persiapan Alat
1. Perangkat komputasi (Laptop/Raspberry Pi/Mini PC) yang sudah terinstall Python 3.
2. Modul GPS Serial (misalnya PL2303 / Mobile Action MA-8910P).
3. Koneksi internet yang stabil untuk Telegram Bot.
4. Akun Telegram aktif.

## Setup Awal
1. Pastikan antena GPS berada di **area terbuka (outdoor)** untuk mendapatkan sinyal satelit (lock) yang optimal.
2. Hubungkan modul GPS ke port USB perangkat.
3. Periksa koneksi perangkat menggunakan perintah `lsusb` dan pastikan perangkat terdeteksi (contoh: `Prolific Technology, Inc. PL2303 Serial Port`).
4. Verifikasi port serial yang digunakan (biasanya `/dev/ttyUSB0`), dan pastikan konfigurasi pada file `.env` sudah sesuai:
   ```env
   SERIAL_PORT=/dev/ttyUSB0
   BAUDRATE=9600
   ```

## Pelaksanaan Pengukuran
1. Jalankan sistem melalui terminal:
   ```bash
   python main.py
   ```
2. Buka aplikasi Telegram dan cari bot yang telah Anda buat.
3. Tekan tombol `Start` atau ketik `/start`.
4. Pilih menu **📊 Status Sistem** untuk memastikan sistem membaca GPS. Jika status sinyal menunjukkan "Mencari satelit...", tunggu beberapa menit hingga indikator menunjukkan "Lock".
5. Mulai pergerakan (jika melakukan pengujian dinamis/berjalan). Sistem secara otomatis akan mencatat setiap perubahan lokasi ke dalam file `data/gps_log.csv`.
6. Secara berkala, gunakan fitur **📍 Cek Lokasi** pada bot Telegram untuk memverifikasi kesesuaian koordinat dengan kondisi riil di lapangan.

## Pengumpulan Data
1. Setelah pengujian selesai, hentikan program dengan menekan `Ctrl+C` pada terminal.
2. Ambil file `data/gps_log.csv`. File ini berisi kolom Timestamp, Latitude, Longitude, Altitude, dan Speed.
3. Buka file CSV tersebut menggunakan aplikasi spreadsheet (Excel, Google Sheets) atau import ke software GIS (QGIS, ArcGIS) untuk analisis spasial dan pembuatan peta jalur.

## Troubleshooting
- **Bot tidak merespons**: Pastikan `TELEGRAM_TOKEN` benar dan koneksi internet stabil.
- **Port Permission Denied**: Berikan hak akses ke serial port dengan perintah `sudo chmod a+rw /dev/ttyUSB0` (untuk sistem Linux).
- **Koordinat Kosong / 0.0**: Pastikan posisi GPS ada di luar ruangan agar tidak terhalang atap atau gedung tinggi.
