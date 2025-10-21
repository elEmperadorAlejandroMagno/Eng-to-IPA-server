"""
FastAPI Server for IPA Transcription API
Lógica del servidor separada de la lógica de transcripciones.
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(__file__))
from transcription_service_modular import create_transcription_service
from config import config

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# CORS configuration from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if not config.is_development() else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize transcription service
transcription_service = create_transcription_service()


class TranscribeRequest(BaseModel):
    text: str
    accent: str = "american"  # 'american' | 'rp'
    useWeakForms: bool = True
    ignoreStress: bool = False
    applySimplification: bool = False  # placeholder, not applied yet


@app.get("/")
def read_root():
    """Root endpoint with API info"""
    return {
        "message": "IPA Transcription API",
        "version": "1.0.0",
        "endpoints": {
            "transcribe": "POST /transcribe - Transcribe text to IPA",
            "ipa": "GET /ipa?word={word}&accent={accent} - Get IPA for single word",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ipa-transcription-api"}


@app.get("/ipa")
def get_ipa(word: str = Query(..., description="Word to transcribe"), 
            accent: str = Query("american", description="Accent: 'american' or 'rp'")):
    """Get IPA transcription for a single word"""
    try:
        # Validate accent
        if accent.lower() not in ['american', 'rp']:
            raise HTTPException(status_code=400, detail="Accent must be 'american' or 'rp'")
        
        # Normalize accent
        normalized_accent = 'american' if accent.lower().startswith('a') else 'rp'
        
        # Get IPA from database
        ipa = transcription_service.db_lookup(word, normalized_accent)
        
        if not ipa:
            return {"word": word, "ipa": None, "accent": normalized_accent, "found": False}
        
        # Apply character corrections
        ipa = transcription_service.apply_character_corrections(ipa, normalized_accent)
        
        return {"word": word, "ipa": ipa, "accent": normalized_accent, "found": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing word: {str(e)}")


@app.post("/transcribe")
def post_transcribe(req: TranscribeRequest):
    """Transcribe full text to IPA with all phonetic rules"""
    try:
        # Validate input
        if not req.text or not req.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if req.accent.lower() not in ['american', 'rp']:
            raise HTTPException(status_code=400, detail="Accent must be 'american' or 'rp'")
        
        # Normalize accent
        normalized_accent = 'american' if req.accent.lower().startswith('a') else 'rp'
        
        # Perform transcription using the service
        result = transcription_service.transcribe_text(
            text=req.text,
            accent=normalized_accent,
            use_weak=req.useWeakForms,
            ignore_stress=req.ignoreStress
        )
        
        return {
            "text": req.text,
            "accent": normalized_accent,
            "ipa": result,
            "options": {
                "useWeakForms": req.useWeakForms,
                "ignoreStress": req.ignoreStress,
                "applySimplification": req.applySimplification
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error transcribing text: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
