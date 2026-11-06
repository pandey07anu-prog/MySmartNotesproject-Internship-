"""
Smart Notes Assistant - MongoDB Connection & Index Management
Provides a singleton connection manager supporting MongoDB Atlas with
automatic fallback to mongomock for local development and unit testing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import pymongo
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

logger = logging.getLogger("smart_notes.database")


class MongoDBManager:
    _instance: Optional["MongoDBManager"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    _is_mock: bool = False

    def __new__(cls) -> "MongoDBManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> Database:
        """Establish connection to MongoDB Atlas or fallback to MongoMock."""
        if self._db is not None:
            return self._db

        uri = settings.MONGODB_URI.strip()
        db_name = settings.DATABASE_NAME

        if uri:
            try:
                logger.info(f"Connecting to MongoDB Atlas at {uri.split('@')[-1] if '@' in uri else 'configured URI'}...")
                client = MongoClient(
                    uri,
                    serverSelectionTimeoutMS=3000,
                    connectTimeoutMS=3000,
                    socketTimeoutMS=5000,
                )
                # Verify ping
                client.admin.command("ping")
                self._client = client
                self._db = client[db_name]
                self._is_mock = False
                logger.info(f"Connected to live MongoDB Atlas database: {db_name}")
            except Exception as e:
                logger.warning(f"Failed to connect to MongoDB Atlas ({e}). Falling back to in-memory MongoMock.")
                self._client = None
                self._db = None

        if self._db is None:
            import mongomock
            logger.info("Initializing in-memory MongoMock database for local execution & testing.")
            self._client = mongomock.MongoClient()
            self._db = self._client[db_name]
            self._is_mock = True

        self._ensure_indexes()
        return self._db

    def _ensure_indexes(self) -> None:
        """Create necessary indexes for uniqueness, performance, and TTL expiration."""
        if self._db is None:
            return

        try:
            # 1. Users collection
            self._db.users.create_index([("email", pymongo.ASCENDING)], unique=True)

            # 2. Notes collection
            # Compound unique index on user_id + note_id
            self._db.notes.create_index(
                [("user_id", pymongo.ASCENDING), ("note_id", pymongo.ASCENDING)],
                unique=True
            )
            self._db.notes.create_index([("user_id", pymongo.ASCENDING), ("category", pymongo.ASCENDING)])
            self._db.notes.create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])

            # 3. Sessions collection
            self._db.sessions.create_index([("session_id", pymongo.ASCENDING)], unique=True)
            self._db.sessions.create_index([("user_id", pymongo.ASCENDING)])
            if not self._is_mock:
                self._db.sessions.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0)
                self._db.email_verification_tokens.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0)
                self._db.password_reset_tokens.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0)

            # 4. Token collections
            self._db.email_verification_tokens.create_index([("token_hash", pymongo.ASCENDING)], unique=True)
            self._db.password_reset_tokens.create_index([("token_hash", pymongo.ASCENDING)], unique=True)

            logger.info("MongoDB indexes verified successfully.")
        except Exception as e:
            logger.warning(f"Index creation note: {e}")

    def get_database(self) -> Database:
        if self._db is None:
            return self.connect()
        return self._db

    def get_client(self) -> MongoClient:
        if self._client is None:
            self.connect()
        return self._client

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    def ping(self) -> bool:
        if self._is_mock:
            return True
        if self._client is None:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None


db_manager = MongoDBManager()


def get_db() -> Database:
    """FastAPI Dependency for database access."""
    return db_manager.get_database()

