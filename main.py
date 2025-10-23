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
from external_fallback import create_fallback_service
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

# Initialize external fallback service
fallback_service = create_fallback_service(timeout=5)


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
        
        source = 'database'
        
        # If not found in database, try external fallback
        if not ipa_american_raw and not ipa_rp_raw:
            fallback_result = fallback_service.fetch_ipa(word)
            
            if fallback_result:
                source = fallback_result['source']
                ipa_american_raw = fallback_result['data'].get('american')
                ipa_rp_raw = fallback_result['data'].get('rp')
            
            # If still not found, raise 404 error
            if not ipa_american_raw and not ipa_rp_raw:
                raise HTTPException(
                    status_code=404,
                    detail=f"Word '{word}' not found in database or external sources."
                )
        
        result = {
            "word": word,
            "found": True,
            "source": source,
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
    import socket
    
    def find_free_port(start_port: int = 8002, max_attempts: int = 10) -> int:
        """Find a free port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((config.HOST, port))
                    return port
                except OSError:
                    continue
        raise RuntimeError(f"Could not find a free port after {max_attempts} attempts")
    
    port = find_free_port(config.PORT)
    if port != config.PORT:
        print(f"Port {config.PORT} is busy, using port {port} instead")
    
    uvicorn.run(app, host=config.HOST, port=port)
