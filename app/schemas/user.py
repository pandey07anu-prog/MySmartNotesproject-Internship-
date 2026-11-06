"""
Smart Notes Assistant - User Schemas
Defines request and response schemas for user profile data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    profile_picture: Optional[str] = None
    is_verified: bool
    created_at: str
    updated_at: str


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    profile_picture: Optional[str] = Field(None, max_length=2000000, description="Base64 or secure URL for profile image")

