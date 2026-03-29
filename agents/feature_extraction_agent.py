"""
AGENT 2: FEATURE EXTRACTION AGENT
=================================

Responsibility:
- Load audio with librosa
- Extract spectral features (centroid, entropy, bandwidth)
- Extract temporal features (zero crossing rate, energy)
- Detect content type (voice, music, ambient, mixed)

Simple methods:
1. extract() - Main entry point
2. compute_spectral_features() - FFT analysis
3. compute_temporal_features() - Time domain analysis
4. detect_content_type() - Classify audio content
"""

from pathlib import Path
from typing import Dict, Optional

import librosa
import librosa.feature
import numpy as np


class FeatureExtractionAgent:
    """Extract audio features for analysis."""

    def __init__(self):
        self.logger = SimpleLogger("FeatureExtractionAgent")
        self.target_sr = 44100

    def extract(self, filepath: str) -> Optional[Dict]:
        """
        Extract all features from audio file.

        Args:
            filepath: Path to audio file

        Returns:
            Dict with features or None if failed
        """
        try:
            y, sr = librosa.load(filepath, sr=self.target_sr, mono=True)

            if len(y) == 0:
                self.logger.error("Empty audio file")
                return None

            self.logger.info(f"Loaded: {Path(filepath).name} ({len(y) / sr:.1f}s)")

            spectral = self.compute_spectral_features(y, sr)
            temporal = self.compute_temporal_features(y, sr)
            content_type = self.detect_content_type(y, sr, spectral, temporal)

            features = {
                "filepath": filepath,
                **spectral,
                **temporal,
                "content_type": content_type,
            }

            self.logger.success(f"Extracted features: {content_type}")
            return features

        except Exception as e:
            self.logger.error(f"Feature extraction failed: {str(e)}")
            return None

    def compute_spectral_features(self, y: np.ndarray, sr: int) -> Dict:
        """
        Compute spectral (frequency domain) features.

        Returns:
            Dict with centroid, entropy, spectral_bandwidth
        """
        mel = librosa.feature.melspectrogram(y=y, sr=sr)
        mel_db = librosa.power_to_db(mel, ref=np.max)

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

        mel_min = mel_db.min()
        mel_max = mel_db.max()
        if mel_max - mel_min < 1e-12:
            entropy = 0.0
        else:
            mel_norm = (mel_db - mel_min) / (mel_max - mel_min)
            entropy = float(-np.sum(mel_norm * np.log2(mel_norm + 1e-10)) / mel_norm.size)

        return {
            "centroid": round(float(np.mean(centroid)), 2),
            "entropy": round(entropy, 2),
            "spectral_bandwidth": round(float(np.mean(bandwidth)), 2),
        }

    def compute_temporal_features(self, y: np.ndarray, sr: int) -> Dict:
        """
        Compute temporal (time domain) features.

        Returns:
            Dict with zero_crossing_rate, rms_energy, peak_amplitude
        """
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        rms = librosa.feature.rms(y=y)[0]
        peak = float(np.max(np.abs(y)))

        return {
            "zero_crossing_rate": round(float(np.mean(zcr)), 4),
            "rms_energy": round(float(np.mean(rms)), 4),
            "peak_amplitude": round(peak, 4),
        }

    def detect_content_type(
        self,
        y: np.ndarray,
        sr: int,
        spectral: Dict,
        temporal: Dict,
    ) -> str:
        """
        Detect whether audio is voice, music, ambient, or mixed.
        """
        zcr = temporal["zero_crossing_rate"]
        centroid = spectral["centroid"]
        entropy = spectral["entropy"]
        bandwidth = spectral["spectral_bandwidth"]
        rms = temporal["rms_energy"]

        # Very weak / sparse content
        if rms < 0.01 and entropy < 3.0:
            return "ambient"

        # Likely speech / podcast / audiobook
        if zcr > 0.08 and 1200 <= centroid <= 3500 and bandwidth < 2500:
            return "voice"

        # Likely music
        if entropy > 4.2 and bandwidth > 1800 and rms >= 0.01:
            return "music"

        # Uncertain / hybrid content
        if (zcr > 0.06 and entropy > 4.0) or (centroid > 1800 and bandwidth > 2200):
            return "mixed"

        return "ambient"


class SimpleLogger:
    """Simple logger for agents."""

    def __init__(self, name: str):
        self.name = name

    def info(self, msg: str):
        print(f"INFO [{self.name}] {msg}")

    def success(self, msg: str):
        print(f"SUCCESS [{self.name}] {msg}")

    def error(self, msg: str):
        print(f"ERROR [{self.name}] {msg}")

    def warning(self, msg: str):
        print(f"WARNING [{self.name}] {msg}")