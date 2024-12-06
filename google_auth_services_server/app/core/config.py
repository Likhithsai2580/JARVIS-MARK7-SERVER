from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Google Auth Service"
    
    # Google OAuth2 settings
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # API
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    FRONTEND_REDIRECT_URL: str = os.getenv("FRONTEND_REDIRECT_URL", "http://localhost:3000")
    
    # Google API Scopes
    GOOGLE_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/photoslibrary",
        "https://www.googleapis.com/auth/contacts",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/messages",
    ]

settings = Settings() 