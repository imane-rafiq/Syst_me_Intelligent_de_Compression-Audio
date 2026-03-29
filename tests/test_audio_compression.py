"""Tests for the AudioCompressor high-level API."""

import os
import sys
import math

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audio_compression import AudioCompressor
from src.utils import generate_test_tone, compute_snr


class TestAudioCompressor:
    """Unit tests for the high-level AudioCompressor."""

    @pytest.fixture
    def audio_sr(self):
        audio, sr = generate_test_tone(440, duration=0.5, sample_rate=22_050)
        return audio, sr

    def test_repr(self):
        c = AudioCompressor(quality=8)
        assert "AudioCompressor" in repr(c)
        assert "quality=8" in repr(c)

    def test_invalid_quality(self):
        with pytest.raises(ValueError):
            AudioCompressor(quality=0)
        with pytest.raises(ValueError):
            AudioCompressor(quality=17)

    def test_compress_keys(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=6)
        result = c.compress(audio, sample_rate=sr)
        assert "bitstring" in result
        assert "tree" in result
        assert "metadata" in result
        assert "stats" in result

    def test_stats_fields(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=6)
        result = c.compress(audio, sample_rate=sr)
        stats = result["stats"]
        assert "compression_ratio" in stats
        assert "space_saving_percent" in stats
        assert "original_samples" in stats
        assert "encode_time_s" in stats

    def test_compress_decompress_length(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=8)
        result = c.compress(audio, sample_rate=sr)
        reconstructed = c.decompress(result)
        assert len(reconstructed) == len(audio)

    def test_snr_improves_with_quality(self):
        audio, sr = generate_test_tone(1_000, duration=0.5, sample_rate=22_050)
        snr_low = None
        snr_high = None
        for quality in [3, 12]:
            c = AudioCompressor(quality=quality, use_psychoacoustics=False)
            result = c.compress(audio, sample_rate=sr)
            reconstructed = c.decompress(result)
            snr = compute_snr(audio, reconstructed)
            if quality == 3:
                snr_low = snr
            else:
                snr_high = snr
        assert snr_high > snr_low, "Higher quality should yield better SNR"

    def test_compression_ratio_above_one(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=4)
        result = c.compress(audio, sample_rate=sr)
        ratio = result["stats"]["compression_ratio"]
        assert ratio > 1.0

    def test_evaluate_returns_metrics(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=8)
        result = c.compress(audio, sample_rate=sr)
        eval_result = c.evaluate(audio, result, sample_rate=sr)
        assert "snr_db" in eval_result
        assert "psnr_db" in eval_result
        assert "compression_ratio" in eval_result
        assert "reconstructed" in eval_result
        assert len(eval_result["reconstructed"]) == len(audio)

    def test_all_quality_levels_work(self):
        audio, sr = generate_test_tone(440, duration=0.2, sample_rate=8_000)
        for quality in range(1, 17):
            c = AudioCompressor(quality=quality, frame_size=256)
            result = c.compress(audio, sample_rate=sr)
            reconstructed = c.decompress(result)
            assert len(reconstructed) == len(audio), f"Failed at quality={quality}"

    def test_without_psychoacoustics(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=8, use_psychoacoustics=False)
        result = c.compress(audio, sample_rate=sr)
        reconstructed = c.decompress(result)
        assert len(reconstructed) == len(audio)

    def test_space_saving_positive(self, audio_sr):
        audio, sr = audio_sr
        c = AudioCompressor(quality=4)
        result = c.compress(audio, sample_rate=sr)
        saving = result["stats"]["space_saving_percent"]
        assert saving > 0
