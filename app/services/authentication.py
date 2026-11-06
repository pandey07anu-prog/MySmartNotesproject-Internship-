"""
Smart Notes Assistant - Authentication & Cryptography Service
Handles Argon2 password hashing, JWT generation & verification,
and token hashing for email verification and password reset flows.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

ph = PasswordHasher()


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash plain-text password using Argon2id."""
        return ph.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against Argon2 hash."""
        try:
            return ph.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    @staticmethod
    def create_access_token(user_id: str, email: str, name: str) -> Tuple[str, datetime]:
        """Create signed short-lived access JWT."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user_id),
            "email": email,
            "name": name,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "type": "access",
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, expires_at

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate access JWT."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["exp", "sub", "iat"]}
            )
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def generate_random_token(nbytes: int = 32) -> str:
        """Generate a cryptographically secure URL-safe token."""
        return secrets.token_urlsafe(nbytes)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Store only the SHA-256 digest of sensitive tokens in the database."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


auth_service = AuthService()

