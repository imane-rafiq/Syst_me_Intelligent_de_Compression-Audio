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
import os
from pathlib import Path
from typing import Optional, Dict


class ExecutionAgent:
    """Compress audio files using FFmpeg."""
    
    def __init__(self):
        self.logger = SimpleLogger("ExecutionAgent")
        self.output_dir = Path("./data/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def compress(self, 
                filepath: str,
                codec: str,
                bitrate: int,
                sample_rate: int,
                channels: int = 2) -> Optional[Dict]:
        """
        Compress audio file with specified parameters.
        
        Args:
            filepath: Path to input audio file
            codec: Codec to use (mp3, aac, opus, ogg, flac)
            bitrate: Bitrate in kbps
            sample_rate: Sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)
        
        Returns:
            Dict with output path and file sizes, or None if failed
        """
        try:
            input_file = Path(filepath)
            
            # Validate input
            if not input_file.exists():
                self.logger.error(f"Input file not found: {filepath}")
                return None
            
            # Get output filename
            output_file = self._get_output_filename(input_file, codec)
            
            self.logger.info(f"Compressing: {input_file.name}")
            self.logger.info(f"Codec: {codec}, Bitrate: {bitrate} kbps, SR: {sample_rate} Hz")
            
            # Build FFmpeg command
            cmd = self.build_ffmpeg_command(
                str(input_file),
                str(output_file),
                codec,
                bitrate,
                sample_rate,
                channels
            )
            
            # Run compression
            success = self.run_ffmpeg(cmd)
            
            if not success:
                self.logger.error("FFmpeg compression failed")
                return None
            
            # Get file sizes
            original_size = input_file.stat().st_size
            compressed_size = output_file.stat().st_size
            compression_ratio = 1.0 - (compressed_size / original_size) if original_size > 0 else 0
            
            result = {
                'output_filepath': str(output_file),
                'output_filename': output_file.name,
                'compressed_size': compressed_size,
                'original_size': original_size,
                'compression_ratio': round(compression_ratio, 3)
            }
            
            self.logger.success(
                f"Compressed: {original_size/1024/1024:.1f} MB → {compressed_size/1024/1024:.1f} MB "
                f"({compression_ratio*100:.1f}% reduction)"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Compression failed: {str(e)}")
            return None
    
    def build_ffmpeg_command(self,
                            input_file: str,
                            output_file: str,
                            codec: str,
                            bitrate: int,
                            sample_rate: int,
                            channels: int) -> list:
        """
        Build FFmpeg command based on codec and parameters.
        
        Returns:
            List of command arguments for subprocess.run()
        """
        
        # Common FFmpeg options
        cmd = [
            'ffmpeg',
            '-i', input_file,           # Input file
            '-y',                       # Overwrite output file
        ]
        
        # Codec-specific options
        if codec == 'mp3':
            # MP3 compression
            cmd.extend([
                '-c:a', 'libmp3lame',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        elif codec == 'aac':
            # AAC compression (high quality)
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        elif codec == 'opus':
            # Opus compression (excellent for speech)
            cmd.extend([
                '-c:a', 'libopus',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        elif codec == 'ogg':
            # OGG Vorbis compression
            cmd.extend([
                '-c:a', 'libvorbis',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        elif codec == 'flac':
            # FLAC (lossless, ignore bitrate)
            cmd.extend([
                '-c:a', 'flac',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        else:
            # Default to AAC
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', f'{bitrate}k',
                '-ar', str(sample_rate),
                '-ac', str(channels),
            ])
        
        cmd.append(output_file)  # Output file
        
        return cmd
    
    def run_ffmpeg(self, cmd: list) -> bool:
        """
        Execute FFmpeg command.
        
        Returns True if successful, False otherwise.
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                return True
            else:
                self.logger.error(f"FFmpeg error: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg timeout (file too large?)")
            return False
        except FileNotFoundError:
            self.logger.error("FFmpeg not found. Install with: sudo apt-get install ffmpeg")
            return False
        except Exception as e:
            self.logger.error(f"FFmpeg execution error: {str(e)}")
            return False
    
    def _get_output_filename(self, input_file: Path, codec: str) -> Path:
        """
        Generate output filename based on codec.
        
        Example:
            input: podcast.wav
            codec: opus
            output: podcast_compressed.opus
        """
        # Map codec to file extension
        codec_ext = {
            'mp3': '.mp3',
            'aac': '.m4a',
            'opus': '.opus',
            'ogg': '.ogg',
            'flac': '.flac'
        }
        
        ext = codec_ext.get(codec.lower(), '.mp3')
        stem = input_file.stem
        output_filename = f"{stem}_compressed{ext}"
        
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