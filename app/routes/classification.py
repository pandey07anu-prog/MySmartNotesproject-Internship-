"""
Smart Notes Assistant - Classification Route (Official Contract Endpoint)
Implements POST /classify strictly compliant with API_CONTRACT.md and examples/test_api.py.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.schemas.note import ClassifyRequest, ClassifyResponse
from app.services.classifier import classifier_service

router = APIRouter(tags=["Classification"])
logger = logging.getLogger("smart_notes.routes.classification")


@router.post("/classify", response_model=ClassifyResponse)
async def classify_note(payload: ClassifyRequest) -> ClassifyResponse:
    """
    Classify a note into one of the four categories: Study, Money, Travel, Shopping.
    Evaluates uncertainty based on model predicted class probability.
    
    Compatible with the official assessment test runner:
    `python examples/test_api.py --url http://127.0.0.1:8000/classify`
    """
    try:
        result = classifier_service.classify(payload.text)
        return ClassifyResponse(
            category=result["category"],
            uncertain=result["uncertain"],
            confidence=result["confidence"]
        )
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification model inference error."
        )

