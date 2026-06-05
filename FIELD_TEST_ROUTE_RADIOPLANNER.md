# Field Test Route — RadioPlanner Alignment

Dokumen ini menyelaraskan titik uji lapangan dengan konfigurasi RadioPlanner dan pipeline DVB-T2 Coverage Analyzer.

## Sumber RadioPlanner

File: `Rx_Parameter.xlsx`

Parameter yang terbaca:

- Project: `Testing Simulation Field Strenth DVB-T2 TVRI Joglo`
- Band/frequency: `514 MHz`
- Propagation model: `Rec. ITU-R P.1812-6`
- Area Study: `Field strength (DL)`
- Rx antenna height di RadioPlanner: `20 m`
- Clutter loss: enabled

Catatan penting: tinggi receiver RadioPlanner `20 m` belum sama dengan uji portable. Untuk apple-to-apple, set RadioPlanner ke tinggi antena real alat, default `1.5 m`, atau catat perbedaannya sebagai keterbatasan.

## Titik Pengujian

File lokasi: `config/test_locations.yaml`

| ID | Nama | Frekuensi | Channel | Catatan |
|---|---|---:|---|---|
| `monas` | Monas | 514.0 MHz | `TVRI_JOGLO_514MHZ` | Area terbuka |
| `bundaran_hi` | Bundaran HI | 514.0 MHz | `TVRI_JOGLO_514MHZ` | Area perkotaan padat |
| `cp_taman_anggrek` | CP/Taman Anggrek | 514.0 MHz | `TVRI_JOGLO_514MHZ` | Area komersial padat |
| `stasiun_juanda` | Stasiun Juanda | 514.0 MHz | `TVRI_JOGLO_514MHZ` | Area stasiun kereta |
| `indomaret_tomang` | Indomaret Tomang | 514.0 MHz | `TVRI_JOGLO_514MHZ` | Area pinggir jalan padat |

Koordinat sengaja `null`. Isi koordinat aktual dari GPS lapangan atau screenshot point analysis RadioPlanner.

## Cara menjalankan measurement per lokasi

Lihat daftar lokasi:

```bash
python3 main.py --list-locations
```

Pengukuran per titik:

```bash
python3 main.py --mode cli --location monas --repeat 5
python3 main.py --mode cli --location bundaran_hi --repeat 5
python3 main.py --mode cli --location cp_taman_anggrek --repeat 5
python3 main.py --mode cli --location stasiun_juanda --repeat 5
python3 main.py --mode cli --location indomaret_tomang --repeat 5
```

Override frekuensi jika diperlukan:

```bash
python3 main.py --mode cli --location monas --freq 514 --repeat 5
```

## Alur RadioPlanner model-aligned

Untuk setiap titik:

1. Jalankan point analysis RadioPlanner pada koordinat titik.
2. Catat `field strength` RadioPlanner dBµV/m.
3. Jalankan alat di lokasi yang sama.
4. Ambil `raw_bandpower_db` dari `data/measurement_log.csv`.
5. Jika ingin menyelaraskan model, hitung offset anchor:

```bash
python3 scripts/compute_model_aligned_offset.py \
  --raw-bandpower-db <RAW_ALAT_ANCHOR> \
  --radioplanner-dbuvm <RADIOPLANNER_ANCHOR>
```

6. Set di `config/measurement_config.yaml`:

```yaml
CALIBRATION_MODE: "radioplanner_model_aligned"
CALIBRATION_OFFSET_DB: <offset_model_db>
CALIBRATION_SOURCE: "RadioPlanner anchor:<tanggal>:<location_id>"
```

## Batas klaim

- `radioplanner_model_aligned` bukan kalibrasi absolut.
- RadioPlanner adalah pembanding model/simulasi.
- Tanpa HD Ranger/spectrum analyzer, hasil tidak boleh ditulis sebagai field strength absolut tersertifikasi.
- Bandwidth alat masih `1.8 MHz`, jadi output adalah `center_bandpower_1p8mhz`, bukan full 8 MHz channel power.

## Bukti yang dikumpulkan

Per titik:

- Foto alat dan posisi antena.
- Screenshot GPS atau log koordinat.
- Screenshot RadioPlanner Point Analysis.
- Baris `data/measurement_log.csv`.
- Screenshot Telegram `/measure` jika mode Telegram dipakai.
- Catatan tinggi antena real, kondisi lokasi, cuaca/halangan besar.
