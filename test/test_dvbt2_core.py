import sys
import unittest
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dvbt2_core import (  # noqa: E402
    Dvbt2SdrConfig,
    calculate_bandpower,
    classify_signal_quality,
    compute_psd,
    estimate_field_strength,
)


class Dvbt2CoreTest(unittest.TestCase):
    def test_compute_psd_and_bandpower_return_numeric_values(self):
        config = Dvbt2SdrConfig(fft_size=2048, num_samples=4096)
        rng = np.random.default_rng(42)
        samples = rng.normal(size=4096) + 1j * rng.normal(size=4096)

        freqs_hz, psd_db = compute_psd(samples, config)
        bandpower_db = calculate_bandpower(freqs_hz, psd_db, config)

        self.assertEqual(len(freqs_hz), config.fft_size)
        self.assertEqual(len(psd_db), config.fft_size)
        self.assertTrue(np.isfinite(bandpower_db))

    def test_field_strength_is_relative_offset_sum(self):
        self.assertEqual(estimate_field_strength(42.5, 3.0), 45.5)

    def test_signal_quality_thresholds(self):
        self.assertEqual(classify_signal_quality(66), "Sangat Baik")
        self.assertEqual(classify_signal_quality(60), "Baik")
        self.assertEqual(classify_signal_quality(50), "Cukup")
        self.assertEqual(classify_signal_quality(40), "Lemah")
        self.assertEqual(classify_signal_quality(30), "Sangat Lemah")


if __name__ == "__main__":
    unittest.main()
