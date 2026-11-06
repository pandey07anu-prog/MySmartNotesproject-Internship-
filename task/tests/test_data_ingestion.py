"""
Automated Test Suite for Smart Notes Assistant - Data Ingestion & Validation Module
Phase 2: Development Environment & Data Foundation

All negative tests use isolated temporary files (via pytest's tmp_path) to ensure
the supplied original datasets are NEVER modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
import pandas as pd

from src.data_ingestion import (
    DataValidationError,
    REQUIRED_CATEGORIES,
    EXPECTED_STARTER_IDS,
    get_project_root,
    load_csv,
    load_starter_notes,
    validate_csv_dataset,
    validate_starter_notes,
    run_full_ingestion,
)


@pytest.fixture
def project_root() -> Path:
    return get_project_root()


@pytest.fixture
def original_data_dir(project_root: Path) -> Path:
    return project_root / "data"


# ---------------------------------------------------------------------------
# 1. Successful loading of valid CSV files
# ---------------------------------------------------------------------------
def test_load_valid_csv(original_data_dir: Path):
    train_path = original_data_dir / "train.csv"
    val_path = original_data_dir / "validation.csv"
    oos_path = original_data_dir / "out_of_scope_examples.csv"

    df_train = load_csv(train_path, required_columns=["text", "category"])
    assert isinstance(df_train, pd.DataFrame)
    assert len(df_train) == 156
    assert list(df_train.columns) == ["text", "category"]

    df_val = load_csv(val_path, required_columns=["text", "category"])
    assert isinstance(df_val, pd.DataFrame)
    assert len(df_val) == 50
    assert list(df_val.columns) == ["text", "category"]

    df_oos = load_csv(oos_path, required_columns=["text"])
    assert isinstance(df_oos, pd.DataFrame)
    assert len(df_oos) == 12
    assert "text" in df_oos.columns


# ---------------------------------------------------------------------------
# 2. Successful loading of valid starter-note JSON
# ---------------------------------------------------------------------------
def test_load_valid_starter_notes_json(original_data_dir: Path):
    starter_path = original_data_dir / "starter_notes.json"
    notes = load_starter_notes(starter_path)

    assert isinstance(notes, list)
    assert len(notes) == 12
    for item in notes:
        assert "id" in item
        assert "text" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["text"], str)
        assert len(item["text"].strip()) > 0

    stats = validate_starter_notes(notes)
    assert stats["is_valid"] is True
    assert stats["record_count"] == 12
    assert stats["unique_ids_count"] == 12
    assert stats["all_expected_ids_present"] is True


# ---------------------------------------------------------------------------
# 3. Missing required columns
# ---------------------------------------------------------------------------
def test_missing_required_columns(tmp_path: Path):
    bad_csv = tmp_path / "missing_cols.csv"
    bad_csv.write_text("text,wrong_col\nHello,World\n", encoding="utf-8")

    with pytest.raises(DataValidationError, match="Missing required column"):
        load_csv(bad_csv, required_columns=["text", "category"])

    df = pd.read_csv(bad_csv)
    stats = validate_csv_dataset(df, "bad_csv", required_columns=["text", "category"])
    assert stats["is_valid"] is False
    assert any("Missing required column" in err for err in stats["validation_errors"])


# ---------------------------------------------------------------------------
# 4. Missing files
# ---------------------------------------------------------------------------
def test_missing_files(tmp_path: Path):
    non_existent_csv = tmp_path / "does_not_exist.csv"
    non_existent_json = tmp_path / "does_not_exist.json"

    with pytest.raises(FileNotFoundError):
        load_csv(non_existent_csv)

    with pytest.raises(FileNotFoundError):
        load_starter_notes(non_existent_json)


# ---------------------------------------------------------------------------
# 5. Invalid category values
# ---------------------------------------------------------------------------
def test_invalid_category_values(tmp_path: Path):
    invalid_cat_csv = tmp_path / "invalid_cat.csv"
    invalid_cat_csv.write_text(
        "text,category\n"
        "Studying math,Study\n"
        "Cooking dinner,Culinary\n"
        "Playing football,Sports\n",
        encoding="utf-8"
    )

    df = load_csv(invalid_cat_csv, required_columns=["text", "category"])
    stats = validate_csv_dataset(
        df,
        "invalid_cat_csv",
        required_columns=["text", "category"],
        check_categories=True
    )

    assert stats["is_valid"] is False
    assert set(stats["unexpected_categories"]) == {"Culinary", "Sports"}
    assert any("Unexpected classification labels" in err for err in stats["validation_errors"])


# ---------------------------------------------------------------------------
# 6. Duplicate starter-note IDs
# ---------------------------------------------------------------------------
def test_duplicate_starter_note_ids(tmp_path: Path):
    duplicate_json = tmp_path / "dup_starter.json"
    dup_data = [
        {"id": "N001", "text": "First note."},
        {"id": "N001", "text": "Second note with duplicate ID."},
        {"id": "N002", "text": "Valid note."}
    ]
    duplicate_json.write_text(json.dumps(dup_data), encoding="utf-8")

    notes = load_starter_notes(duplicate_json)
    stats = validate_starter_notes(notes, expected_ids=None)

    assert stats["is_valid"] is False
    assert "N001" in stats["duplicate_ids"]
    assert any("Duplicate starter note IDs" in err for err in stats["validation_errors"])


# ---------------------------------------------------------------------------
# 7. Empty note content
# ---------------------------------------------------------------------------
def test_empty_note_content(tmp_path: Path):
    empty_text_csv = tmp_path / "empty_text.csv"
    empty_text_csv.write_text(
        "text,category\n"
        "Valid text,Study\n"
        "   ,Money\n",
        encoding="utf-8"
    )

    df = load_csv(empty_text_csv, required_columns=["text", "category"])
    stats = validate_csv_dataset(df, "empty_text_csv", required_columns=["text", "category"])

    assert stats["is_valid"] is False
    assert stats["empty_text_records"] == 1
    assert any("empty or whitespace-only" in err for err in stats["validation_errors"])

    # Test empty note in JSON starter notes
    empty_json_data = [
        {"id": "N001", "text": "   "},
        {"id": "N002", "text": "Valid text"}
    ]
    json_stats = validate_starter_notes(empty_json_data, expected_ids=None)
    assert json_stats["is_valid"] is False
    assert json_stats["empty_text_records"] == 1


# ---------------------------------------------------------------------------
# 8. Preservation of the ₹ character
# ---------------------------------------------------------------------------
def test_preservation_of_rupee_character(original_data_dir: Path):
    # Verify train.csv has 12 notes containing ₹
    df_train = load_csv(original_data_dir / "train.csv")
    train_rupee = df_train[df_train["text"].str.contains("₹")]
    assert len(train_rupee) == 12
    # Ensure ₹ character is exact unicode '\u20b9'
    assert all("\u20b9" in t for t in train_rupee["text"])

    # Verify validation.csv has 3 notes containing ₹
    df_val = load_csv(original_data_dir / "validation.csv")
    val_rupee = df_val[df_val["text"].str.contains("₹")]
    assert len(val_rupee) == 3
    assert all("\u20b9" in t for t in val_rupee["text"])

    # Verify starter_notes.json has N006 with ₹
    notes = load_starter_notes(original_data_dir / "starter_notes.json")
    n006 = next(n for n in notes if n["id"] == "N006")
    assert "₹" in n006["text"]
    assert "₹2,000" in n006["text"]


# ---------------------------------------------------------------------------
# 9. Repeated execution without source-data modification
# ---------------------------------------------------------------------------
def test_repeated_execution_without_source_data_modification(original_data_dir: Path):
    target_files = [
        original_data_dir / "train.csv",
        original_data_dir / "validation.csv",
        original_data_dir / "out_of_scope_examples.csv",
        original_data_dir / "starter_notes.json"
    ]

    def compute_hashes():
        return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in target_files}

    initial_hashes = compute_hashes()

    # Run full ingestion multiple times
    for _ in range(3):
        success, all_stats = run_full_ingestion(data_dir=original_data_dir, verbose=False)
        assert success is True
        for stat in all_stats.values():
            assert stat["is_valid"] is True

    # Re-verify hashes remain completely identical
    final_hashes = compute_hashes()
    assert initial_hashes == final_hashes

