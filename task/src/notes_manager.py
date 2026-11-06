"""
Smart Notes Assistant - Notes Management & Business Logic Layer
Phase 5: Production-Quality Notes Management & Persistent Storage

This module provides full CRUD functionality, category filtering, idempotent
starter-note loading, persistent monotonic unique ID generation, and seamless
integration with the genuine Phase 3/4 machine-learning classification pipeline.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.data_ingestion import get_project_root, load_starter_notes as ingest_starter_notes
from src.notes_storage import NotesStorage, StorageCorruptedError, StorageValidationError
from src.search_engine import DEFAULT_SEARCH_METHOD, search_notes as search_notes_engine
from src.uncertainty import (
    ALLOWED_CATEGORIES,
    UncertaintyModelError,
    load_uncertainty_model,
    predict_with_uncertainty,
    validate_threshold,
)

MAX_NOTE_TEXT_LENGTH = 1000
MINIMUM_NEW_NOTE_COUNTER = 13


class NotesManagerError(Exception):
    """Base exception for notes manager operations."""
    pass


class NoteNotFoundError(NotesManagerError):
    """Raised when a note ID does not exist."""
    pass


class NoteValidationError(NotesManagerError, ValueError):
    """Raised when note text fails validation (empty, whitespace, >1000 characters)."""
    pass


class CategoryValidationError(NotesManagerError, ValueError):
    """Raised when an unsupported category is supplied to filtering or search."""
    pass


class StarterNoteConflictError(NotesManagerError):
    """Raised when a starter note collides with an existing note having different content."""
    pass


class DuplicateIdError(NotesManagerError):
    """Raised if an ID collision is detected during note insertion."""
    pass


def validate_note_content(text: Any) -> str:
    """
    Validate note text according to Phase 5 specifications:
    - Must be a string.
    - Must not be empty.
    - Must not be whitespace-only.
    - Must not exceed 1000 characters.
    - Preserves user text exactly without truncation.
    """
    if not isinstance(text, str):
        raise TypeError(f"Note text must be a string, got {type(text).__name__}: {text!r}")

    stripped = text.strip()
    if not stripped:
        raise NoteValidationError("Note text cannot be empty or whitespace-only.")

    if len(text) > MAX_NOTE_TEXT_LENGTH:
        raise NoteValidationError(
            f"Note text exceeds maximum length of {MAX_NOTE_TEXT_LENGTH} characters "
            f"(got {len(text)} characters)."
        )

    return text


class NotesManager:
    """
    Manages notes CRUD operations, persistent storage synchronization,
    and genuine ML uncertainty classification integration.
    """

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        model_path: Optional[Union[str, Path]] = None,
        uncertainty_threshold: float = 0.40,
        auto_create_storage: bool = True
    ) -> None:
        """
        Initialize the NotesManager.
        
        Loads the trained ML classification pipeline ONCE.
        Does not retrain or reload the model on each operation.
        """
        root = get_project_root()

        # 1. Resolve storage path
        if storage_path is not None:
            self.storage_file = Path(storage_path).resolve()
        else:
            self.storage_file = root / "data" / "notes.json"

        self.storage = NotesStorage(self.storage_file)
        if auto_create_storage and not self.storage.exists():
            self.storage.initialize_storage()

        # 2. Resolve model path and load ONCE
        if model_path is not None:
            self.model_file = Path(model_path).resolve()
        else:
            self.model_file = root / "models" / "notes_pipeline.joblib"

        self.threshold = validate_threshold(uncertainty_threshold)
        self.model = load_uncertainty_model(self.model_file)

    def _get_current_timestamp(self) -> str:
        """Return the current ISO-8601 formatted UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _allocate_next_id(self, data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Allocate a persistent, monotonic unique ID starting from next_id.
        Ensures the allocated ID does not collide with any existing note.
        """
        existing_ids = {note["id"] for note in data.get("notes", [])}
        counter = int(data.get("next_id", MINIMUM_NEW_NOTE_COUNTER))

        while True:
            candidate_id = f"N{counter:03d}"
            if candidate_id not in existing_ids:
                break
            counter += 1

        next_counter = counter + 1
        return candidate_id, next_counter

    def get_next_id(self) -> str:
        """
        Inspect the next note ID that will be generated without incrementing the counter.
        """
        data = self.storage.load()
        candidate_id, _ = self._allocate_next_id(data)
        return candidate_id

    def count(self) -> int:
        """Return the total number of notes currently in storage."""
        data = self.storage.load()
        return len(data.get("notes", []))

    def add_note(self, text: str) -> Dict[str, Any]:
        """
        Add a new personal note.
        
        Workflow:
        1. Validates text (string, non-empty, non-whitespace, <= 1000 chars).
        2. Generates persistent unique ID starting at N013.
        3. Classifies text using the existing ML pipeline.
        4. Applies uncertainty threshold (default 0.40).
        5. Preserves predicted category even if uncertain.
        6. Atomically saves note and updated counter to storage.
        7. Returns the saved note dictionary.
        """
        valid_text = validate_note_content(text)

        # Classify note using genuine Phase 4 ML pipeline
        pred = predict_with_uncertainty(valid_text, self.model, threshold=self.threshold)

        data = self.storage.load()
        note_id, next_counter = self._allocate_next_id(data)

        timestamp = self._get_current_timestamp()
        new_note: Dict[str, Any] = {
            "id": note_id,
            "text": valid_text,
            "category": pred["category"],
            "confidence": pred["confidence"],
            "uncertain": pred["uncertain"],
            "created_at": timestamp,
            "updated_at": timestamp
        }

        # Update storage state atomically
        data["notes"].append(new_note)
        data["next_id"] = next_counter
        self.storage.save(data)

        return copy.deepcopy(new_note)

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """
        Retrieve a single note by its unique ID.
        
        Raises:
            NoteNotFoundError: If the note ID is not found.
        """
        if not isinstance(note_id, str) or not note_id.strip():
            raise NoteNotFoundError(f"Invalid note ID: {note_id!r}")

        data = self.storage.load()
        for note in data.get("notes", []):
            if note["id"] == note_id:
                return copy.deepcopy(note)

        raise NoteNotFoundError(f"Note with ID '{note_id}' not found.")

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """
        Retrieve all notes from storage.
        
        Returns:
            List[Dict[str, Any]]: Deep copies of all stored notes.
        """
        data = self.storage.load()
        return copy.deepcopy(data.get("notes", []))

    def filter_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Filter notes by exact classification category.
        
        Args:
            category: One of 'Study', 'Money', 'Travel', 'Shopping'.
            
        Returns:
            List[Dict[str, Any]]: Matching notes, or an empty list if none match.
            
        Raises:
            CategoryValidationError: If category is not in ALLOWED_CATEGORIES.
        """
        if category not in ALLOWED_CATEGORIES:
            raise CategoryValidationError(
                f"Invalid category filter '{category}'. Must be one of {list(ALLOWED_CATEGORIES)}"
            )

        data = self.storage.load()
        matching = [note for note in data.get("notes", []) if note["category"] == category]
        return copy.deepcopy(matching)

    def update_note(self, note_id: str, new_text: str) -> Dict[str, Any]:
        """
        Update an existing note's text and reclassify it.
        
        Requirements:
        1. Finds note by ID (raises NoteNotFoundError if missing).
        2. Validates replacement text (string, non-empty, <= 1000 chars).
        3. Reclassifies text using the existing ML model.
        4. Recalculates confidence and uncertainty status.
        5. Preserves original ID and created_at timestamp.
        6. Updates updated_at timestamp.
        7. Atomically persists changes to disk.
        
        Returns:
            Dict[str, Any]: The updated note dictionary.
        """
        if not isinstance(note_id, str) or not note_id.strip():
            raise NoteNotFoundError(f"Invalid note ID: {note_id!r}")

        valid_text = validate_note_content(new_text)

        data = self.storage.load()
        target_note: Optional[Dict[str, Any]] = None

        for note in data.get("notes", []):
            if note["id"] == note_id:
                target_note = note
                break

        if target_note is None:
            raise NoteNotFoundError(f"Cannot update nonexistent note with ID '{note_id}'.")

        # Reclassify with genuine model
        pred = predict_with_uncertainty(valid_text, self.model, threshold=self.threshold)

        # Update fields in-place
        target_note["text"] = valid_text
        target_note["category"] = pred["category"]
        target_note["confidence"] = pred["confidence"]
        target_note["uncertain"] = pred["uncertain"]
        target_note["updated_at"] = self._get_current_timestamp()
        # Note: target_note["id"] and target_note["created_at"] remain strictly untouched

        self.storage.save(data)
        return copy.deepcopy(target_note)

    def delete_note(self, note_id: str) -> Dict[str, Any]:
        """
        Delete a note by its unique ID.
        
        Requirements:
        - Deletes note if present; raises NoteNotFoundError if missing.
        - Persists deletion atomically to storage.
        - Never decrements or reuses the next_id counter.
        
        Returns:
            Dict[str, Any]: The deleted note record.
        """
        if not isinstance(note_id, str) or not note_id.strip():
            raise NoteNotFoundError(f"Invalid note ID: {note_id!r}")

        data = self.storage.load()
        notes = data.get("notes", [])
        index_to_remove: Optional[int] = None

        for idx, note in enumerate(notes):
            if note["id"] == note_id:
                index_to_remove = idx
                break

        if index_to_remove is None:
            raise NoteNotFoundError(f"Cannot delete nonexistent note with ID '{note_id}'.")

        deleted_note = notes.pop(index_to_remove)

        # Note: data["next_id"] is deliberately NOT decremented.
        # Deleted IDs are NEVER reused.
        self.storage.save(data)
        return copy.deepcopy(deleted_note)

    def load_starter_notes(
        self,
        starter_file_path: Optional[Union[str, Path]] = None
    ) -> List[Dict[str, Any]]:
        """
        Load the 12 starter notes from data/starter_notes.json.
        
        Guarantees:
        - Preserves original IDs (N001-N012) and exact text.
        - Does NOT modify data/starter_notes.json.
        - Classifies each note using the genuine trained ML pipeline.
        - Idempotency: repeated execution does not duplicate notes.
        - Conflict detection: raises StarterNoteConflictError if an existing note
          shares a starter ID but has different text content.
        - Does not overwrite user notes.
        - Ensures next_id is at least 13.
        
        Returns:
            List[Dict[str, Any]]: All 12 starter notes currently stored.
        """
        root = get_project_root()
        if starter_file_path is not None:
            starter_path = Path(starter_file_path).resolve()
        else:
            starter_path = root / "data" / "starter_notes.json"

        raw_starter_notes = ingest_starter_notes(starter_path)

        data = self.storage.load()
        existing_notes_map = {n["id"]: n for n in data.get("notes", [])}

        new_notes_to_add: List[Dict[str, Any]] = []

        for starter_item in raw_starter_notes:
            s_id = starter_item["id"]
            s_text = starter_item["text"]

            if s_id in existing_notes_map:
                existing_note = existing_notes_map[s_id]
                # Check for content conflict
                if existing_note["text"] != s_text:
                    raise StarterNoteConflictError(
                        f"Conflict detected for starter note '{s_id}'. "
                        f"Existing text: {existing_note['text']!r} does not match "
                        f"starter text: {s_text!r}."
                    )
                # Already loaded with identical text -> Idempotent skip
                continue

            # Classify note using the genuine ML pipeline
            pred = predict_with_uncertainty(s_text, self.model, threshold=self.threshold)
            timestamp = self._get_current_timestamp()

            new_note_entry: Dict[str, Any] = {
                "id": s_id,
                "text": s_text,
                "category": pred["category"],
                "confidence": pred["confidence"],
                "uncertain": pred["uncertain"],
                "created_at": timestamp,
                "updated_at": timestamp
            }
            new_notes_to_add.append(new_note_entry)

        if new_notes_to_add:
            data["notes"].extend(new_notes_to_add)

        # Ensure next_id counter is at least 13 and exceeds any numeric ID present
        max_numeric_id = 0
        for n in data.get("notes", []):
            n_id = n.get("id", "")
            if n_id.startswith("N") and n_id[1:].isdigit():
                max_numeric_id = max(max_numeric_id, int(n_id[1:]))

        data["next_id"] = max(
            int(data.get("next_id", MINIMUM_NEW_NOTE_COUNTER)),
            MINIMUM_NEW_NOTE_COUNTER,
            max_numeric_id + 1
        )

        self.storage.save(data)

        # Return the 12 starter notes from storage
        updated_notes_map = {n["id"]: n for n in data["notes"]}
        return [copy.deepcopy(updated_notes_map[s["id"]]) for s in raw_starter_notes if s["id"] in updated_notes_map]

    def search_notes(
        self,
        query: str,
        method: str = DEFAULT_SEARCH_METHOD,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search all currently saved notes using the specified or default search method.
        
        Requirements:
        - Searches all saved notes (starter + user-created notes).
        - Returns ranked notes with 'score' and 'rank'.
        - Preserves 'id', 'text', 'category', 'confidence', 'uncertain'.
        - Immediately reflects added, updated, or deleted notes.
        - Defaults to DEFAULT_SEARCH_METHOD ('tfidf').
        """
        notes = self.get_all_notes()
        return search_notes_engine(query=query, notes=notes, method=method, top_k=top_k)

