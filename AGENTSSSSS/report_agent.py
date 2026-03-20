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
3. load_audio() - Load audio with librosa
4. calculate_metrics() - All metrics
"""

import numpy as np
import librosa
import librosa.util
from pathlib import Path
from typing import Optional, Dict


class ReportAgent:
    """Generate quality reports for compressed audio."""
    
    def __init__(self):
        self.logger = SimpleLogger("ReportAgent")
    
    def generate(self, 
                original_filepath: str,
                compressed_filepath: str) -> Optional[Dict]:
        """
        Generate compression report with quality metrics.
        
        Args:
            original_filepath: Path to original audio
            compressed_filepath: Path to compressed audio
        
        Returns:
            Dict with metrics and quality assessment, or None if failed
        """
        try:
            self.logger.info("Generating report...")
            
            # Get file info
            original_path = Path(original_filepath)
            compressed_path = Path(compressed_filepath)
            
            original_size = original_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            compression_ratio = 1.0 - (compressed_size / original_size) if original_size > 0 else 0
            
            # Load audio files
            y_original, sr_original = librosa.load(original_filepath, sr=None, mono=True)
            y_compressed, sr_compressed = librosa.load(compressed_filepath, sr=sr_original, mono=True)
            
            if len(y_original) == 0 or len(y_compressed) == 0:
                self.logger.error("Failed to load audio files")
                return None
            
            # Align lengths (compressed might be slightly different)
            min_len = min(len(y_original), len(y_compressed))
            y_original = y_original[:min_len]
            y_compressed = y_compressed[:min_len]
            
            # Calculate metrics
            snr_db = self.calculate_snr(y_original, y_compressed)
            
            # Get bitrate from filename (heuristic)
            bitrate = self._extract_bitrate_from_filename(compressed_filepath)
            
            # Get codec from file extension
            codec = compressed_path.suffix.lstrip('.')
            
            # Duration
            duration = len(y_original) / sr_original
            
            report = {
                'filename': original_path.name,
                'duration': round(duration, 2),
                'compression_ratio': round(compression_ratio, 3),
                'original_size_mb': round(original_size / (1024 * 1024), 2),
                'compressed_size_mb': round(compressed_size / (1024 * 1024), 2),
                'snr_db': round(snr_db, 2) if snr_db is not None else None,
                'bitrate_kbps': bitrate,
                'codec': codec,
                'report_file': str(Path("./data/outputs") / f"{original_path.stem}_report.json")
            }
            
            self.logger.success("Report generated")
            self._print_summary(report)
            
            return report
        
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return None
    
    def calculate_snr(self, 
                     y_original: np.ndarray,
                     y_compressed: np.ndarray) -> Optional[float]:
        """
        Calculate Signal-to-Noise Ratio (SNR).
        
        SNR = 10 * log10(P_signal / P_noise)
        
        Where:
        - P_signal = Power of original signal
        - P_noise = Power of difference (compression artifacts)
        
        Returns:
            SNR in dB, or None if calculation failed
        """
        try:
            # Calculate RMS power of original signal
            signal_power = np.mean(y_original ** 2)
            
            # Calculate error (noise) from compression
            error = y_original - y_compressed
            noise_power = np.mean(error ** 2)
            
            # Avoid log(0)
            if noise_power < 1e-10 or signal_power < 1e-10:
                return None
            
            # SNR in dB
            snr = 10 * np.log10(signal_power / noise_power)
            
            return snr
        
        except Exception as e:
            self.logger.warning(f"SNR calculation failed: {str(e)}")
            return None
    
    def _extract_bitrate_from_filename(self, filepath: str) -> int:
        """
        Try to extract bitrate from filename.
        
        This is a heuristic since we don't have access to compression decision.
        In a real workflow, the decision agent would pass this.
        """
        filename = Path(filepath).name.lower()
        
        # Try to find patterns like "64k", "128kbps", etc.
        import re
        match = re.search(r'(\d+)\s*k', filename)
        if match:
            return int(match.group(1))
        
        # Default based on file size
        compressed_mb = Path(filepath).stat().st_size / (1024 * 1024)
        if compressed_mb < 5:
            return 32
        elif compressed_mb < 10:
            return 64
        elif compressed_mb < 20:
            return 128
        else:
            return 192
    
    def _print_summary(self, report: Dict):
        """Print a nice summary of the report."""
        print("\n" + "="*50)
        print("📊 COMPRESSION REPORT")
        print("="*50)
        print(f"File: {report['filename']}")
        print(f"Duration: {report['duration']} seconds")
        print(f"Codec: {report['codec'].upper()}")
        print(f"Bitrate: {report['bitrate_kbps']} kbps")
        print(f"Original: {report['original_size_mb']} MB")
        print(f"Compressed: {report['compressed_size_mb']} MB")
        print(f"Compression Ratio: {report['compression_ratio']*100:.1f}%")
        if report['snr_db'] is not None:
            print(f"SNR: {report['snr_db']} dB")
        print("="*50 + "\n")


class SimpleLogger:
    """Simple logger for agents."""
    
    def __init__(self, name: str):
        self.name = name
    
    def info(self, msg: str):
        print(f"ℹ️  [{self.name}] {msg}")
    
    def success(self, msg: str):
        print(f"✅ [{self.name}] {msg}")
    
    def error(self, msg: str):
        print(f"❌ [{self.name}] {msg}")
    
    def warning(self, msg: str):
        print(f"⚠️  [{self.name}] {msg}")