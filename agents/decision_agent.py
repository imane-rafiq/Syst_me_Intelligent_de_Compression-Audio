import json
import os
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


class SimpleLogger:
    def __init__(self, name: str):
        self.name = name

    def info(self, msg: str):
        print(f"[{self.name}] {msg}")

    def success(self, msg: str):
        print(f"[{self.name}] SUCCESS: {msg}")

    def warning(self, msg: str):
        print(f"[{self.name}] WARNING: {msg}")

    def error(self, msg: str):
        print(f"[{self.name}] ERROR: {msg}")


class DecisionAgent:
    """
    Enhanced Decision Agent with 3 main functionalities:
    1. Audio Compression - Decide optimal codec/bitrate
    2. Audio Transcription - Convert audio to text
    3. Text-to-Speech - Convert text to audio
    """

    ALLOWED_CODECS = {"mp3", "aac", "opus", "ogg", "flac"}
    ALLOWED_BITRATES = {32, 48, 64, 96, 128, 192, 256}

    def __init__(self):
        self.logger = SimpleLogger("DecisionAgent")

        # Try multiple API key environment variables
        self.api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )

        if self.api_key:
            self.logger.success("API key loaded")
        else:
            self.logger.warning("No API key found, fallback will be used")

    # ========================================================================
    # FUNCTIONALITY 1: AUDIO COMPRESSION DECISION
    # ========================================================================

    def decide(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """
        Decide compression parameters based on audio analysis.
        Used by: Compress Audio button
        """
        try:
            if self.api_key:
                self.logger.info("Making compression decision with Claude...")
                llm_decision = self.call_llm_compression(metadata, features)
                if llm_decision is not None:
                    return llm_decision
                self.logger.warning("LLM compression failed, using fallback")
            else:
                self.logger.warning("No API key, using fallback compression")

            return self.fallback_decision(metadata, features)

        except Exception as e:
            self.logger.error(f"Compression decision failed: {e}")
            return None

    def call_llm_compression(self, metadata: Dict, features: Dict) -> Optional[Dict]:
        """Call Claude for compression decision."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            prompt = self._build_compression_prompt(metadata, features)

            self.logger.info("Calling Claude for compression decision...")

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            self.logger.info("Claude compression response received")
            parsed = self.parse_compression_response(response_text)

            if parsed is not None:
                self.logger.success(
                    f"Compression decision: {parsed['codec']} @ {parsed['bitrate']} kbps"
                )

            return parsed

        except ImportError:
            self.logger.error("anthropic package not installed")
            return None
        except Exception as e:
            self.logger.error(f"LLM compression call failed: {e}")
            return None

    def _build_compression_prompt(self, metadata: Dict, features: Dict) -> str:
        """Build prompt for compression decision."""
        return f"""
You are an expert audio compression engineer.

Audio Information:
{json.dumps(metadata, indent=2)}

Audio Features:
{json.dumps(features, indent=2)}

Analyze this audio and decide the best compression parameters.

Guidelines:
- Voice/Speech: Prefer Opus codec, 32-96 kbps, mono allowed
- Music: Prefer AAC or MP3, 128-256 kbps, maintain stereo
- Ambient/Nature: MP3 or OGG, 96-128 kbps
- Mixed content: AAC at 128 kbps as balanced choice
- High-quality requirement: Consider FLAC (lossless)

Return ONLY valid JSON (no explanation):
{{
    "codec": "opus|aac|mp3|ogg|flac",
    "bitrate": 32|48|64|96|128|192|256,
    "sample_rate": {metadata.get('sample_rate', 44100)},
    "channels": 1|2,
    "reasoning": "brief explanation of why these parameters were chosen"
}}
""".strip()

    def parse_compression_response(self, response_text: str) -> Optional[Dict]:
        """Parse compression decision response from Claude."""
        try:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    # Try to find JSON object
                    start = response_text.find("{")
                    end = response_text.rfind("}")
                    if start == -1 or end == -1 or end <= start:
                        self.logger.error("No JSON found in compression response")
                        return None
                    json_str = response_text[start : end + 1]

                data = json.loads(json_str)

            # Validate required fields
            required = ["codec", "bitrate", "sample_rate", "reasoning"]
            if not all(key in data for key in required):
                self.logger.error("Missing required keys in compression response")
                return None

            # Validate codec
            codec = str(data["codec"]).lower().strip()
            if codec not in self.ALLOWED_CODECS:
                self.logger.error(f"Invalid codec: {codec}")
                return None

            # Normalize bitrate
            bitrate = int(data["bitrate"])
            if bitrate not in self.ALLOWED_BITRATES:
                bitrate = min(self.ALLOWED_BITRATES, key=lambda x: abs(x - bitrate))
                self.logger.info(f"Adjusted bitrate to {bitrate}")

            sample_rate = int(data["sample_rate"])
            channels = int(data.get("channels", 2))
            channels = 1 if channels == 1 else 2

            return {
                "codec": codec,
                "bitrate": bitrate,
                "sample_rate": sample_rate,
                "channels": channels,
                "reasoning": str(data["reasoning"]).strip(),
            }

        except Exception as e:
            self.logger.error(f"Compression parsing failed: {e}")
            return None

    def fallback_decision(self, metadata: Dict, features: Dict) -> Dict:
        """Fallback compression decision without LLM."""
        content_type = features.get("content_type", "ambient")
        duration = metadata.get("duration", 0)
        original_channels = metadata.get("channels", 2)
        sample_rate = metadata.get("sample_rate", 44100)

        if content_type == "voice":
            codec = "opus"
            bitrate = 48 if duration > 1800 else 64
            channels = 1
            reasoning = "Voice detected. Opus codec with mono compression maintains intelligibility while saving space."

        elif content_type == "music":
            codec = "aac"
            bitrate = 192 if original_channels >= 2 else 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = "Music detected. AAC codec at higher bitrate preserves musical detail and quality."

        elif content_type == "mixed":
            codec = "aac"
            bitrate = 128
            channels = 2 if original_channels >= 2 else 1
            reasoning = "Mixed content detected. AAC at 128 kbps provides balanced compression."

        else:
            codec = "mp3"
            bitrate = 96
            channels = 1 if original_channels == 1 else 2
            reasoning = "Ambient content detected. MP3 provides good compression for this type."

        # Reduce bitrate for very long files
        if duration > 3600 and codec != "flac":
            bitrate = max(32, bitrate - 32)
            reasoning += " Long duration detected, bitrate reduced to save storage."

        return {
            "codec": codec,
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "channels": channels,
            "reasoning": reasoning,
        }

    # ========================================================================
    # FUNCTIONALITY 2: AUDIO TRANSCRIPTION (Audio to Text)
    # ========================================================================

    def transcribe(self, metadata: Dict, features: Dict, audio_path: Optional[str] = None) -> Optional[Dict]:
        """
        Transcribe audio to text.
        Used by: Audio to Text button
        
        Args:
            metadata: Audio metadata from InputAgent
            features: Audio features from FeatureExtractionAgent
            audio_path: Path to audio file (optional, for future speech-to-text services)
        
        Returns:
            Dictionary with transcribed text and metadata
        """
        try:
            if audio_path:
                self.logger.info("Starting actual transcription with Deepgram...")
                transcription = self.call_deepgram_transcription(audio_path, metadata)
                if transcription is not None:
                    return transcription
                self.logger.warning("LLM transcription failed, using fallback")
            else:
                self.logger.warning("No API key, using fallback transcription")

            return self.fallback_transcription(metadata)

        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return None

    def call_deepgram_transcription(self, audio_path: str, metadata: Dict) -> Optional[Dict]:
        """
        Call Deepgram API for actual speech-to-text transcription.
        """
        try:
            import requests

            # Deepgram token provided by user
            deepgram_token = "1a3e0ba20571682c1b896f5e56cd78b566f73cbe"
            
            # Using REST API endpoint for pre-recorded local files
            endpoint = "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true"
            
            headers = {
                "Authorization": f"Token {deepgram_token}",
                "Content-Type": "audio/*" # Auto-detects codec
            }

            self.logger.info("Sending audio to Deepgram REST API...")

            with open(audio_path, "rb") as f:
                response = requests.post(endpoint, headers=headers, data=f, timeout=300)

            if response.status_code != 200:
                self.logger.error(f"Deepgram API error: {response.text}")
                return None

            data = response.json()
            
            # Extract transcript from Deepgram structure
            results = data.get("results", {})
            channels = results.get("channels", [{}])
            if not channels:
                self.logger.error("No channels returned from Deepgram")
                return None
                
            alternatives = channels[0].get("alternatives", [{}])
            transcript_text = alternatives[0].get("transcript", "")
            confidence = alternatives[0].get("confidence", 0.0)

            self.logger.success("Deepgram transcription received successfully")

            return {
                "transcription": {
                    "text": transcript_text if transcript_text else "[No speech detected]",
                    "confidence": confidence,
                    "language": "en",
                },
                "analysis": {
                    "content_type": "speech",
                    "difficulty": "easy",
                    "analysis": "Transcribed successfully via Deepgram Nova-3 model.",
                },
                "metadata": {
                    "duration": metadata.get("duration", 0),
                    "sample_rate": metadata.get("sample_rate", 0),
                    "channels": metadata.get("channels", 0),
                },
            }

        except Exception as e:
            self.logger.error(f"Deepgram transcription call failed: {e}")
            return None

    def _build_transcription_prompt(self, metadata: Dict, features: Dict) -> str:
        """Build prompt for transcription analysis."""
        return f"""
You are analyzing audio for transcription. Based on the audio characteristics below, 
provide transcription guidance and an analysis of what the audio contains.

Audio Metadata:
- Duration: {metadata.get('duration', 0):.2f} seconds
- Sample Rate: {metadata.get('sample_rate', 0)} Hz
- Channels: {metadata.get('channels', 0)} ({'Mono' if metadata.get('channels') == 1 else 'Stereo'})
- Format: {metadata.get('codec', 'unknown')}

Audio Features:
- Content Type: {features.get('content_type', 'unknown')}
- Spectral Centroid: {features.get('centroid', 0):.0f} Hz
- Spectral Entropy: {features.get('entropy', 0):.2f}
- Zero Crossing Rate: {features.get('zero_crossing_rate', 0):.4f}
- RMS Energy: {features.get('rms_energy', 0):.4f}

Based on these characteristics, provide:
1. Analysis of the audio content (what type of audio this is)
2. Expected transcription difficulty (easy/moderate/difficult)
3. Recommended transcription approach
4. A placeholder transcription for demonstration

Return ONLY valid JSON:
{{
    "text": "Transcribed audio content here...",
    "confidence": 0.85,
    "language": "en",
    "analysis": "Brief analysis of audio content",
    "difficulty": "easy|moderate|difficult",
    "content_type": "speech|music|mixed|other"
}}
""".strip()

    def _parse_transcription_response(self, response_text: str, metadata: Dict) -> Optional[Dict]:
        """Parse transcription response from Claude."""
        try:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON
                if "```json" in response_text:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    start = response_text.find("{")
                    end = response_text.rfind("}")
                    if start == -1 or end == -1:
                        self.logger.error("No JSON found in transcription response")
                        return None
                    json_str = response_text[start : end + 1]

                data = json.loads(json_str)

            # Extract transcription text
            transcription_text = data.get("text", "")
            if not transcription_text:
                self.logger.error("No transcription text in response")
                return None

            self.logger.success("Transcription parsed successfully")

            return {
                "transcription": {
                    "text": transcription_text,
                    "confidence": data.get("confidence", 0.85),
                    "language": data.get("language", "en"),
                },
                "analysis": {
                    "content_type": data.get("content_type", "unknown"),
                    "difficulty": data.get("difficulty", "moderate"),
                    "analysis": data.get("analysis", ""),
                },
                "metadata": {
                    "duration": metadata.get("duration", 0),
                    "sample_rate": metadata.get("sample_rate", 0),
                    "channels": metadata.get("channels", 0),
                },
            }

        except Exception as e:
            self.logger.error(f"Transcription parsing failed: {e}")
            return None

    def fallback_transcription(self, metadata: Dict) -> Dict:
        """Fallback transcription response."""
        duration = metadata.get("duration", 0)
        
        # Generate placeholder text based on duration
        if duration < 5:
            text = "Short audio clip detected. Please use Speech-to-Text service for accurate transcription."
        elif duration < 60:
            text = "Short audio content. Transcription service available through API integration."
        else:
            text = "Longer audio file. Consider breaking into segments for better transcription accuracy."

        return {
            "transcription": {
                "text": text,
                "confidence": 0,
                "language": "unknown",
            },
            "analysis": {
                "content_type": "unknown",
                "difficulty": "unknown",
                "analysis": "No API key available for transcription. Please configure Speech-to-Text service.",
            },
            "metadata": {
                "duration": metadata.get("duration", 0),
                "sample_rate": metadata.get("sample_rate", 0),
                "channels": metadata.get("channels", 0),
            },
        }

    # ========================================================================
    # FUNCTIONALITY 3: TEXT-TO-SPEECH (Text to Audio)
    # ========================================================================

    def synthesize(self, text: str, voice_params: Dict) -> Optional[Dict]:
        """
        Convert text to audio (Text-to-Speech synthesis).
        Used by: Text to Audio button
        
        Args:
            text: Text to convert to audio
            voice_params: Dictionary with voice parameters
                - voice_id: "male" | "female"
                - language: "en" | "fr" | "es" | etc.
                - speed: 0.5 to 2.0 (1.0 = normal)
                - pitch: 0.5 to 2.0 (1.0 = normal)
        
        Returns:
            Dictionary with synthesis parameters and audio metadata
        """
        try:
            if self.api_key:
                self.logger.info("Starting text-to-speech synthesis...")
                synthesis = self.call_llm_synthesis(text, voice_params)
                if synthesis is not None:
                    return synthesis
                self.logger.warning("LLM synthesis failed, using fallback")
            else:
                self.logger.warning("No API key, using fallback synthesis")

            return self.fallback_synthesis(text, voice_params)

        except Exception as e:
            self.logger.error(f"Text-to-speech synthesis failed: {e}")
            return None

    def call_llm_synthesis(self, text: str, voice_params: Dict) -> Optional[Dict]:
        """
        Call Claude for text-to-speech synthesis guidance.
        
        Note: This is a placeholder for actual synthesis.
        In production, you would use:
        - Google Cloud Text-to-Speech
        - Azure Text-to-Speech
        - OpenAI TTS
        - ElevenLabs
        - AWS Polly
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = self._build_synthesis_prompt(text, voice_params)

            self.logger.info("Calling Claude for synthesis guidance...")

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            self.logger.success("Claude synthesis response received")

            return self._parse_synthesis_response(response_text, text, voice_params)

        except Exception as e:
            self.logger.error(f"LLM synthesis call failed: {e}")
            return None

    def _build_synthesis_prompt(self, text: str, voice_params: Dict) -> str:
        """Build prompt for text-to-speech synthesis."""
        voice_id = voice_params.get("voice_id", "female")
        language = voice_params.get("language", "en")
        speed = voice_params.get("speed", 1.0)
        pitch = voice_params.get("pitch", 1.0)

        return f"""
You are analyzing text for speech synthesis. Provide guidance on how to synthesize this text to audio.

Text to synthesize:
"{text}"

Voice Parameters:
- Voice: {voice_id}
- Language: {language}
- Speed: {speed}x (1.0 = normal)
- Pitch: {pitch}x (1.0 = normal)

Analyze this text and provide synthesis recommendations:

Return ONLY valid JSON:
{{
    "synthesis_params": {{
        "voice": "{voice_id}",
        "language": "{language}",
        "speed": {speed},
        "pitch": {pitch},
        "tone": "professional|casual|friendly|etc"
    }},
    "estimated_duration": 5.5,
    "word_count": {len(text.split())},
    "analysis": "Brief analysis of the text for synthesis",
    "notes": "Any special pronunciation or emphasis notes"
}}
""".strip()

    def _parse_synthesis_response(self, response_text: str, text: str, voice_params: Dict) -> Optional[Dict]:
        """Parse synthesis response from Claude."""
        try:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON
                if "```json" in response_text:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    start = response_text.find("{")
                    end = response_text.rfind("}")
                    if start == -1 or end == -1:
                        self.logger.error("No JSON found in synthesis response")
                        return None
                    json_str = response_text[start : end + 1]

                data = json.loads(json_str)

            self.logger.success("Synthesis parameters parsed successfully")

            return {
                "synthesis_params": data.get("synthesis_params", voice_params),
                "estimated_duration": data.get("estimated_duration", 0),
                "word_count": data.get("word_count", len(text.split())),
                "analysis": data.get("analysis", ""),
                "notes": data.get("notes", ""),
                "text_input": {
                    "text": text,
                    "length": len(text),
                    "word_count": len(text.split()),
                },
                "status": "ready_for_synthesis",
            }

        except Exception as e:
            self.logger.error(f"Synthesis parsing failed: {e}")
            return None

    def fallback_synthesis(self, text: str, voice_params: Dict) -> Dict:
        """Fallback text-to-speech synthesis response."""
        word_count = len(text.split())
        estimated_duration = word_count * 0.5  # Rough estimate: ~0.5s per word

        return {
            "synthesis_params": voice_params,
            "estimated_duration": estimated_duration,
            "word_count": word_count,
            "analysis": "No TTS API configured. Text-to-Speech requires integration with a TTS service.",
            "notes": "Please configure a TTS service (Google Cloud, Azure, ElevenLabs, AWS Polly, etc.)",
            "text_input": {
                "text": text,
                "length": len(text),
                "word_count": word_count,
            },
            "status": "requires_tts_service",
        }