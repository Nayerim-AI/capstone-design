# RadioPlanner Comparison Plan

## Tujuan pembandingan

Tujuan pembandingan adalah mengecek apakah hasil prototype DVB-T2 Coverage Analyzer memiliki pola/tren yang masuk akal dibandingkan simulasi/model RadioPlanner pada titik koordinat yang sama.

RadioPlanner digunakan sebagai pembanding simulasi/model propagasi, bukan sebagai pengganti kalibrasi alat ukur profesional. Tanpa HD Ranger/spectrum analyzer terkalibrasi, hasil alat tidak boleh diklaim sebagai field strength absolut tersertifikasi.

## Parameter yang harus sama antara alat dan RadioPlanner

| Parameter | Di alat | Di RadioPlanner | Wajib dicatat |
|---|---|---|---|
| Frekuensi/kanal | `frequency_mhz` atau channel | Frequency/channel transmitter | Ya |
| Koordinat receiver | GPS BU-353 latitude/longitude | Point Analysis coordinate | Ya |
| Tinggi antena receiver | Diukur manual | Receiver antenna height | Ya |
| Polarisasi/arah antena | Catatan manual | Sesuai konfigurasi | Ya |
| Lokasi transmitter | Catatan sumber/stasiun | Transmitter site | Ya |
| Tx power/EIRP | Dari data transmitter | RadioPlanner Tx power/EIRP | Ya |
| Tinggi antena pemancar | Dari data transmitter | Tx antenna height | Ya |
| Gain antena pemancar | Dari data transmitter | Tx antenna gain | Ya |
| Azimuth/tilt | Dari data transmitter | Antenna pattern/orientation | Ya |
| Model propagasi | Tidak ada di alat | Model RadioPlanner | Ya |
| Threshold field strength | Kategori laporan | Threshold RadioPlanner/Komdigi | Ya |
| Waktu pengukuran | Timestamp sistem/GPS | Catatan laporan | Ya |
| Lingkungan titik | Foto/catatan | Tidak langsung | Ya |

## Langkah input di RadioPlanner

1. Buat/cek project RadioPlanner untuk area uji.
2. Masukkan data transmitter: nama site, latitude/longitude, frekuensi/kanal DVB-T2, Tx power/EIRP, tinggi antena, gain antena, azimuth, tilt, pola antena jika tersedia, model propagasi, dan threshold field strength.
3. Masukkan data terrain/map sesuai kemampuan RadioPlanner.
4. Jalankan coverage/field strength prediction.
5. Untuk setiap titik uji dari GPS alat, gunakan Field Strength/Point Analysis di koordinat yang sama.
6. Catat output dalam dBµV/m dan ambil screenshot.

## Langkah pengambilan data dari alat

1. Siapkan Orange Pi Zero3, RTL-SDR V3, antena capung, GPS BU-353, dan internet.
2. Catat tinggi antena receiver, nama titik, lingkungan, obstacle, indoor/outdoor, dan orientasi antena.
3. Pastikan service aktif: `sudo systemctl status dvbt2-analyzer.service`.
4. Di Telegram jalankan `/status`, lalu `/measure <frequency_mhz>` contoh `/measure 514`.
5. Pastikan GPS `Valid`. Jika belum fix, ulangi setelah GPS valid.
6. Simpan screenshot Telegram, terminal/log, CSV, foto alat, dan foto lokasi.
7. Ulangi minimal 3 kali per titik; gunakan rata-rata dan std deviasi.

## Format tabel pembanding

| No | Lokasi | Latitude | Longitude | Tinggi Rx Antena (m) | Frekuensi/Kanal | Field Strength Alat (dBµV/m est.) | Std Dev (dB) | Field Strength RadioPlanner (dBµV/m) | Selisih (Alat - RP) dB | Kategori Komdigi | Catatan |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| 1 | Titik A | -6.xxxxxx | 106.xxxxxx | 1.5 | 514 MHz / CH xx | xx.xx | x.xx | xx.xx | xx.xx | Cukup | GPS valid, outdoor |
| 2 | Titik B | -6.xxxxxx | 106.xxxxxx | 1.5 | 514 MHz / CH xx | xx.xx | x.xx | xx.xx | xx.xx | Baik | Dekat obstacle |

Rumus selisih:

```text
selisih_dB = field_strength_alat_dbuvm_est - field_strength_radioplanner_dbuvm
```

## Cara membaca hasil

- Jika selisih antar titik relatif konsisten, alat bisa dipakai untuk melihat tren relatif setelah diberi offset kerja.
- Jika titik dengan prediksi RadioPlanner tinggi juga menunjukkan nilai alat lebih tinggi, pola pipeline masuk akal secara relatif.
- Jika selisih berubah besar antar titik, kemungkinan ada pengaruh antenna orientation, multipath, obstacle lokal, overload RTL-SDR, GPS mismatch, atau parameter transmitter/model RadioPlanner tidak cocok.
- RadioPlanner tidak membuktikan kalibrasi alat. Validasi absolut tetap butuh alat ukur referensi.

## Kalimat aman untuk laporan

> Pengujian ini membandingkan estimasi level sinyal dari prototype berbasis RTL-SDR dengan hasil prediksi RadioPlanner pada koordinat yang sama. RadioPlanner digunakan sebagai pembanding model propagasi, bukan sebagai alat kalibrasi. Karena penelitian tidak menggunakan spectrum analyzer/field strength meter terkalibrasi seperti HD Ranger, nilai dBµV/m pada prototype diperlakukan sebagai estimasi relatif dengan offset kalibrasi, bukan nilai absolut tersertifikasi.

> Hasil yang dianalisis adalah kesesuaian tren dan selisih level pada beberapa titik uji, dengan parameter frekuensi, koordinat, tinggi antena penerima, dan konfigurasi transmitter dibuat sedekat mungkin antara alat dan RadioPlanner.
