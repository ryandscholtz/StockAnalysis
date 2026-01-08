"""
Authentication models and schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    exp: datetime
    iat: datetime
    token_type: str = "access"


class User(BaseModel):
    """User model for authentication"""
    id: str
    username: str
    email: str
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str
