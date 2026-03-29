"""Tests for utility functions."""

import math
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import (
    compute_snr,
    compute_psnr,
    compute_compression_ratio,
    compute_space_saving,
    generate_test_tone,
    generate_chirp,
    load_audio,
    save_audio,
)


class TestMetrics:
    """Unit tests for quality metrics."""

    def test_snr_perfect_reconstruction(self):
        """SNR should be infinite when original == reconstructed."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000))
        snr = compute_snr(audio, audio.copy())
        assert math.isinf(snr) or snr > 100

    def test_snr_decreases_with_noise(self):
        rng = np.random.default_rng(0)
        audio = np.sin(np.linspace(0, 4 * np.pi, 4000))
        noisy_light = audio + rng.normal(0, 0.01, len(audio))
        noisy_heavy = audio + rng.normal(0, 0.5, len(audio))
        snr_light = compute_snr(audio, noisy_light)
        snr_heavy = compute_snr(audio, noisy_heavy)
        assert snr_light > snr_heavy

    def test_snr_positive_for_correlated_signal(self):
        audio = np.sin(np.linspace(0, 4 * np.pi, 4000)) * 0.5
        noisy = audio + np.random.default_rng(1).normal(0, 0.05, len(audio))
        assert compute_snr(audio, noisy) > 0

    def test_psnr_perfect(self):
        audio = np.ones(100) * 0.5
        psnr = compute_psnr(audio, audio.copy())
        assert math.isinf(psnr) or psnr > 100

    def test_psnr_positive(self):
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000)) * 0.5
        noisy = audio + np.random.default_rng(2).normal(0, 0.01, len(audio))
        assert compute_psnr(audio, noisy) > 0

    def test_compression_ratio_greater_than_one(self):
        audio = np.zeros(10_000)
        # 10 000 * 16 = 160 000 original bits; bitstring shorter
        short_bitstring = "0" * 1_000
        ratio = compute_compression_ratio(audio, short_bitstring)
        assert ratio > 1.0

    def test_compression_ratio_formula(self):
        audio = np.zeros(100)
        bitstring = "0" * 800  # same as 100 * 8 bits
        ratio = compute_compression_ratio(audio, bitstring, bits_per_sample=8)
        assert abs(ratio - 1.0) < 1e-9

    def test_space_saving_zero(self):
        """If compressed == original size, saving is 0%."""
        audio = np.zeros(100)
        bitstring = "0" * (100 * 16)
        saving = compute_space_saving(audio, bitstring)
        assert abs(saving) < 1e-6

    def test_space_saving_positive(self):
        audio = np.zeros(1_000)
        bitstring = "0" * (500 * 16)
        saving = compute_space_saving(audio, bitstring)
        assert abs(saving - 50.0) < 1e-6

    def test_different_length_tolerance(self):
        """compute_snr/psnr should use the shorter length."""
        a = np.sin(np.linspace(0, np.pi, 100))
        b = np.sin(np.linspace(0, np.pi, 110))
        snr = compute_snr(a, b)
        assert np.isfinite(snr)


class TestSignalGenerators:
    """Unit tests for synthetic signal generators."""

    def test_tone_length(self):
        audio, sr = generate_test_tone(frequency=440, duration=1.0, sample_rate=44_100)
        assert len(audio) == 44_100
        assert sr == 44_100

    def test_tone_amplitude(self):
        audio, _ = generate_test_tone(amplitude=0.5)
        assert np.max(np.abs(audio)) <= 0.5 + 1e-9

    def test_tone_frequency(self):
        """Frequency of the tone should match via zero-crossing count."""
        sr = 44_100
        freq = 1_000
        audio, _ = generate_test_tone(frequency=freq, duration=1.0, sample_rate=sr)
        # Count zero crossings (should be approximately 2 * freq per second)
        crossings = np.where(np.diff(np.sign(audio)))[0]
        estimated_freq = len(crossings) / 2.0
        assert abs(estimated_freq - freq) < 5  # within 5 Hz

    def test_chirp_length(self):
        audio, sr = generate_chirp(duration=2.0, sample_rate=44_100)
        assert len(audio) == 2 * 44_100

    def test_chirp_amplitude(self):
        audio, _ = generate_chirp(amplitude=0.3)
        assert np.max(np.abs(audio)) <= 0.3 + 1e-9


class TestAudioIO:
    """Unit tests for load_audio / save_audio roundtrip."""

    def test_roundtrip_wav(self):
        """Save and load back a WAV file; samples should match closely."""
        original, sr = generate_test_tone(frequency=440, duration=0.5, sample_rate=44_100)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            save_audio(path, original, sample_rate=sr)
            loaded, loaded_sr = load_audio(path)
            assert loaded_sr == sr
            assert len(loaded) == len(original)
            # 16-bit quantisation error is < 1/32768
            np.testing.assert_allclose(original, loaded, atol=1.0 / 32768 + 1e-6)
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_audio("/tmp/nonexistent_audio_file.wav")

    def test_save_clipping(self):
        """Samples outside [-1, 1] should be clipped."""
        audio = np.array([0.5, 1.5, -2.0, 0.0])
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            save_audio(path, audio, sample_rate=44_100)
            loaded, _ = load_audio(path)
            assert np.all(np.abs(loaded) <= 1.0 + 1e-6)
        finally:
            os.unlink(path)
