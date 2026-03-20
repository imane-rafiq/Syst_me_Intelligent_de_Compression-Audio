"""
AGENT 4: EXECUTION AGENT
========================

Responsibility:
- Compress audio using FFmpeg
- Apply codec, bitrate, and sample rate settings
- Save compressed file to outputs directory
- Track file sizes for metrics

Simple methods:
1. compress() - Main entry point
2. build_ffmpeg_command() - Build FFmpeg command
3. run_ffmpeg() - Execute FFmpeg
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional


class ExecutionAgent:
    """Compress audio files using FFmpeg."""

    def __init__(self):
        self.logger = SimpleLogger("ExecutionAgent")
        self.output_dir = Path("./data/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compress(
        self,
        filepath: str,
        codec: str,
        bitrate_kbps: int,
        sample_rate_hz: int,
        channels: int = 2,
    ) -> Optional[Dict]:
        """
        Compress audio file with specified parameters.

        Returns:
            Dict with output path, compression metrics, and applied params
        """
        try:
            input_file = Path(filepath)

            if not input_file.exists():
                self.logger.error(f"Input file not found: {filepath}")
                return None

            output_file = self._get_output_filename(input_file, codec)

            self.logger.info(f"Compressing: {input_file.name}")
            self.logger.info(
                f"Codec: {codec}, Bitrate: {bitrate_kbps} kbps, SR: {sample_rate_hz} Hz, Channels: {channels}"
            )

            cmd = self.build_ffmpeg_command(
                input_file=str(input_file),
                output_file=str(output_file),
                codec=codec,
                bitrate_kbps=bitrate_kbps,
                sample_rate_hz=sample_rate_hz,
                channels=channels,
            )

            success = self.run_ffmpeg(cmd)
            if not success:
                self.logger.error("FFmpeg compression failed")
                return None

            original_size = input_file.stat().st_size
            compressed_size = output_file.stat().st_size
            compression_ratio = (
                1.0 - (compressed_size / original_size) if original_size > 0 else 0.0
            )

            result = {
                "output_filepath": str(output_file),
                "output_filename": output_file.name,
                "compressed_size": compressed_size,
                "original_size": original_size,
                "compression_ratio": round(compression_ratio, 3),
                "codec": codec,
                "bitrate_kbps": bitrate_kbps,
                "sample_rate_hz": sample_rate_hz,
                "channels": channels,
            }

            self.logger.success(
                f"Compressed: {original_size / 1024 / 1024:.1f} MB → "
                f"{compressed_size / 1024 / 1024:.1f} MB "
                f"({compression_ratio * 100:.1f}% reduction)"
            )
            return result

        except Exception as e:
            self.logger.error(f"Compression failed: {str(e)}")
            return None

    def build_ffmpeg_command(
        self,
        input_file: str,
        output_file: str,
        codec: str,
        bitrate_kbps: int,
        sample_rate_hz: int,
        channels: int,
    ) -> list:
        """
        Build FFmpeg command based on codec and parameters.
        """
        codec = codec.lower().strip()

        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-y",
        ]

        if codec == "mp3":
            cmd.extend([
                "-c:a", "libmp3lame",
                "-b:a", f"{bitrate_kbps}k",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        elif codec == "aac":
            cmd.extend([
                "-c:a", "aac",
                "-b:a", f"{bitrate_kbps}k",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        elif codec == "opus":
            cmd.extend([
                "-c:a", "libopus",
                "-b:a", f"{bitrate_kbps}k",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        elif codec == "ogg":
            cmd.extend([
                "-c:a", "libvorbis",
                "-b:a", f"{bitrate_kbps}k",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        elif codec == "flac":
            cmd.extend([
                "-c:a", "flac",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        else:
            self.logger.warning(f"Unsupported codec '{codec}', defaulting to AAC")
            codec = "aac"
            cmd.extend([
                "-c:a", "aac",
                "-b:a", f"{bitrate_kbps}k",
                "-ar", str(sample_rate_hz),
                "-ac", str(channels),
            ])

        cmd.append(output_file)
        return cmd

    def run_ffmpeg(self, cmd: list) -> bool:
        """
        Execute FFmpeg command.
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True

            self.logger.error(f"FFmpeg error: {result.stderr}")
            return False

        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg timeout (file too large?)")
            return False
        except FileNotFoundError:
            self.logger.error("FFmpeg not found. Install ffmpeg first.")
            return False
        except Exception as e:
            self.logger.error(f"FFmpeg execution error: {str(e)}")
            return False

    def _get_output_filename(self, input_file: Path, codec: str) -> Path:
        """
        Generate output filename based on codec.
        """
        codec_ext = {
            "mp3": ".mp3",
            "aac": ".m4a",
            "opus": ".opus",
            "ogg": ".ogg",
            "flac": ".flac",
        }

        ext = codec_ext.get(codec.lower(), ".m4a")
        output_filename = f"{input_file.stem}_compressed{ext}"
        return self.output_dir / output_filename


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