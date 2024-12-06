from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import google.auth.transport.requests
from typing import Optional, Dict, Any
import json

from app.core.config import settings

class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = settings.GOOGLE_SCOPES

    def create_authorization_url(self) -> tuple[str, str]:
        """Create authorization URL for Google OAuth2."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.scopes,
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return authorization_url, state

    def fetch_token(self, authorization_response: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.scopes,
            state=state
        )
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        token_info = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        
        return token_info

    def verify_oauth2_token(self, token: str) -> Dict[str, Any]:
        """Verify the OAuth2 token and return user info."""
        try:
            request = google.auth.transport.requests.Request()
            id_info = id_token.verify_oauth2_token(
                token, request, self.client_id
            )
            return id_info
        except ValueError:
            return None

    def refresh_credentials(self, refresh_token: str) -> Optional[Credentials]:
        """Refresh the access token using the refresh token."""
        credentials = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            return credentials
        return None

google_auth_service = GoogleAuthService() 