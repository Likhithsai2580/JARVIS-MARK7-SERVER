from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
import jwt
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.services.google_auth import google_auth_service
from app.schemas.auth import AuthResponse, Token
from . import services

router = APIRouter()

router.include_router(services.router, prefix="/services", tags=["services"])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

@router.get("/authorization")
async def authorize(token: str = Query(...)):
    """
    Authorization endpoint that initiates the Google OAuth2 flow
    """
    try:
        # Verify the incoming token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        
        # Create authorization URL
        auth_url, state = google_auth_service.create_authorization_url()
        
        # Redirect to Google's consent screen
        return RedirectResponse(url=auth_url)
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )

@router.get("/callback")
async def callback(
    request: Request,
    state: str = Query(...),
    code: str = Query(...),
    error: Optional[str] = None
):
    """
    Callback endpoint that handles the response from Google's OAuth2 consent screen
    """
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Authorization failed: {error}"
        )
    
    try:
        # Get the full URL of the request
        authorization_response = str(request.url)
        
        # Exchange the authorization code for tokens
        token_info = google_auth_service.fetch_token(
            authorization_response=authorization_response,
            state=state
        )
        
        # Create access token for our API
        access_token = create_access_token(
            data={"sub": token_info["token"]},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Get user info from the ID token
        user_info = google_auth_service.verify_oauth2_token(token_info["token"])
        
        # Create the response
        auth_response = AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user_info=user_info
        )
        
        # Redirect to frontend with the tokens
        redirect_url = f"{settings.FRONTEND_REDIRECT_URL}?token={access_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process callback: {str(e)}"
        )

@router.post("/refresh-token")
async def refresh_token(token: Token):
    """
    Endpoint to refresh an expired access token
    """
    try:
        # Verify the existing token
        payload = jwt.decode(token.access_token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        
        # Refresh the Google credentials
        credentials = google_auth_service.refresh_credentials(payload["sub"])
        
        if not credentials:
            raise HTTPException(
                status_code=400,
                detail="Failed to refresh token"
            )
        
        # Create new access token
        access_token = create_access_token(
            data={"sub": credentials.token},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) 