import argparse
import time
from dataclasses import dataclass

import numpy as np

try:
    from rtlsdr import RtlSdr
except ImportError:
    RtlSdr = None

import logging
logger = logging.getLogger("CapstoneDvbT2")


@dataclass
class Dvbt2SdrConfig:
    """Konfigurasi utama pengukuran DVB-T2 berbasis RTL-SDR."""

    sample_rate: float = 2.048e6
    num_samples: int = 256 * 1024
    fft_size: int = 2048
    measurement_bw_hz: float = 1.8e6
    dc_exclude_hz: float = 20e3
    gain_db: float = 19.7
    calibration_offset_db: float = 0.0
    warmup_reads: int = 2
    settle_time_s: float = 1.0
    repeat_delay_s: float = 0.5
    calibration_mode: str = "raw"
    cable_loss_db: float = 0.0
    antenna_factor_db_per_m: float | None = None
    komdigi_lower_dbuvm: float = 39.5
    komdigi_upper_dbuvm: float = 76.2
    rx_antenna_height_m: float | None = None


_SUPPORTED_GAINS_CACHE = {}


def list_sdr_available_gains():
    """Return available gain values for the first RTL-SDR device, or None."""
    if RtlSdr is None:
        return None
    try:
        sdr = RtlSdr()
        gains = sdr.valid_gains_db
        sdr.close()
        return sorted(gains)
    except Exception as exc:
        logger.warning("Tidak bisa membaca available gains: %s", exc)
        return None


def pick_nearest_gain(requested_gain, available_gains):
    """Pilih gain terdekat yang didukung device.\n\n    Jika requested_gain ada di daftar, pakai itu.\n    Jika tidak, pilih gain terdekat (tidak melebihi requested_gain).\n    """
    if not available_gains:
        return requested_gain
    if requested_gain in available_gains:
        return requested_gain
    lower = [g for g in available_gains if g <= requested_gain]
    if lower:
        return max(lower)
    return min(available_gains)


def initialize_sdr(freq_mhz, config=None):
    """Inisialisasi RTL-SDR untuk frekuensi center tertentu."""
    if config is None:
        config = Dvbt2SdrConfig()

    if RtlSdr is None:
        raise RuntimeError(
            "Library pyrtlsdr tidak ditemukan. Install/aktifkan pyrtlsdr terlebih dahulu."
        )

    try:
        sdr = RtlSdr()
        sdr.sample_rate = config.sample_rate
        sdr.center_freq = float(freq_mhz) * 1e6

        # Set fixed gain, pilih gain terdekat yang didukung device
        gains = sdr.valid_gains_db
        actual_gain = pick_nearest_gain(config.gain_db, sorted(gains))
        logger.info(
            "Requested gain: %.1f dB, selected: %.1f dB, available: %s",
            config.gain_db, actual_gain, gains,
        )
        sdr.gain = actual_gain

        time.sleep(config.settle_time_s)
        return sdr
    except Exception as exc:
        raise RuntimeError(
            "RTL-SDR tidak dapat diinisialisasi. "
            "Pastikan dongle terpasang, tidak dipakai proses lain, dan driver sudah benar. "
            f"Detail: {exc}"
        ) from exc


def capture_iq_samples(sdr, config=None):
    """Ambil IQ sample kompleks dari RTL-SDR."""
    if config is None:
        config = Dvbt2SdrConfig()
    return sdr.read_samples(config.num_samples)


def compute_psd(samples, config=None):
    """Hitung PSD relatif menggunakan FFT, window Hann, dan averaging Welch sederhana.

    Output PSD masih relatif terhadap skala RTL-SDR, bukan dBm absolut.
    """
    if config is None:
        config = Dvbt2SdrConfig()

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
        segment = samples[start: start + config.fft_size]
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


def calculate_bandpower(freqs_hz, psd_db, config=None):
    """Hitung bandpower relatif pada measurement bandwidth.

    Area sekitar DC/center frequency dibuang untuk mengurangi efek DC spike RTL-SDR.
    """
    if config is None:
        config = Dvbt2SdrConfig()

    freqs_hz = np.asarray(freqs_hz)
    psd_db = np.asarray(psd_db)

    half_bw = config.measurement_bw_hz / 2.0
    band_mask = (freqs_hz >= -half_bw) & (freqs_hz <= half_bw)
    dc_mask = np.abs(freqs_hz) <= config.dc_exclude_hz
    final_mask = band_mask & (~dc_mask)

    if not np.any(final_mask):
        raise ValueError("Tidak ada bin FFT valid untuk measurement bandwidth.")

    power_linear = np.sum(10.0 ** (psd_db[final_mask] / 10.0))
    bandpower_db = 10.0 * np.log10(power_linear + 1e-12)

    return float(bandpower_db)


def calculate_total_correction_db(
    calibration_offset_db=0.0,
    cable_loss_db=0.0,
    antenna_factor_db_per_m=None,
):
    """Hitung total koreksi transparan.

    Rumus:
      total_correction_db = calibration_offset_db + cable_loss_db + antenna_factor_db_per_m (jika ada)

    Jika antenna_factor_db_per_m belum diketahui (None), lewati.
    """
    total = calibration_offset_db + cable_loss_db
    if antenna_factor_db_per_m is not None:
        total += antenna_factor_db_per_m
    return total


def estimate_field_strength(bandpower_relative_db, total_correction_db=0.0):
    """Estimasi field strength berbasis bandpower relatif dan total koreksi transparan.

    field_strength_est_dbuvm = raw_bandpower_db + total_correction_db

    Nilai ini bukan field strength absolut tersertifikasi. Total koreksi perlu diisi
    dari data kalibrasi/antenna factor/cable loss atau offset model RadioPlanner.
    """
    return float(bandpower_relative_db + total_correction_db)


def classify_signal_quality(field_strength_dbuvm_est):
    """Klasifikasi kualitas sinyal berdasarkan estimasi dBuV/m.

    Threshold ini adalah nilai kerja sementara.
    Untuk kategori Komdigi resmi, gunakan classify_komdigi_reference().
    """
    value = float(field_strength_dbuvm_est)
    if value > 65.0:
        return "Sangat Baik"
    if 55.0 <= value <= 65.0:
        return "Baik"
    if 48.0 <= value < 55.0:
        return "Cukup"
    if 35.0 <= value < 48.0:
        return "Lemah"
    return "Sangat Lemah"


def classify_komdigi_reference(field_strength_est_dbuvm, lower_dbuvm=39.5, upper_dbuvm=76.2):
    """Klasifikasi berdasarkan acuan Komdigi DVB-T2.

    Kategori ini bukan lulus/gagal alat. Alat berhasil jika mampu membaca
    dan mengklasifikasikan nilai.

    - field_strength_est_dbuvm < lower_dbuvm → DI_BAWAH_ACUAN
    - lower_dbuvm <= field_strength_est_dbuvm <= upper_dbuvm → DALAM_RENTANG_ACUAN
    - field_strength_est_dbuvm > upper_dbuvm → DI_ATAS_ACUAN
    """
    if field_strength_est_dbuvm is None:
        return "TIDAK_TERUKUR"
    if field_strength_est_dbuvm < lower_dbuvm:
        return "DI_BAWAH_ACUAN"
    if field_strength_est_dbuvm <= upper_dbuvm:
        return "DALAM_RENTANG_ACUAN"
    return "DI_ATAS_ACUAN"


def get_calibration_disclaimer(calibration_mode):
    """Return disclaimer sesuai mode kalibrasi."""
    if calibration_mode == "reference_instrument_calibrated":
        return "hasil dikalibrasi dengan alat referensi"
    return "estimasi SDR, bukan kalibrasi absolut"


def _base_result(freq_mhz, config, actual_gain_db=None):
    return {
        "frequency_mhz": float(freq_mhz),
        "sample_rate_msps": float(config.sample_rate / 1e6),
        "measurement_bw_mhz": float(config.measurement_bw_hz / 1e6),
        "gain_db": float(config.gain_db),
        "actual_gain_db": float(actual_gain_db) if actual_gain_db is not None else float(config.gain_db),
        "calibration_offset_db": float(config.calibration_offset_db),
        "calibration_mode": config.calibration_mode,
        "measurement_mode": "center_bandpower_1p8mhz",
    }


def run_single_measurement(freq_mhz=514.0, repeat=5, config=None, app_config=None):
    """Jalankan pengukuran DVB-T2 pada satu frekuensi dan kembalikan dictionary hasil.

    Hasil power dan field strength adalah estimasi relatif, bukan nilai absolut
    tersertifikasi.
    """
    if config is None:
        config = Dvbt2SdrConfig()

    result = _base_result(freq_mhz, config)
    sdr = None

    try:
        sdr = initialize_sdr(freq_mhz, config)

        # Catat actual gain setelah SDR diinisialisasi
        actual_gain = getattr(sdr, "gain", config.gain_db)
        result["actual_gain_db"] = float(actual_gain)

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

        # Hitung total correction dan field strength secara transparan
        total_correction_db = calculate_total_correction_db(
            calibration_offset_db=config.calibration_offset_db,
            cable_loss_db=config.cable_loss_db,
            antenna_factor_db_per_m=config.antenna_factor_db_per_m,
        )
        field_strength_est = estimate_field_strength(average_bandpower_db, total_correction_db)
        komdigi_category = classify_komdigi_reference(
            field_strength_est,
            lower_dbuvm=config.komdigi_lower_dbuvm,
            upper_dbuvm=config.komdigi_upper_dbuvm,
        )

        result.update(
            {
                "average_bandpower_db": average_bandpower_db,
                "min_bandpower_db": float(np.min(measurements)),
                "max_bandpower_db": float(np.max(measurements)),
                "std_deviation_db": float(np.std(measurements)),
                "power_db_est": average_bandpower_db,
                "field_strength_dbuvm_est": field_strength_est,
                "total_correction_db": total_correction_db,
                "signal_quality": classify_signal_quality(field_strength_est),
                "komdigi_category": komdigi_category,
                "cable_loss_db": config.cable_loss_db,
                "antenna_factor_db_per_m": config.antenna_factor_db_per_m,
                "rx_antenna_height_m": getattr(config, "rx_antenna_height_m", None),
                "raw_measurements": measurements.tolist(),
                "note": (
                    f"Power dan field strength adalah estimasi relatif. "
                    f"Kalibrasi mode: {config.calibration_mode}. "
                    f"Total correction: {total_correction_db:.2f} dB. "
                    f"{get_calibration_disclaimer(config.calibration_mode)}."
                ),
            }
        )
        return result
    except Exception as exc:
        result.update(
            {
                "average_bandpower_db": None,
                "min_bandpower_db": None,
                "max_bandpower_db": None,
                "std_deviation_db": None,
                "power_db_est": None,
                "field_strength_dbuvm_est": None,
                "total_correction_db": None,
                "signal_quality": "Error",
                "komdigi_category": "TIDAK_TERUKUR",
                "raw_measurements": [],
                "error": str(exc),
            }
        )
        return result
    finally:
        if sdr is not None:
            try:
                sdr.close()
            except Exception:
                pass


def print_measurement_result(result):
    """Cetak hasil pengukuran ke terminal dengan format sederhana."""
    print("=== DVB-T2 CORE MEASUREMENT ===")
    print(f"Frequency              : {result['frequency_mhz']:.3f} MHz")
    print(f"Sample rate            : {result['sample_rate_msps']:.3f} MS/s")
    print(f"Measurement bandwidth  : {result['measurement_bw_mhz']:.3f} MHz")
    print(f"Gain (requested)       : {result['gain_db']:.1f} dB")
    print(f"Gain (actual)          : {result['actual_gain_db']:.1f} dB")
    print(f"Calibration offset     : {result['calibration_offset_db']:.2f} dB")
    print(f"Calibration mode       : {result['calibration_mode']}")
    print(f"Measurement mode       : {result['measurement_mode']}")

    if result.get("error"):
        print("")
        print("ERROR:")
        print(result["error"])
        return

    print(f"Average bandpower      : {result['average_bandpower_db']:.2f} dB")
    print(f"Min bandpower          : {result['min_bandpower_db']:.2f} dB")
    print(f"Max bandpower          : {result['max_bandpower_db']:.2f} dB")
    print(f"Std deviation          : {result['std_deviation_db']:.2f} dB")
    print(f"Total correction       : {result.get('total_correction_db', 0):.2f} dB")
    print(f"Power estimate         : {result['power_db_est']:.2f} dB")
    print(f"Cable loss             : {result.get('cable_loss_db', 0):.2f} dB")
    print(f"Antenna factor         : {result.get('antenna_factor_db_per_m', 'not set')}")
    print(f"Rx antenna height      : {result.get('rx_antenna_height_m', 'not set')} m")
    print(f"Field strength est     : {result['field_strength_dbuvm_est']:.2f} dBuV/m")
    print(f"Signal quality         : {result['signal_quality']}")
    print(f"Komdigi category       : {result.get('komdigi_category', 'N/A')}")
    print(f"Komdigi lower          : {getattr(result, 'komdigi_lower_dbuvm', 39.5):.1f} dBuV/m")
    print(f"Komdigi upper          : {getattr(result, 'komdigi_upper_dbuvm', 76.2):.1f} dBuV/m")
    print(f"Raw measurements       : {result['raw_measurements']}")
    print("")
    print(result["note"])


def parse_args():
    parser = argparse.ArgumentParser(description="DVB-T2 Coverage Analyzer Portable")
    parser.add_argument(
        "--list-gains", action="store_true",
        help="Tampilkan daftar gain yang didukung RTL-SDR dan keluar.",
    )
    parser.add_argument(
        "--available-gains", action="store_true",
        dest="list_gains",
        help="Alias untuk --list-gains.",
    )
    return parser.parse_args()
