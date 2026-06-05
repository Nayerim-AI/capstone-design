# Field Test Route — DVB-T2 Jabodetabek × RadioPlanner

Dokumen ini menyelaraskan rute uji lapangan, baseline MUX DVB-T2 Jabodetabek, dan format data agar hasil alat lapangan bisa dibandingkan dengan prediksi RadioPlanner / ID Radio Planner.

## Prinsip

Setiap titik memakai daftar MUX/frekuensi yang sama. Perbedaan hasil harus dibaca sebagai efek kondisi lapangan: jarak/arah pemancar, gedung tinggi, multipath, ketinggian/arah antena, noise lokal, kabel/konektor, dan fixed gain receiver.

Jangan membandingkan berdasarkan nama TV saja. Bandingkan berdasarkan:

```text
Titik + koordinat + UHF channel + frekuensi MHz + lock/tidak lock + strength/RSSI + quality/SNR/MER + catatan lokasi
```

Jika alat belum terkalibrasi absolut, tulis sebagai `relative measurement` / `estimasi SDR`, bukan field strength final tersertifikasi.

## Baseline MUX Wajib Scan

Source: Permenkominfo/Kemkomdigi No. 6 Tahun 2019 dan referensi DVB-T2 Jabodetabek.

| Channel ID | MUX / Grup | UHF | MHz | Contoh Channel | Status |
|---|---|---:|---:|---|---|
| `UHF24_EMTEK` | Emtek Group | 24 | 498 | SCTV, Indosiar, Moji, Mentari TV | baseline |
| `UHF28_MNC` | MNC Group | 28 | 530 | RCTI, GTV, MNCTV, iNews | baseline |
| `UHF31_METROTV` | Metro TV Group | 31 | 554 | Metro TV, Magna Channel, BN Channel | baseline |
| `UHF34_VIVA` | VIVA Group | 34 | 578 | tvOne, ANTV, JakTV | baseline |
| `UHF40_TRANS` | Trans Media | 40 | 626 | Trans TV, Trans7, CNN Indonesia, CNBC Indonesia | baseline |
| `UHF43_TVRI` | TVRI / Publik | 43 | 650 | TVRI Nasional, TVRI Sport, TVRI World, TVRI Jakarta, NET | baseline |

Optional:

| Channel ID | UHF | MHz | Status |
|---|---:|---:|---|
| `UHF25_TVRI_JOGLO_514` | 25 | 514 | optional / RadioPlanner Rx_Parameter anchor |
| `UHF48_OPTIONAL` | 48 | 690 | optional jika ada waktu |

Config: `config/dvbt2_channels.yaml`.

## Titik Uji dan Urutan Rute

Config: `config/test_locations.yaml`.

| Order | ID | Titik | Initial Coordinate | Karakter |
|---:|---|---|---|---|
| 1 | `stasiun_juanda` | Stasiun Juanda | `-6.1711, 106.8350` | stasiun/rel/noise/multipath |
| 2 | `monas` | Monas / Lapangan Merdeka | `-6.1754, 106.8272` | open area benchmark |
| 3 | `bundaran_hi` | Bundaran HI | `-6.1944, 106.8230` | urban canyon/gedung tinggi |
| 4 | `indomaret_tomang` | Indomaret Tomang Raya | `-6.1683, 106.8007` | roadside Jakarta Barat |
| 5 | `cp_taman_anggrek` | Central Park / Taman Anggrek | `-6.1774, 106.7907` | mall/gedung tinggi |

Koordinat ini hanya patokan RadioPlanner. Saat pengukuran, koordinat aktual wajib diambil dari GPS/HP di posisi berdiri antena.

## Command Lapangan

Lihat lokasi:

```bash
python3 main.py --list-locations
python3 main.py --route-order
```

Lihat channel/MUX:

```bash
python3 main.py --list-channels
```

Scan baseline 6 MUX per titik:

```bash
python3 main.py --mode cli --location stasiun_juanda --scan baseline --repeat 5
python3 main.py --mode cli --location monas --scan baseline --repeat 5
python3 main.py --mode cli --location bundaran_hi --scan baseline --repeat 5
python3 main.py --mode cli --location indomaret_tomang --scan baseline --repeat 5
python3 main.py --mode cli --location cp_taman_anggrek --scan baseline --repeat 5
```

Scan optional:

```bash
python3 main.py --mode cli --location monas --scan optional --repeat 5
```

Scan all baseline + optional:

```bash
python3 main.py --mode cli --location monas --scan all --repeat 5
```

Scan satu channel tertentu:

```bash
python3 main.py --mode cli --location monas --scan single --channel UHF24_EMTEK --repeat 5
```

Manual frequency override:

```bash
python3 main.py --mode cli --scan single --freq 498 --repeat 5
```

## Output Log

### RF measurement log lama

```text
data/measurement_log.csv
```

Tetap berisi RF measurement detail dan kompatibel dengan P0.

### Field scan log baru

```text
data/field_scan_log.csv
```

Schema mendukung template referensi:

```text
timestamp,site_id,site_name,initial_lat,initial_lon,lat,lon,uhf_channel,frequency_mhz,channel_name,network,scan_priority,lock_status,signal_strength,field_strength_est_dbuvm,signal_quality,snr_mer_db,ber,per,antenna_type,antenna_height_m,antenna_direction_deg,receiver_gain_db,calibration_mode,radio_planner_dbuvm,radio_planner_margin_db,delta_vs_radioplanner_db,measurement_mode,notes
```

Catatan: RTL-SDR flow saat ini mengukur power/bandpower. Field `lock_status`, `SNR/MER`, `BER/PER` bernilai `unknown/null` sampai ada decoder DVB-T2 atau scanner tambahan yang menyediakan metrik tersebut.

## RadioPlanner Alignment

Untuk setiap titik dan frekuensi:

1. Di RadioPlanner, pakai koordinat aktual dan tinggi RX yang sama dengan alat.
2. Catat field strength dBµV/m dan margin.
3. Jalankan scan lapangan.
4. Bandingkan `radio_planner_dbuvm` vs `field_strength_est_dbuvm`.
5. Hitung delta/offset bila diperlukan.

Offset model-aligned:

```bash
python3 scripts/compute_model_aligned_offset.py \
  --raw-bandpower-db <RAW_ALAT_ANCHOR> \
  --radioplanner-dbuvm <RADIOPLANNER_ANCHOR>
```

Lalu set:

```yaml
CALIBRATION_MODE: "radioplanner_model_aligned"
CALIBRATION_OFFSET_DB: <offset_model_db>
CALIBRATION_SOURCE: "RadioPlanner anchor:<tanggal>:<site>:<uhf>"
```

## Batas Klaim

- RadioPlanner adalah pembanding model/simulasi, bukan instrumen kalibrasi.
- `radioplanner_model_aligned` bukan kalibrasi absolut.
- Hasil SDR tetap estimasi relatif jika belum dibandingkan dengan instrumen referensi.
- Bandwidth measurement masih `1.8 MHz`, jadi output adalah `center_bandpower_1p8mhz`, bukan total 8 MHz channel power.

## Checklist Bukti Per Titik

- Foto lokasi dan posisi antena.
- Screenshot GPS/koordinat aktual.
- Screenshot hasil scan/manual tune.
- Log CSV mentah `measurement_log.csv` dan `field_scan_log.csv`.
- Catatan tinggi antena, gain, arah antena.
- Screenshot/prediksi RadioPlanner untuk titik dan frekuensi yang sama.
