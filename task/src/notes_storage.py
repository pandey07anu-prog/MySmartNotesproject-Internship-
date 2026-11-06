"""
Smart Notes Assistant - Persistent JSON Storage Layer
Phase 5: Production-Quality Notes Management & Persistent Storage

This module provides atomic, safe, and schema-validated JSON persistence for notes.
Key guarantees:
- Atomic writes: writes to a temporary file and atomically replaces the target.
- Corrupted file safety: never silently overwrites malformed or corrupted JSON.
- ID counter preservation: maintains and validates persistent unique IDs.
- UTF-8 integrity: preserves all Unicode text, including currency symbols like ₹.
- Deep-copy isolation: prevents in-memory modifications from polluting storage state.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

CURRENT_SCHEMA_VERSION = 1
MINIMUM_START_ID_NUM = 13


class NotesStorageError(Exception):
    """Base exception for notes storage errors."""
    pass


class StorageCorruptedError(NotesStorageError):
    """Raised when the storage JSON file is corrupted, malformed, or unreadable."""
    pass


class StorageValidationError(NotesStorageError):
    """Raised when the storage JSON data fails schema or data integrity validation."""
    pass


class NotesStorage:
    """
    Handles atomic, schema-validated file operations on data/notes.json.
    """

    def __init__(self, file_path: Union[str, Path]) -> None:
        self.file_path = Path(file_path).resolve()

    def exists(self) -> bool:
        """Return True if the storage file exists on disk."""
        return self.file_path.exists() and self.file_path.is_file()

    def initialize_storage(self) -> Dict[str, Any]:
        """
        Safely create and initialize the storage file if it does not exist.
        If the file already exists, it is loaded and validated without overwriting.
        
        Returns:
            Dict[str, Any]: The loaded or newly initialized storage dictionary.
        """
        if self.exists():
            return self.load()

        initial_data: Dict[str, Any] = {
            "version": CURRENT_SCHEMA_VERSION,
            "next_id": MINIMUM_START_ID_NUM,
            "notes": []
        }
        self.save(initial_data)
        return copy.deepcopy(initial_data)

    def load(self) -> Dict[str, Any]:
        """
        Load and rigorously validate the JSON database from disk.
        
        Returns:
            Dict[str, Any]: Deep copy of the stored data.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            StorageCorruptedError: If the file contains malformed JSON or encoding errors.
            StorageValidationError: If the JSON structure violates the storage schema.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Storage file does not exist: {self.file_path}")

        try:
            with open(self.file_path, "r", encoding="utf-8") as fp:
                raw_data = json.load(fp)
        except UnicodeDecodeError as e:
            raise StorageCorruptedError(
                f"Storage file contains invalid encoding at {self.file_path}: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise StorageCorruptedError(
                f"Storage file is corrupted or contains malformed JSON at {self.file_path}: {e}"
            ) from e
        except PermissionError as e:
            raise NotesStorageError(
                f"Permission denied reading storage file at {self.file_path}: {e}"
            ) from e
        except OSError as e:
            raise NotesStorageError(
                f"OS error reading storage file at {self.file_path}: {e}"
            ) from e

        self.validate_schema(raw_data)
        return copy.deepcopy(raw_data)

    def save(self, data: Dict[str, Any]) -> None:
        """
        Atomically persist data to the storage file using a temporary file.
        
        Ensures:
        - Schema is strictly validated before any write operation.
        - Data is written to a temporary file on the same filesystem.
        - File is synced to disk and replaced atomically via os.replace.
        - If an error occurs, the original file is left completely untouched.
        
        Args:
            data: Dictionary matching the storage schema.
            
        Raises:
            StorageValidationError: If candidate data violates schema rules.
            NotesStorageError: If disk write or file replacement fails.
        """
        self.validate_schema(data)

        # Ensure parent directory exists
        parent_dir = self.file_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        # Write to temporary file in the same directory for atomic os.replace
        temp_file_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent_dir,
                delete=False,
                prefix=f".{self.file_path.name}.",
                suffix=".tmp"
            ) as tf:
                temp_file_path = Path(tf.name)
                json.dump(data, tf, indent=2, ensure_ascii=False)
                tf.flush()
                os.fsync(tf.fileno())

            # Atomically replace target file
            os.replace(temp_file_path, self.file_path)
            temp_file_path = None
        except PermissionError as e:
            raise NotesStorageError(
                f"Permission denied writing to storage file at {self.file_path}: {e}"
            ) from e
        except OSError as e:
            raise NotesStorageError(
                f"Failed atomic write to storage file at {self.file_path}: {e}"
            ) from e
        finally:
            if temp_file_path is not None and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def validate_schema(data: Any) -> None:
        """
        Rigorously validate that the data conforms to the required storage schema.
        
        Schema rules:
        - Root must be a dictionary.
        - 'version' must be an integer >= 1.
        - 'next_id' must be an integer >= 1.
        - 'notes' must be a list of note objects.
        - Each note must contain required keys: id, text, category, confidence,
          uncertain, created_at, updated_at.
        - No duplicate note IDs.
        """
        if not isinstance(data, dict):
            raise StorageValidationError(
                f"Storage root must be a JSON object (dict), got {type(data).__name__}"
            )

        # Validate root keys
        required_root_keys = {"version", "next_id", "notes"}
        missing_root_keys = required_root_keys - set(data.keys())
        if missing_root_keys:
            raise StorageValidationError(
                f"Storage data missing required root keys: {sorted(missing_root_keys)}"
            )

        # Validate version
        version = data.get("version")
        if not isinstance(version, int) or version < 1:
            raise StorageValidationError(
                f"Storage 'version' must be a positive integer, got: {version!r}"
            )

        # Validate next_id
        next_id = data.get("next_id")
        if isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1:
            raise StorageValidationError(
                f"Storage 'next_id' must be a positive integer, got: {next_id!r}"
            )

        # Validate notes list
        notes = data.get("notes")
        if not isinstance(notes, list):
            raise StorageValidationError(
                f"Storage 'notes' must be a list, got {type(notes).__name__}"
            )

        seen_ids: Set[str] = set()
        required_note_keys = {
            "id", "text", "category", "confidence",
            "uncertain", "created_at", "updated_at"
        }

        for idx, note in enumerate(notes):
            if not isinstance(note, dict):
                raise StorageValidationError(
                    f"Note at index {idx} must be a dictionary, got {type(note).__name__}"
                )

            missing_keys = required_note_keys - set(note.keys())
            if missing_keys:
                raise StorageValidationError(
                    f"Note at index {idx} missing required fields: {sorted(missing_keys)}"
                )

            # Validate ID
            note_id = note["id"]
            if not isinstance(note_id, str) or not note_id.strip():
                raise StorageValidationError(
                    f"Note at index {idx} has invalid 'id': {note_id!r}"
                )
            if note_id in seen_ids:
                raise StorageValidationError(
                    f"Duplicate note ID '{note_id}' detected at index {idx}"
                )
            seen_ids.add(note_id)

            # Validate text
            note_text = note["text"]
            if not isinstance(note_text, str) or not note_text.strip():
                raise StorageValidationError(
                    f"Note '{note_id}' has empty or whitespace-only 'text'"
                )

            # Validate category
            category = note["category"]
            if not isinstance(category, str) or not category.strip():
                raise StorageValidationError(
                    f"Note '{note_id}' has invalid 'category': {category!r}"
                )

            # Validate confidence
            confidence = note["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise StorageValidationError(
                    f"Note '{note_id}' confidence must be numeric, got: {confidence!r}"
                )
            if float(confidence) < 0.0 or float(confidence) > 1.0:
                raise StorageValidationError(
                    f"Note '{note_id}' confidence must be in [0.0, 1.0], got: {confidence}"
                )

            # Validate uncertain flag
            uncertain = note["uncertain"]
            if not isinstance(uncertain, bool):
                raise StorageValidationError(
                    f"Note '{note_id}' 'uncertain' must be boolean, got: {uncertain!r}"
                )

            # Validate timestamps
            created_at = note["created_at"]
            updated_at = note["updated_at"]
            if not isinstance(created_at, str) or not created_at.strip():
                raise StorageValidationError(
                    f"Note '{note_id}' 'created_at' must be a non-empty ISO-8601 string"
                )
            if not isinstance(updated_at, str) or not updated_at.strip():
                raise StorageValidationError(
                    f"Note '{note_id}' 'updated_at' must be a non-empty ISO-8601 string"
                )

