# Panduan Penggunaan Sistem & Telegram Bot

Dokumen ini menjelaskan cara menggunakan dan berinteraksi dengan sistem pelacak GPS melalui Telegram.

## Instalasi Dependensi
Sebelum menjalankan sistem, pastikan semua library Python yang dibutuhkan sudah terinstal:
```bash
pip install -r requirements.txt
```

## Menjalankan Sistem
1. Salin file konfigurasi awal:
   ```bash
   cp .env.example .env
   ```
2. Edit file `.env` menggunakan teks editor (misalnya `nano .env`) dan masukkan `TELEGRAM_TOKEN` yang didapat dari `@BotFather` di aplikasi Telegram.
3. Jalankan aplikasi:
   ```bash
   python main.py
   ```
4. Biarkan terminal tetap terbuka. Sistem sekarang memantau pergerakan GPS dan menunggu perintah Telegram.

## Perintah Telegram Bot

Anda dapat mengontrol bot melalui menu keyboard (Custom Keyboard) di bagian bawah layar chat, atau dengan mengetikkan perintah berikut:

### `/start`
Menampilkan pesan sambutan dan memunculkan tombol menu navigasi utama (Cek Lokasi dan Status Sistem).

### `/lokasi` (atau tombol "📍 Cek Lokasi")
Meminta bot untuk mengirimkan lokasi terkini yang dibaca oleh sensor GPS. 
- Bot akan mengirimkan **Location Map** bawaan Telegram yang bisa diklik.
- Bot juga akan memberikan rincian teks berupa Latitude, Longitude, Altitude, Kecepatan, waktu update terakhir, dan link Google Maps.
- *Catatan:* Jika GPS belum mendapatkan sinyal, bot akan memberikan peringatan untuk menunggu.

### `/status` (atau tombol "📊 Status Sistem")
Menampilkan status hardware (sensor GPS). Bot akan menginformasikan:
- Apakah kabel/koneksi USB GPS terhubung ke sistem.
- Apakah sensor sedang dalam keadaan "Lock" (mendapat sinyal dari satelit) atau "Mencari satelit".
- Waktu pembacaan data GPS terakhir.

## Mengakses Data Hasil
Sistem secara otomatis membuat folder bernama `data` yang di dalamnya terdapat:
- `system.log`: Catatan (log) event internal aplikasi (error, inisialisasi, dll).
- `gps_log.csv`: Hasil tracking perjalanan yang mencakup waktu dan koordinat. File ini dapat dibuka di Excel atau perangkat lunak pemetaan GIS.
