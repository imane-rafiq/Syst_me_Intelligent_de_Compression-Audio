"""
Utility Functions
==================
Helper functions for audio I/O, quality metrics, and result plotting.
"""

import os
import struct
import wave
from typing import Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------

def load_audio(path: str) -> Tuple[np.ndarray, int]:
    """
    Load a WAV file and return normalised float32 samples and sample rate.

    Only the first channel is used for multi-channel files.

    Parameters
    ----------
    path : str
        Path to the WAV file.

    Returns
    -------
    samples : ndarray, shape (N,)
        Audio samples normalised to [-1, 1].
    sample_rate : int
        Sample rate in Hz.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file cannot be read or has an unsupported format.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Audio file not found: {path}")

    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()  # bytes per sample
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # Decode raw bytes
    if sample_width == 1:
        dtype = np.uint8
        max_val = 128.0
    elif sample_width == 2:
        dtype = np.int16
        max_val = 32767.0
    elif sample_width == 4:
        dtype = np.int32
        max_val = 2147483647.0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width} bytes")

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)

    # Normalise unsigned 8-bit audio
    if sample_width == 1:
        samples = (samples - 128.0) / 128.0
    else:
        samples /= max_val

    # Take first channel if stereo
    if n_channels > 1:
        samples = samples[::n_channels]

    return samples, sample_rate


def save_audio(path: str, samples: np.ndarray, sample_rate: int) -> None:
    """
    Save float64 audio samples as a 16-bit PCM WAV file.

    Parameters
    ----------
    path : str
        Destination file path (must end in .wav).
    samples : ndarray
        Audio samples in [-1, 1].
    sample_rate : int
        Sample rate in Hz.
    """
    # Clip and convert to 16-bit PCM
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def generate_test_tone(
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 44_100,
    amplitude: float = 0.5,
) -> Tuple[np.ndarray, int]:
    """
    Generate a pure sine-wave test tone.

    Parameters
    ----------
    frequency : float
        Tone frequency in Hz (default 440 Hz, concert A).
    duration : float
        Duration in seconds (default 1.0).
    sample_rate : int
        Sample rate in Hz (default 44 100).
    amplitude : float
        Peak amplitude in [0, 1] (default 0.5).

    Returns
    -------
    samples : ndarray, shape (N,)
    sample_rate : int
    """
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    samples = amplitude * np.sin(2.0 * np.pi * frequency * t)
    return samples, sample_rate


def generate_chirp(
    f_start: float = 100.0,
    f_end: float = 8_000.0,
    duration: float = 2.0,
    sample_rate: int = 44_100,
    amplitude: float = 0.5,
) -> Tuple[np.ndarray, int]:
    """
    Generate a linear chirp (frequency sweep) test signal.

    Parameters
    ----------
    f_start : float
        Start frequency in Hz.
    f_end : float
        End frequency in Hz.
    duration : float
        Duration in seconds.
    sample_rate : int
        Sample rate in Hz.
    amplitude : float
        Peak amplitude in [0, 1].

    Returns
    -------
    samples : ndarray, shape (N,)
    sample_rate : int
    """
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    k = (f_end - f_start) / duration
    phase = 2.0 * np.pi * (f_start * t + 0.5 * k * t ** 2)
    samples = amplitude * np.sin(phase)
    return samples, sample_rate


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

def compute_snr(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """
    Compute the Signal-to-Noise Ratio (SNR) in dB.

    SNR = 10 * log10(power(signal) / power(noise))

    Parameters
    ----------
    original : ndarray
        Original audio samples.
    reconstructed : ndarray
        Reconstructed audio samples (same length as *original*).

    Returns
    -------
    float — SNR in dB.  Returns ``inf`` if the noise power is zero.
    """
    length = min(len(original), len(reconstructed))
    orig = original[:length]
    recon = reconstructed[:length]
    signal_power = np.mean(orig ** 2)
    noise_power = np.mean((orig - recon) ** 2)
    if noise_power < 1e-30:
        return float("inf")
    return 10.0 * np.log10(signal_power / noise_power)


def compute_psnr(original: np.ndarray, reconstructed: np.ndarray) -> float:
    """
    Compute the Peak Signal-to-Noise Ratio (PSNR) in dB.

    PSNR = 20 * log10(max_amplitude / RMSE)

    Parameters
    ----------
    original : ndarray
    reconstructed : ndarray

    Returns
    -------
    float — PSNR in dB.
    """
    length = min(len(original), len(reconstructed))
    orig = original[:length]
    recon = reconstructed[:length]
    mse = np.mean((orig - recon) ** 2)
    if mse < 1e-30:
        return float("inf")
    max_amplitude = max(np.max(np.abs(orig)), 1e-10)
    return 20.0 * np.log10(max_amplitude / np.sqrt(mse))


def compute_compression_ratio(
    original: np.ndarray,
    bitstring: str,
    bits_per_sample: int = 16,
) -> float:
    """
    Compute the compression ratio.

    compression_ratio = original_bits / compressed_bits

    Parameters
    ----------
    original : ndarray
        Original audio samples.
    bitstring : str
        Compressed bitstring (from Huffman encoding).
    bits_per_sample : int
        Number of bits per sample in the uncompressed representation
        (default 16 for 16-bit PCM).

    Returns
    -------
    float — ratio ≥ 1.0 (higher means more compression).
    """
    original_bits = len(original) * bits_per_sample
    compressed_bits = len(bitstring)
    if compressed_bits == 0:
        return float("inf")
    return original_bits / compressed_bits


def compute_space_saving(
    original: np.ndarray,
    bitstring: str,
    bits_per_sample: int = 16,
) -> float:
    """
    Compute the space saving as a percentage.

    space_saving = (1 − compressed_bits / original_bits) × 100

    Parameters
    ----------
    original : ndarray
    bitstring : str
    bits_per_sample : int

    Returns
    -------
    float — percentage of storage saved.
    """
    original_bits = len(original) * bits_per_sample
    compressed_bits = len(bitstring)
    if original_bits == 0:
        return 0.0
    return (1.0 - compressed_bits / original_bits) * 100.0
