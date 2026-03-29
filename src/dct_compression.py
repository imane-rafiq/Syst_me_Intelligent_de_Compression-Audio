"""
DCT-based Audio Compression
=============================
Implements a block DCT (Discrete Cosine Transform) audio compressor
with perceptual weighting and uniform scalar quantisation.

Compression pipeline
--------------------
Encoding
  1. Segment audio into overlapping frames.
  2. Apply a Hanning window to each frame.
  3. Compute the Type-II DCT of each frame.
  4. Scale each DCT coefficient by its psychoacoustic perceptual weight.
  5. Quantise coefficients with a configurable step size.
  6. Entropy-encode the quantised integers with Huffman coding.

Decoding
  1. Huffman-decode the bitstream.
  2. Dequantise (multiply by step size).
  3. Apply inverse DCT (IDCT) to each frame.
  4. Overlap-add frames to reconstruct the audio signal.
"""

import numpy as np
from scipy.fft import dct, idct
from typing import Dict, List, Tuple

from .huffman import HuffmanCoder
from .psychoacoustic_model import PsychoacousticModel


class DCTCompressor:
    """
    Block-DCT audio compressor with psychoacoustic-guided quantisation.

    Parameters
    ----------
    frame_size : int
        Number of samples per DCT block (default 1 024).
    hop_size : int or None
        Hop between successive frames. If ``None``, defaults to
        ``frame_size // 2`` (50 % overlap).
    quantisation_bits : int
        Effective number of bits used for uniform scalar quantisation
        (default 8).  Fewer bits → higher compression, lower quality.
    sample_rate : int
        Sample rate of the input audio (default 44 100 Hz).
    use_psychoacoustics : bool
        If ``True``, the psychoacoustic model modulates quantisation step
        per coefficient (default ``True``).
    """

    def __init__(
        self,
        frame_size: int = 1_024,
        hop_size: int = None,
        quantisation_bits: int = 8,
        sample_rate: int = 44_100,
        use_psychoacoustics: bool = True,
    ) -> None:
        self.frame_size = frame_size
        self.hop_size = hop_size if hop_size is not None else frame_size // 2
        self.quantisation_bits = quantisation_bits
        self.sample_rate = sample_rate
        self.use_psychoacoustics = use_psychoacoustics

        # Sine window: w[n] = sin(pi*(n+0.5)/N)
        # Satisfies w[n]^2 + w[n + N/2]^2 = 1 for all n when hop = N/2,
        # enabling perfect reconstruction via overlap-add of w^2.
        n = np.arange(frame_size)
        self._window = np.sin(np.pi * (n + 0.5) / frame_size)

        self._huffman = HuffmanCoder()
        self._psycho = PsychoacousticModel(
            sample_rate=sample_rate, frame_size=frame_size
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(self, audio: np.ndarray) -> Dict:
        """
        Compress a mono audio signal.

        Parameters
        ----------
        audio : ndarray, shape (N,)
            Normalised float audio samples in [-1, 1].

        Returns
        -------
        dict with keys:
            ``bitstring``  — Huffman-encoded bitstring (str).
            ``tree``       — Huffman tree root (for decoding).
            ``metadata``   — dict with frame_size, hop_size, n_frames,
                             audio_length, q_step, quant_max.
        """
        audio = np.asarray(audio, dtype=np.float64)
        frames = self._frame(audio)

        # Compute global quantisation step from maximum DCT energy
        all_coeffs = np.array([dct(f * self._window, norm="ortho") for f in frames])
        q_step = self._compute_q_step(all_coeffs)
        quant_max = int(np.max(np.abs(all_coeffs)) / q_step) + 1

        # Quantise each frame and collect integers
        quant_indices: List[int] = []
        for i, frame in enumerate(frames):
            coeffs = dct(frame * self._window, norm="ortho")
            if self.use_psychoacoustics:
                weights = self._psycho.perceptual_weights(frame)
                # Expand weights to full frame size via interpolation
                weights_full = np.interp(
                    np.arange(self.frame_size),
                    np.linspace(0, self.frame_size - 1, len(weights)),
                    weights,
                )
                # Coefficients with low perceptual weight get coarser step
                effective_step = q_step / (weights_full + 0.1)
            else:
                effective_step = np.full(self.frame_size, q_step)

            quantised = np.round(coeffs / effective_step).astype(int)
            quant_indices.extend(quantised.tolist())

        bitstring, tree = self._huffman.encode(quant_indices)

        metadata = {
            "frame_size": self.frame_size,
            "hop_size": self.hop_size,
            "n_frames": len(frames),
            "audio_length": len(audio),
            "q_step": float(q_step),
            "quant_max": int(quant_max),
            "sample_rate": self.sample_rate,
            "use_psychoacoustics": self.use_psychoacoustics,
        }
        return {"bitstring": bitstring, "tree": tree, "metadata": metadata}

    def decompress(self, compressed: Dict) -> np.ndarray:
        """
        Decompress a signal from the dictionary produced by :meth:`compress`.

        Parameters
        ----------
        compressed : dict
            Output of :meth:`compress`.

        Returns
        -------
        ndarray, shape (audio_length,)  —  reconstructed float audio.
        """
        bitstring = compressed["bitstring"]
        tree = compressed["tree"]
        meta = compressed["metadata"]

        frame_size = meta["frame_size"]
        hop_size = meta["hop_size"]
        n_frames = meta["n_frames"]
        audio_length = meta["audio_length"]
        q_step = meta["q_step"]
        use_psycho = meta.get("use_psychoacoustics", False)

        # Huffman decode
        flat_indices = self._huffman.decode(bitstring, tree)

        # Reshape into frames
        total_coeffs = n_frames * frame_size
        flat_indices = flat_indices[:total_coeffs]
        frame_indices = np.array(flat_indices, dtype=float).reshape(n_frames, frame_size)

        # Reconstruct audio via weighted overlap-add (WOLA).
        # The sine window satisfies w[n]^2 + w[n + N/2]^2 = 1 for all n when
        # hop = N/2, so the sum of squares over overlapping frames equals 1.
        # Analysis: C = DCT(frame * w)
        # Synthesis: r = IDCT(C) * w
        # Normalisation: divide by sum of w^2 per sample (= 1 in the interior).
        output = np.zeros(audio_length + frame_size)
        window = np.sin(np.pi * (np.arange(frame_size) + 0.5) / frame_size)
        norm = np.zeros_like(output)

        for i in range(n_frames):
            start = i * hop_size
            coeffs = frame_indices[i] * q_step
            # IDCT recovers the windowed frame; apply the synthesis window.
            frame_reconstructed = idct(coeffs, norm="ortho") * window
            output[start: start + frame_size] += frame_reconstructed
            norm[start: start + frame_size] += window ** 2

        # Divide by the accumulated window-squared sum (≈ 1 in the interior).
        norm = np.where(norm < 1e-8, 1.0, norm)
        output /= norm
        return output[:audio_length]

    def compression_ratio(self, audio: np.ndarray, compressed: Dict) -> float:
        """
        Compute the compression ratio relative to 16-bit PCM.

        Parameters
        ----------
        audio : ndarray
            Original audio samples.
        compressed : dict
            Output of :meth:`compress`.

        Returns
        -------
        float — bits_original / bits_compressed.
        """
        original_bits = len(audio) * 16  # 16-bit PCM
        compressed_bits = len(compressed["bitstring"])
        if compressed_bits == 0:
            return float("inf")
        return original_bits / compressed_bits

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _frame(self, audio: np.ndarray) -> List[np.ndarray]:
        """Split *audio* into overlapping frames of length ``frame_size``."""
        frames = []
        n = len(audio)
        start = 0
        while start + self.frame_size <= n:
            frames.append(audio[start: start + self.frame_size].copy())
            start += self.hop_size
        # Pad the last frame if needed
        remainder = n - start
        if remainder > 0:
            pad = np.zeros(self.frame_size)
            pad[:remainder] = audio[start:]
            frames.append(pad)
        return frames

    def _compute_q_step(self, all_coeffs: np.ndarray) -> float:
        """Derive the uniform quantisation step from the coefficient range."""
        max_val = np.max(np.abs(all_coeffs))
        levels = 2 ** self.quantisation_bits
        q_step = (2.0 * max_val) / levels
        return max(q_step, 1e-10)
