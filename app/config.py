"""
Smart Notes Assistant - Configuration Module
Loads application configuration from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env if present
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)


class Settings:
    PROJECT_NAME: str = "Smart Notes Assistant"
    TAGLINE: str = "Your thoughts, intelligently organized."
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

    # MongoDB Atlas
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "smart_notes_db")

    # Security & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "smart-notes-production-grade-secret-key-2026-secure")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # Email / SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@smartnotes.ai")

    # Machine Learning & Search
    UNCERTAINTY_THRESHOLD: float = float(os.getenv("UNCERTAINTY_THRESHOLD", "0.50"))
    MIN_SEARCH_SIMILARITY: float = float(os.getenv("MIN_SEARCH_SIMILARITY", "0.05"))
    MODEL_PATH: str = str(PROJECT_ROOT / "model" / "classifier.joblib")

    # Cookie security
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1")
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")


settings = Settings()
