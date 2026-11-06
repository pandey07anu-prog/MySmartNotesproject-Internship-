"""
Smart Notes Assistant - Authentication Routes
Implements registration, login, logout, verification, password reset, and session refresh.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pymongo.database import Database

from app.config import settings
from app.database.mongodb import get_db
from app.dependencies import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.services.authentication import auth_service
from app.services.email import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("smart_notes.routes.auth")


def set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None) -> None:
    """Set secure HTTP-only cookies on the response."""
    # Access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/auth/refresh",
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear session cookies upon logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/auth/refresh")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Register a new user account with Argon2 hashing and email verification."""
    email_norm = payload.email.lower().strip()

    # Check duplicate
    existing = db.users.find_one({"email": email_norm})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Hash password with Argon2
    password_hash = auth_service.hash_password(payload.password)
    now_iso = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "name": payload.name.strip(),
        "email": email_norm,
        "password_hash": password_hash,
        "profile_picture": None,
        "is_verified": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    result = db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Generate verification token record for audit/token persistence
    raw_token = auth_service.generate_random_token(32)
    token_hash = auth_service.hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    db.email_verification_tokens.insert_one({
        "token_hash": token_hash,
        "user_id": user_id,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    # Dispatch verification email (non-blocking for frictionless onboarding)
    email_res = email_service.send_verification_email(email_norm, raw_token)

    # Automatically issue access token for immediate workspace access
    access_token, _ = auth_service.create_access_token(user_id, email_norm, payload.name.strip())
    set_auth_cookies(response, access_token)

    return {
        "message": "Registration successful. Welcome to Smart Notes!",
        "user": {
            "id": user_id,
            "name": payload.name.strip(),
            "email": email_norm,
            "is_verified": True,
            "created_at": now_iso,
        },
        "email_status": email_res,
        "access_token": access_token,
    }


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Authenticate with email and password, establishing an HTTP-only cookie session."""
    email_norm = payload.email.lower().strip()
    user = db.users.find_one({"email": email_norm})

    if not user or not auth_service.verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    user_id = str(user["_id"])
    access_token, _ = auth_service.create_access_token(user_id, email_norm, user.get("name", "User"))

    # Create persistent session with refresh token
    refresh_token = auth_service.generate_random_token(48)
    refresh_hash = auth_service.hash_token(refresh_token)
    session_id = auth_service.generate_random_token(16)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "refresh_token_hash": refresh_hash,
        "user_agent": request.headers.get("user-agent", ""),
        "ip_address": request.client.host if request.client else "",
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    set_auth_cookies(response, access_token, refresh_token)

    return {
        "message": "Signed in successfully.",
        "access_token": access_token,
        "user": {
            "id": user_id,
            "name": user.get("name"),
            "email": user.get("email"),
            "profile_picture": user.get("profile_picture"),
            "is_verified": user.get("is_verified", True),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
        }
    }


@router.post("/logout")
async def logout(response: Response, current_user: Dict[str, Any] = Depends(get_current_user), db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Log out user, invalidate active session, and clear cookies."""
    user_id = current_user["id"]
    db.sessions.delete_many({"user_id": user_id})
    clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieve currently authenticated user profile."""
    return {"user": current_user}


@router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Issue a new access token using a valid refresh token."""
    token = refresh_token_cookie
    if not token:
        try:
            body = await request.json()
            token = body.get("refresh_token")
        except Exception:
            token = None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )

    token_hash = auth_service.hash_token(token)
    session = db.sessions.find_one({"refresh_token_hash": token_hash})

    if not session:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid or expired.",
        )

    # Check expiration
    if session.get("expires_at") and session["expires_at"] < datetime.now(timezone.utc):
        db.sessions.delete_one({"_id": session["_id"]})
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    user = db.users.find_one({"_id": ObjectId(session["user_id"])})
    if not user:
        db.sessions.delete_one({"_id": session["_id"]})
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    new_access_token, _ = auth_service.create_access_token(
        str(user["_id"]),
        user["email"],
        user.get("name", "User")
    )
    set_auth_cookies(response, new_access_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Verify account email with single-use cryptographic token."""
    token_hash = auth_service.hash_token(payload.token)
    record = db.email_verification_tokens.find_one({"token_hash": token_hash})

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )

    # Check expiration
    if record.get("expires_at") and record["expires_at"] < datetime.now(timezone.utc):
        db.email_verification_tokens.delete_one({"_id": record["_id"]})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one.",
        )

    user_id = record["user_id"]
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_verified": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    # Remove token to prevent reuse
    db.email_verification_tokens.delete_one({"_id": record["_id"]})

    return {"message": "Email verified successfully."}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Initiate password reset flow without revealing email registration state."""
    email_norm = payload.email.lower().strip()
    user = db.users.find_one({"email": email_norm})

    if user:
        raw_token = auth_service.generate_random_token(32)
        token_hash = auth_service.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Invalidate old reset tokens for this user
        db.password_reset_tokens.delete_many({"user_id": str(user["_id"])})

        db.password_reset_tokens.insert_one({
            "token_hash": token_hash,
            "user_id": str(user["_id"]),
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        })

        email_service.send_password_reset_email(email_norm, raw_token)

    return {
        "message": "If an account exists with this email, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """Reset user password using valid token and invalidate all active sessions."""
    token_hash = auth_service.hash_token(payload.token)
    record = db.password_reset_tokens.find_one({"token_hash": token_hash})

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link.",
        )

    if record.get("expires_at") and record["expires_at"] < datetime.now(timezone.utc):
        db.password_reset_tokens.delete_one({"_id": record["_id"]})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired.",
        )

    user_id = record["user_id"]
    new_hash = auth_service.hash_password(payload.new_password)
    now_iso = datetime.now(timezone.utc).isoformat()

    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": new_hash, "updated_at": now_iso}}
    )

    # Invalidate token and all existing user sessions
    db.password_reset_tokens.delete_one({"_id": record["_id"]})
    db.sessions.delete_many({"user_id": user_id})

    return {"message": "Password reset successfully. Please sign in with your new password."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Change password for currently authenticated user."""
    user = db.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user or not auth_service.verify_password(payload.current_password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    new_hash = auth_service.hash_password(payload.new_password)
    now_iso = datetime.now(timezone.utc).isoformat()

    db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"password_hash": new_hash, "updated_at": now_iso}}
    )

    return {"message": "Password updated successfully."}

