import argparse
import time
from dataclasses import dataclass

import numpy as np

try:
    from rtlsdr import RtlSdr
except ImportError:
    RtlSdr = None


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
        sdr.gain = config.gain_db
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
    """
    Hitung PSD relatif menggunakan FFT, window Hann, dan averaging Welch sederhana.

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


def calculate_bandpower(freqs_hz, psd_db, config=None):
    """
    Hitung bandpower relatif pada measurement bandwidth.

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


def estimate_field_strength(bandpower_relative_db, calibration_offset_db=0.0):
    """
    Estimasi field strength berbasis bandpower relatif dan offset kalibrasi.

    Nilai ini bukan field strength absolut tersertifikasi. Offset kalibrasi perlu
    diisi dari data pembanding alat ukur referensi.
    """
    return float(bandpower_relative_db + calibration_offset_db)


def classify_signal_quality(field_strength_dbuvm_est):
    """Klasifikasi kualitas sinyal berdasarkan estimasi dBuV/m."""
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


def _base_result(freq_mhz, config):
    return {
        "frequency_mhz": float(freq_mhz),
        "sample_rate_msps": float(config.sample_rate / 1e6),
        "measurement_bw_mhz": float(config.measurement_bw_hz / 1e6),
        "gain_db": float(config.gain_db),
        "calibration_offset_db": float(config.calibration_offset_db),
    }


def run_single_measurement(freq_mhz=514.0, repeat=5, config=None):
    """
    Jalankan pengukuran DVB-T2 pada satu frekuensi dan kembalikan dictionary hasil.

    Hasil power dan field strength adalah estimasi relatif, bukan nilai absolut
    tersertifikasi.
    """
    if config is None:
        config = Dvbt2SdrConfig()

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

        result.update(
            {
                "average_bandpower_db": average_bandpower_db,
                "min_bandpower_db": float(np.min(measurements)),
                "max_bandpower_db": float(np.max(measurements)),
                "std_deviation_db": float(np.std(measurements)),
                "power_db_est": average_bandpower_db,
                "field_strength_dbuvm_est": field_strength_est,
                "signal_quality": classify_signal_quality(field_strength_est),
                "raw_measurements": measurements.tolist(),
                "note": (
                    "Power dan field strength adalah estimasi relatif. "
                    "Gunakan calibration_offset_db dari alat pembanding untuk kalibrasi."
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
                "signal_quality": "Error",
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
    print(f"Gain                   : {result['gain_db']:.1f} dB")
    print(f"Calibration offset     : {result['calibration_offset_db']:.2f} dB")

    if result.get("error"):
        print("")
        print("ERROR:")
        print(result["error"])
        return

    print(f"Average bandpower      : {result['average_bandpower_db']:.2f} dB")
    print(f"Min bandpower          : {result['min_bandpower_db']:.2f} dB")
    print(f"Max bandpower          : {result['max_bandpower_db']:.2f} dB")
    print(f"Std deviation          : {result['std_deviation_db']:.2f} dB")
    print(f"Power estimate         : {result['power_db_est']:.2f} dB")
    print(f"Field strength est     : {result['field_strength_dbuvm_est']:.2f} dBuV/m")
    print(f"Signal quality         : {result['signal_quality']}")
    print(f"Raw measurements       : {result['raw_measurements']}")
    print("")
    print(result["note"])


def parse_args():
    parser = argparse.ArgumentParser(
        description="Core DVB-T2 coverage analyzer berbasis Orange Pi + RTL-SDR."
    )
    parser.add_argument("--freq", type=float, default=514.0, help="Frekuensi MHz.")
    parser.add_argument("--repeat", type=int, default=5, help="Jumlah pengulangan.")
    parser.add_argument(
        "--cal-offset",
        type=float,
        default=0.0,
        help="Offset kalibrasi dB untuk estimasi field strength.",
    )
    parser.add_argument(
        "--gain", type=float, default=19.7, help="Gain RTL-SDR dalam dB."
    )
    parser.add_argument(
        "--bw",
        type=float,
        default=1.8,
        help="Measurement bandwidth dalam MHz.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = Dvbt2SdrConfig(
        gain_db=args.gain,
        measurement_bw_hz=args.bw * 1e6,
        calibration_offset_db=args.cal_offset,
    )
    result = run_single_measurement(freq_mhz=args.freq, repeat=args.repeat, config=config)
    print_measurement_result(result)


if __name__ == "__main__":
    main()
