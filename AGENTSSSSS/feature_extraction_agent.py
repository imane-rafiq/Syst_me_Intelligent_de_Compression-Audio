"""
AGENT 2: FEATURE EXTRACTION AGENT
==================================
 
Responsibility:
- Load audio with librosa
- Extract spectral features (centroid, entropy, bandwidth)
- Extract temporal features (zero crossing rate, energy)
- Detect content type (voice, music, ambient)
 
Simple methods:
1. extract() - Main entry point
2. compute_spectral_features() - FFT analysis
3. compute_temporal_features() - Time domain analysis
4. detect_content_type() - Classify voice/music/ambient
"""
 
import numpy as np
import librosa
import librosa.feature
from typing import Optional, Dict
from pathlib import Path
 
 
class FeatureExtractionAgent:
    """Extract audio features for analysis."""
    
    def __init__(self):
        self.logger = SimpleLogger("FeatureExtractionAgent")
        self.target_sr = 44100  # Standard sample rate
    
    def extract(self, filepath: str) -> Optional[Dict]:
        """
        Extract all features from audio file.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            Dict with features or None if failed
        """
        try:
            # Load audio
            y, sr = librosa.load(filepath, sr=self.target_sr, mono=True)
            
            if len(y) == 0:
                self.logger.error("Empty audio file")
                return None
            
            self.logger.info(f"Loaded: {Path(filepath).name} ({len(y)/sr:.1f}s)")
            
            # Extract features
            spectral = self.compute_spectral_features(y, sr)
            temporal = self.compute_temporal_features(y, sr)
            content_type = self.detect_content_type(y, sr, spectral, temporal)
            
            features = {
                'filepath': filepath,
                **spectral,
                **temporal,
                'content_type': content_type,
            }
            
            self.logger.success(f"Extracted features: {content_type}")
            return features
        
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {str(e)}")
            return None
    
    def compute_spectral_features(self, y: np.ndarray, sr: int) -> Dict:
        """
        Compute spectral (frequency domain) features.
        
        Returns:
            Dict with: centroid, entropy, bandwidth
        """
        # Compute STFT (Short-Time Fourier Transform)
        S = librosa.feature.melspectrogram(y=y, sr=sr)
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # Spectral centroid: where most energy is concentrated
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        centroid_mean = float(np.mean(centroid))
        
        # Spectral entropy: complexity/richness
        # Normalize spectrogram to [0, 1]
        S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min())
        entropy = float(-np.sum(S_norm * np.log2(S_norm + 1e-10)) / S_norm.size)
        
        # Spectral bandwidth: how spread out frequencies are
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        bandwidth_mean = float(np.mean(bandwidth))
        
        return {
            'centroid': round(centroid_mean, 2),
            'entropy': round(entropy, 2),
            'spectral_bandwidth': round(bandwidth_mean, 2),
        }
    
    def compute_temporal_features(self, y: np.ndarray, sr: int) -> Dict:
        """
        Compute temporal (time domain) features.
        
        Returns:
            Dict with: zero_crossing_rate, rms_energy, peak_amplitude
        """
        # Zero crossing rate: how often signal changes sign
        # High ZCR = voice-like (contains high frequencies)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = float(np.mean(zcr))
        
        # RMS energy: loudness/volume
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        
        # Peak amplitude: maximum volume
        peak = float(np.max(np.abs(y)))
        
        return {
            'zero_crossing_rate': round(zcr_mean, 4),
            'rms_energy': round(rms_mean, 4),
            'peak_amplitude': round(peak, 4),
        }
    
    def detect_content_type(self, y: np.ndarray, sr: int, 
                          spectral: Dict, temporal: Dict) -> str:
        """
        Detect if audio is voice, music, or ambient.
        
        Uses simple heuristics:
        - Voice: High ZCR + high centroid
        - Music: Medium ZCR + varied spectrum + high entropy
        - Ambient: Low energy variation + low entropy
        
        Returns:
            String: "voice", "music", or "ambient"
        """
        zcr = temporal['zero_crossing_rate']
        centroid = spectral['centroid']
        entropy = spectral['entropy']
        rms = temporal['rms_energy']
        
        # Heuristics (you can tune these)
        if zcr > 0.1 and centroid > 2000:
            # High ZCR + high centroid = voice
            return "voice"
        
        elif entropy > 4.5 and centroid > 1000:
            # High entropy + mid centroid = music
            return "music"
        
        else:
            # Low entropy + low variation = ambient
            return "ambient"
 
 
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
 