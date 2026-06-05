# Audit Field Strength Pipeline DVB-T2 Coverage Analyzer

## Ringkasan kondisi pipeline saat ini

Pipeline sudah layak sebagai prototype pengukuran relatif berbasis RTL-SDR + GPS + Telegram. Program sudah bisa memilih frekuensi center, membaca IQ sample dari RTL-SDR, menghitung bandpower relatif dengan FFT/Welch sederhana, menambahkan offset kalibrasi, mengklasifikasikan kualitas sinyal, membaca koordinat GPS NMEA, dan mengirim dashboard Telegram.

Namun pipeline belum layak diklaim sebagai pengukuran field strength absolut dBµV/m. Nilai `field_strength_dbuvm_est` saat ini adalah `bandpower_relative_db + calibration_offset_db`, bukan hasil konversi fisik dari input receiver ke medan listrik. Belum ada antenna factor, cable loss, gain chain, koreksi bandwidth/RBW, konversi dBm/dBµV, validasi linearitas RTL-SDR, atau offset hasil kalibrasi dengan alat referensi tersertifikasi.

RadioPlanner dapat dipakai sebagai pembanding simulasi/model, bukan pengganti kalibrasi alat ukur profesional.

## File yang diperiksa

| File | Fungsi | Catatan audit |
|---|---|---|
| `main.py` | Entry point CLI/Telegram | Memilih mode, frekuensi CLI, konfigurasi SDR, start GPS/Telegram. |
| `src/config.py` | Load `.env` | Memuat token, default frequency, calibration offset, GPS port/baudrate. |
| `src/dvbt2_core.py` | Core RF/RTL-SDR | Inisialisasi SDR, baca IQ, FFT/PSD, bandpower, estimasi field strength. |
| `src/gps_reader.py` | GPS BU-353/NMEA | Parsing GGA/RMC, status fix, latitude/longitude, maps URL, log GPS. |
| `src/logger.py` | System log dan GPS CSV | Saat ini hanya CSV GPS, belum CSV measurement RF lengkap. |
| `src/telegram_bot.py` | Bot Telegram | `/status`, `/measure`, format dashboard field strength + koordinat. |
| `.env.example` | Template konfigurasi | Token, default freq, calibration offset, GPS config. |
| `deployment/dvbt2-analyzer.service` | Autostart service | Menjalankan bot Telegram via systemd. |
| `scripts/preflight_check.sh` | Cek hardware/config | Cek `.env`, GPS device, RTL-SDR via `lsusb`. |
| `docs/QUICKSTART.md` | Panduan operasi | Sudah menyebut field strength masih estimasi relatif. |
| `docs/SOP_Pengukuran.md` | SOP lama | Masih fokus GPS logger, belum SOP DVB-T2 field strength. |
| `test/*.py` | Unit tests | Test PSD, offset, GPS schema, Telegram formatting. |

## Alur pipeline aktual

1. User menjalankan CLI `python3 main.py --mode cli --freq 514 --repeat 5` atau Telegram `/measure 514`.
2. Konfigurasi dibaca dari `.env`: `DEFAULT_FREQ_MHZ`, `CALIBRATION_OFFSET_DB`, `GPS_ENABLED`, `GPS_PORT`, `GPS_BAUDRATE`.
3. `main.py` membuat `Dvbt2SdrConfig(calibration_offset_db=...)`.
4. `src/dvbt2_core.py` membuka RTL-SDR dengan `sample_rate=2.048e6`, `center_freq=freq_mhz*1e6`, dan `gain=19.7 dB`.
5. Program melakukan warmup read, lalu membaca IQ sample sebanyak `repeat` kali.
6. Sample diproses dengan FFT 2048, Hann window, Welch averaging 50% overlap, `fftshift`, dan PSD relatif dalam dB.
7. Bandpower dihitung dalam `measurement_bw_hz=1.8e6`, dengan area DC ±20 kHz dibuang.
8. Field strength estimasi dihitung: `average_bandpower_db + calibration_offset_db`.
9. Kualitas sinyal diklasifikasikan dengan threshold hardcoded 65/55/48/35 dBµV/m.
10. Telegram membaca GPS dan mengirim dashboard berisi frekuensi, bandpower, field strength estimasi, gain, std deviasi, status GPS, latitude, longitude, Maps URL, dan calibration offset.

## Temuan mayor

### 1. Field strength dBµV/m belum dihitung secara fisik

Kode saat ini hanya menjumlahkan bandpower relatif dan offset. Untuk dBµV/m dibutuhkan rantai koreksi: power/voltage input receiver, antenna factor, cable loss, koreksi LNA/attenuator, dan offset kalibrasi. Klaim aman: estimasi relatif, bukan absolut tersertifikasi.

### 2. Belum ada antenna factor dan cable loss

Tidak ditemukan konfigurasi untuk antenna factor antena capung per frekuensi, cable loss, connector loss, LNA/attenuator, atau tinggi antena receiver.

### 3. Bandwidth ukur 1.8 MHz tidak apple-to-apple dengan kanal DVB-T2 8 MHz

Dengan sample rate 2.048 MS/s, alat hanya melihat sekitar ±1.024 MHz di sekitar center frequency. Ini tidak menangkap seluruh lebar kanal 8 MHz. Jika target field strength kanal DVB-T2, perlu SDR/sample rate yang mencakup kanal, sweep sub-band, atau disclaimer bahwa yang diukur adalah level relatif sekitar center frequency.

### 4. CSV measurement RF lengkap belum ada

`src/logger.py` hanya menulis `data/gps_log.csv`. Belum ada CSV pengukuran RF dengan timestamp, lokasi, latitude, longitude, frequency/channel, gain, raw power, correction/offset, field_strength_dbuvm, kategori, dan status Telegram.

### 5. Tidak ada mapping kanal DVB-T2

Program memilih frekuensi dengan angka MHz langsung. Belum ada tabel channel UHF Indonesia, bandwidth 8 MHz, atau label kanal.

### 6. Threshold kategori belum diberi sumber

Threshold 65/55/48/35 dBµV/m belum memiliki referensi Komdigi/ITU/vendor di kode atau dokumen.

### 7. Gain SDR fixed, tetapi belum terekspos di `.env`

`gain_db=19.7` diset manual ke `sdr.gain`, lebih repeatable daripada auto gain. Namun nilainya hardcoded dan belum dicatat dari config lapangan.

## Temuan minor

1. `src/dvbt2_core.py` mengimpor `argparse` tetapi tidak dipakai.
2. `docs/SOP_Pengukuran.md` masih menyebut GPS Logger dan belum sinkron dengan DVB-T2 + RTL-SDR V3 + BU-353.
3. Telegram status `RTL-SDR: OK` hanya mengecek import `RtlSdr`, bukan membuka device.
4. Telegram `/measure` tidak menyimpan hasil measurement RF ke CSV.
5. Jika GPS belum fix, measurement tetap dikirim; data tanpa koordinat harus ditandai tidak valid untuk comparison.
6. Tidak ada rate limit eksplisit pada `/measure`.
7. Tidak ada field `telegram_status` di log karena measurement log belum ada.
8. `CALIBRATION_OFFSET_DB=0.0` default harus dijelaskan sebagai belum dikalibrasi.
9. Tidak ada catatan tinggi antena receiver.
10. Tidak ada pencatatan lingkungan: lokasi, arah antena, cuaca, obstacle, indoor/outdoor.

## Risiko teknis

| Risiko | Dampak | Level |
|---|---|---|
| Nilai dBµV/m belum absolut | Kesimpulan laporan bisa dianggap klaim kalibrasi palsu | Tinggi |
| Bandwidth ukur hanya 1.8 MHz | Tidak merepresentasikan total kanal DVB-T2 8 MHz | Tinggi |
| Tidak ada CSV measurement lengkap | Evidence lapangan sulit diverifikasi | Tinggi |
| Tidak ada antenna factor/cable loss | Konversi field strength tidak valid secara metrologi | Tinggi |
| Threshold kategori tanpa sumber | Kategori Komdigi bisa dipertanyakan | Sedang-Tinggi |
| GPS kadang belum fix | Titik RadioPlanner tidak apple-to-apple | Sedang |
| Internet/Telegram gagal | Hasil bisa tidak terkirim; perlu log lokal | Sedang |
| RTL-SDR overload/nonlinear | Bandpower relatif bisa bias | Sedang |

## Bagian yang sudah layak dipakai

- Struktur repo cukup jelas.
- RTL-SDR memakai manual/fixed gain `19.7 dB`, bukan auto gain.
- Ada warmup read dan settle time.
- Ada repeat measurement dan statistik average/min/max/std.
- Ada error handling saat RTL-SDR, GPS, atau Telegram bermasalah.
- GPS BU-353/NMEA sudah diparse untuk GGA/RMC dan koordinat masuk ke `gps_log.csv`.
- Telegram dashboard menampilkan field strength estimasi, koordinat, Maps URL, gain, sample rate, bandwidth ukur, calibration offset, dan disclaimer.

## Bagian yang belum layak diklaim

- Belum layak disebut alat ukur field strength absolut tersertifikasi.
- Belum layak disebut pengganti HD Ranger/spectrum analyzer.
- Belum layak mengklaim kategori Komdigi final.
- Belum layak menjadikan RadioPlanner sebagai validasi absolut.
- Belum layak menyatakan seluruh kanal DVB-T2 8 MHz terukur.

## Rekomendasi sebelum pengujian lapangan

1. Tambahkan `data/measurement_log.csv` dengan kolom minimal: timestamp, GPS, lokasi, frequency/channel, sample rate, measurement bandwidth, gain, raw bandpower, std deviasi, antenna factor, cable loss, calibration offset, total correction, field_strength_dbuvm_est, category, telegram_status, error.
2. Jadikan `SDR_GAIN_DB`, `MEASUREMENT_BW_HZ`, `SAMPLE_RATE_HZ`, `ANTENNA_FACTOR_DB_PER_M`, `CABLE_LOSS_DB`, `RX_ANTENNA_HEIGHT_M`, dan `CHANNEL_NAME` bagian dari config.
3. Tambahkan mode `--channel` atau mapping kanal UHF.
4. Dokumentasikan rumus konversi; jika belum kalibrasi, gunakan istilah `relative_field_strength_estimate`.
5. Revisi SOP agar sesuai alat aktual.
6. Simpan screenshot Telegram, terminal, CSV, foto setup alat, tinggi antena, dan screenshot RadioPlanner.
7. Jangan gunakan hasil RadioPlanner sebagai offset kalibrasi alat.
