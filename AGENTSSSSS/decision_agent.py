"""
AGENT 3: DECISION AGENT (LLM)
==============================

Responsibility:
- Call Claude API (or GPT/Gemini)
- Analyze audio metadata + features
- Decide best codec and bitrate
- Provide reasoning for the choice

Simple methods:
1. decide() - Main entry point
2. call_llm() - Call Claude API
3. parse_llm_response() - Parse decision from LLM
4. fallback_decision() - Non-LLM heuristic decision
"""

import os
import json
from typing import Optional, Dict
from pathlib import Path


class DecisionAgent:
    """Use LLM to decide compression parameters."""
    
    def __init__(self):
        self.logger = SimpleLogger("DecisionAgent")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
    
    def decide(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """
        Decide compression parameters using LLM.
        
        Args:
            metadata: From Input Agent (duration, sample_rate, channels, etc.)
            features: From Feature Extraction Agent (centroid, entropy, content_type, etc.)
        
        Returns:
            Dict with: codec, bitrate, sample_rate, channels, reasoning
        """
        try:
            # Try LLM decision first
            if self.api_key:
                decision = self.call_llm(metadata, features)
                if decision:
                    return decision
                self.logger.warning("LLM failed, using fallback")
            
            # Fallback to heuristic
            decision = self.fallback_decision(metadata, features)
            return decision
        
        except Exception as e:
            self.logger.error(f"Decision failed: {str(e)}")
            return None
    
    def call_llm(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """
        Call Claude API to make compression decision.
        
        Returns decision or None if API call fails.
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Build prompt
            prompt = self._build_prompt(metadata, features)
            
            self.logger.info("Calling Claude API...")
            
            # Call Claude
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            response_text = message.content[0].text
            self.logger.info(f"Claude response: {response_text[:100]}...")
            
            decision = self.parse_llm_response(response_text)
            return decision
        
        except ImportError:
            self.logger.warning("anthropic library not installed")
            return None
        except Exception as e:
            self.logger.error(f"LLM API call failed: {str(e)}")
            return None
    
    def _build_prompt(self, metadata: Dict, features: Dict) -> str:
        """Build prompt for Claude."""
        
        return f"""You are an expert audio compression engineer.

Analyze this audio and recommend compression parameters.

AUDIO INFORMATION:
- Duration: {metadata['duration']:.1f} seconds
- Sample Rate: {metadata['sample_rate']} Hz
- Channels: {metadata['channels']} (1=mono, 2=stereo)
- Original Size: {metadata['filesize_mb']:.1f} MB
- Codec: {metadata['codec']}

AUDIO ANALYSIS:
- Content Type: {features['content_type']}
- Spectral Centroid: {features['centroid']:.0f} Hz
- Spectral Entropy: {features['entropy']:.2f} (complexity)
- Zero Crossing Rate: {features['zero_crossing_rate']:.4f} (voice indicator)
- RMS Energy: {features['rms_energy']:.4f} (loudness)

DECIDE:
1. Best codec: mp3, aac, opus, ogg, or flac
2. Best bitrate: 32, 48, 64, 96, 128, 192, 256 kbps
3. Keep original sample rate: {metadata['sample_rate']} Hz
4. Channels: {metadata['channels']} or reduce to mono?

RULES:
- Voice: Opus at 32-96 kbps (voice scales down well)
- Music: AAC or MP3 at 128-256 kbps (needs quality)
- Ambient: MP3 at 96-128 kbps (less detail needed)
- Long files: Consider Opus (better compression)
- Stereo music: Keep 2 channels for quality

RESPONSE FORMAT (IMPORTANT - MUST BE VALID JSON):
{{
  "codec": "opus",
  "bitrate": 64,
  "sample_rate": {metadata['sample_rate']},
  "channels": {metadata['channels']},
  "reasoning": "Your explanation in 1-2 sentences"
}}

Only return JSON, no other text."""
    
    def parse_llm_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from LLM response.
        
        Handles LLM that wraps JSON in markdown or text.
        """
        try:
            # Try direct JSON parsing
            decision = json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code block
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
                decision = json.loads(json_str)
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
                decision = json.loads(json_str)
            else:
                # Fallback: try to find JSON object
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    decision = json.loads(json_str)
                else:
                    return None
        
        # Validate required fields
        required = ['codec', 'bitrate', 'sample_rate', 'reasoning']
        if not all(k in decision for k in required):
            return None
        
        # Normalize codec name
        decision['codec'] = decision['codec'].lower()
        
        # Ensure bitrate is int
        decision['bitrate'] = int(decision['bitrate'])
        decision['sample_rate'] = int(decision['sample_rate'])
        
        self.logger.success(f"Parsed decision: {decision['codec']} @ {decision['bitrate']} kbps")
        return decision
    
    def fallback_decision(self, metadata: Dict, features: Dict) -> Dict:
        """
        Make decision without LLM (simple heuristics).
        
        Used when LLM API is unavailable.
        """
        content_type = features['content_type']
        duration = metadata['duration']
        channels = metadata['channels']
        
        # Simple heuristics based on content type
        if content_type == "voice":
            codec = "opus"
            bitrate = 64  # Voice tolerates low bitrate
            reasoning = "Speech content detected. Opus at 64kbps preserves clarity while reducing file size significantly."
        
        elif content_type == "music":
            codec = "aac"
            bitrate = 192 if channels == 2 else 128  # Music needs quality
            reasoning = "Musical content detected. AAC at 192kbps (stereo) provides good quality-to-size ratio."
        
        else:  # ambient
            codec = "mp3"
            bitrate = 128
            reasoning = "Ambient sound detected. MP3 at 128kbps is sufficient for background audio."
        
        # Reduce bitrate for very long files
        if duration > 3600:  # More than 1 hour
            bitrate = max(32, bitrate - 32)
            reasoning += " File is long, reducing bitrate to save space."
        
        return {
            'codec': codec,
            'bitrate': bitrate,
            'sample_rate': metadata['sample_rate'],
            'channels': channels,
            'reasoning': reasoning
        }


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