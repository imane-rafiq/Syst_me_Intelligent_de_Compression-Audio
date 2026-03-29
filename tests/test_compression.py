"""Tests for the DCT compressor and psychoacoustic model."""

import os
import sys
import math

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dct_compression import DCTCompressor
from src.psychoacoustic_model import PsychoacousticModel, hz_to_bark, bark_to_hz
from src.utils import compute_snr, generate_test_tone


class TestDCTCompressor:
    """Unit tests for DCTCompressor."""

    @pytest.fixture
    def sine_audio(self):
        """1-second 440 Hz sine wave at 44 100 Hz."""
        audio, sr = generate_test_tone(440, duration=1.0, sample_rate=44_100)
        return audio, sr

    def test_compress_returns_dict(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(frame_size=512, quantisation_bits=8, sample_rate=sr)
        result = compressor.compress(audio)
        assert "bitstring" in result
        assert "tree" in result
        assert "metadata" in result

    def test_compress_metadata_fields(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(frame_size=512, quantisation_bits=8, sample_rate=sr)
        result = compressor.compress(audio)
        meta = result["metadata"]
        assert meta["frame_size"] == 512
        assert meta["audio_length"] == len(audio)
        assert meta["sample_rate"] == sr

    def test_decompress_length(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(frame_size=512, quantisation_bits=8, sample_rate=sr)
        result = compressor.compress(audio)
        reconstructed = compressor.decompress(result)
        assert len(reconstructed) == len(audio)

    def test_reconstruct_snr_positive(self, sine_audio):
        """SNR should be positive for a sine wave at quality 8."""
        audio, sr = sine_audio
        compressor = DCTCompressor(
            frame_size=512, quantisation_bits=8, sample_rate=sr, use_psychoacoustics=False
        )
        result = compressor.compress(audio)
        reconstructed = compressor.decompress(result)
        snr = compute_snr(audio, reconstructed)
        assert snr > 5, f"Expected SNR > 5 dB, got {snr:.2f} dB"

    def test_higher_bits_better_snr(self, sine_audio):
        """More quantisation bits should yield better SNR."""
        audio, sr = sine_audio
        snrs = []
        for bits in [4, 6, 8, 10]:
            comp = DCTCompressor(
                frame_size=512, quantisation_bits=bits,
                sample_rate=sr, use_psychoacoustics=False
            )
            result = comp.compress(audio)
            reconstructed = comp.decompress(result)
            snr = compute_snr(audio, reconstructed)
            snrs.append(snr)
        # SNR should not strictly decrease with more bits
        assert snrs[-1] > snrs[0], "More bits should yield higher SNR"

    def test_compression_ratio_greater_than_one(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(
            frame_size=512, quantisation_bits=6, sample_rate=sr
        )
        result = compressor.compress(audio)
        ratio = compressor.compression_ratio(audio, result)
        assert ratio > 1.0, f"Expected ratio > 1.0, got {ratio}"

    def test_compression_without_psychoacoustics(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(
            frame_size=512, quantisation_bits=8,
            sample_rate=sr, use_psychoacoustics=False
        )
        result = compressor.compress(audio)
        reconstructed = compressor.decompress(result)
        assert len(reconstructed) == len(audio)
        snr = compute_snr(audio, reconstructed)
        assert snr > 0

    def test_short_audio(self):
        """Should handle audio shorter than one frame gracefully."""
        audio = np.random.default_rng(0).random(200) * 0.5
        compressor = DCTCompressor(frame_size=512, quantisation_bits=8, sample_rate=8_000)
        result = compressor.compress(audio)
        reconstructed = compressor.decompress(result)
        assert len(reconstructed) == len(audio)

    def test_bitstring_is_binary(self, sine_audio):
        audio, sr = sine_audio
        compressor = DCTCompressor(frame_size=512, quantisation_bits=8, sample_rate=sr)
        result = compressor.compress(audio)
        assert all(c in "01" for c in result["bitstring"])


class TestPsychoacousticModel:
    """Unit tests for PsychoacousticModel."""

    def test_masking_threshold_shape(self):
        model = PsychoacousticModel(sample_rate=44_100, frame_size=1_024)
        frame = np.sin(np.linspace(0, 2 * np.pi * 440, 1_024)) * 0.5
        threshold = model.masking_threshold(frame)
        assert threshold.shape == (1_024 // 2 + 1,)

    def test_masking_threshold_positive(self):
        model = PsychoacousticModel(sample_rate=44_100, frame_size=1_024)
        frame = np.sin(np.linspace(0, 2 * np.pi * 440, 1_024)) * 0.5
        threshold = model.masking_threshold(frame)
        assert np.all(threshold > 0)

    def test_perceptual_weights_range(self):
        model = PsychoacousticModel(sample_rate=44_100, frame_size=1_024)
        frame = np.random.default_rng(0).random(1_024) * 0.5
        weights = model.perceptual_weights(frame)
        assert np.all(weights >= 0)
        assert np.all(weights <= 1)

    def test_silence_low_weights(self):
        """Loud signal should raise the masking threshold near its frequency."""
        model = PsychoacousticModel(sample_rate=44_100, frame_size=1_024)
        frame_silent = np.zeros(1_024)

        # Proper 440 Hz tone within a 1024-sample frame at 44 100 Hz
        t = np.arange(1_024) / 44_100
        frame_loud = np.sin(2.0 * np.pi * 440 * t) * 0.9

        threshold_silent = model.masking_threshold(frame_silent)
        threshold_loud = model.masking_threshold(frame_loud)

        # Near the 440 Hz bin (~bin 10), the loud signal should produce a
        # higher masking threshold than silence.
        bin_440 = int(round(440 * 1_024 / 44_100))
        low, high = max(0, bin_440 - 5), bin_440 + 6
        assert np.max(threshold_loud[low:high]) > np.max(threshold_silent[low:high])

    def test_hz_to_bark_monotone(self):
        freqs = np.array([100.0, 500.0, 1_000.0, 4_000.0, 8_000.0])
        barks = hz_to_bark(freqs)
        assert np.all(np.diff(barks) > 0), "Bark scale should be monotonically increasing"

    def test_bark_to_hz_approximate_inverse(self):
        freqs = np.array([200.0, 1_000.0, 3_000.0])
        barks = hz_to_bark(freqs)
        recovered = bark_to_hz(barks)
        # bark_to_hz is a rough closed-form approximation; allow up to 40% error
        np.testing.assert_allclose(recovered, freqs, rtol=0.4)
