"""
Smart Notes Assistant - Note Schemas
Defines request and response schemas for note classification, storage, and retrieval.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, StrictStr, field_validator


class ClassifyRequest(BaseModel):
    """
    Contract-compliant payload for POST /classify.
    StrictStr enforces that numbers, booleans, and null are rejected with 422.
    """
    text: StrictStr = Field(..., description="Note text to classify")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class ClassifyResponse(BaseModel):
    category: str
    uncertain: bool
    confidence: float


class NoteCreateRequest(BaseModel):
    text: StrictStr = Field(..., description="Note content")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class NoteUpdateRequest(BaseModel):
    text: StrictStr = Field(..., description="Updated note content")

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Note text cannot be empty or whitespace-only.")
        if len(v) > 1000:
            raise ValueError("Note text exceeds maximum length of 1000 characters.")
        return v


class NoteResponse(BaseModel):
    note_id: str
    text: str
    category: str
    confidence: float
    uncertain: bool
    created_at: str
    updated_at: str


class SearchResultItem(BaseModel):
    note_id: str
    text: str
    category: str
    confidence: float
    uncertain: bool
    score: float
    created_at: str
    updated_at: str


class SearchResponse(BaseModel):
    query: str
    method: str
    total_matches: int
    results: List[SearchResultItem]


class DashboardStatsResponse(BaseModel):
    total_notes: int
    study_count: int
    money_count: int
    travel_count: int
    shopping_count: int
    uncertain_count: int
    recent_notes: List[NoteResponse]

