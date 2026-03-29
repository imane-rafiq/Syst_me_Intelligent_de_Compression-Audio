"""
Audio Compression — Main Pipeline
===================================
High-level ``AudioCompressor`` class that orchestrates the full
compression / decompression workflow and exposes a simple API.

Usage
-----
>>> from src import AudioCompressor
>>> compressor = AudioCompressor(quality=8)
>>> result = compressor.compress(audio_samples, sample_rate=44_100)
>>> recovered = compressor.decompress(result)
"""

import time
from typing import Dict, Optional

import numpy as np

from .dct_compression import DCTCompressor
from .utils import compute_snr, compute_psnr, compute_compression_ratio, compute_space_saving


class AudioCompressor:
    """
    Intelligent audio compressor.

    Combines block-DCT, psychoacoustic masking, and Huffman entropy
    coding into a single easy-to-use object.

    Parameters
    ----------
    quality : int
        Compression quality from 1 (lowest, highest compression)
        to 16 (highest, near-lossless). Default is 8.
    frame_size : int
        DCT block size in samples. Larger values give better
        frequency resolution (default 1 024).
    use_psychoacoustics : bool
        Enable psychoacoustic masking for perceptual quality
        improvement (default ``True``).
    """

    _QUALITY_TO_BITS = {
        1: 3, 2: 4, 3: 4, 4: 5, 5: 5, 6: 6, 7: 6, 8: 7,
        9: 8, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14, 16: 16,
    }

    def __init__(
        self,
        quality: int = 8,
        frame_size: int = 1_024,
        use_psychoacoustics: bool = True,
    ) -> None:
        if not 1 <= quality <= 16:
            raise ValueError(f"quality must be between 1 and 16, got {quality}")

        self.quality = quality
        self.frame_size = frame_size
        self.use_psychoacoustics = use_psychoacoustics
        self._q_bits = self._QUALITY_TO_BITS[quality]

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def compress(self, audio: np.ndarray, sample_rate: int = 44_100) -> Dict:
        """
        Compress a mono audio signal.

        Parameters
        ----------
        audio : ndarray, shape (N,)
            Float audio samples (normalised to [-1, 1]).
        sample_rate : int
            Sample rate of *audio* in Hz (default 44 100).

        Returns
        -------
        dict with keys:
            - ``bitstring``  : Huffman-encoded payload (str).
            - ``tree``       : Huffman tree root (for decoding).
            - ``metadata``   : Compression parameters.
            - ``stats``      : Compression statistics dict.
        """
        audio = np.asarray(audio, dtype=np.float64)

        compressor = DCTCompressor(
            frame_size=self.frame_size,
            quantisation_bits=self._q_bits,
            sample_rate=sample_rate,
            use_psychoacoustics=self.use_psychoacoustics,
        )

        t0 = time.perf_counter()
        result = compressor.compress(audio)
        elapsed = time.perf_counter() - t0

        ratio = compute_compression_ratio(audio, result["bitstring"])
        saving = compute_space_saving(audio, result["bitstring"])

        result["stats"] = {
            "compression_ratio": ratio,
            "space_saving_percent": saving,
            "original_samples": len(audio),
            "compressed_bits": len(result["bitstring"]),
            "encode_time_s": elapsed,
            "quality": self.quality,
            "quantisation_bits": self._q_bits,
            "use_psychoacoustics": self.use_psychoacoustics,
        }
        return result

    def decompress(self, compressed: Dict) -> np.ndarray:
        """
        Reconstruct audio from the output of :meth:`compress`.

        Parameters
        ----------
        compressed : dict
            Output of :meth:`compress`.

        Returns
        -------
        ndarray, shape (N,) — reconstructed float audio in [-1, 1].
        """
        meta = compressed["metadata"]
        compressor = DCTCompressor(
            frame_size=meta["frame_size"],
            quantisation_bits=self._q_bits,
            sample_rate=meta["sample_rate"],
            use_psychoacoustics=meta.get("use_psychoacoustics", False),
        )
        return compressor.decompress(compressed)

    def evaluate(
        self,
        original: np.ndarray,
        compressed: Dict,
        sample_rate: int = 44_100,
    ) -> Dict:
        """
        Decompress and evaluate quality of *compressed* against *original*.

        Parameters
        ----------
        original : ndarray
            Original audio samples.
        compressed : dict
            Output of :meth:`compress`.
        sample_rate : int
            Sample rate.

        Returns
        -------
        dict with keys:
            - ``snr_db``          : Signal-to-Noise Ratio (dB).
            - ``psnr_db``         : Peak SNR (dB).
            - ``compression_ratio`` : Compression ratio.
            - ``space_saving_percent`` : Space saved (%).
            - ``reconstructed``   : Reconstructed audio ndarray.
        """
        t0 = time.perf_counter()
        reconstructed = self.decompress(compressed)
        decode_time = time.perf_counter() - t0

        snr = compute_snr(original, reconstructed)
        psnr = compute_psnr(original, reconstructed)
        ratio = compute_compression_ratio(original, compressed["bitstring"])
        saving = compute_space_saving(original, compressed["bitstring"])

        return {
            "snr_db": snr,
            "psnr_db": psnr,
            "compression_ratio": ratio,
            "space_saving_percent": saving,
            "decode_time_s": decode_time,
            "reconstructed": reconstructed,
        }

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AudioCompressor(quality={self.quality}, "
            f"frame_size={self.frame_size}, "
            f"use_psychoacoustics={self.use_psychoacoustics})"
        )
