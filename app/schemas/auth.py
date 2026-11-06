"""
Smart Notes Assistant - Authentication Schemas
Defines request and response payloads for authentication flows with Pydantic validation.
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    email: EmailStr = Field(..., description="Valid Email Address")
    password: str = Field(..., min_length=8, max_length=128, description="Account Password")
    confirm_password: str = Field(..., description="Password Confirmation")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @model_validator(mode="after")
    def verify_password_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered Email")
    password: str = Field(..., description="Account Password")
    remember_me: bool = Field(default=False)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Email Verification Token")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered Email")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Password Reset Token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New Password")
    confirm_password: str = Field(..., description="Confirm New Password")

    @model_validator(mode="after")
    def verify_password_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current Password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New Password")
    confirm_password: str = Field(..., description="Confirm New Password")

    @model_validator(mode="after")
    def verify_password_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match.")
        return self

