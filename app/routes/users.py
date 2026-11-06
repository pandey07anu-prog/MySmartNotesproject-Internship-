"""
Smart Notes Assistant - User Management Routes
Provides profile retrieval, updates, and account deletion.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.database import Database

from app.database.mongodb import get_db
from app.dependencies import get_current_user
from app.routes.auth import clear_auth_cookies
from app.schemas.user import UserProfileResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger("smart_notes.routes.users")


@router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserProfileResponse:
    """Retrieve the current user's profile information."""
    return UserProfileResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        profile_picture=current_user.get("profile_picture"),
        is_verified=current_user.get("is_verified", True),
        created_at=current_user.get("created_at", ""),
        updated_at=current_user.get("updated_at", ""),
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_user_profile(
    payload: UserUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> UserProfileResponse:
    """Update profile details (name, profile picture)."""
    user_id = current_user["id"]
    updates: Dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    if payload.name is not None and payload.name.strip():
        updates["name"] = payload.name.strip()

    if payload.profile_picture is not None:
        # Validate profile image data length / format
        pic_data = payload.profile_picture.strip()
        if pic_data.startswith("data:image/") or pic_data.startswith("http://") or pic_data.startswith("https://") or pic_data == "":
            updates["profile_picture"] = pic_data if pic_data else None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid profile picture format. Must be an image URL or data URI."
            )

    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    updated_doc = db.users.find_one({"_id": ObjectId(user_id)})
    assert updated_doc is not None

    return UserProfileResponse(
        id=str(updated_doc["_id"]),
        name=updated_doc.get("name", ""),
        email=updated_doc.get("email", ""),
        profile_picture=updated_doc.get("profile_picture"),
        is_verified=updated_doc.get("is_verified", True),
        created_at=updated_doc.get("created_at", ""),
        updated_at=updated_doc.get("updated_at", ""),
    )


@router.delete("/me")
async def delete_user_account(
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Permanently delete user account and all private notes and sessions."""
    user_id = current_user["id"]

    # Delete all user's notes
    deleted_notes = db.notes.delete_many({"user_id": user_id}).deleted_count

    # Delete all user's sessions and tokens
    db.sessions.delete_many({"user_id": user_id})
    db.email_verification_tokens.delete_many({"user_id": user_id})
    db.password_reset_tokens.delete_many({"user_id": user_id})

    # Delete user record
    db.users.delete_one({"_id": ObjectId(user_id)})

    clear_auth_cookies(response)
    logger.info(f"Deleted user account {user_id} and {deleted_notes} notes.")

    return {
        "message": "Account and all associated private notes deleted permanently.",
        "deleted_notes_count": deleted_notes,
    }

