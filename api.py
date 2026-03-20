from pathlib import Path
import shutil
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from orchestrator import AudioCompressionOrchestrator

app = FastAPI(
    title="Audio Compression Multi-Agent API",
    description="API for intelligent audio compression using a multi-agent system",
    version="1.0.0",
)

orchestrator = AudioCompressionOrchestrator()

UPLOAD_DIR = Path("data/audio_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "Audio Compression API is running",
        "docs": "/docs",
        "endpoints": [
            "/analyze",
            "/pipeline",
        ],
    }


@app.post("/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        metadata = orchestrator.input_agent.load_and_validate(str(file_path))
        if metadata is None:
            raise HTTPException(status_code=400, detail="InputAgent failed")

        features = orchestrator.feature_agent.extract(str(file_path))
        if features is None:
            raise HTTPException(status_code=400, detail="FeatureExtractionAgent failed")

        decision = orchestrator.decision_agent.decide(metadata, features)
        if decision is None:
            raise HTTPException(status_code=400, detail="DecisionAgent failed")

        return JSONResponse(
            content={
                "status": "success",
                "metadata": metadata,
                "features": features,
                "decision": decision,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline")
async def run_pipeline(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = orchestrator.run_pipeline(str(file_path))

        if result is None:
            raise HTTPException(status_code=500, detail="Pipeline returned None")

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return JSONResponse(
            content={
                "status": "success",
                "result": result,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))