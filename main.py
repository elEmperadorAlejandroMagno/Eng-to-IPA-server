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
    """Get all IPA transcription forms for a single word from multiple sources"""
    try:
        sources = []
        
        # 1. Obtener de la base de datos local
        ipa_american_raw = transcription_service.db_lookup(word, 'american')
        ipa_rp_raw = transcription_service.db_lookup(word, 'rp')
        
        if ipa_american_raw or ipa_rp_raw:
            db_result = {
                "source": "database",
                "american": None,
                "rp": None
            }
            
            # Process American accent
            if ipa_american_raw:
                corrected = transcription_service.apply_character_corrections(ipa_american_raw, 'american')
                db_result["american"] = corrected
            
            # Process RP accent with weak/strong forms
            if ipa_rp_raw:
                parsed = transcription_service.parse_weak_strong_format(ipa_rp_raw)
                
                if 'strong' in parsed and 'weak' in parsed:
                    strong = transcription_service.apply_character_corrections(parsed['strong'], 'rp')
                    weak = transcription_service.apply_character_corrections(parsed['weak'], 'rp')
                    db_result["rp"] = {
                        "strong": strong,
                        "weak": weak
                    }
                elif 'single' in parsed:
                    single = transcription_service.apply_character_corrections(parsed['single'], 'rp')
                    db_result["rp"] = single
            
            sources.append(db_result)
        
        # 2. Obtener de fuentes externas (siempre)
        external_results = fallback_service.fetch_ipa(word)
        
        for ext_result in external_results:
            source_data = {
                "source": ext_result['source'],
                "american": None,
                "rp": None
            }
            
            data = ext_result['data']
            
            # Process American
            if data.get('american'):
                corrected = transcription_service.apply_character_corrections(data['american'], 'american')
                source_data["american"] = corrected
            
            # Process RP
            if data.get('rp'):
                corrected = transcription_service.apply_character_corrections(data['rp'], 'rp')
                source_data["rp"] = corrected
            
            sources.append(source_data)
        
        # Si no se encontró nada en ninguna fuente
        if not sources:
            raise HTTPException(
                status_code=404,
                detail=f"Word '{word}' not found in any source."
            )
        
        return {
            "word": word,
            "found": True,
            "sources": sources
        }
        
    except HTTPException:
        raise
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
            use_weak= True,
        )
        
        return {
            "text": req.text,
            "accent": normalized_accent,
            "ipa": result['transcription'],
            "notFound": result['not_found'],
            "options": {
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
