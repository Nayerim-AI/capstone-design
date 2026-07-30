# Catatan Update

Tanggal: 30 Juli 2026

## Ringkasan

- Menambahkan penyimpanan hasil pengukuran ke SQLite pada `data/capstone.db`.
- Menambahkan tabel sesi pemindaian, hasil pengukuran, dan pembacaan bandpower mentah.
- Mengintegrasikan logging SQLite ke jalur CLI dan perintah pengukuran Telegram tanpa menghapus logging CSV yang sudah ada.
- Menyimpan statistik pembacaan (`minimum`, `maksimum`, dan deviasi standar), kategori acuan Komdigi, kualitas sinyal, konfigurasi SDR, koreksi kalibrasi, serta data GPS yang tersedia.
- Menambahkan `src/backfill_csv.py` untuk memigrasikan riwayat `data/measurement_log.csv` ke SQLite. Data CSV lama hanya berisi nilai agregat sehingga pembacaan mentah individual tidak dapat direkonstruksi.
- Menambahkan `src/plot_measurements.py` untuk membuat grafik per kanal, peta titik pengukuran, timeline, dan sweep frekuensi dari SQLite.
- Menambahkan aturan `.gitignore` agar database, WAL/SHM, file ekspor `.measure`, CSV, log, dan grafik hasil runtime tidak masuk repository.

## Penggunaan

Migrasi data CSV lama satu kali:

```bash
python3 src/backfill_csv.py
```

Peringatan: skrip backfill tidak melakukan deduplikasi. Jangan menjalankannya berulang pada database yang sama tanpa memeriksa data terlebih dahulu.

Membuat grafik dari data SQLite:

```bash
python3 src/plot_measurements.py
```

Hasil grafik disimpan lokal di `data/plots/` dan tidak dilacak Git.

## Verifikasi

```bash
python3 -m unittest discover -s test -v
python3 -m py_compile main.py src/logger.py src/telegram_bot.py src/database.py src/backfill_csv.py src/plot_measurements.py
```

Hasil sebelum commit: 39 test lulus. Pemeriksaan sintaks Python dan pembuatan empat grafik lulus. Suite lama masih menampilkan satu `ResourceWarning` karena file fixture CSV tidak ditutup di `test/test_p0_measurement_pipeline.py`; test tetap lulus.

## Batasan

- Nilai RTL-SDR tetap merupakan estimasi berbasis bandpower dan koreksi konfigurasi, bukan pengukuran field strength absolut tersertifikasi.
- Database dan hasil plot adalah data runtime lokal; backup harus dilakukan terpisah jika diperlukan.
- Dashboard WiFi yang masih dalam pengembangan belum termasuk update ini karena perlu perbaikan keamanan sebelum dipublikasikan.
