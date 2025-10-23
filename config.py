"""
Environment configuration for the IPA Transcription API
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class with environment variables and defaults"""
    
    # Server Configuration
    PORT: int = int(os.getenv('PORT', '8002'))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', './app/data/ipa_database.db')
    
    # CORS Configuration
    _cors_env = os.getenv('CORS_ORIGINS', '')
    CORS_ORIGINS: List[str] = _cors_env.split(',') if _cors_env else []
    CORS_ORIGINS.append('http://0.0.0.0:8003')
    
    # API Configuration
    API_TITLE: str = os.getenv('API_TITLE', 'IPA Transcription API')
    API_DESCRIPTION: str = os.getenv(
        'API_DESCRIPTION', 
        'API for English IPA transcriptions with advanced phonetic rules'
    )
    API_VERSION: str = os.getenv('API_VERSION', '1.0.0')
    
    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'production')
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode"""
        return cls.ENVIRONMENT.lower() == 'development'
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return cls.ENVIRONMENT.lower() == 'production'

# Global config instance
config = Config()