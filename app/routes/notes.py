"""
Smart Notes Assistant - Notes Management Routes
Provides CRUD endpoints for notes with strict user ownership isolation,
ML auto-classification, and starter-note seeding.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.database.mongodb import get_db
from app.dependencies import get_current_user
from app.schemas.note import NoteCreateRequest, NoteResponse, NoteUpdateRequest
from app.services.note_service import note_service

router = APIRouter(prefix="/notes", tags=["Notes"])
logger = logging.getLogger("smart_notes.routes.notes")


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> NoteResponse:
    """Create a new note, auto-classify it via the trained ML model, and persist to MongoDB."""
    try:
        note = note_service.create_note(db, current_user["id"], payload.text)
        return NoteResponse(**note)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create note: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save note: {str(e)}"
        )


@router.get("", response_model=List[NoteResponse])
async def list_notes(
    category: Optional[str] = Query(None, description="Filter by category: Study, Money, Travel, Shopping"),
    uncertain_only: bool = Query(False, description="Filter for uncertain notes needing review"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> List[NoteResponse]:
    """Retrieve all notes belonging to the authenticated user, with optional category filtering."""
    try:
        notes = note_service.get_notes(db, current_user["id"], category=category, uncertain_only=uncertain_only)
        return [NoteResponse(**n) for n in notes]
    except Exception as e:
        logger.exception(f"Failed to list notes: {e}")
        return []


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> NoteResponse:
    """Retrieve a single note by ID. Enforces strict user ownership."""
    try:
        note = note_service.get_note_by_id(db, current_user["id"], note_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID '{note_id}' not found.",
            )
        return NoteResponse(**note)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving note: {str(e)}"
        )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    payload: NoteUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> NoteResponse:
    """Update note content, reclassify with ML pipeline, and update timestamp."""
    try:
        updated = note_service.update_note(db, current_user["id"], note_id, payload.text)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID '{note_id}' not found.",
            )
        return NoteResponse(**updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update note: {str(e)}"
        )


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Delete note. Strictly verifies user ownership."""
    try:
        success = note_service.delete_note(db, current_user["id"], note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID '{note_id}' not found.",
            )
        return {"message": f"Note '{note_id}' deleted successfully.", "note_id": note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete note: {str(e)}"
        )


@router.post("/seed")
async def seed_starter_notes(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """
    Idempotently loads official starter notes (N001-N012) into the authenticated user's workspace.
    Loading multiple times does not create duplicates.
    """
    try:
        result = note_service.seed_starter_notes(db, current_user["id"])
        return result
    except Exception as e:
        logger.exception(f"Failed to seed starter notes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load starter notes: {str(e)}"
        )


@router.post("/reclassify")
async def reclassify_notes(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Reclassifies all existing notes for the authenticated user using the upgraded 98% accuracy model."""
    try:
        count = note_service.reclassify_user_notes(db, current_user["id"])
        return {
            "message": f"Successfully reclassified {count} note(s) using the upgraded ML model.",
            "count": count
        }
    except Exception as e:
        logger.exception(f"Failed to reclassify notes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not reclassify notes: {str(e)}"
        )

