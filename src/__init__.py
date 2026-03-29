"""
Système Intelligent de Compression Audio
=========================================
Intelligent Audio Compression System using DCT, Huffman coding,
and psychoacoustic modeling.
"""

from .audio_compression import AudioCompressor
from .huffman import HuffmanCoder
from .dct_compression import DCTCompressor
from .psychoacoustic_model import PsychoacousticModel
from .utils import compute_snr, compute_compression_ratio, load_audio, save_audio

__all__ = [
    "AudioCompressor",
    "HuffmanCoder",
    "DCTCompressor",
    "PsychoacousticModel",
    "compute_snr",
    "compute_compression_ratio",
    "load_audio",
    "save_audio",
]
