"""
Smart Notes Assistant - Main FastAPI Application
Coordinates database connections, ML model lifecycle, CORS middleware,
REST endpoints, and static frontend hosting.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Ensure immediate unbuffered console logging for Render
sys.stdout.reconfigure(line_buffering=True)

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings, PROJECT_ROOT
from app.database.mongodb import db_manager
from app.routes.auth import router as auth_router
from app.routes.classification import router as classification_router
from app.routes.dashboard import router as dashboard_router
from app.routes.notes import router as notes_router
from app.routes.search import router as search_router
from app.routes.users import router as users_router
from app.services.classifier import classifier_service

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart_notes.main")

STATIC_DIR = PROJECT_ROOT / "app" / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    port = os.environ.get("PORT", "10000")
    print(f"[STARTUP] Smart Notes Assistant initializing on port {port}...", flush=True)
    logger.info("Initializing Smart Notes Assistant backend...")
    
    # 1. Connect MongoDB
    db_manager.connect()
    
    # 2. Pre-load ML model into memory once
    try:
        classifier_service.load_model()
        logger.info("ML Classifier pipeline loaded and ready for sub-second inference.")
    except Exception as e:
        logger.error(f"Error initializing classifier model: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Smart Notes Assistant backend...")
    db_manager.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent personal notes management platform powered by genuine machine learning.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        settings.APP_BASE_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for contract compliance on invalid request bodies
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Ensure invalid JSON, missing fields, non-strings, or whitespace-only inputs
    return standard 422 Unprocessable Entity responses safely encoded.
    """
    errors = exc.errors()
    # Format error messages cleanly without non-serializable exception objects
    clean_errors = []
    for err in errors:
        clean_err = {
            "type": err.get("type", "validation_error"),
            "loc": err.get("loc", []),
            "msg": str(err.get("msg", "Invalid value")),
        }
        clean_errors.append(clean_err)

    first_msg = clean_errors[0]["msg"] if clean_errors else "Invalid request payload."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": first_msg, "errors": clean_errors}
    )


# Global HTTP Exception Handler ensuring all errors return valid JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
        headers=getattr(exc, "headers", None)
    )


# Global Unhandled Exception Handler guaranteeing JSON output (never plain text "Internal Server Error")
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again."}
    )



# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check verifying database connectivity and model status."""
    db_ok = db_manager.ping()
    model_ok = classifier_service.is_loaded
    return {
        "status": "healthy" if (db_ok and model_ok) else "degraded",
        "service": settings.PROJECT_NAME,
        "database": {
            "connected": db_ok,
            "mode": "mock" if db_manager.is_mock else "mongodb_atlas",
        },
        "classifier": {
            "loaded": model_ok,
            "classes": classifier_service._classes,
            "uncertainty_threshold": classifier_service._threshold,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include Routers
app.include_router(classification_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(notes_router)
app.include_router(search_router)
app.include_router(dashboard_router)

# Mount static directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Serve landing page & single-page application
@app.get("/", include_in_schema=False)
async def serve_index():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return JSONResponse(content={"message": "Smart Notes Assistant API is running. Access /docs for API schema."})


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
