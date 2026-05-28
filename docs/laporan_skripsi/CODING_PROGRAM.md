# BAB IV — IMPLEMENTASI SISTEM
## CODING PROGRAM

### 1. Import Library dan Konfigurasi Sistem

**Deskripsi:**
Pada tahap ini, sistem melakukan import semua library Python yang dibutuhkan untuk RTL-SDR, GPS, Telegram Bot, serta library pendukung seperti numpy, argparse, dotenv, dll. Konfigurasi sistem dilakukan melalui file `.env` yang berisi parameter default seperti frekuensi center 514 MHz, baudrate GPS 4800, dan offset kalibrasi.

**Kode Implementasi:**

```python
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import ENV_FILE, load_config
from dvbt2_core import Dvbt2SdrConfig, print_measurement_result, run_single_measurement
from gps_reader import GPSReader
from logger import system_logger
from telegram_bot import run_telegram_bot
```

**Penjelasan:**
- `import argparse` dan `sys` digunakan untuk parse command-line arguments.
- `pathlib.Path` digunakan untuk handling path file secara cross-platform.
- `SRC_DIR` adalah direktori yang berisi source code utama (`*.py`).
- Semua modul sistem (`dvbt2_core`, `gps_reader`, `telegram_bot`, `logger`) diimport dari `SRC_DIR`.
- `config.py` diimport untuk loading konfigurasi dari `.env`.

---

### 2. Inisialisasi dan Pembacaan Data GPS

**Deskripsi:**
GPS Reader melakukan inisialisasi koneksi serial ke modul GPS (biasanya `/dev/ttyUSB0 @ 4800 baud). Setelah terhubung, sistem membaca data NMEA secara real-time. Data GPS sangat penting untuk mengetahui koordinat lokasi saat pengukuran dilakukan.

**Kode Implementasi:**

```python
class GPSReader:
    def __init__(self, port="/dev/ttyUSB0", baudrate=4800, enabled=True):
        self.port = port
        self.baudrate = baudrate
        self.enabled = enabled
        self.serial_conn = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
        self.current_result = _base_gps_result(...)
```

**Penjelasan:**
- Kelas GPSReader adalah class utama untuk membaca data GPS.
- Parameter default: port `/dev/ttyUSB0`, baudrate 4800, enabled True.
- `serial_conn` adalah koneksi serial ke modul GPS.
- `is_running` adalah flag untuk mengontrol thread pembacaan NMEA.
- `lock` digunakan untuk thread safety saat mengakses `current_result`.
- `_base_gps_result()` mengembalikan dictionary hasil GPS dengan status awal "Belum Fix".

---

### 3. Inisialisasi RTL-SDR dan Akuisisi Sampel IQ

**Deskripsi:**
RTL-SDR diinisialisasi dengan setting frekuensi center (default 514 MHz) dan gain (19.7 dB). Setelah SDR diinisialisasi, dilakukan pembacaan IQ samples (256K samples kompleks) untuk analisis spektrum sinyal DVB-T2.

**Kode Implementasi:**

```python
def initialize_sdr(freq_mhz, config=None):
    if config is None:
        config = Dvbt2SdrConfig()
    if RtlSdr is None:
        raise RuntimeError("Library pyrtlsdr tidak ditemukan...")
    try:
        sdr = RtlSdr()
        sdr.sample_rate = config.sample_rate
        sdr.center_freq = float(freq_mhz) * 1e6
        sdr.gain = config.gain_db
        time.sleep(config.settle_time_s)
        return sdr
    except Exception as exc:
        raise RuntimeError("RTL-SDR tidak dapat diinisialisasi...") from exc
```

**Penjelasan:**
- Fungsi `initialize_sdr()` adalah entry point untuk menginisialisasi RTL-SDR.
- Parameter `freq_mhz` adalah frekuensi center (default 514 MHz).
- `sdr.sample_rate = 2.048e6` (2.048 MSps) adalah rate sampling standar RTL-SDR.
- `sdr.center_freq = freq_mhz * 1e6` mengatur frekuensi center ke MHz.
- `sdr.gain = 19.7` mengatur amplifikasi sinyal.
- `time.sleep(config.settle_time_s)` menunggu SDR stabil.
- Sample rate 2.048 MSps adalah standar untuk RTL-SDR.
- `settle_time_s = 1.0` adalah waktu tunggu stabilisasi sebelum sampling.

---

### 4. Pemrosesan FFT dan Perhitungan Power Spectral Density

**Deskripsi:**
Setelah IQ samples diambil, dilakukan FFT (Fast Fourier Transform) dengan window Hann untuk mengurangi spectral leakage. Hasil FFT dikuadratkan dan di-rata-rata menggunakan metode Welch untuk mendapatkan Power Spectral Density (PSD) relatif.

**Kode Implementasi:**

```python
def compute_psd(samples, config=None):
    samples = np.asarray(samples, dtype=np.complex64)
    if len(samples) < config.fft_size:
        raise ValueError("Jumlah sample lebih kecil dari FFT size.")
    
    window = np.hanning(config.fft_size).astype(np.float32)
    window_power = np.sum(window**2)
    hop_size = config.fft_size // 2
    segment_count = 1 + (len(samples) - config.fft_size) // hop_size
    psd_accum = np.zeros(config.fft_size, dtype=np.float64)
    
    for idx in range(segment_count):
        start = idx * hop_size
        segment = samples[start : start + config.fft_size]
        segment = segment - np.mean(segment)
        windowed_segment = segment * window
        fft_result = np.fft.fft(windowed_segment, n=config.fft_size)
        psd_accum += (np.abs(fft_result) ** 2) / window_power
    
    psd_linear = psd_accum / segment_count
    psd_linear = np.fft.fftshift(psd_linear)
    psd_db = 10.0 * np.log10(psd_linear + 1e-12)
    
    freqs_hz = np.fft.fftfreq(config.fft_size, d=1.0 / config.sample_rate)
    freqs_hz = np.fft.fftshift(freqs_hz)
    
    return freqs_hz, psd_db
```

**Penjelasan:**
- `np.complex64` digunakan untuk IQ samples.
- `np.hanning()` adalah window Hann untuk mengurangi spectral leakage.
- `window_power = np.sum(window**2)` untuk normalisasi.
- `hop_size = config.fft_size // 2` adalah step overlap 50%.
- `segment_count` menghitung jumlah segment yang dapat diambil dari samples.
- `segment = segment - np.mean(segment)` remove DC bias.
- `np.abs(fft_result) ** 2` adalah magnitude squared.
- `psd_accum += ... / window_power` adalah averaging Welch.
- `psd_db = 10.0 * np.log10()` konversi ke dB.
- `np.fft.fftfreq()` menghitung frekuensi Hz untuk setiap bin FFT.

---

### 5. Perhitungan Daya Sinyal dan Konversi Field Strength

**Deskripsi:**
Bandpower dihitung dengan integrasi PSD pada measurement bandwidth (±1.8 MHz dari center frequency). DC spike (±20 kHz) dibuang untuk menghindari artefak RTL-SDR. Hasil bandpower dikonversi menjadi field strength dengan menambahkan calibration offset.

**Kode Implementasi:**

```python
def calculate_bandpower(freqs_hz, psd_db, config=None):
    half_bw = config.measurement_bw_hz / 2.0
    band_mask = (freqs_hz >= -half_bw) & (freqs_hz <= half_bw)
    dc_mask = np.abs(freqs_hz) <= config.dc_exclude_hz
    final_mask = band_mask & (~dc_mask)
    
    if not np.any(final_mask):
        raise ValueError("Tidak ada bin FFT valid untuk measurement bandwidth.")
    
    power_linear = np.sum(10.0 ** (psd_db[final_mask] / 10.0))
    bandpower_db = 10.0 * np.log10(power_linear + 1e-12)
    return float(bandpower_db)

def estimate_field_strength(bandpower_relative_db, calibration_offset_db=0.0):
    return float(bandpower_relative_db + calibration_offset_db)
```

**Penjelasan:**
- `half_bw = config.measurement_bw_hz / 2.0` → bandwidth ±1.8 MHz.
- `band_mask` menandai area ±1.8 MHz dari center frequency.
- `dc_mask` menandai area DC ±20 kHz untuk diexclude.
- `final_mask = band_mask & (~dc_mask)` → area valid untuk integrasi.
- `10.0 ** (psd_db / 10.0)` konversi dari dB ke linear.
- `np.sum()` adalah integrasi power dalam bandwidth.
- `bandpower_db = 10.0 * np.log10()` konversi ke dB.
- `calibration_offset_db` adalah offset untuk kalibrasi alat.

---

### 6. Integrasi dan Pengiriman Laporan via Telegram Bot

**Deskripsi:**
Hasil pengukuran dikompilasi ke dalam format dashboard yang dikirim ke Telegram Bot. Dashboard mencakup informasi RF (frekuensi, bandpower, field strength, kualitas sinyal) dan GPS (koordinat, status satelit, waktu).

**Kode Implementasi:**

```python
def format_measurement_dashboard(rf_result, gps_result, config):
    lines = [
        "📡 DVB-T2 Coverage Analyzer",
        "",
        "🕒 Waktu Sistem:",
        datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB"),
        "",
        "📻 Pengukuran RF",
        f"Frekuensi              : {freq_mhz:.3f} MHz",
        f"Bandpower Relatif     : {bandpower:.2f} dB",
        f"Estimasi Field Strength: {field_strength:.2f} dBµV/m",
        f"Kualitas Sinyal       : {signal_quality}",
        f"Sample Rate           : {sample_rate:.3f} MS/s",
        f"Bandwidth Ukur        : {bw_mhz:.3f} MHz",
        f"Gain SDR              : {gain_db:.1f} dB",
        "",
        "📍 GPS",
        f"Status                : {gps_status}",
        f"Latitude              : {latitude:.6f}",
        f"Longitude             : {longitude:.6f}",
        f"Maps                  : {maps_url}",
        "",
        "⚙️ Sistem",
        f"RTL-SDR               : {rtl_sdr_status}",
        f"GPS Port              : {config.gps_port}",
        f"GPS Baudrate          : {config.gps_baudrate}",
    ]
    return "\n".join(lines)
```

**Penjelasan:**
- `format_measurement_dashboard()` mengompilasi hasil ke format Telegram.
- `datetime.now(WIB)` menampilkan waktu WIB.
- `bandpower` dari hasil `run_single_measurement()`.
- `field_strength` dengan penambahan calibration offset.
- `gps_status` dari GPSReader (Valid/Belum Fix/Nonaktif).
- `maps_url` = `https://maps.google.com/?q={lat},{lng}`.
- Dashboard dikirim via `/measure` command di Telegram.

---

### 7. Fungsi Pengukuran Tunggal (Single Measurement)

**Deskripsi:**
`run_single_measurement()` adalah fungsi utama yang melakukan seluruh alur pengukuran: inisialisasi SDR, warmup readings, repeated measurements, FFT, averaging, dan perhitungan bandpower & field strength.

**Kode Implementasi:**

```python
def run_single_measurement(freq_mhz=514.0, repeat=5, config=None):
    result = _base_result(freq_mhz, config)
    sdr = None
    try:
        sdr = initialize_sdr(freq_mhz, config)
        
        for _ in range(config.warmup_reads):
            capture_iq_samples(sdr, config)
        
        raw_measurements = []
        for _ in range(int(repeat)):
            samples = capture_iq_samples(sdr, config)
            freqs_hz, psd_db = compute_psd(samples, config)
            bandpower_db = calculate_bandpower(freqs_hz, psd_db, config)
            raw_measurements.append(bandpower_db)
            time.sleep(config.repeat_delay_s)
        
        measurements = np.asarray(raw_measurements, dtype=np.float64)
        average_bandpower_db = float(np.mean(measurements))
        field_strength_est = estimate_field_strength(
            average_bandpower_db, config.calibration_offset_db
        )
        
        result.update({
            "average_bandpower_db": average_bandpower_db,
            "field_strength_dbuvm_est": field_strength_est,
            "signal_quality": classify_signal_quality(field_strength_est),
        })
        
        return result
    except Exception as exc:
        result.update({"error": str(exc)})
        return result
    finally:
        if sdr is not None:
            try:
                sdr.close()
            except Exception:
                pass
```

**Penjelasan:**
- `warmup_reads = 2`: mengambil 2 kali sampling untuk stabilisasi awal.
- `repeat = 5`: melakukan 5 kali pengukuran untuk mendapatkan rata-rata.
- `time.sleep(config.repeat_delay_s)` memastikan sampling tidak overlap.
- `np.mean(raw_measurements)` adalah average dari 5 kali pengukuran.
- `classify_signal_quality()` memetakan field strength ke kategori kualitas.
- `sdr.close()` membersihkan resource setelah pengukuran selesai.

---

### 8. Program Utama (Main Loop)

**Deskripsi:**
`main()` adalah entry point utama. Berdasarkan mode (CLI/Telegram), melakukan alur yang sesuai. CLI mode hanya melakukan pengukuran satu kali dan menampilkan output ke terminal. Telegram mode memulai polling untuk menerima command.

**Kode Implementasi:**

```python
def main():
    args = parse_args()
    
    try:
        app_config = load_config()
    except ValueError as exc:
        system_logger.error("%s", exc)
        return 1
    
    if args.mode == "cli":
        return run_cli(app_config, args)
    if args.mode == "telegram":
        return run_telegram(app_config)
    
    system_logger.error("Mode operasi tidak dikenal: %s", args.mode)
    return 1
```

**Penjelasan:**
- `parse_args()` memuat command line arguments.
- `load_config()` membaca konfigurasi dari `.env`.
- Mode CLI: `run_cli()` → pengukuran satu kali → output ke terminal.
- Mode Telegram: `run_telegram()` → starts polling → menerima command.
- Error handling untuk mode tidak dikenal.

---

### 9. Konfigurasi Awal Telegram Bot

**Deskripsi:**
Telegram Bot diinisialisasi dengan token dan chat ID dari `.env`. Handler command `start`, `status`, dan `measure` ditambahkan ke bot. Polling dimulai untuk menerima update dari Telegram.

**Kode Implementasi:**

```python
class TelegramBot:
    def __init__(self, app_config, gps_reader=None):
        self.config = app_config
        self.gps_reader = gps_reader
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📡 DVB-T2 Coverage Analyzer Portable\n"
            "Perintah tersedia:\n"
            "/status - status sistem\n"
            "/measure - pengukuran RF dan status GPS"
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        system_status = {
            "rtl_sdr": "OK" if RtlSdr is not None else "Error",
            "mode": "Telegram Polling",
        }
        await update.message.reply_text(format_status_dashboard(system_status, gps_result, self.config))
    
    async def measure(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        freq_mhz = self.config.default_freq_mhz
        if context.args:
            try:
                freq_mhz = float(context.args[0])
            except ValueError:
                await update.message.reply_text("Format frekuensi tidak valid. Contoh: /measure 514")
                return
        sdr_config = Dvbt2SdrConfig(calibration_offset_db=self.config.calibration_offset_db)
        result = run_single_measurement(freq_mhz=freq_mhz, repeat=5, config=sdr_config)
        await update.message.reply_text(format_measurement_dashboard(result, gps_result, self.config))
```

**Penjelasan:**
- `TelegramBot` adalah class utama untuk Telegram Bot.
- `app_config` berisi token dan konfigurasi.
- `gps_reader` untuk membaca koordinat GPS saat pengukuran.
- `/start`: menampilkan welcome message dan daftar perintah.
- `/status`: menampilkan status sistem (RTL-SDR OK/Error).
- `/measure`: melakukan pengukuran RF + GPS → kirim dashboard ke user.
- `run_polling()` untuk polling updates dari Telegram.

---

## RINGKKASAN IMPLEMENTASI

Sistem DVB-T2 Coverage Analyzer terdiri dari 9 modul utama:
1. **CLI Entry** → main.py → parse_args, load_config, run_cli/telegram
2. **GPS Reader** → gps_reader.py → NMEA parsing, CSV logging
3. **RTL-SDR Core** → dvbt2_core.py → FFT, PSD, bandpower, field strength
4. **Telegram Bot** → telegram_bot.py → command handlers, polling
5. **Logging** → logger.py → system.log + GPS CSV
6. **Config** → config.py → load .env, AppConfig

**Alur Data:**
```text
CLI/Telegram Command
    │
    ▼
load_config() → AppConfig
    │
    ▼
GPS Reader (GPS-enabled) → GPS coordinates
    │
    ▼
RTL-SDR (freq_mhz) → IQ samples
    │
    ▼
FFT (2048) → Welch Averaging → PSD
    │
    ▼
Bandpower (±1.8 MHz) → Field Strength (dBµV/m)
    │
    ▼
Classify → Telegram Dashboard
    │
    ▼
GPS log CSV (GPS.log)
```
