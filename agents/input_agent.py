# agents/input_agent.py
# Renommer physiquement le fichier en input_agent.py

import json
import subprocess
from pathlib import Path
from typing import Dict, Optional


class SimpleLogger:
    def __init__(self, name: str):
        self.name = name

    def info(self, msg: str):
        print(f"ℹ️ [{self.name}] {msg}")

    def success(self, msg: str):
        print(f"✅ [{self.name}] {msg}")

    def warning(self, msg: str):
        print(f"⚠️ [{self.name}] {msg}")

    def error(self, msg: str):
        print(f"❌ [{self.name}] {msg}")


class InputAgent:
    SUPPORTED_FORMATS = {
        ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".aiff"
    }

    def __init__(self):
        self.logger = SimpleLogger("InputAgent")

    def load_and_validate(self, filepath: str) -> Optional[Dict]:
        file_path = Path(filepath)

        if not file_path.exists():
            self.logger.error(f"File not found: {filepath}")
            return None

        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            self.logger.error(f"Unsupported format: {file_path.suffix}")
            return None

        metadata = self.get_metadata_ffprobe(filepath)
        if metadata is None:
            self.logger.error("Could not extract metadata")
            return None

        if not self._validate_metadata(metadata):
            self.logger.error("Invalid audio metadata")
            return None

        self.logger.success(f"Loaded and validated: {metadata['file_name']}")
        return metadata

    def get_metadata_ffprobe(self, filepath: str) -> Optional[Dict]:
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                self.logger.error(result.stderr.strip() or "ffprobe failed")
                return None

            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            format_info = data.get("format", {})

            audio_stream = next(
                (stream for stream in streams if stream.get("codec_type") == "audio"),
                None,
            )

            if audio_stream is None:
                self.logger.error("No audio stream found")
                return None

            bit_depth = audio_stream.get("bits_per_sample")
            if bit_depth in (None, "", "0", 0):
                raw_depth = audio_stream.get("bits_per_raw_sample")
                bit_depth = int(raw_depth) if raw_depth not in (None, "", "N/A") else None
            else:
                bit_depth = int(bit_depth)

            file_size_bytes = Path(filepath).stat().st_size

            metadata = {
                "file_path": str(Path(filepath).resolve()),
                "file_name": Path(filepath).name,
                "duration_sec": float(format_info.get("duration", 0)),
                "sample_rate_hz": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "codec": audio_stream.get("codec_name", "unknown"),
                "bit_depth": bit_depth,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            }
            return metadata

        except subprocess.TimeoutExpired:
            self.logger.error("ffprobe timeout")
            return None
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON returned by ffprobe")
            return None
        except Exception as e:
            self.logger.error(str(e))
            return None

    def _validate_metadata(self, metadata: Dict) -> bool:
        required = [
            "file_path",
            "file_name",
            "duration_sec",
            "sample_rate_hz",
            "channels",
            "codec",
        ]
        if not all(key in metadata for key in required):
            return False

        if metadata["duration_sec"] <= 0:
            return False

        if metadata["sample_rate_hz"] < 8000 or metadata["sample_rate_hz"] > 192000:
            return False

        if metadata["channels"] < 1 or metadata["channels"] > 8:
            return False

        return True