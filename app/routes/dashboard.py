"""
Smart Notes Assistant - Dashboard & Stats Routes
Provides real-time personal metrics calculated directly from MongoDB.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.database.mongodb import get_db
from app.dependencies import get_current_user
from app.schemas.note import DashboardStatsResponse, NoteResponse
from app.services.note_service import note_service

router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger("smart_notes.routes.dashboard")


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> DashboardStatsResponse:
    """Retrieve real personal workspace analytics computed from MongoDB Atlas."""
    stats = note_service.get_dashboard_stats(db, current_user["id"])
    return DashboardStatsResponse(
        total_notes=stats["total_notes"],
        study_count=stats["study_count"],
        money_count=stats["money_count"],
        travel_count=stats["travel_count"],
        shopping_count=stats["shopping_count"],
        uncertain_count=stats["uncertain_count"],
        recent_notes=[NoteResponse(**n) for n in stats["recent_notes"]],
    )


@router.post("/seed")
async def seed_starter_notes_root(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    """Root-level alias for seeding starter notes."""
    return note_service.seed_starter_notes(db, current_user["id"])

