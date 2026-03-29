"""
Psychoacoustic Model
=====================
Implements a simplified Bark-scale psychoacoustic masking model to
determine perceptual thresholds for each audio frame.

The model computes:
  1. The short-time power spectrum (FFT-based).
  2. A mapping onto the Bark frequency scale.
  3. Spreading of masking energy across Bark bands.
  4. A masking threshold per FFT bin.

These thresholds guide quantisation in the DCT compressor: coefficients
below the masking threshold are perceptually irrelevant and can be
quantised coarsely or discarded entirely without audible degradation.
"""

import numpy as np
from typing import Tuple


# ---------------------------------------------------------------------------
# Bark scale helpers
# ---------------------------------------------------------------------------

def hz_to_bark(freq_hz: np.ndarray) -> np.ndarray:
    """Convert frequency in Hz to Bark scale (Zwicker formula)."""
    return 13.0 * np.arctan(0.00076 * freq_hz) + 3.5 * np.arctan((freq_hz / 7500.0) ** 2)


def bark_to_hz(bark: np.ndarray) -> np.ndarray:
    """Approximate inverse of the Zwicker Bark formula (Newton iteration)."""
    # Closed-form approximation
    return 600.0 * np.sinh(bark / 6.0)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class PsychoacousticModel:
    """
    Simplified psychoacoustic masking model.

    Parameters
    ----------
    sample_rate : int
        Audio sample rate in Hz (default 44 100).
    frame_size : int
        FFT frame size in samples (default 1 024).
    """

    # Absolute threshold of hearing (in dB SPL) — ISO 226 approximation
    _ATH_COEFFS = (3.64, -0.8, -6.5, 0.001, 0.0)

    def __init__(self, sample_rate: int = 44_100, frame_size: int = 1_024) -> None:
        self.sample_rate = sample_rate
        self.frame_size = frame_size

        # Frequency of each FFT bin (positive half)
        n_bins = frame_size // 2 + 1
        self.freqs = np.linspace(0, sample_rate / 2, n_bins)
        self.barks = hz_to_bark(np.maximum(self.freqs, 1e-3))

        # Precompute absolute threshold of hearing (ATH) per bin
        self.ath = self._absolute_threshold(self.freqs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def masking_threshold(self, frame: np.ndarray) -> np.ndarray:
        """
        Compute the masking threshold for a single audio *frame*.

        Parameters
        ----------
        frame : ndarray, shape (frame_size,)
            Time-domain audio samples (float, arbitrary amplitude).

        Returns
        -------
        threshold : ndarray, shape (frame_size // 2 + 1,)
            Masking threshold in linear amplitude units (same scale as
            the FFT magnitude spectrum of *frame*).
        """
        # Power spectrum
        spectrum = np.fft.rfft(frame * np.hanning(len(frame)))
        power = np.abs(spectrum) ** 2 + 1e-30  # avoid log(0)

        # Spreading function on Bark scale
        spread_power = self._spreading(power)

        # Masking threshold = spread power * masking offset − ATH
        # We use a simple factor: threshold is 14 dB below masker
        mask_db = 10.0 * np.log10(spread_power) - 14.0
        threshold_db = np.maximum(mask_db, self.ath)

        # Convert back to linear amplitude
        threshold = 10.0 ** (threshold_db / 20.0)
        return threshold

    def perceptual_weights(self, frame: np.ndarray) -> np.ndarray:
        """
        Return per-bin perceptual weight factors in [0, 1].

        A weight close to 0 means the coefficient is near or below the
        masking threshold and can be quantised very coarsely.
        A weight close to 1 means the coefficient is clearly audible.

        Parameters
        ----------
        frame : ndarray, shape (frame_size,)

        Returns
        -------
        weights : ndarray, shape (frame_size // 2 + 1,)
        """
        spectrum = np.fft.rfft(frame * np.hanning(len(frame)))
        magnitude = np.abs(spectrum)
        threshold = self.masking_threshold(frame)

        # Signal-to-mask ratio (linear)
        smr = magnitude / (threshold + 1e-30)
        # Sigmoid-shaped mapping: weights ∈ (0, 1)
        weights = smr / (smr + 1.0)
        return weights

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _spreading(self, power: np.ndarray) -> np.ndarray:
        """Apply a simplified spreading function on the Bark scale."""
        barks = self.barks
        spread = np.zeros_like(power)
        for i, (p, b_i) in enumerate(zip(power, barks)):
            # Spreading function: lower slope 27 dB/Bark, upper 6 dB/Bark
            delta_bark = barks - b_i
            sf = np.where(
                delta_bark >= 0,
                10.0 ** (-6.0 * delta_bark / 10.0),   # upper slope
                10.0 ** (-27.0 * np.abs(delta_bark) / 10.0),  # lower slope
            )
            spread += p * sf
        return spread

    @staticmethod
    def _absolute_threshold(freqs: np.ndarray) -> np.ndarray:
        """
        Approximate absolute threshold of hearing (ATH) in dB SPL.

        Formula from Painter & Spanias (2000), valid for f > 0.
        """
        f = np.maximum(freqs / 1000.0, 0.1)  # kHz, avoid div-by-zero
        ath = (
            3.64 * f ** -0.8
            - 6.5 * np.exp(-0.6 * (f - 3.3) ** 2)
            + 1e-3 * f ** 4
        )
        return ath
