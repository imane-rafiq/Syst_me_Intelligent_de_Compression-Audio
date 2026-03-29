"""
AGENT 5: REPORT AGENT
=====================

Responsibility:
- Load original and compressed audio
- Calculate quality metrics (SNR, compression ratio)
- Generate final report
- Save report to JSON file

Simple methods:
1. generate() - Main entry point
2. calculate_snr() - Signal-to-Noise Ratio
3. calculate_metrics() - All metrics
"""

import json
from pathlib import Path
from typing import Dict, Optional

import librosa
import numpy as np


class ReportAgent:
    """Generate quality reports for compressed audio."""

    def __init__(self):
        self.logger = SimpleLogger("ReportAgent")
        self.output_dir = Path("./data/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        original_filepath: str,
        compressed_filepath: str,
        compression_params: Dict,
    ) -> Optional[Dict]:
        """
        Generate compression report with quality metrics.

        Args:
            original_filepath: Path to original audio
            compressed_filepath: Path to compressed audio
            compression_params: Dict containing real params from Decision/Execution agent

        Returns:
            Dict with metrics and quality assessment, or None if failed
        """
        try:
            self.logger.info("Generating report...")

            original_path = Path(original_filepath)
            compressed_path = Path(compressed_filepath)

            if not original_path.exists():
                self.logger.error(f"Original file not found: {original_filepath}")
                return None

            if not compressed_path.exists():
                self.logger.error(f"Compressed file not found: {compressed_filepath}")
                return None

            original_size = original_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            compression_ratio = (
                1.0 - (compressed_size / original_size) if original_size > 0 else 0.0
            )

            y_original, sr_original = librosa.load(original_filepath, sr=None, mono=True)
            y_compressed, _ = librosa.load(compressed_filepath, sr=sr_original, mono=True)

            if len(y_original) == 0 or len(y_compressed) == 0:
                self.logger.error("Failed to load audio files")
                return None

            min_len = min(len(y_original), len(y_compressed))
            y_original = y_original[:min_len]
            y_compressed = y_compressed[:min_len]

            snr_db = self.calculate_snr(y_original, y_compressed)
            duration_sec = len(y_original) / sr_original

            report = {
                "file_name": original_path.name,
                "original_filepath": str(original_path),
                "compressed_filepath": str(compressed_path),
                "duration_sec": round(duration_sec, 2),
                "compression_ratio": round(compression_ratio, 3),
                "original_size_mb": round(original_size / (1024 * 1024), 2),
                "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
                "snr_db": round(snr_db, 2) if snr_db is not None else None,
                "codec": compression_params.get("codec"),
                "bitrate_kbps": compression_params.get("bitrate_kbps"),
                "sample_rate_hz": compression_params.get("sample_rate_hz"),
                "channels": compression_params.get("channels"),
                "decision_source": compression_params.get("decision_source"),
                "reasoning": compression_params.get("reasoning"),
            }

            report_path = self.output_dir / f"{original_path.stem}_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            report["report_file"] = str(report_path)

            self.logger.success("Report generated and saved")
            self._print_summary(report)

            return report

        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return None

    def calculate_snr(
        self,
        y_original: np.ndarray,
        y_compressed: np.ndarray,
    ) -> Optional[float]:
        """
        Calculate Signal-to-Noise Ratio (SNR).
        """
        try:
            signal_power = np.mean(y_original ** 2)
            error = y_original - y_compressed
            noise_power = np.mean(error ** 2)

            if noise_power < 1e-10 or signal_power < 1e-10:
                return None

            snr = 10 * np.log10(signal_power / noise_power)
            return float(snr)

        except Exception as e:
            self.logger.warning(f"SNR calculation failed: {str(e)}")
            return None

    def _print_summary(self, report: Dict):
        """Print a summary of the report."""
        print("\n" + "=" * 50)
        print("REPORT: COMPRESSION REPORT")
        print("=" * 50)
        print(f"File: {report['file_name']}")
        print(f"Duration: {report['duration_sec']} seconds")
        print(f"Codec: {str(report['codec']).upper()}")
        print(f"Bitrate: {report['bitrate_kbps']} kbps")
        print(f"Sample rate: {report['sample_rate_hz']} Hz")
        print(f"Channels: {report['channels']}")
        print(f"Original: {report['original_size_mb']} MB")
        print(f"Compressed: {report['compressed_size_mb']} MB")
        print(f"Compression Ratio: {report['compression_ratio'] * 100:.1f}%")
        if report["snr_db"] is not None:
            print(f"SNR: {report['snr_db']} dB")
        else:
            print("SNR: unavailable")
        print(f"Saved JSON: {report['report_file']}")
        print("=" * 50 + "\n")


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