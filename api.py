from pathlib import Path
import shutil
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import AudioCompressionOrchestrator
from dotenv import load_dotenv
import os
import logging

# ============================================================================
# SETUP
# ============================================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Audio Processing API",
    description="Professional audio compression, transcription, and synthesis",
    version="3.0.0",
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
orchestrator = AudioCompressionOrchestrator()
UPLOAD_DIR = Path("data/audio_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class VoiceParams(BaseModel):
    """Voice parameters for text-to-speech."""
    voice_id: str = "female"
    language: str = "en"
    speed: float = 1.0
    pitch: float = 1.0


class TextToSpeechRequest(BaseModel):
    """Request model for text-to-speech."""
    text: str
    voice_params: VoiceParams = VoiceParams()


# ============================================================================
# STATUS ENDPOINTS
# ============================================================================

@app.get("/")
def home():
    """Home endpoint."""
    return {
        "status": "online",
        "service": "Audio Processing API",
        "version": "3.0.0",
        "endpoints": {
            "compress": "POST /compress",
            "transcribe": "POST /transcribe",
            "synthesize": "POST /synthesize",
            "analyze": "POST /analyze",
            "health": "GET /health",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health_check():
    """Health check."""
    return {"status": "healthy", "service": "audio-api", "version": "3.0.0"}

# ============================================================================
# ENDPOINT 1: COMPRESS AUDIO
# ========================================================================== 

@app.post("/compress")
async def compress_audio(file: UploadFile = File(...)):
    """
    Complete audio compression pipeline.
    - Button: "Compress Audio"
    - Features: AI-selected codec/bitrate
    """
    try:
        logger.info(f"Compressing: {file.filename}")
        
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = orchestrator.run_pipeline(str(file_path))
        
        if result is None or "error" in result:
            error_msg = result.get("error", "Unknown error") if result else "Pipeline failed"
            logger.error(f"Compression failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        logger.info("Compression completed")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Audio compression completed",
                "result": result
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compression error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compression failed: {str(e)}")


# ============================================================================
# ENDPOINT: PIPELINE (Alias for Compress - used by UI)
# ==========================================================================

@app.post("/pipeline")
async def pipeline(file: UploadFile = File(...)):
    """
    Full audio processing pipeline (alias for /compress).
    Used by the Streamlit UI.
    """
    return await compress_audio(file)


# ============================================================================
# ENDPOINT 2: TRANSCRIBE AUDIO (Audio to Text)
# ========================================================================== 

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Convert audio to text (transcription).
    - Button: "Audio to Text"
    - Features: Speech-to-text conversion using Claude
    """
    try:
        logger.info(f"Transcribing: {file.filename}")
        
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Step 1: Load metadata
        logger.info("Step 1: Loading audio metadata")
        metadata = orchestrator.input_agent.load_and_validate(str(file_path))
        if metadata is None:
            raise HTTPException(status_code=400, detail="Failed to load audio file")
        
        # Step 2: Extract features
        logger.info("Step 2: Extracting features")
        features = orchestrator.feature_agent.extract(str(file_path))
        if features is None:
            raise HTTPException(status_code=400, detail="Failed to extract features")
        
        # Step 3: Get transcription
        logger.info("Step 3: Generating transcription")
        transcription = orchestrator.decision_agent.transcribe(metadata, features, str(file_path))
        if transcription is None:
            raise HTTPException(status_code=400, detail="Transcription failed")
        
        logger.info("Transcription completed")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Audio transcription completed",
                "metadata": metadata,
                "features": features,
                "transcription": transcription
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ============================================================================
# ENDPOINT 3: TEXT-TO-SPEECH (Text to Audio)
# ========================================================================== 

@app.post("/synthesize")
async def synthesize_audio(request: TextToSpeechRequest):
    """
    Convert text to audio (text-to-speech synthesis).
    - Button: "Text to Audio"
    - Features: Text-to-speech using Claude guidance
    
    Request body:
    {
        "text": "Your text here",
        "voice_params": {
            "voice_id": "female",
            "language": "en",
            "speed": 1.0,
            "pitch": 1.0
        }
    }
    """
    try:
        logger.info(f"Synthesizing text ({len(request.text)} chars)")
        
        # Get synthesis parameters from decision agent
        synthesis = orchestrator.decision_agent.synthesize(
            text=request.text,
            voice_params=request.voice_params.dict()
        )
        
        if synthesis is None:
            raise HTTPException(status_code=400, detail="Text-to-speech synthesis failed")
        
        logger.info("Synthesis completed")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Text-to-speech synthesis completed",
                "synthesis": synthesis
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


# ============================================================================
# ENDPOINT 4: ANALYZE AUDIO (Without Compression)
# ========================================================================== 

@app.post("/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    """
    Analyze audio without compression.
    Returns metadata, features, and compression decision only.
    """
    try:
        logger.info(f"Analyzing: {file.filename}")
        
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        metadata = orchestrator.input_agent.load_and_validate(str(file_path))
        if metadata is None:
            raise HTTPException(status_code=400, detail="Failed to load audio")
        
        features = orchestrator.feature_agent.extract(str(file_path))
        if features is None:
            raise HTTPException(status_code=400, detail="Failed to extract features")
        
        decision = orchestrator.decision_agent.decide(metadata, features)
        if decision is None:
            raise HTTPException(status_code=400, detail="Failed to make decision")
        
        logger.info("Analysis completed")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Audio analysis completed",
                "metadata": metadata,
                "features": features,
                "decision": decision
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# ============================================================================
# LEGACY ENDPOINTS (Backward Compatibility)
# ========================================================================== 

@app.post("/input/load")
async def load_input(data: dict):
    filepath = data.get("filepath")
    if not filepath:
        raise HTTPException(status_code=400, detail="Missing filepath")
    metadata = orchestrator.input_agent.load_and_validate(filepath)
    if metadata is None:
        raise HTTPException(status_code=400, detail="Failed to load")
    return metadata


@app.post("/features/extract")
async def extract_features(data: dict):
    filepath = data.get("filepath")
    if not filepath:
        raise HTTPException(status_code=400, detail="Missing filepath")
    features = orchestrator.feature_agent.extract(filepath)
    if features is None:
        raise HTTPException(status_code=400, detail="Feature extraction failed")
    return features


@app.post("/decision/decide")
async def make_decision(data: dict):
    metadata = data.get("metadata")
    features = data.get("features")
    if not metadata or not features:
        raise HTTPException(status_code=400, detail="Missing metadata or features")
    decision = orchestrator.decision_agent.decide(metadata, features)
    if decision is None:
        raise HTTPException(status_code=400, detail="Decision failed")
    return decision


@app.post("/execution/compress")
async def compress_file(data: dict):
    filepath = data.get("filepath")
    codec = data.get("codec")
    bitrate = data.get("bitrate")
    sample_rate = data.get("sample_rate")
    channels = data.get("channels", 2)
    if not all([filepath, codec, bitrate, sample_rate]):
        raise HTTPException(status_code=400, detail="Missing parameters")
    result = orchestrator.execution_agent.compress(
        filepath=filepath,
        codec=codec,
        bitrate_kbps=bitrate,
        sample_rate_hz=sample_rate,
        channels=channels
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Compression failed")
    return result


@app.post("/report/generate")
async def generate_report(data: dict):
    original_filepath = data.get("original_filepath")
    compressed_filepath = data.get("compressed_filepath")
    if not all([original_filepath, compressed_filepath]):
        raise HTTPException(status_code=400, detail="Missing file paths")
    result = orchestrator.report_agent.generate(original_filepath, compressed_filepath)
    if result is None:
        raise HTTPException(status_code=400, detail="Report generation failed")
    return result

# ============================================================================
# ERROR HANDLERS
# ========================================================================== 

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "code": 500
        }
    )

# ============================================================================
# STARTUP/SHUTDOWN
# ========================================================================== 

@app.on_event("startup")
async def startup():
    logger.info("Audio API starting...")
    logger.info(f"API Key available: {'Yes' if os.getenv('ANTHROPIC_API_KEY') else 'No'}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Audio API shutting down...")

# ============================================================================
# MAIN
# ========================================================================== 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")