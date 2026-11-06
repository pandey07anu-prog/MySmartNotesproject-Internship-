"""
Smart Notes Assistant - Search Routes
Provides TF-IDF Cosine Similarity and Keyword Search over authenticated user notes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.database.mongodb import get_db
from app.dependencies import get_current_user
from app.schemas.note import SearchResponse, SearchResultItem
from app.services.note_service import note_service
from app.services.search import search_service

router = APIRouter(tags=["Search"])
logger = logging.getLogger("smart_notes.routes.search")


@router.get("/search", response_model=SearchResponse)
async def search_user_notes(
    q: str = Query(..., min_length=1, max_length=200, description="Search query string"),
    method: str = Query("tfidf", description="Search algorithm: 'tfidf' or 'keyword'"),
    top_k: int = Query(20, ge=1, le=50, description="Maximum number of results to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Database = Depends(get_db)
) -> SearchResponse:
    """
    Search the authenticated user's private notes library.
    Supports TF-IDF Vector Space Cosine Similarity and Keyword Overlap matching.
    """
    cleaned_query = q.strip()
    if not cleaned_query:
        return SearchResponse(
            query=q,
            method=method,
            total_matches=0,
            results=[]
        )

    # Fetch notes belonging exclusively to this user
    user_notes = note_service.get_notes(db, current_user["id"])

    if method.lower() == "keyword":
        ranked_items = search_service.keyword_search(cleaned_query, user_notes, top_k=top_k)
    else:
        ranked_items = search_service.tfidf_search(cleaned_query, user_notes, top_k=top_k)

    results = []
    for item in ranked_items:
        results.append(SearchResultItem(
            note_id=item["note_id"],
            text=item["text"],
            category=item["category"],
            confidence=item["confidence"],
            uncertain=item["uncertain"],
            score=item["score"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        ))

    return SearchResponse(
        query=cleaned_query,
        method=method.lower(),
        total_matches=len(results),
        results=results
    )

