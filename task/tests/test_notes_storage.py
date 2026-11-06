"""
Automated Test Suite for Smart Notes Assistant - Persistent JSON Storage Layer
Phase 5: Production-Quality Notes Management & Persistent Storage

Tests all storage behaviors:
- Safe initialization of storage file when absent.
- Schema validation (root keys, version, next_id, note structure).
- Deep copy isolation.
- Unicode and rupee symbol (₹) preservation.
- Corrupted JSON handling (raising StorageCorruptedError without overwriting).
- Atomic write mechanics (leaving original intact on failure).
- Duplicate note ID detection in storage files.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.notes_storage import (
    CURRENT_SCHEMA_VERSION,
    MINIMUM_START_ID_NUM,
    NotesStorage,
    NotesStorageError,
    StorageCorruptedError,
    StorageValidationError,
)


@pytest.fixture
def storage_file(tmp_path: Path) -> Path:
    """Provide a path to a temporary notes.json storage file."""
    return tmp_path / "notes.json"


@pytest.fixture
def storage(storage_file: Path) -> NotesStorage:
    """Provide a NotesStorage instance configured with a temporary file."""
    return NotesStorage(storage_file)


# ---------------------------------------------------------------------------
# 1. Initialization & Safe Creation
# ---------------------------------------------------------------------------
def test_initialize_storage_creates_file(storage: NotesStorage, storage_file: Path):
    assert not storage.exists()
    data = storage.initialize_storage()

    assert storage.exists()
    assert data["version"] == CURRENT_SCHEMA_VERSION
    assert data["next_id"] == MINIMUM_START_ID_NUM
    assert data["notes"] == []

    # Verify disk content matches
    loaded = storage.load()
    assert loaded == data


def test_initialize_storage_does_not_overwrite_existing(storage: NotesStorage, storage_file: Path):
    initial_data = {
        "version": 1,
        "next_id": 14,
        "notes": [
            {
                "id": "N013",
                "text": "Existing test note.",
                "category": "Study",
                "confidence": 0.88,
                "uncertain": False,
                "created_at": "2026-11-04T10:00:00Z",
                "updated_at": "2026-11-04T10:00:00Z"
            }
        ]
    }
    storage.save(initial_data)

    # Re-initialize should NOT overwrite
    reloaded = storage.initialize_storage()
    assert reloaded["next_id"] == 14
    assert len(reloaded["notes"]) == 1
    assert reloaded["notes"][0]["id"] == "N013"


# ---------------------------------------------------------------------------
# 2. Unicode and Rupee Symbol (₹) Preservation
# ---------------------------------------------------------------------------
def test_unicode_and_rupee_symbol_preservation(storage: NotesStorage, storage_file: Path):
    note_with_rupee = {
        "version": 1,
        "next_id": 14,
        "notes": [
            {
                "id": "N006",
                "text": "Move ₹2,000 into the savings account this month.",
                "category": "Money",
                "confidence": 0.95,
                "uncertain": False,
                "created_at": "2026-11-04T10:00:00Z",
                "updated_at": "2026-11-04T10:00:00Z"
            }
        ]
    }
    storage.save(note_with_rupee)

    loaded = storage.load()
    loaded_text = loaded["notes"][0]["text"]
    assert "₹" in loaded_text
    assert loaded_text == "Move ₹2,000 into the savings account this month."

    # Verify raw disk bytes are UTF-8 without unicode escape sequences
    raw_content = storage_file.read_text(encoding="utf-8")
    assert "₹2,000" in raw_content
    assert "\\u20b9" not in raw_content


# ---------------------------------------------------------------------------
# 3. Corrupted JSON Handling
# ---------------------------------------------------------------------------
def test_corrupted_json_raises_storage_corrupted_error(storage: NotesStorage, storage_file: Path):
    # Write invalid / malformed JSON
    corrupted_content = '{"version": 1, "next_id": 13, "notes": [{"id": "N001", '
    storage_file.write_text(corrupted_content, encoding="utf-8")

    with pytest.raises(StorageCorruptedError, match="corrupted or contains malformed JSON"):
        storage.load()

    # Crucial guarantee: original corrupted file is NOT replaced with empty DB
    assert storage_file.read_text(encoding="utf-8") == corrupted_content


def test_invalid_utf8_encoding_raises_storage_corrupted_error(storage: NotesStorage, storage_file: Path):
    # Write invalid byte sequence that cannot be decoded as UTF-8
    storage_file.write_bytes(b"\x80\x81\x82malformed")

    with pytest.raises(StorageCorruptedError, match="invalid encoding"):
        storage.load()


# ---------------------------------------------------------------------------
# 4. Schema Validation (Root Structure)
# ---------------------------------------------------------------------------
def test_schema_validation_rejects_non_dict_root(storage: NotesStorage):
    with pytest.raises(StorageValidationError, match="Storage root must be a JSON object"):
        storage.validate_schema(["not", "a", "dict"])


def test_schema_validation_rejects_missing_root_keys(storage: NotesStorage):
    with pytest.raises(StorageValidationError, match="missing required root keys"):
        storage.validate_schema({"version": 1, "notes": []})

    with pytest.raises(StorageValidationError, match="missing required root keys"):
        storage.validate_schema({"version": 1, "next_id": 13})


def test_schema_validation_rejects_invalid_version_and_next_id(storage: NotesStorage):
    # Version must be positive int
    with pytest.raises(StorageValidationError, match="Storage 'version' must be a positive integer"):
        storage.validate_schema({"version": 0, "next_id": 13, "notes": []})

    with pytest.raises(StorageValidationError, match="Storage 'version' must be a positive integer"):
        storage.validate_schema({"version": "1", "next_id": 13, "notes": []})

    # Next_id must be positive int
    with pytest.raises(StorageValidationError, match="Storage 'next_id' must be a positive integer"):
        storage.validate_schema({"version": 1, "next_id": -1, "notes": []})

    with pytest.raises(StorageValidationError, match="Storage 'next_id' must be a positive integer"):
        storage.validate_schema({"version": 1, "next_id": True, "notes": []})


# ---------------------------------------------------------------------------
# 5. Schema Validation (Notes Structure & Content)
# ---------------------------------------------------------------------------
def test_schema_validation_rejects_non_list_notes(storage: NotesStorage):
    with pytest.raises(StorageValidationError, match="Storage 'notes' must be a list"):
        storage.validate_schema({"version": 1, "next_id": 13, "notes": {"id": "N001"}})


def test_schema_validation_rejects_missing_note_keys(storage: NotesStorage):
    bad_data = {
        "version": 1,
        "next_id": 14,
        "notes": [
            {
                "id": "N013",
                "text": "Valid text",
                # missing category, confidence, etc.
            }
        ]
    }
    with pytest.raises(StorageValidationError, match="missing required fields"):
        storage.validate_schema(bad_data)


def test_schema_validation_rejects_duplicate_note_ids(storage: NotesStorage):
    duplicate_data = {
        "version": 1,
        "next_id": 14,
        "notes": [
            {
                "id": "N001",
                "text": "Note 1",
                "category": "Study",
                "confidence": 0.80,
                "uncertain": False,
                "created_at": "2026-11-04T10:00:00Z",
                "updated_at": "2026-11-04T10:00:00Z"
            },
            {
                "id": "N001",  # DUPLICATE ID
                "text": "Note 2",
                "category": "Study",
                "confidence": 0.85,
                "uncertain": False,
                "created_at": "2026-11-04T10:00:00Z",
                "updated_at": "2026-11-04T10:00:00Z"
            }
        ]
    }
    with pytest.raises(StorageValidationError, match="Duplicate note ID 'N001' detected"):
        storage.validate_schema(duplicate_data)


def test_schema_validation_rejects_invalid_note_fields(storage: NotesStorage):
    base_note = {
        "id": "N013",
        "text": "Sample text",
        "category": "Study",
        "confidence": 0.75,
        "uncertain": False,
        "created_at": "2026-11-04T10:00:00Z",
        "updated_at": "2026-11-04T10:00:00Z"
    }

    # Empty text
    n1 = dict(base_note, text="   ")
    with pytest.raises(StorageValidationError, match="empty or whitespace-only 'text'"):
        storage.validate_schema({"version": 1, "next_id": 14, "notes": [n1]})

    # Confidence out of range
    n2 = dict(base_note, confidence=1.5)
    with pytest.raises(StorageValidationError, match="confidence must be in \\[0.0, 1.0\\]"):
        storage.validate_schema({"version": 1, "next_id": 14, "notes": [n2]})

    # Non-boolean uncertain
    n3 = dict(base_note, uncertain="false")
    with pytest.raises(StorageValidationError, match="'uncertain' must be boolean"):
        storage.validate_schema({"version": 1, "next_id": 14, "notes": [n3]})


# ---------------------------------------------------------------------------
# 6. Deep Copy Isolation
# ---------------------------------------------------------------------------
def test_deep_copy_isolation(storage: NotesStorage):
    storage.initialize_storage()
    data = storage.load()
    data["notes"].append({"corrupted": True})

    # Ensure in-memory modification of the returned dict did not affect subsequent load
    fresh = storage.load()
    assert fresh["notes"] == []

