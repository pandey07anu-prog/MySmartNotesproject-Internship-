"""
Smart Notes Assistant - FastAPI Dependencies
Provides database session injection, JWT extraction from HTTP-only cookies
or Authorization headers, and ownership authentication guards.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from bson import ObjectId
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from pymongo.database import Database

from app.database.mongodb import get_db
from app.services.authentication import auth_service


def extract_token_from_request(
    request: Request,
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    authorization_header: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """
    Retrieve JWT from Authorization header or HTTP-only cookie.
    Explicit Bearer header takes precedence over ambient cookie.
    """
    if authorization_header and authorization_header.startswith("Bearer "):
        return authorization_header[7:].strip()
    if access_token_cookie:
        return access_token_cookie
    return None


async def get_current_user(
    request: Request,
    db: Database = Depends(get_db),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    authorization_header: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    Validates authenticated user context.
    Raises HTTP 401 if token is missing, invalid, or expired.
    """
    token = extract_token_from_request(request, access_token_cookie, authorization_header)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = auth_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    # Query user from MongoDB
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = db.users.find_one({"_id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )

    user_dict = dict(user)
    user_dict["id"] = str(user_dict["_id"])
    user_dict.pop("_id", None)
    user_dict.pop("password_hash", None)
    return user_dict


async def get_optional_user(
    request: Request,
    db: Database = Depends(get_db),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    authorization_header: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[Dict[str, Any]]:
    """Returns authenticated user if present, or None if guest."""
    try:
        return await get_current_user(request, db, access_token_cookie, authorization_header)
    except HTTPException:
        return None
