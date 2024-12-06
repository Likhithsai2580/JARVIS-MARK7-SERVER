from pydantic_settings import BaseSettings
from typing import Dict

class Settings(BaseSettings):
    # Server URLs
    LLM_SERVER_URL: str = "http://localhost:8000"
    ANDROID_BRIDGE_URL: str = "http://localhost:3000"
    CODEBREW_SERVER_URL: str = "http://localhost:8001"
    GOOGLE_AUTH_URL: str = "http://localhost:8002"
    OMNIPARSER_URL: str = "http://localhost:8003"
    FUNCTIONAL_SERVER_URL: str = "http://localhost:8004"
    
    # API Keys and Secrets
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = "your-secret-key"
    
    # Service Configuration
    ENABLE_CACHE: bool = True
    DEBUG: bool = True
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

settings = Settings() 