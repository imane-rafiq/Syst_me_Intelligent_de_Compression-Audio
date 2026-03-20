"""
AGENT 3: DECISION AGENT (LLM)
=============================

Responsibility:
- Call Claude API (or another LLM)
- Analyze audio metadata + features
- Decide best codec and bitrate
- Provide reasoning for the choice

Simple methods:
1. decide() - Main entry point
2. call_llm() - Call Claude API
3. parse_llm_response() - Parse decision from LLM
4. fallback_decision() - Non-LLM heuristic decision
"""

import json
import os
from typing import Dict, Optional


class DecisionAgent:
    """Use LLM to decide compression parameters."""

    ALLOWED_CODECS = {"mp3", "aac", "opus", "ogg", "flac"}
    ALLOWED_BITRATES = {32, 48, 64, 96, 128, 192, 256}

    def __init__(self):
        self.logger = SimpleLogger("DecisionAgent")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def decide(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """
        Decide compression parameters using LLM or fallback.

        Returns:
            Dict with:
            - codec
            - bitrate_kbps
            - sample_rate_hz
            - channels
            - reasoning
            - decision_source
        """
        try:
            if self.api_key:
                decision = self.call_llm(metadata, features)
                if decision:
                    return decision
                self.logger.warning("LLM failed, using fallback")

            return self.fallback_decision(metadata, features)

        except Exception as e:
            self.logger.error(f"Decision failed: {str(e)}")
            return None

    def call_llm(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """Call Claude API to make compression decision."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = self._build_prompt(metadata, features)

            self.logger.info("Calling Claude API...")

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            self.logger.info(f"Claude response: {response_text[:100]}...")

            return self.parse_llm_response(response_text)

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
- Duration: {metadata['duration_sec']:.1f} seconds
- Sample Rate: {metadata['sample_rate_hz']} Hz
- Channels: {metadata['channels']} (1=mono, 2=stereo)
- Original Size: {metadata['file_size_mb']:.1f} MB
- Codec: {metadata['codec']}
- Bit Depth: {metadata.get('bit_depth')}

AUDIO ANALYSIS:
- Content Type: {features['content_type']}
- Spectral Centroid: {features['centroid']:.0f} Hz
- Spectral Entropy: {features['entropy']:.2f}
- Spectral Bandwidth: {features['spectral_bandwidth']:.0f} Hz
- Zero Crossing Rate: {features['zero_crossing_rate']:.4f}
- RMS Energy: {features['rms_energy']:.4f}

DECIDE:
1. Best codec: mp3, aac, opus, ogg, or flac
2. Best bitrate_kbps: 32, 48, 64, 96, 128, 192, 256
3. Sample rate to use
4. Channels: keep stereo or reduce to mono
5. Short reasoning

RULES:
- Voice: prefer Opus at 32-96 kbps
- Music: prefer AAC/MP3 at 128-256 kbps
- Ambient: prefer MP3/AAC at 96-128 kbps
- Long voice recordings: prefer mono and lower bitrate
- Classical/high-detail music: FLAC is acceptable
- Mixed content: choose a balanced compromise

RESPONSE FORMAT (MUST BE VALID JSON):
{{
  "codec": "opus",
  "bitrate_kbps": 64,
  "sample_rate_hz": {metadata['sample_rate_hz']},
  "channels": {metadata['channels']},
  "reasoning": "Your explanation in 1-2 sentences"
}}

Only return JSON, no extra text.
"""

    def parse_llm_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from LLM response.
        Handles markdown-wrapped JSON too.
        """
        try:
            decision = json.loads(response_text)
        except json.JSONDecodeError:
            try:
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    if start < 0 or end <= start:
                        return None
                    json_str = response_text[start:end]
                decision = json.loads(json_str)
            except Exception:
                return None

        required = ["codec", "bitrate_kbps", "sample_rate_hz", "reasoning"]
        if not all(k in decision for k in required):
            return None

        codec = str(decision["codec"]).lower().strip()
        if codec not in self.ALLOWED_CODECS:
            return None

        bitrate_kbps = int(decision["bitrate_kbps"])
        if bitrate_kbps not in self.ALLOWED_BITRATES:
            bitrate_kbps = min(self.ALLOWED_BITRATES, key=lambda x: abs(x - bitrate_kbps))

        sample_rate_hz = int(decision["sample_rate_hz"])
        channels = int(decision.get("channels", 2))
        channels = 1 if channels == 1 else 2

        parsed = {
            "codec": codec,
            "bitrate_kbps": bitrate_kbps,
            "sample_rate_hz": sample_rate_hz,
            "channels": channels,
            "reasoning": str(decision["reasoning"]).strip(),
            "decision_source": "llm",
        }

        self.logger.success(
            f"Parsed decision: {parsed['codec']} @ {parsed['bitrate_kbps']} kbps"
        )
        return parsed

    def fallback_decision(self, metadata: Dict, features: Dict) -> Dict:
        """
        Make decision without LLM using simple heuristics.
        """
        content_type = features["content_type"]
        duration_sec = metadata["duration_sec"]
        original_channels = metadata["channels"]
        sample_rate_hz = metadata["sample_rate_hz"]

        if content_type == "voice":
            codec = "opus"
            bitrate_kbps = 48 if duration_sec > 3600 else 64
            channels = 1
            reasoning = (
                "Speech content detected. Opus with mono compression preserves intelligibility "
                "while reducing size efficiently."
            )

        elif content_type == "music":
            codec = "aac"
            bitrate_kbps = 192 if original_channels == 2 else 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = (
                "Music content detected. AAC at medium-high bitrate gives a good balance "
                "between fidelity and compression."
            )

        elif content_type == "mixed":
            codec = "aac"
            bitrate_kbps = 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = (
                "Mixed content detected. AAC at 128 kbps provides a balanced compromise "
                "for both speech and richer sound elements."
            )

        else:  # ambient
            codec = "mp3"
            bitrate_kbps = 128
            channels = 1 if original_channels == 1 else 2
            reasoning = (
                "Ambient sound detected. MP3 at moderate bitrate is usually sufficient "
                "for non-critical background audio."
            )

        if duration_sec > 3600 and codec != "flac":
            bitrate_kbps = max(32, bitrate_kbps - 32)
            reasoning += " File is long, so bitrate was reduced to save more storage."

        return {
            "codec": codec,
            "bitrate_kbps": bitrate_kbps,
            "sample_rate_hz": sample_rate_hz,
            "channels": channels,
            "reasoning": reasoning,
            "decision_source": "fallback",
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