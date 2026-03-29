#!/usr/bin/env python3
"""
Système Intelligent de Compression Audio
==========================================
Main entry point for the intelligent audio compression system.

Usage
-----
Compress a WAV file::

    python main.py compress input.wav --quality 8 --output compressed.bin

Decompress back to WAV::

    python main.py decompress compressed.bin --output reconstructed.wav

Run a demo with a synthetic test tone::

    python main.py demo

Evaluate compression quality at various quality levels::

    python main.py benchmark
"""

import argparse
import os
import pickle
import sys

import numpy as np

# ---------------------------------------------------------------------------
# Ensure src/ is importable when running from the repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))

from src import AudioCompressor
from src.utils import (
    load_audio,
    save_audio,
    generate_test_tone,
    generate_chirp,
    compute_snr,
    compute_psnr,
    compute_compression_ratio,
    compute_space_saving,
)


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_compress(args: argparse.Namespace) -> None:
    """Compress a WAV file."""
    print(f"[INFO] Loading audio: {args.input}")
    audio, sample_rate = load_audio(args.input)
    print(f"[INFO] Samples: {len(audio):,}  |  Sample rate: {sample_rate} Hz")

    compressor = AudioCompressor(
        quality=args.quality,
        frame_size=args.frame_size,
        use_psychoacoustics=not args.no_psycho,
    )
    print(f"[INFO] Compressing with {compressor} …")
    result = compressor.compress(audio, sample_rate=sample_rate)

    stats = result["stats"]
    print(
        f"[INFO] Done.\n"
        f"       Compression ratio  : {stats['compression_ratio']:.2f}×\n"
        f"       Space saving       : {stats['space_saving_percent']:.1f}%\n"
        f"       Encode time        : {stats['encode_time_s'] * 1000:.1f} ms\n"
        f"       Compressed bits    : {stats['compressed_bits']:,}"
    )

    # Serialize with pickle (includes Huffman tree)
    output_path = args.output or (os.path.splitext(args.input)[0] + ".sica")
    with open(output_path, "wb") as fh:
        pickle.dump(result, fh)
    print(f"[INFO] Compressed data written to: {output_path}")


def cmd_decompress(args: argparse.Namespace) -> None:
    """Decompress a .sica file back to WAV."""
    print(f"[INFO] Loading compressed file: {args.input}")
    with open(args.input, "rb") as fh:
        result = pickle.load(fh)

    meta = result["metadata"]
    quality = result["stats"]["quality"]
    compressor = AudioCompressor(
        quality=quality,
        frame_size=meta["frame_size"],
        use_psychoacoustics=meta.get("use_psychoacoustics", True),
    )

    print("[INFO] Decompressing …")
    reconstructed = compressor.decompress(result)

    output_path = args.output or (os.path.splitext(args.input)[0] + "_reconstructed.wav")
    save_audio(output_path, reconstructed, sample_rate=meta["sample_rate"])
    print(f"[INFO] Reconstructed audio written to: {output_path}")


def cmd_demo(args: argparse.Namespace) -> None:
    """Run a demonstration with a synthetic test signal."""
    print("=" * 60)
    print("  Système Intelligent de Compression Audio — Demo")
    print("=" * 60)

    sample_rate = 44_100

    # Generate a mixed test signal (440 Hz + 1 kHz + 4 kHz)
    t = np.linspace(0, 2.0, 2 * sample_rate, endpoint=False)
    audio = (
        0.4 * np.sin(2 * np.pi * 440 * t)
        + 0.3 * np.sin(2 * np.pi * 1_000 * t)
        + 0.2 * np.sin(2 * np.pi * 4_000 * t)
    )

    print(f"\nTest signal : 440 Hz + 1 kHz + 4 kHz sine mix")
    print(f"Duration    : 2 seconds  |  Sample rate: {sample_rate} Hz")
    print(f"Samples     : {len(audio):,}")

    print(f"\n{'Quality':>8}  {'Ratio':>8}  {'Saving%':>9}  {'SNR(dB)':>10}  {'PSNR(dB)':>10}")
    print("-" * 55)

    for quality in [2, 4, 6, 8, 10, 12, 14]:
        compressor = AudioCompressor(
            quality=quality, frame_size=1_024, use_psychoacoustics=True
        )
        compressed = compressor.compress(audio, sample_rate=sample_rate)
        reconstructed = compressor.decompress(compressed)

        snr = compute_snr(audio, reconstructed)
        psnr = compute_psnr(audio, reconstructed)
        ratio = compute_compression_ratio(audio, compressed["bitstring"])
        saving = compute_space_saving(audio, compressed["bitstring"])

        print(
            f"{quality:>8}  {ratio:>8.2f}  {saving:>8.1f}%  {snr:>10.2f}  {psnr:>10.2f}"
        )

    print("\n[INFO] Demo complete.")

    # Optionally save results
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        save_audio(os.path.join(args.output_dir, "original.wav"), audio, sample_rate)
        for quality in [4, 8, 12]:
            compressor = AudioCompressor(quality=quality, use_psychoacoustics=True)
            compressed = compressor.compress(audio, sample_rate=sample_rate)
            reconstructed = compressor.decompress(compressed)
            out_path = os.path.join(args.output_dir, f"reconstructed_q{quality}.wav")
            save_audio(out_path, reconstructed, sample_rate)
            print(f"[INFO] Saved: {out_path}")


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Benchmark the compressor across all quality levels."""
    import time

    sample_rate = 44_100

    signals = {
        "sine_440Hz": generate_test_tone(440, duration=1.0, sample_rate=sample_rate)[0],
        "chirp_100-8kHz": generate_chirp(100, 8_000, duration=1.0, sample_rate=sample_rate)[0],
    }

    for sig_name, audio in signals.items():
        print(f"\n{'=' * 65}")
        print(f"  Signal: {sig_name}  ({len(audio):,} samples)")
        print(f"{'=' * 65}")
        print(
            f"{'Quality':>8}  {'Ratio':>8}  {'Saving%':>9}  "
            f"{'SNR(dB)':>10}  {'Enc(ms)':>9}  {'Dec(ms)':>9}"
        )
        print("-" * 65)

        for quality in range(1, 17):
            compressor = AudioCompressor(
                quality=quality, frame_size=1_024, use_psychoacoustics=True
            )

            t0 = time.perf_counter()
            compressed = compressor.compress(audio, sample_rate=sample_rate)
            enc_ms = (time.perf_counter() - t0) * 1_000

            t0 = time.perf_counter()
            reconstructed = compressor.decompress(compressed)
            dec_ms = (time.perf_counter() - t0) * 1_000

            snr = compute_snr(audio, reconstructed)
            ratio = compute_compression_ratio(audio, compressed["bitstring"])
            saving = compute_space_saving(audio, compressed["bitstring"])

            snr_str = f"{snr:.2f}" if np.isfinite(snr) else "  ∞"
            print(
                f"{quality:>8}  {ratio:>8.2f}  {saving:>8.1f}%  "
                f"{snr_str:>10}  {enc_ms:>9.1f}  {dec_ms:>9.1f}"
            )

    print("\n[INFO] Benchmark complete.")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Système Intelligent de Compression Audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- compress ---
    p_compress = sub.add_parser("compress", help="Compress a WAV file")
    p_compress.add_argument("input", help="Input WAV file path")
    p_compress.add_argument(
        "--quality", "-q", type=int, default=8, choices=range(1, 17),
        metavar="[1-16]", help="Compression quality (1=lowest, 16=highest, default 8)"
    )
    p_compress.add_argument(
        "--frame-size", "-f", type=int, default=1_024,
        help="DCT frame size in samples (default 1024)"
    )
    p_compress.add_argument(
        "--output", "-o", default=None,
        help="Output .sica file path (default: input basename + .sica)"
    )
    p_compress.add_argument(
        "--no-psycho", action="store_true",
        help="Disable psychoacoustic masking"
    )
    p_compress.set_defaults(func=cmd_compress)

    # --- decompress ---
    p_decompress = sub.add_parser("decompress", help="Decompress a .sica file to WAV")
    p_decompress.add_argument("input", help="Input .sica file path")
    p_decompress.add_argument(
        "--output", "-o", default=None,
        help="Output WAV file path"
    )
    p_decompress.set_defaults(func=cmd_decompress)

    # --- demo ---
    p_demo = sub.add_parser("demo", help="Run a demonstration with synthetic signals")
    p_demo.add_argument(
        "--output-dir", "-o", default=None,
        help="Directory to write demo WAV files (optional)"
    )
    p_demo.set_defaults(func=cmd_demo)

    # --- benchmark ---
    p_bench = sub.add_parser("benchmark", help="Benchmark all quality levels")
    p_bench.set_defaults(func=cmd_benchmark)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
