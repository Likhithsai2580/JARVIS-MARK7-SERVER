from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    sub: Optional[str] = None

class GoogleToken(BaseModel):
    token: str
    refresh_token: Optional[str] = None
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: dict 