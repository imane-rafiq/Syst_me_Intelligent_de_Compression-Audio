import json
import os
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


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


class DecisionAgent:
    ALLOWED_CODECS = {"mp3", "aac", "opus", "ogg", "flac"}
    ALLOWED_BITRATES = {32, 48, 64, 96, 128, 192, 256}

    def __init__(self):
        self.logger = SimpleLogger("DecisionAgent")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if self.api_key:
            self.logger.success("ANTHROPIC_API_KEY loaded")
        else:
            self.logger.warning("ANTHROPIC_API_KEY not found")

    def decide(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        try:
            if self.api_key:
                self.logger.info("Trying LLM decision...")
                llm_decision = self.call_llm(metadata, features)
                if llm_decision is not None:
                    return llm_decision
                self.logger.warning("LLM call failed, fallback activated")
            else:
                self.logger.warning("No API key found, fallback activated")

            return self.fallback_decision(metadata, features)

        except Exception as e:
            self.logger.error(f"Decision failed: {e}")
            return None

    def call_llm(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = self._build_prompt(metadata, features)

            self.logger.info("Calling Claude API...")

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            response_text = response.content[0].text
            self.logger.info(f"Claude raw response: {response_text[:120]}...")
            parsed = self.parse_llm_response(response_text)

            if parsed is not None:
                self.logger.success(
                    f"LLM decision parsed: {parsed['codec']} / {parsed['bitrate_kbps']} kbps"
                )

            return parsed

        except ImportError:
            self.logger.error("anthropic package not installed")
            return None
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return None

    def _build_prompt(self, metadata: Dict, features: Dict) -> str:
        return f"""
You are an audio compression decision agent.

Input metadata:
{json.dumps(metadata, indent=2)}

Input features:
{json.dumps(features, indent=2)}

Choose the best compression parameters.

Rules:
- voice: prefer opus, 32 to 96 kbps, mono allowed
- music: prefer aac or mp3, 128 to 256 kbps
- ambient: moderate bitrate is acceptable
- mixed: choose a balanced compromise
- flac only if preserving quality matters more than size

Return ONLY valid JSON with this schema:
{{
  "codec": "opus",
  "bitrate_kbps": 64,
  "sample_rate_hz": 16000,
  "channels": 1,
  "reasoning": "short explanation"
}}
""".strip()

    def parse_llm_response(self, response_text: str) -> Optional[Dict]:
        try:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    start = response_text.find("{")
                    end = response_text.rfind("}")
                    if start == -1 or end == -1 or end <= start:
                        self.logger.error("No valid JSON found in LLM response")
                        return None
                    json_str = response_text[start:end + 1]

                data = json.loads(json_str)

            required = ["codec", "bitrate_kbps", "sample_rate_hz", "reasoning"]
            if not all(key in data for key in required):
                self.logger.error("Missing required keys in LLM response")
                return None

            codec = str(data["codec"]).lower().strip()
            if codec not in self.ALLOWED_CODECS:
                self.logger.error(f"Unsupported codec returned by LLM: {codec}")
                return None

            bitrate_kbps = int(data["bitrate_kbps"])
            if bitrate_kbps not in self.ALLOWED_BITRATES:
                bitrate_kbps = min(self.ALLOWED_BITRATES, key=lambda x: abs(x - bitrate_kbps))

            sample_rate_hz = int(data["sample_rate_hz"])
            channels = int(data.get("channels", 2))
            channels = 1 if channels == 1 else 2

            return {
                "codec": codec,
                "bitrate_kbps": bitrate_kbps,
                "sample_rate_hz": sample_rate_hz,
                "channels": channels,
                "reasoning": str(data["reasoning"]).strip(),
                "decision_source": "llm",
            }

        except Exception as e:
            self.logger.error(f"Parse failed: {e}")
            return None

    def fallback_decision(self, metadata: Dict, features: Dict) -> Dict:
        content_type = features.get("content_type", "ambient")
        duration_sec = metadata.get("duration_sec", 0)
        original_channels = metadata.get("channels", 2)
        sample_rate_hz = metadata.get("sample_rate_hz", 44100)

        if content_type == "voice":
            codec = "opus"
            bitrate_kbps = 48 if duration_sec > 1800 else 64
            channels = 1
            reasoning = (
                "Voice detected. Opus with mono gives strong compression while keeping speech intelligible."
            )

        elif content_type == "music":
            codec = "aac"
            bitrate_kbps = 192 if original_channels >= 2 else 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = "Music detected. AAC at higher bitrate preserves more musical detail."

        elif content_type == "mixed":
            codec = "aac"
            bitrate_kbps = 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = "Mixed content detected. AAC at 128 kbps is a balanced compromise."

        else:
            codec = "mp3"
            bitrate_kbps = 96
            channels = 1 if original_channels == 1 else 2
            reasoning = "Ambient content detected. Moderate bitrate is usually enough."

        if duration_sec > 3600 and codec != "flac":
            bitrate_kbps = max(32, bitrate_kbps - 32)
            reasoning += " Long duration detected, so bitrate was reduced to save space."

        return {
            "codec": codec,
            "bitrate_kbps": bitrate_kbps,
            "sample_rate_hz": sample_rate_hz,
            "channels": channels,
            "reasoning": reasoning,
            "decision_source": "fallback",
        }