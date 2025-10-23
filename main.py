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
def get_ipa(word: str = Query(..., description="Word to transcribe")):
    """Get all IPA transcription forms for a single word (American, RP, weak/strong)"""
    try:
        # Get raw data from database for both accents
        ipa_american_raw = transcription_service.db_lookup(word, 'american')
        ipa_rp_raw = transcription_service.db_lookup(word, 'rp')
        
        if not ipa_american_raw and not ipa_rp_raw:
            return {"word": word, "found": False, "american": None, "rp": None}
        
        result = {
            "word": word,
            "found": True,
            "american": None,
            "rp": None
        }
        
        # Process American accent
        if ipa_american_raw:
            corrected = transcription_service.apply_character_corrections(ipa_american_raw, 'american')
            result["american"] = corrected
        
        # Process RP accent with weak/strong forms
        if ipa_rp_raw:
            parsed = transcription_service.parse_weak_strong_format(ipa_rp_raw)
            
            if 'strong' in parsed and 'weak' in parsed:
                # Has weak and strong forms
                strong = transcription_service.apply_character_corrections(parsed['strong'], 'rp')
                weak = transcription_service.apply_character_corrections(parsed['weak'], 'rp')
                result["rp"] = {
                    "strong": strong,
                    "weak": weak
                }
            elif 'single' in parsed:
                # Only one form
                single = transcription_service.apply_character_corrections(parsed['single'], 'rp')
                result["rp"] = single
        
        return result
        
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
            "ipa": result['transcription'],
            "notFound": result['not_found'],
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
