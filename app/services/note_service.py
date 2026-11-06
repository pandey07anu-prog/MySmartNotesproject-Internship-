"""
Smart Notes Assistant - Notes Management Service
Handles note CRUD operations, ML reclassification, user-scoped querying,
and idempotent starter note seeding.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.config import settings, PROJECT_ROOT
from app.services.classifier import classifier_service

logger = logging.getLogger("smart_notes.note_service")


class NoteService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def generate_next_note_id(cls, db: Database, user_id: str) -> str:
        """
        Generate a unique note_id for the user.
        Ensures user-created notes never collide with or reuse N001-N012.
        Assigns N013, N014, ... or increments from highest existing N###.
        """
        user_notes = list(db.notes.find({"user_id": str(user_id)}, {"note_id": 1}))
        existing_numbers = []
        for n in user_notes:
            nid = n.get("note_id", "")
            match = re.match(r"^N(\d+)$", nid)
            if match:
                existing_numbers.append(int(match.group(1)))

        # N001 through N012 are reserved exclusively for official starter notes
        max_num = max(existing_numbers) if existing_numbers else 12
        next_num = max(13, max_num + 1)
        return f"N{next_num:03d}"

    @classmethod
    def create_note(cls, db: Database, user_id: str, text: str) -> Dict[str, Any]:
        """
        Classifies note text with the ML model and saves it to MongoDB.
        Enforces user ownership.
        """
        user_id_str = str(user_id)
        prediction = classifier_service.classify(text)
        note_id = cls.generate_next_note_id(db, user_id_str)
        now = cls._now_iso()

        doc = {
            "note_id": note_id,
            "user_id": user_id_str,
            "text": text.strip(),
            "category": prediction["category"],
            "confidence": prediction["confidence"],
            "uncertain": prediction["uncertain"],
            "created_at": now,
            "updated_at": now,
        }

        db.notes.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @classmethod
    def get_notes(
        cls,
        db: Database,
        user_id: str,
        category: Optional[str] = None,
        uncertain_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve notes strictly belonging to user_id, with optional filtering."""
        query: Dict[str, Any] = {"user_id": str(user_id)}
        if category and category.strip():
            query["category"] = category.strip()
        if uncertain_only:
            query["uncertain"] = True

        cursor = db.notes.find(query).sort("created_at", -1)
        notes = []
        for doc in cursor:
            doc.pop("_id", None)
            notes.append(doc)
        return notes

    @classmethod
    def get_note_by_id(cls, db: Database, user_id: str, note_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific note, strictly verifying user ownership."""
        doc = db.notes.find_one({"user_id": str(user_id), "note_id": note_id})
        if doc:
            doc.pop("_id", None)
            return doc
        return None

    @classmethod
    def update_note(cls, db: Database, user_id: str, note_id: str, new_text: str) -> Optional[Dict[str, Any]]:
        """
        Reclassifies updated text and updates MongoDB document.
        Preserves original created_at timestamp.
        """
        existing = db.notes.find_one({"user_id": str(user_id), "note_id": note_id})
        if not existing:
            return None

        prediction = classifier_service.classify(new_text)
        now = cls._now_iso()

        update_fields = {
            "text": new_text.strip(),
            "category": prediction["category"],
            "confidence": prediction["confidence"],
            "uncertain": prediction["uncertain"],
            "updated_at": now,
        }

        db.notes.update_one(
            {"user_id": str(user_id), "note_id": note_id},
            {"$set": update_fields}
        )

        existing.update(update_fields)
        existing.pop("_id", None)
        return existing

    @classmethod
    def delete_note(cls, db: Database, user_id: str, note_id: str) -> bool:
        """Deletes a note, strictly verifying user ownership."""
        result = db.notes.delete_one({"user_id": str(user_id), "note_id": note_id})
        return result.deleted_count > 0

    @classmethod
    def reclassify_user_notes(cls, db: Database, user_id: str) -> int:
        """
        Reclassifies all existing notes for the user with the latest ML model pipeline.
        Useful when the model has been retrained with upgraded vocabulary and accuracy.
        """
        cursor = db.notes.find({"user_id": str(user_id)})
        count = 0
        for doc in cursor:
            pred = classifier_service.classify(doc.get("text", ""))
            db.notes.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "category": pred["category"],
                    "confidence": pred["confidence"],
                    "uncertain": pred["uncertain"],
                    "updated_at": cls._now_iso(),
                }}
            )
            count += 1
        return count

    @classmethod
    def seed_starter_notes(cls, db: Database, user_id: str) -> Dict[str, Any]:
        """
        Idempotently seeds the 12 official starter notes from data/starter_notes.json
        into the user's workspace. Preserves IDs N001-N012.
        Loading multiple times will not duplicate or overwrite existing notes.
        """
        user_id_str = str(user_id)
        starter_path = PROJECT_ROOT / "data" / "starter_notes.json"
        if not starter_path.exists():
            return {"inserted": 0, "existing": 0, "message": "Starter notes file not found."}

        with open(starter_path, "r", encoding="utf-8") as f:
            starters = json.load(f)

        inserted_count = 0
        existing_count = 0
        now = cls._now_iso()

        for item in starters:
            nid = item["id"]
            text = item["text"]

            # Check if this user already has this starter note
            existing = db.notes.find_one({"user_id": user_id_str, "note_id": nid})
            if existing:
                existing_count += 1
                continue

            prediction = classifier_service.classify(text)
            doc = {
                "note_id": nid,
                "user_id": user_id_str,
                "text": text,
                "category": prediction["category"],
                "confidence": prediction["confidence"],
                "uncertain": prediction["uncertain"],
                "created_at": now,
                "updated_at": now,
            }
            try:
                db.notes.insert_one(doc)
                inserted_count += 1
            except DuplicateKeyError:
                existing_count += 1

        return {
            "inserted": inserted_count,
            "existing": existing_count,
            "total_starters": len(starters),
            "message": f"Seeded {inserted_count} new starter notes ({existing_count} already existed)."
        }

    @classmethod
    def get_dashboard_stats(cls, db: Database, user_id: str) -> Dict[str, Any]:
        """
        Calculates all dashboard metrics strictly from MongoDB for this user.
        No fake data.
        """
        user_id_str = str(user_id)
        total = db.notes.count_documents({"user_id": user_id_str})
        study = db.notes.count_documents({"user_id": user_id_str, "category": "Study"})
        money = db.notes.count_documents({"user_id": user_id_str, "category": "Money"})
        travel = db.notes.count_documents({"user_id": user_id_str, "category": "Travel"})
        shopping = db.notes.count_documents({"user_id": user_id_str, "category": "Shopping"})
        uncertain = db.notes.count_documents({"user_id": user_id_str, "uncertain": True})

        recent_cursor = db.notes.find({"user_id": user_id_str}).sort("created_at", -1).limit(5)
        recent_notes = []
        for n in recent_cursor:
            n.pop("_id", None)
            recent_notes.append(n)

        return {
            "total_notes": total,
            "study_count": study,
            "money_count": money,
            "travel_count": travel,
            "shopping_count": shopping,
            "uncertain_count": uncertain,
            "recent_notes": recent_notes,
        }


note_service = NoteService()

