"""
Smart Notes Assistant - FastAPI Backend Service
Phase 7: FastAPI Backend Engineering, Integration, Security & Full Verification

This module provides the local REST API connecting the future native Windows
desktop application to the genuine ML classification pipeline, persistent
notes storage, and search engine.

Features:
- Single-load ML pipeline lifecycle management.
- Strict Pydantic input validation (rejecting non-strings, numbers, empty inputs).
- Decoupled classification endpoint (`POST /classify`).
- Full CRUD notes management with category filtering and persistent IDs.
- Process-local mutation synchronization via asyncio.Lock.
- Idempotent starter-note loading with conflict detection (`POST /notes/load-starter`).
- Search endpoint (`GET /search`) supporting TF-IDF and keyword retrieval.
- Health endpoint (`GET /health`).
- Clean error masking: internal paths and stack traces are never exposed.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictStr, field_validator

from src.data_ingestion import get_project_root
from src.notes_manager import (
    CategoryValidationError,
    NoteNotFoundError,
    NotesManager,
    NotesManagerError,
    NoteValidationError,
    StarterNoteConflictError,
)
from src.search_engine import DEFAULT_SEARCH_METHOD, SUPPORTED_SEARCH_METHODS
from src.uncertainty import ALLOWED_CATEGORIES, predict_with_uncertainty


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class ClassifyRequest(BaseModel):
    """Request payload for text classification."""
    text: StrictStr = Field(..., max_length=1000, description="Note text to classify")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class ClassifyResponse(BaseModel):
    """Response payload for text classification."""
    category: str
    uncertain: bool
    confidence: float


class NoteCreateRequest(BaseModel):
    """Request payload for creating a note."""
    text: StrictStr = Field(..., max_length=1000, description="Note content")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class NoteUpdateRequest(BaseModel):
    """Request payload for updating a note."""
    text: StrictStr = Field(..., max_length=1000, description="Updated note content")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class NoteResponse(BaseModel):
    """Response schema for a single note record."""
    id: str
    text: str
    category: str
    confidence: float
    uncertain: bool
    created_at: str
    updated_at: str


class SearchResultNote(BaseModel):
    """Response schema for a note returned by search."""
    id: str
    text: str
    category: str
    confidence: float
    uncertain: bool
    score: float
    rank: int


class StarterNotesLoadResponse(BaseModel):
    """Response summary for starter notes loading."""
    loaded_count: int
    notes: List[NoteResponse]
    message: str


class DeleteResponse(BaseModel):
    """Response payload for note deletion."""
    deleted: bool
    id: str
    message: str


class HealthResponse(BaseModel):
    """Response payload for health check."""
    status: str
    model_ready: bool
    storage_ready: bool
    version: str


# ---------------------------------------------------------------------------
# Application Factory & Lifespan Management
# ---------------------------------------------------------------------------
def create_app(
    notes_manager: Optional[NotesManager] = None,
    storage_path: Optional[Union[str, Path]] = None,
    model_path: Optional[Union[str, Path]] = None,
    uncertainty_threshold: float = 0.40,
) -> FastAPI:
    """
    Application factory providing dependency isolation, single model loading,
    and process-local mutation synchronization.
    """
    write_lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        # Startup: initialize manager once if not pre-injected
        if notes_manager is not None:
            mgr = notes_manager
        else:
            resolved_storage = storage_path or os.getenv("SMART_NOTES_STORAGE_PATH")
            mgr = NotesManager(
                storage_path=resolved_storage,
                model_path=model_path,
                uncertainty_threshold=uncertainty_threshold,
                auto_create_storage=True,
            )

        app_instance.state.notes_manager = mgr
        app_instance.state.write_lock = write_lock
        yield
        # Shutdown cleanup if needed
        app_instance.state.notes_manager = None

    app = FastAPI(
        title="Smart Notes Assistant API",
        description="Local REST service connecting the desktop UI to the trained ML notes assistant.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # Error Handlers
    # -----------------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Extract clean error messages without exposing internals
        error_msgs = []
        for err in exc.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            error_msgs.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "; ".join(error_msgs)},
        )

    @app.exception_handler(NoteNotFoundError)
    async def note_not_found_handler(request: Request, exc: NoteNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(StarterNoteConflictError)
    async def starter_conflict_handler(request: Request, exc: StarterNoteConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(CategoryValidationError)
    async def category_validation_handler(request: Request, exc: CategoryValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(NoteValidationError)
    async def note_validation_handler(request: Request, exc: NoteValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Never expose internal paths, stack traces, or exception details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # -----------------------------------------------------------------------
    # Dependencies
    # -----------------------------------------------------------------------
    def get_manager(request: Request) -> NotesManager:
        mgr = getattr(request.app.state, "notes_manager", None)
        if mgr is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Notes service is not ready.",
            )
        return mgr

    def get_lock(request: Request) -> asyncio.Lock:
        return request.app.state.write_lock

    # -----------------------------------------------------------------------
    # Endpoints
    # -----------------------------------------------------------------------

    # 1. Health
    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Service Health Check",
        tags=["System"],
    )
    async def health(request: Request):
        mgr = getattr(request.app.state, "notes_manager", None)
        model_ready = False
        storage_ready = False

        if mgr is not None:
            model_ready = hasattr(mgr, "model") and mgr.model is not None
            storage_ready = hasattr(mgr, "storage") and mgr.storage is not None

        is_healthy = model_ready and storage_ready
        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "model_ready": model_ready,
                "storage_ready": storage_ready,
                "version": "1.0.0",
            },
        )

    # 2. Classify
    @app.post(
        "/classify",
        response_model=ClassifyResponse,
        summary="Classify Note Text",
        tags=["Classification"],
    )
    async def classify(payload: ClassifyRequest, mgr: NotesManager = Depends(get_manager)):
        pred = predict_with_uncertainty(
            payload.text,
            mgr.model,
            threshold=mgr.threshold,
        )
        return ClassifyResponse(
            category=pred["category"],
            uncertain=pred["uncertain"],
            confidence=pred["confidence"],
        )

    # 3. List Notes
    @app.get(
        "/notes",
        response_model=List[NoteResponse],
        summary="Retrieve Saved Notes",
        tags=["Notes"],
    )
    async def list_notes(
        category: Optional[str] = Query(None, description="Filter by category"),
        mgr: NotesManager = Depends(get_manager),
    ):
        if category is not None:
            if category not in ALLOWED_CATEGORIES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid category '{category}'. Must be one of {list(ALLOWED_CATEGORIES)}",
                )
            notes = mgr.filter_by_category(category)
        else:
            notes = mgr.get_all_notes()
        return notes

    # 4. Create Note
    @app.post(
        "/notes",
        response_model=NoteResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a Note",
        tags=["Notes"],
    )
    async def create_note(
        payload: NoteCreateRequest,
        mgr: NotesManager = Depends(get_manager),
        lock: asyncio.Lock = Depends(get_lock),
    ):
        async with lock:
            saved_note = mgr.add_note(payload.text)
        return saved_note

    # 5. Retrieve Note
    @app.get(
        "/notes/{note_id}",
        response_model=NoteResponse,
        summary="Get Note by ID",
        tags=["Notes"],
    )
    async def get_note(note_id: str, mgr: NotesManager = Depends(get_manager)):
        return mgr.get_note(note_id)

    # 6. Update Note
    @app.put(
        "/notes/{note_id}",
        response_model=NoteResponse,
        summary="Update Note Content",
        tags=["Notes"],
    )
    async def update_note(
        note_id: str,
        payload: NoteUpdateRequest,
        mgr: NotesManager = Depends(get_manager),
        lock: asyncio.Lock = Depends(get_lock),
    ):
        async with lock:
            updated_note = mgr.update_note(note_id, payload.text)
        return updated_note

    # 7. Delete Note
    @app.delete(
        "/notes/{note_id}",
        response_model=DeleteResponse,
        summary="Delete a Note",
        tags=["Notes"],
    )
    async def delete_note(
        note_id: str,
        mgr: NotesManager = Depends(get_manager),
        lock: asyncio.Lock = Depends(get_lock),
    ):
        async with lock:
            deleted_note = mgr.delete_note(note_id)
        return DeleteResponse(
            deleted=True,
            id=deleted_note["id"],
            message=f"Note '{deleted_note['id']}' deleted successfully.",
        )

    # 8. Search Notes
    @app.get(
        "/search",
        response_model=List[SearchResultNote],
        summary="Search Notes",
        tags=["Search"],
    )
    async def search(
        query: str = Query(..., description="Search query string"),
        method: str = Query(DEFAULT_SEARCH_METHOD, description="Search method: 'tfidf' or 'keyword'"),
        top_k: int = Query(3, ge=1, le=100, description="Maximum results to return"),
        mgr: NotesManager = Depends(get_manager),
    ):
        cleaned_query = query.strip()
        if not cleaned_query:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Search query cannot be empty or whitespace-only.",
            )
        if method not in SUPPORTED_SEARCH_METHODS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid search method '{method}'. Must be one of {list(SUPPORTED_SEARCH_METHODS)}",
            )
        results = mgr.search_notes(query=cleaned_query, method=method, top_k=top_k)
        return results

    # 9. Load Starter Notes
    @app.post(
        "/notes/load-starter",
        response_model=StarterNotesLoadResponse,
        summary="Load Starter Notes",
        tags=["Notes"],
    )
    async def load_starter_notes(
        mgr: NotesManager = Depends(get_manager),
        lock: asyncio.Lock = Depends(get_lock),
    ):
        async with lock:
            loaded_notes = mgr.load_starter_notes()
        return StarterNotesLoadResponse(
            loaded_count=len(loaded_notes),
            notes=loaded_notes,
            message="Starter notes loaded successfully.",
        )

    return app


# Default app instance for Uvicorn
app = create_app()
