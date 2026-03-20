"""
AGENT 1: INPUT AGENT
====================
 
Responsibility:
- Load audio files
- Extract metadata (duration, sample_rate, channels, codec, filesize)
- Validate files are supported and readable
 
Simple methods:
1. load_and_validate() - Main entry point
2. get_metadata_ffprobe() - Uses FFmpeg to read metadata
"""
 
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict
 
 
class InputAgent:
    """Load and validate audio files."""
    
    # Supported audio formats
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.opus', '.aiff', '.aac'}
    
    def __init__(self):
        self.logger = SimpleLogger("InputAgent")
    
    def load_and_validate(self, filepath: str) -> Optional[Dict]:
        """
        Load an audio file and extract metadata.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Dict with metadata or None if failed
        """
        filepath = Path(filepath)
        
        # Check file exists
        if not filepath.exists():
            self.logger.error(f"File not found: {filepath}")
            return None
        
        # Check file extension
        if filepath.suffix.lower() not in self.SUPPORTED_FORMATS:
            self.logger.error(f"Unsupported format: {filepath.suffix}")
            return None
        
        # Extract metadata
        metadata = self.get_metadata_ffprobe(str(filepath))
        
        if metadata is None:
            self.logger.error(f"Failed to extract metadata from {filepath}")
            return None
        
        # Validate metadata
        if not self._validate_metadata(metadata):
            self.logger.error(f"Invalid metadata: {metadata}")
            return None
        
        self.logger.success(f"Loaded: {filepath.name}")
        return metadata
    
    def get_metadata_ffprobe(self, filepath: str) -> Optional[Dict]:
        """
        Extract metadata using FFprobe (FFmpeg tool).
        
        Reads: duration, sample_rate, channels, codec, file size
        """
        try:
            # FFprobe command
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                filepath
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.error(f"FFprobe failed: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract first audio stream
            if not data.get('streams'):
                self.logger.error("No audio streams found")
                return None
            
            stream = data['streams'][0]
            fmt = data.get('format', {})
            
            # Get file size
            file_size_bytes = Path(filepath).stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            metadata = {
                'filepath': filepath,
                'filename': Path(filepath).name,
                'duration': float(fmt.get('duration', 0)),
                'sample_rate': int(stream.get('sample_rate', 0)),
                'channels': int(stream.get('channels', 0)),
                'codec': stream.get('codec_name', 'unknown'),
                'filesize_bytes': file_size_bytes,
                'filesize_mb': round(file_size_mb, 2)
            }
            
            return metadata
        
        except subprocess.TimeoutExpired:
            self.logger.error("FFprobe timeout")
            return None
        except json.JSONDecodeError:
            self.logger.error("Invalid FFprobe JSON output")
            return None
        except Exception as e:
            self.logger.error(f"FFprobe error: {str(e)}")
            return None
    
    def _validate_metadata(self, metadata: Dict) -> bool:
        """
        Validate extracted metadata is sensible.
        
        Returns True if valid, False otherwise.
        """
        # Check required fields
        required = ['duration', 'sample_rate', 'channels', 'codec']
        if not all(k in metadata for k in required):
            return False
        
        # Check sensible values
        if metadata['duration'] < 0.1:  # Less than 100ms
            return False
        
        if metadata['duration'] > 36000:  # More than 10 hours
            return False
        
        if metadata['sample_rate'] < 8000:  # Less than 8 kHz
            return False
        
        if metadata['sample_rate'] > 192000:  # More than 192 kHz
            return False
        
        if metadata['channels'] < 1 or metadata['channels'] > 8:
            return False
        
        return True
 
 
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