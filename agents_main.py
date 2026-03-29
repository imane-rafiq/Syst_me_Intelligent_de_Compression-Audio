"""
Main FastAPI application that serves all 5 agents.
Each agent is an independent endpoint.
 
Run with:
    uvicorn agents_main:app --reload --port 8000
 
Then test with:
    curl -X POST http://localhost:8000/input/load \
      -H "Content-Type: application/json" \
      -d '{"filepath": "/path/to/audio.wav"}'
"""
 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path
import os
from dotenv import load_dotenv
 
# Load environment variables
load_dotenv()
 
# Initialize FastAPI app
app = FastAPI(
    title="Audio Compression Multi-Agent System",
    description="5 independent agents for intelligent audio compression",
    version="1.0.0"
)
 
# Create directories
DATA_DIR = Path("./data")
MANIFEST_DIR = DATA_DIR / "manifests"
OUTPUTS_DIR = DATA_DIR / "outputs"
AUDIO_DIR = DATA_DIR / "audio_files"
 
for d in [DATA_DIR, MANIFEST_DIR, OUTPUTS_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)
 
 
# ============================================================================
# AGENT 1: INPUT AGENT - Load and validate audio files
# ============================================================================
 
class LoadAudioRequest(BaseModel):
    filepath: str
 
class AudioMetadata(BaseModel):
    filepath: str
    filename: str
    duration: float
    sample_rate: int
    channels: int
    codec: str
    filesize_bytes: int
    filesize_mb: float
 
@app.post("/input/load", response_model=AudioMetadata, tags=["Input Agent"])
async def input_load(request: LoadAudioRequest):
    """
    Agent 1: INPUT AGENT
    
    Responsibility:
    - Load audio file
    - Extract metadata (duration, sample rate, channels, codec)
    - Validate file exists and is readable
    
    Input: {"filepath": "/path/to/audio.wav"}
    Output: Metadata dict with duration, sample_rate, channels, etc.
    """
    try:
        from agents.input_agent import InputAgent
        
        agent = InputAgent()
        metadata = agent.load_and_validate(request.filepath)
        
        if not metadata:
            raise HTTPException(status_code=400, detail="Invalid or unsupported audio file")
        
        # Save metadata to manifest for next agents
        manifest_file = MANIFEST_DIR / "metadata.json"
        with open(manifest_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading audio: {str(e)}")
 
 
# ============================================================================
# AGENT 2: FEATURE EXTRACTION AGENT - Analyze audio characteristics
# ============================================================================
 
class ExtractFeaturesRequest(BaseModel):
    filepath: str
 
class AudioFeatures(BaseModel):
    filepath: str
    centroid: float
    entropy: float
    zero_crossing_rate: float
    rms_energy: float
    spectral_bandwidth: float
    content_type: str  # "voice", "music", "ambient"
    peak_amplitude: float
 
@app.post("/features/extract", response_model=AudioFeatures, tags=["Feature Extraction"])
async def features_extract(request: ExtractFeaturesRequest):
    """
    Agent 2: FEATURE EXTRACTION AGENT
    
    Responsibility:
    - Extract spectral features (centroid, entropy, bandwidth)
    - Extract temporal features (zero crossing rate, energy)
    - Detect content type (voice, music, ambient)
    
    Input: {"filepath": "/path/to/audio.wav"}
    Output: Features dict with spectral/temporal analysis
    """
    try:
        from agents.feature_extraction_agent import FeatureExtractionAgent
        
        agent = FeatureExtractionAgent()
        features = agent.extract(request.filepath)
        
        if not features:
            raise HTTPException(status_code=400, detail="Failed to extract features")
        
        # Save features
        features_file = MANIFEST_DIR / "features.json"
        with open(features_file, 'w') as f:
            json.dump(features, f, indent=2)
        
        return features
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting features: {str(e)}")
 
 
# ============================================================================
# AGENT 3: DECISION AGENT - LLM decides compression parameters
# ============================================================================
 
class DecideCompressionRequest(BaseModel):
    filepath: str
    metadata: Optional[dict] = None
    features: Optional[dict] = None
 
class CompressionDecision(BaseModel):
    codec: str              # "mp3", "aac", "opus", "ogg", "flac"
    bitrate: int           # in kbps
    sample_rate: int       # Hz
    channels: int          # 1 (mono) or 2 (stereo)
    reasoning: str         # Why LLM made this choice
 
@app.post("/decision/decide", response_model=CompressionDecision, tags=["Decision Agent"])
async def decision_decide(request: DecideCompressionRequest):
    """
    Agent 3: DECISION AGENT (LLM)
    
    Responsibility:
    - Call Claude/GPT API
    - Analyze features + metadata
    - Decide best codec and bitrate
    - Provide reasoning
    
    Input: {"filepath": "...", "metadata": {...}, "features": {...}}
    Output: Decision dict with codec, bitrate, reasoning
    """
    try:
        from agents.decision_agent import DecisionAgent
        
        # Load metadata and features if not provided
        if request.metadata is None:
            try:
                with open(MANIFEST_DIR / "metadata.json") as f:
                    request.metadata = json.load(f)
            except:
                raise HTTPException(status_code=400, detail="Metadata not found. Run input/load first.")
        
        if request.features is None:
            try:
                with open(MANIFEST_DIR / "features.json") as f:
                    request.features = json.load(f)
            except:
                raise HTTPException(status_code=400, detail="Features not found. Run features/extract first.")
        
        agent = DecisionAgent()
        decision = agent.decide(request.metadata, request.features)
        
        if not decision:
            raise HTTPException(status_code=500, detail="LLM decision failed")
        
        # Save decision
        decision_file = MANIFEST_DIR / "decision.json"
        with open(decision_file, 'w') as f:
            json.dump(decision, f, indent=2)
        
        return decision
    
    except HTTPException:
        raise
    except Exception as e:
        print("DECISION ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=f"Error making decision: {str(e)}")
 
 
# ============================================================================
# AGENT 4: EXECUTION AGENT - Compress audio with FFmpeg
# ============================================================================
 
class ExecuteCompressionRequest(BaseModel):
    filepath: str
    codec: str
    bitrate: int
    sample_rate: int
    channels: int = 2
 
class CompressionResult(BaseModel):
    output_filepath: str
    output_filename: str
    compressed_size: int
    original_size: int
    compression_ratio: float
 
@app.post("/execution/compress", response_model=CompressionResult, tags=["Execution Agent"])
async def execution_compress(request: ExecuteCompressionRequest):
    """
    Agent 4: EXECUTION AGENT
    
    Responsibility:
    - Call FFmpeg to compress audio
    - Apply codec, bitrate, sample rate
    - Save compressed file
    
    Input: {"filepath": "...", "codec": "opus", "bitrate": 64, ...}
    Output: Path to compressed file + file sizes
    """
    try:
        from agents.execution_agent import ExecutionAgent
        
        agent = ExecutionAgent()
        result = agent.compress(
            request.filepath,
            request.codec,
            request.bitrate,
            request.sample_rate,
            request.channels
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Compression failed")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error compressing audio: {str(e)}")
 
 
# ============================================================================
# AGENT 5: REPORT AGENT - Calculate quality metrics
# ============================================================================
 
class GenerateReportRequest(BaseModel):
    original_filepath: str
    compressed_filepath: str
 
class CompressionReport(BaseModel):
    filename: str
    duration: float
    compression_ratio: float
    original_size_mb: float
    compressed_size_mb: float
    snr_db: Optional[float]
    bitrate_kbps: int
    codec: str
    report_file: str
 
@app.post("/report/generate", response_model=CompressionReport, tags=["Report Agent"])
async def report_generate(request: GenerateReportRequest):
    """
    Agent 5: REPORT AGENT
    
    Responsibility:
    - Calculate quality metrics (SNR, compression ratio)
    - Generate final report
    - Save report to JSON
    
    Input: {"original_filepath": "...", "compressed_filepath": "..."}
    Output: Report with metrics + path to report file
    """
    try:
        from agents.report_agent import ReportAgent
        
        agent = ReportAgent()
        report = agent.generate(
            request.original_filepath,
            request.compressed_filepath
        )
        
        if not report:
            raise HTTPException(status_code=500, detail="Report generation failed")
        
        # Save report
        report_file = OUTPUTS_DIR / f"{Path(request.original_filepath).stem}_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
 
 
# ============================================================================
# HEALTH CHECK & INFO
# ============================================================================
 
@app.get("/health", tags=["System"])
def health_check():
    """Check if all services are running."""
    return {
        "status": "ok",
        "service": "Audio Compression Multi-Agent System",
        "agents": ["Input", "FeatureExtraction", "Decision", "Execution", "Report"]
    }
 
@app.get("/", tags=["System"])
def read_root():
    """API documentation."""
    return {
        "message": "Audio Compression Multi-Agent System API",
        "docs": "http://localhost:8000/docs",
        "agents": {
            "1_input": "POST /input/load",
            "2_features": "POST /features/extract",
            "3_decision": "POST /decision/decide",
            "4_execution": "POST /execution/compress",
            "5_report": "POST /report/generate"
        }
    }
 
 
if __name__ == "__main__":
    import uvicorn
    print("Starting Audio Compression Agent System...")
    print("API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)