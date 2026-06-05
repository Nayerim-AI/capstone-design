# TUP-5 Fill Recommendation

## Bagian TUP-5 yang masih placeholder

1. Latar belakang teknis pengukuran coverage DVB-T2.
2. Spesifikasi alat: Orange Pi Zero3, RTL-SDR V3, antena capung, GPS BU-353, Telegram Bot, koneksi internet.
3. Diagram blok sistem dan alur data.
4. Metode pengukuran field strength.
5. Rumus pengolahan sinyal dan koreksi.
6. Parameter SDR: frekuensi, sample rate, bandwidth ukur, FFT size, gain, repeat count.
7. Parameter antena dan instalasi: tinggi antena receiver, antenna factor, cable loss, orientasi antena, lokasi/lingkungan.
8. Validasi/pembandingan dengan RadioPlanner.
9. Tabel hasil uji lapangan.
10. Analisis selisih alat vs RadioPlanner.
11. Keterbatasan alat karena tidak memakai HD Ranger/spectrum analyzer terkalibrasi.
12. Kesimpulan sementara dan saran pengembangan.

## Data yang harus diisi

| Bagian | Data yang wajib diisi |
|---|---|
| Identitas titik uji | Nama lokasi, latitude, longitude, waktu, foto lokasi |
| Parameter frekuensi | Frekuensi MHz, kanal DVB-T2, bandwidth kanal |
| Parameter alat | Gain SDR, sample rate, measurement bandwidth, FFT size, repeat count |
| Parameter antena Rx | Tinggi antena, jenis antena, antenna factor jika ada, cable loss |
| Hasil alat | Raw bandpower, field strength estimasi, std deviasi, kategori |
| Hasil GPS | Status fix, latitude, longitude, Google Maps URL |
| Hasil Telegram | Screenshot pesan `/measure` |
| Hasil RadioPlanner | Field Strength/Point Analysis dBµV/m pada koordinat yang sama |
| Selisih | Alat - RadioPlanner dalam dB |
| Parameter transmitter | Lokasi Tx, Tx power/EIRP, tinggi antena, gain antena, azimuth, model propagasi |

## Bukti yang perlu disisipkan

1. Foto alat lengkap saat digunakan.
2. Foto posisi antena dan GPS saat pengujian.
3. Screenshot terminal/service status.
4. Screenshot Telegram hasil `/measure`.
5. CSV log measurement RF lengkap.
6. CSV atau screenshot GPS log.
7. Screenshot RadioPlanner Field Strength map.
8. Screenshot RadioPlanner Point Analysis per titik.
9. Tabel perbandingan alat vs RadioPlanner.
10. Catatan parameter pengujian lapangan.

## Kalimat rekomendasi hasil pengujian

> Berdasarkan pengujian awal, sistem prototype mampu melakukan akuisisi sinyal DVB-T2 menggunakan RTL-SDR, membaca koordinat GPS, menghitung level sinyal relatif, dan mengirimkan hasil pengukuran melalui Telegram. Nilai yang dihasilkan digunakan sebagai estimasi level sinyal untuk analisis tren coverage pada titik uji.

> Pembandingan dengan RadioPlanner dilakukan pada frekuensi dan koordinat yang sama. Hasil pembandingan digunakan untuk melihat kesesuaian pola/tren antara estimasi alat dan model propagasi, bukan sebagai kalibrasi absolut.

## Kalimat keterbatasan terkait tidak adanya HD Ranger

> Penelitian ini tidak menggunakan field strength meter atau spectrum analyzer terkalibrasi seperti HD Ranger. Oleh karena itu, nilai dBµV/m dari prototype tidak diklaim sebagai nilai absolut tersertifikasi. Nilai tersebut merupakan estimasi berbasis bandpower relatif RTL-SDR yang memerlukan koreksi dan kalibrasi lebih lanjut menggunakan alat referensi.

> RadioPlanner digunakan sebagai aplikasi pembanding berbasis simulasi/model propagasi. RadioPlanner tidak menggantikan fungsi alat ukur referensi untuk kalibrasi, tetapi membantu mengevaluasi kewajaran hasil pada titik koordinat yang sama.

## Kesimpulan sementara yang aman secara akademik

> Prototype DVB-T2 Coverage Analyzer telah menunjukkan fungsi dasar akuisisi sinyal, pembacaan GPS, pengiriman Telegram, dan estimasi level sinyal relatif. Sistem layak digunakan untuk uji lapangan pendahuluan dengan tujuan mengumpulkan data tren sinyal dan mengevaluasi integrasi sistem.

> Untuk klaim field strength absolut dan kategori coverage final, sistem masih memerlukan penyempurnaan berupa pencatatan measurement CSV lengkap, koreksi antenna factor, cable loss, gain receiver, bandwidth kanal, serta validasi menggunakan alat ukur referensi terkalibrasi.

## Perbaikan sebelum laporan final

1. Tambahkan log CSV measurement RF lengkap.
2. Masukkan tinggi antena receiver ke catatan/log.
3. Tambahkan konfigurasi dan dokumentasi antenna factor/cable loss.
4. Jelaskan bahwa hasil saat ini adalah estimasi relatif.
5. Buat tabel pembanding RadioPlanner dengan koordinat yang sama.
6. Revisi SOP agar tidak lagi berfokus pada GPS logger saja.
7. Tambahkan sumber untuk threshold kategori Komdigi atau ubah menjadi kategori sementara.
8. Tambahkan evidence lengkap sesuai `EVIDENCE_MANIFEST.csv`.
