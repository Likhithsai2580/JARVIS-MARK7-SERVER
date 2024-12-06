from google.auth.transport.requests import Request
from .server_template import BaseServer
from fastapi import HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict
from app.services.google_auth import google_auth_service
from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.auth import GoogleToken
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleAuthRequest(BaseModel):
    token: str
    scope: Optional[str] = None

class GoogleAuthResponse(BaseModel):
    user_info: Dict
    access_token: str
    refresh_token: Optional[str] = None

class GoogleAuthServer(BaseServer):
    def __init__(self):
        super().__init__("GoogleAuth")
        self.google_auth = google_auth_service
        
        @self.app.post("/authenticate", response_model=GoogleAuthResponse)
        async def authenticate(request: GoogleAuthRequest):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message="Processing Google authentication request",
                    log_type="info",
                    details={"scope": request.scope}
                )
                response = await self.process_authentication(request)
                await self.logger.log(
                    message="Google authentication successful",
                    log_type="info",
                    details={"user_info": response.get("user_info", {}).get("email")}
                )
                return response
            except Exception as e:
                await self.logger.log(
                    message="Google authentication failed",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.post("/refresh")
        async def refresh_token(refresh_token: str):
            self.set_busy(True)
            try:
                await self.logger.log(
                    message="Processing token refresh request",
                    log_type="info"
                )
                response = await self.process_token_refresh(refresh_token)
                await self.logger.log(
                    message="Token refresh successful",
                    log_type="info",
                    details={"expires_in": response.get("expires_in")}
                )
                return response
            except Exception as e:
                await self.logger.log(
                    message="Token refresh failed",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise
            finally:
                self.set_busy(False)
        
        @self.app.post("/revoke")
        async def revoke_token(token: str):
            try:
                await self.logger.log(
                    message="Processing token revocation request",
                    log_type="info"
                )
                await self.revoke_access(token)
                await self.logger.log(
                    message="Token revocation successful",
                    log_type="info"
                )
                return {"status": "success", "message": "Token revoked"}
            except Exception as e:
                await self.logger.log(
                    message="Token revocation failed",
                    log_type="error",
                    details={"error": str(e)}
                )
                raise HTTPException(status_code=500, detail=str(e))
    
    async def process_authentication(self, request: GoogleAuthRequest) -> Dict:
        """Process Google authentication"""
        try:
            await self.logger.log(
                message="Verifying OAuth2 token",
                log_type="info"
            )
            # Verify the OAuth2 token
            user_info = self.google_auth.verify_oauth2_token(request.token)
            if not user_info:
                await self.logger.log(
                    message="Invalid or expired token",
                    log_type="warning"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token"
                )
            
            # Create authorization URL if needed
            if request.scope:
                await self.logger.log(
                    message="Creating authorization URL",
                    log_type="info",
                    details={"scope": request.scope}
                )
                auth_url, state = self.google_auth.create_authorization_url()
                return {
                    "user_info": user_info,
                    "access_token": request.token,
                    "auth_url": auth_url,
                    "state": state
                }
            
            # Get token info
            await self.logger.log(
                message="Fetching token info",
                log_type="info"
            )
            token_info = await self._get_token_info(request.token)
            
            return {
                "user_info": user_info,
                "access_token": token_info.get("token"),
                "refresh_token": token_info.get("refresh_token")
            }
            
        except Exception as e:
            await self.logger.log(
                message="Authentication process failed",
                log_type="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=str(e))
    
    async def process_token_refresh(self, refresh_token: str) -> Dict:
        """Refresh access token"""
        try:
            await self.logger.log(
                message="Refreshing credentials",
                log_type="info"
            )
            # Refresh credentials using the refresh token
            credentials = self.google_auth.refresh_credentials(refresh_token)
            if not credentials:
                await self.logger.log(
                    message="Invalid or expired refresh token",
                    log_type="warning"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired refresh token"
                )
            
            response = {
                "access_token": credentials.token,
                "expires_in": credentials.expiry.timestamp() - datetime.now().timestamp() if credentials.expiry else 3600
            }
            
            await self.logger.log(
                message="Credentials refreshed successfully",
                log_type="info",
                details={"expires_in": response["expires_in"]}
            )
            
            return response
            
        except Exception as e:
            await self.logger.log(
                message="Token refresh process failed",
                log_type="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=str(e))
    
    async def revoke_access(self, token: str):
        """Revoke access token"""
        try:
            await self.logger.log(
                message="Verifying token before revocation",
                log_type="info"
            )
            # Verify token before revocation
            user_info = self.google_auth.verify_oauth2_token(token)
            if not user_info:
                await self.logger.log(
                    message="Invalid token for revocation",
                    log_type="warning"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            
            await self.logger.log(
                message="Creating credentials for revocation",
                log_type="info"
            )
            # Create credentials object
            credentials = self.google_auth.create_credentials(token)
            
            await self.logger.log(
                message="Revoking token",
                log_type="info"
            )
            # Revoke token
            credentials.revoke(Request())
            
            await self.logger.log(
                message="Token revoked successfully",
                log_type="info"
            )
            
        except Exception as e:
            await self.logger.log(
                message="Access revocation failed",
                log_type="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_token_info(self, token: str) -> Dict:
        """Get token information"""
        try:
            await self.logger.log(
                message="Fetching token information",
                log_type="info"
            )
            # Exchange token for token info
            token_info = self.google_auth.fetch_token(
                authorization_response=f"?token={token}",
                state="state"  # State should be managed properly in production
            )
            
            await self.logger.log(
                message="Token information retrieved successfully",
                log_type="info"
            )
            
            return token_info
        except Exception as e:
            await self.logger.log(
                message="Failed to get token information",
                log_type="error",
                details={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    server = GoogleAuthServer()
    server.run() 