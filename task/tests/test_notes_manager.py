"""
Automated Test Suite for Smart Notes Assistant - Notes Management Layer
Phase 5: Production-Quality Notes Management & Persistent Storage

Comprehensive tests covering:
- Starter note loading, preservation of original IDs and text, idempotency, conflict detection.
- Persistent unique ID generation starting at N013, non-reuse after deletion.
- Note creation (add), input validation, 1000-char limits, ML uncertainty integration.
- Note retrieval and category filtering across all 4 valid categories.
- Note updating (text reclassification, timestamp updates, ID preservation).
- Note deletion (persistent removal, non-reuse of deleted IDs).
- End-to-end persistence across manager re-initializations.
- Integration test using the genuine Phase 3/4 ML pipeline artifact.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import pytest

from src.data_ingestion import get_project_root
from src.notes_manager import (
    CategoryValidationError,
    DuplicateIdError,
    MAX_NOTE_TEXT_LENGTH,
    NoteNotFoundError,
    NotesManager,
    NotesManagerError,
    NoteValidationError,
    StarterNoteConflictError,
)
from src.uncertainty import ALLOWED_CATEGORIES


class MockMLPipeline:
    """Mock ML pipeline for fast, deterministic unit testing."""

    def __init__(self):
        self.classes_ = ["Study", "Money", "Travel", "Shopping"]

    def predict_proba(self, texts):
        results = []
        for text in texts:
            t = text.lower()
            if "exam" in t or "study" in t or "python" in t or "assignment" in t:
                results.append([0.85, 0.05, 0.05, 0.05])  # Study
            elif "bill" in t or "bank" in t or "rent" in t or "₹" in t or "money" in t:
                results.append([0.05, 0.90, 0.03, 0.02])  # Money
            elif "flight" in t or "hotel" in t or "trip" in t or "delhi" in t or "jaipur" in t:
                results.append([0.05, 0.05, 0.82, 0.08])  # Travel
            elif "buy" in t or "shopping" in t or "supermarket" in t or "headphones" in t:
                results.append([0.05, 0.05, 0.05, 0.85])  # Shopping
            else:
                # Ambiguous / uncertain note (confidence = 0.35 < 0.40)
                results.append([0.35, 0.25, 0.20, 0.20])
        return results


@pytest.fixture
def mock_ml_pipeline(monkeypatch):
    """Patch load_uncertainty_model to return MockMLPipeline for fast isolated testing."""
    mock_instance = MockMLPipeline()
    monkeypatch.setattr("src.notes_manager.load_uncertainty_model", lambda *args, **kwargs: mock_instance)
    return mock_instance


@pytest.fixture
def manager(tmp_path: Path, mock_ml_pipeline) -> NotesManager:
    """Return a NotesManager instance with isolated temporary storage."""
    temp_storage = tmp_path / "notes.json"
    return NotesManager(storage_path=temp_storage, uncertainty_threshold=0.40)


@pytest.fixture
def real_model_manager(tmp_path: Path) -> NotesManager:
    """Return a NotesManager configured with the genuine Phase 3/4 ML model artifact."""
    project_root = get_project_root()
    real_model_path = project_root / "models" / "notes_pipeline.joblib"
    temp_storage = tmp_path / "notes_real.json"
    return NotesManager(
        storage_path=temp_storage,
        model_path=real_model_path,
        uncertainty_threshold=0.40
    )


# ---------------------------------------------------------------------------
# 1. Starter Notes Loading & Idempotency
# ---------------------------------------------------------------------------
def test_load_starter_notes_success(manager: NotesManager):
    starter_notes = manager.load_starter_notes()

    # Must contain exactly 12 starter notes
    assert len(starter_notes) == 12
    assert manager.count() == 12

    # Check IDs N001 through N012
    expected_ids = [f"N{i:03d}" for i in range(1, 13)]
    stored_ids = [n["id"] for n in starter_notes]
    assert stored_ids == expected_ids

    # Check note N006 contains the rupee symbol
    n006 = manager.get_note("N006")
    assert "₹2,000" in n006["text"]
    assert n006["category"] == "Money"

    # Confirm next_id was initialized to at least 13
    assert manager.get_next_id() == "N013"


def test_starter_notes_loading_is_idempotent(manager: NotesManager):
    manager.load_starter_notes()
    initial_count = manager.count()
    assert initial_count == 12

    # Second load must not duplicate notes
    manager.load_starter_notes()
    assert manager.count() == 12

    # Third load must still not duplicate
    manager.load_starter_notes()
    assert manager.count() == 12


def test_starter_notes_source_file_is_untouched(manager: NotesManager):
    root = get_project_root()
    starter_file = root / "data" / "starter_notes.json"
    hash_before = hashlib.sha256(starter_file.read_bytes()).hexdigest()

    manager.load_starter_notes()

    hash_after = hashlib.sha256(starter_file.read_bytes()).hexdigest()
    assert hash_before == hash_after


def test_starter_notes_conflict_detection(manager: NotesManager):
    manager.load_starter_notes()

    # Manually modify an existing note in storage to simulate a conflict
    data = manager.storage.load()
    data["notes"][0]["text"] = "Altered note content conflicting with starter file."
    manager.storage.save(data)

    # Calling load_starter_notes should detect the conflict and raise StarterNoteConflictError
    with pytest.raises(StarterNoteConflictError, match="Conflict detected for starter note 'N001'"):
        manager.load_starter_notes()


# ---------------------------------------------------------------------------
# 2. Unique ID Generation
# ---------------------------------------------------------------------------
def test_first_user_note_receives_n013(manager: NotesManager):
    manager.load_starter_notes()
    note = manager.add_note("Review discrete mathematics formulas.")

    assert note["id"] == "N013"
    assert manager.get_next_id() == "N014"


def test_sequential_unique_id_generation(manager: NotesManager):
    manager.load_starter_notes()
    n1 = manager.add_note("Study Note 1")
    n2 = manager.add_note("Money Note 2")
    n3 = manager.add_note("Travel Note 3")

    assert n1["id"] == "N013"
    assert n2["id"] == "N014"
    assert n3["id"] == "N015"
    assert manager.get_next_id() == "N016"


def test_deleted_ids_are_never_reused(manager: NotesManager):
    manager.load_starter_notes()
    n13 = manager.add_note("First note.")
    n14 = manager.add_note("Second note.")
    n15 = manager.add_note("Third note.")

    assert n13["id"] == "N013"
    assert n14["id"] == "N014"
    assert n15["id"] == "N015"

    # Delete N014
    manager.delete_note("N014")
    assert manager.count() == 14  # 12 starter + 2 user notes

    # Next note must be N016, NOT N014
    n16 = manager.add_note("Fourth note.")
    assert n16["id"] == "N016"
    assert manager.get_next_id() == "N017"


# ---------------------------------------------------------------------------
# 3. Add Notes & Input Validation
# ---------------------------------------------------------------------------
def test_add_valid_note_with_ml_classification(manager: NotesManager):
    note = manager.add_note("Prepare summary for final chemistry exam tomorrow.")

    assert note["id"] == "N013"
    assert note["category"] == "Study"
    assert note["confidence"] >= 0.40
    assert note["uncertain"] is False
    assert "created_at" in note
    assert "updated_at" in note


def test_add_ambiguous_note_is_marked_uncertain(manager: NotesManager):
    # Text with ambiguous vocabulary -> Mock model gives conf = 0.35
    note = manager.add_note("Random ambiguous note without clear keywords.")

    assert note["confidence"] == 0.35
    assert note["uncertain"] is True
    # Crucial architectural requirement: category is preserved even when uncertain
    assert note["category"] in ALLOWED_CATEGORIES


def test_add_note_validation_empty_and_whitespace(manager: NotesManager):
    with pytest.raises(NoteValidationError, match="empty or whitespace-only"):
        manager.add_note("")

    with pytest.raises(NoteValidationError, match="empty or whitespace-only"):
        manager.add_note("    \t\n  ")


def test_add_note_validation_non_string(manager: NotesManager):
    with pytest.raises(TypeError, match="must be a string"):
        manager.add_note(None)

    with pytest.raises(TypeError, match="must be a string"):
        manager.add_note(12345)


def test_add_note_validation_length_limits(manager: NotesManager):
    # Exactly 1000 characters is accepted
    exact_1000_chars = "A" * 1000
    note = manager.add_note(exact_1000_chars)
    assert len(note["text"]) == 1000

    # 1001 characters is rejected
    too_long_chars = "B" * 1001
    with pytest.raises(NoteValidationError, match="exceeds maximum length of 1000 characters"):
        manager.add_note(too_long_chars)


# ---------------------------------------------------------------------------
# 4. Retrieve & Filter Notes
# ---------------------------------------------------------------------------
def test_get_all_notes_and_get_note_by_id(manager: NotesManager):
    manager.load_starter_notes()
    all_notes = manager.get_all_notes()
    assert len(all_notes) == 12

    note_3 = manager.get_note("N003")
    assert note_3["id"] == "N003"
    assert "Delhi" in note_3["text"]


def test_get_nonexistent_note_raises_error(manager: NotesManager):
    with pytest.raises(NoteNotFoundError, match="not found"):
        manager.get_note("N999")


def test_filter_by_each_valid_category(manager: NotesManager):
    manager.load_starter_notes()

    for cat in ALLOWED_CATEGORIES:
        matching = manager.filter_by_category(cat)
        assert isinstance(matching, list)
        for n in matching:
            assert n["category"] == cat


def test_filter_by_invalid_category_raises_error(manager: NotesManager):
    with pytest.raises(CategoryValidationError, match="Invalid category filter"):
        manager.filter_by_category("Cooking")


def test_filter_empty_result(manager: NotesManager):
    # Isolated manager with no notes in storage
    res = manager.filter_by_category("Study")
    assert res == []


# ---------------------------------------------------------------------------
# 5. Update Notes
# ---------------------------------------------------------------------------
def test_update_note_success(manager: NotesManager):
    manager.load_starter_notes()
    original = manager.get_note("N001")
    orig_created_at = original["created_at"]

    # Change to a Money-related note
    updated = manager.update_note("N001", "Pay the broadband internet bill.")

    assert updated["id"] == "N001"  # ID unchanged
    assert updated["text"] == "Pay the broadband internet bill."
    assert updated["category"] == "Money"  # Reclassified
    assert updated["created_at"] == orig_created_at  # Created timestamp preserved
    assert updated["updated_at"] >= orig_created_at  # Updated timestamp refreshed


def test_update_nonexistent_note_raises_error(manager: NotesManager):
    with pytest.raises(NoteNotFoundError, match="Cannot update nonexistent note"):
        manager.update_note("N999", "New text")


def test_update_note_validation(manager: NotesManager):
    manager.load_starter_notes()

    with pytest.raises(NoteValidationError, match="empty or whitespace-only"):
        manager.update_note("N001", "   ")

    with pytest.raises(NoteValidationError, match="exceeds maximum length"):
        manager.update_note("N001", "X" * 1001)


# ---------------------------------------------------------------------------
# 6. Delete Notes
# ---------------------------------------------------------------------------
def test_delete_note_success(manager: NotesManager):
    manager.load_starter_notes()
    assert manager.count() == 12

    deleted = manager.delete_note("N005")
    assert deleted["id"] == "N005"
    assert manager.count() == 11

    with pytest.raises(NoteNotFoundError):
        manager.get_note("N005")


def test_delete_nonexistent_note_raises_error(manager: NotesManager):
    with pytest.raises(NoteNotFoundError, match="Cannot delete nonexistent note"):
        manager.delete_note("N999")


# ---------------------------------------------------------------------------
# 7. Persistence Across Reinitialization
# ---------------------------------------------------------------------------
def test_notes_and_counter_persist_across_restarts(tmp_path: Path, mock_ml_pipeline):
    storage_path = tmp_path / "persistent_notes.json"

    # Session 1: Create notes
    mgr1 = NotesManager(storage_path=storage_path)
    mgr1.load_starter_notes()
    mgr1.add_note("User note 13")
    mgr1.add_note("User note 14")
    mgr1.delete_note("N013")
    assert mgr1.get_next_id() == "N015"

    # Session 2: Fresh reinitialization pointing to same storage
    mgr2 = NotesManager(storage_path=storage_path)
    assert mgr2.count() == 13  # 12 starter + 1 surviving user note (N014)
    assert mgr2.get_next_id() == "N015"

    # Add note in session 2: must get N015, not N013
    n15 = mgr2.add_note("User note 15")
    assert n15["id"] == "N015"
    assert mgr2.get_next_id() == "N016"


# ---------------------------------------------------------------------------
# 8. Genuine ML Model Integration Test
# ---------------------------------------------------------------------------
def test_real_model_integration(real_model_manager: NotesManager):
    """
    Test end-to-end functionality using the genuine Phase 3/4 trained model pipeline.
    """
    # 1. Load starter notes using the real model
    starter_notes = real_model_manager.load_starter_notes()
    assert len(starter_notes) == 12

    # Verify realistic classification on starter notes
    n1 = real_model_manager.get_note("N001")
    assert n1["category"] == "Study"
    assert n1["confidence"] > 0.40
    assert n1["uncertain"] is False

    n2 = real_model_manager.get_note("N002")
    assert n2["category"] == "Money"
    assert n2["confidence"] > 0.40
    assert n2["uncertain"] is False

    # 2. Add an in-scope user note
    user_note = real_model_manager.add_note("Transfer ₹5,000 to my mutual funds account.")
    assert user_note["id"] == "N013"
    assert user_note["category"] == "Money"
    assert user_note["confidence"] > 0.40
    assert user_note["uncertain"] is False

    # 3. Add an out-of-scope note (e.g. medical appointment)
    # At threshold 0.40, out-of-scope or borderline notes are flagged uncertain
    oos_note = real_model_manager.add_note("Remember to take vitamins after breakfast.")
    assert oos_note["id"] == "N014"
    assert oos_note["uncertain"] is True  # Model confidence is 0.3681 < 0.40
    assert oos_note["category"] in ALLOWED_CATEGORIES  # Category preserved

