# PATCH P0 Measurement Log

## Perubahan yang dilakukan

Patch P0 menambahkan kesiapan minimum untuk uji lapangan pendahuluan DVB-T2 Coverage Analyzer:

1. Konfigurasi measurement transparan.
2. Fixed/manual SDR gain.
3. Mapping kanal/frekuensi DVB-T2 berbasis file placeholder.
4. RF measurement log CSV lengkap.
5. Perhitungan field strength estimasi transparan:

```text
field_strength_est_dbuvm = raw_bandpower_db + total_correction_db
```

6. Klasifikasi acuan Komdigi:

```text
< 39.5         -> DI_BAWAH_ACUAN
39.5 .. 76.2  -> DALAM_RENTANG_ACUAN
> 76.2        -> DI_ATAS_ACUAN
```

7. Helper script menghitung offset RadioPlanner model-aligned.
8. Telegram dashboard diperbarui dengan channel/frequency, kategori, gain, calibration mode, measurement mode, timestamp, GPS, dan disclaimer.
9. Test otomatis untuk config, CSV header, kategori, offset, field strength, Telegram message, GPS no-fix, dan log saat Telegram gagal.

## File baru/diubah

### File baru

- `config/measurement_config.yaml`
- `config/dvbt2_channels.yaml`
- `scripts/compute_model_aligned_offset.py`
- `test/test_p0_measurement_pipeline.py`
- `PATCH_P0_MEASUREMENT_LOG.md`

### File diubah

- `main.py`
- `src/config.py`
- `src/dvbt2_core.py`
- `src/logger.py`
- `src/telegram_bot.py`
- `.env.example`

File audit sebelumnya tidak dihapus:

- `AUDIT_FIELD_STRENGTH_PIPELINE.md`
- `RADIOPLANNER_COMPARISON_PLAN.md`
- `EVIDENCE_MANIFEST.csv`
- `TUP5_FILL_RECOMMENDATION.md`

## Cara menjalankan pengukuran

### CLI

```bash
cd ~/capstone-design-repo
python3 main.py --mode cli --freq 514 --repeat 5
```

### Telegram service

```bash
sudo systemctl restart dvbt2-analyzer.service
sudo systemctl status dvbt2-analyzer.service
journalctl -u dvbt2-analyzer.service -f
```

Di Telegram:

```text
/status
/measure
/measure 514
```

### Menampilkan gain RTL-SDR yang tersedia

```bash
python3 main.py --list-gains
```

Jika gain yang diminta tidak tersedia, program memilih gain terdekat yang didukung RTL-SDR dan menulis nilai aktual ke log.

## Cara mengisi config frekuensi

Edit:

```bash
nano config/dvbt2_channels.yaml
nano config/measurement_config.yaml
```

Contoh `dvbt2_channels.yaml`:

```yaml
channels:
  TEST_CH:
    channel_name: "TEST_CH"
    frequency_mhz: 0.0
    bandwidth_mhz: 8.0
    notes: "Isi sesuai kanal DVB-T2 lapangan"
```

Jangan mengarang frekuensi lokal. Isi berdasarkan kanal/frekuensi pengujian sebenarnya.

Edit `measurement_config.yaml`:

```yaml
CHANNEL_NAME: "TEST_CH"
FREQUENCY_MHZ: 514.0
SDR_GAIN_DB: 19.7
RX_ANTENNA_HEIGHT_M: 1.5
```

## Cara menghitung offset dari RadioPlanner

Gunakan anchor point: koordinat sama, frekuensi sama, tinggi antena receiver sama.

```bash
python3 scripts/compute_model_aligned_offset.py \
  --raw-bandpower-db 42.50 \
  --radioplanner-dbuvm 55.00
```

Output:

```text
offset_model_db = 12.50 dB
CALIBRATION_MODE=radioplanner_model_aligned
CALIBRATION_OFFSET_DB=12.50
```

Catatan: offset ini bukan kalibrasi absolut. Ini hanya model-aligned terhadap RadioPlanner pada anchor point.

## Keterbatasan

1. Bandwidth ukur saat ini 1.8 MHz. Ini center-bandpower estimation, bukan full 8 MHz DVB-T2 channel measurement.
2. Default `CALIBRATION_MODE=raw`, `CALIBRATION_OFFSET_DB=0.0`, `CALIBRATION_SOURCE=none`.
3. `ANTENNA_FACTOR_DB_PER_M=null` jika belum diketahui. Jangan diisi asal.
4. `CABLE_LOSS_DB=0.0` jika belum diukur.
5. Tanpa HD Ranger/spectrum analyzer, hasil tidak boleh diklaim sebagai field strength absolut tersertifikasi.
6. RadioPlanner adalah pembanding simulasi/model, bukan alat kalibrasi profesional.

## Format bukti untuk TUP-5

Minimal kumpulkan:

1. `data/measurement_log.csv`
2. `data/gps_log.csv`
3. Screenshot Telegram `/measure` dengan GPS valid.
4. Screenshot terminal/service status.
5. Foto alat dan posisi antena.
6. Foto lokasi uji.
7. Screenshot RadioPlanner Field Strength.
8. Screenshot RadioPlanner Point Analysis pada koordinat yang sama.
9. Catatan parameter transmitter RadioPlanner.
10. Tabel perbandingan alat vs RadioPlanner.

## Format CSV measurement

File: `data/measurement_log.csv`

Kolom:

```text
timestamp,latitude,longitude,gps_fix,gps_satellites,channel_name,frequency_mhz,sdr_gain_db,sample_rate_hz,measurement_bandwidth_hz,measurement_mode,raw_bandpower_db,calibration_mode,calibration_offset_db,calibration_source,antenna_factor_db_per_m,cable_loss_db,rx_antenna_height_m,total_correction_db,field_strength_est_dbuvm,komdigi_lower_dbuvm,komdigi_upper_dbuvm,category,telegram_status,telegram_delay_s,notes
```
