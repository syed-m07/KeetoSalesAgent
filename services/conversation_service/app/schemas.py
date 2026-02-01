"""
Pydantic schemas for request/response validation.
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


# --- User Schemas ---

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data in responses (no password)."""
    id: UUID
    email: str
    name: str
    company: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for login response with JWT token."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- TTS Schemas ---

class SpeakRequest(BaseModel):
    """Schema for TTS request."""
    text: str
    lang: str = "en"
