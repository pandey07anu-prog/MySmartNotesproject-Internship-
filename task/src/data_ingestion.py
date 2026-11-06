"""
Smart Notes Assistant - Data Ingestion & Validation Module
Phase 2: Development Environment & Data Foundation

This module provides reusable, deterministic, and safe loading, inspection,
and validation of the supplied assessment datasets.
It never modifies, overwrites, or deletes source data files.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import pandas as pd

# Standard allowed classification labels according to CATEGORY_GUIDE.md
REQUIRED_CATEGORIES: Tuple[str, ...] = ("Study", "Money", "Travel", "Shopping")

# Expected starter note IDs
EXPECTED_STARTER_IDS: Tuple[str, ...] = tuple(f"N{i:03d}" for i in range(1, 13))


class DataValidationError(Exception):
    """Custom exception raised when dataset validation fails."""
    pass


def get_project_root() -> Path:
    """
    Resolve and return the absolute path to the project root directory ('task').
    """
    # Assuming this file is located in <root>/src/data_ingestion.py
    current_path = Path(__file__).resolve()
    # If in src/, parent is project root
    if current_path.parent.name == "src":
        return current_path.parent.parent
    return Path.cwd()


def resolve_data_path(
    relative_or_absolute_path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Resolve a file path relative to base_dir or the project root.
    """
    path = Path(relative_or_absolute_path)
    if path.is_absolute():
        return path
    root = Path(base_dir) if base_dir else get_project_root()
    return (root / path).resolve()


def load_csv(
    file_path: Union[str, Path],
    required_columns: Optional[Sequence[str]] = None,
    encoding: str = "utf-8"
) -> pd.DataFrame:
    """
    Load a CSV file with strict encoding and validate column presence.
    
    Args:
        file_path: Path to the CSV file.
        required_columns: Optional sequence of column names that must exist.
        encoding: File character encoding (default: utf-8).
        
    Returns:
        pd.DataFrame containing the loaded records.
        
    Raises:
        FileNotFoundError: If the target file does not exist.
        DataValidationError: If required columns are missing or parsing fails.
    """
    resolved_path = Path(file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {resolved_path}")
    if not resolved_path.is_file():
        raise DataValidationError(f"Path is not a regular file: {resolved_path}")

    try:
        df = pd.read_csv(resolved_path, encoding=encoding)
    except UnicodeDecodeError as e:
        raise DataValidationError(f"Encoding error reading {resolved_path}: {e}") from e
    except Exception as e:
        raise DataValidationError(f"Failed to read CSV at {resolved_path}: {e}") from e

    if required_columns is not None:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise DataValidationError(
                f"Missing required column(s) {missing_cols} in {resolved_path.name}. "
                f"Found columns: {list(df.columns)}"
            )

    return df


def load_starter_notes(
    file_path: Union[str, Path],
    encoding: str = "utf-8"
) -> List[Dict[str, Any]]:
    """
    Load and parse starter_notes.json with strict structural validation.
    
    Args:
        file_path: Path to the JSON file.
        encoding: File character encoding (default: utf-8).
        
    Returns:
        List of note dictionaries with 'id' and 'text'.
        
    Raises:
        FileNotFoundError: If file is missing.
        DataValidationError: If JSON is invalid or missing required note fields.
    """
    resolved_path = Path(file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Starter notes file not found at: {resolved_path}")
    if not resolved_path.is_file():
        raise DataValidationError(f"Path is not a regular file: {resolved_path}")

    try:
        with open(resolved_path, "r", encoding=encoding) as fp:
            data = json.load(fp)
    except UnicodeDecodeError as e:
        raise DataValidationError(f"Encoding error reading {resolved_path}: {e}") from e
    except json.JSONDecodeError as e:
        raise DataValidationError(f"Malformed JSON in {resolved_path}: {e}") from e

    if not isinstance(data, list):
        raise DataValidationError(
            f"Starter notes must be a JSON array of objects, got {type(data).__name__}"
        )

    return data


def validate_csv_dataset(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Sequence[str],
    check_categories: bool = False,
    allowed_categories: Sequence[str] = REQUIRED_CATEGORIES
) -> Dict[str, Any]:
    """
    Perform deep validation of a tabular dataset (record counts, nulls, duplicates, categories).
    
    Returns:
        Dictionary containing comprehensive metrics and validation status.
    """
    stats: Dict[str, Any] = {
        "dataset_name": dataset_name,
        "record_count": len(df),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
        "empty_text_records": 0,
        "duplicate_rows_count": int(df.duplicated().sum()),
        "rupee_symbol_count": 0,
        "is_valid": True,
        "validation_errors": []
    }

    # Verify required columns
    for col in required_columns:
        if col not in df.columns:
            stats["is_valid"] = False
            stats["validation_errors"].append(f"Missing required column: '{col}'")

    if not stats["is_valid"]:
        return stats

    # Check for empty or whitespace-only text
    if "text" in df.columns:
        # Treat non-string or null as empty/invalid
        text_series = df["text"].fillna("").astype(str)
        empty_mask = text_series.str.strip().eq("")
        stats["empty_text_records"] = int(empty_mask.sum())
        if stats["empty_text_records"] > 0:
            stats["is_valid"] = False
            stats["validation_errors"].append(
                f"Found {stats['empty_text_records']} empty or whitespace-only text record(s)"
            )

        # Count occurrences of the rupee symbol ₹
        stats["rupee_symbol_count"] = int(text_series.str.contains("₹").sum())

    # Check categories if requested
    if check_categories:
        if "category" not in df.columns:
            stats["is_valid"] = False
            stats["validation_errors"].append("Expected 'category' column not found")
        else:
            cat_series = df["category"].fillna("").astype(str)
            distribution = cat_series.value_counts().to_dict()
            stats["category_distribution"] = distribution
            
            unexpected_cats = [c for c in distribution.keys() if c not in allowed_categories]
            stats["unexpected_categories"] = unexpected_cats
            if unexpected_cats:
                stats["is_valid"] = False
                stats["validation_errors"].append(
                    f"Unexpected classification labels found: {unexpected_cats}. "
                    f"Allowed categories: {list(allowed_categories)}"
                )

    return stats


def validate_starter_notes(
    notes: List[Dict[str, Any]],
    dataset_name: str = "starter_notes.json",
    expected_ids: Optional[Sequence[str]] = EXPECTED_STARTER_IDS
) -> Dict[str, Any]:
    """
    Validate starter notes integrity, duplicate IDs, missing fields, and empty text.
    """
    stats: Dict[str, Any] = {
        "dataset_name": dataset_name,
        "record_count": len(notes),
        "unique_ids_count": 0,
        "duplicate_ids": [],
        "missing_fields_count": 0,
        "empty_text_records": 0,
        "rupee_symbol_count": 0,
        "all_expected_ids_present": False,
        "is_valid": True,
        "validation_errors": []
    }

    ids_seen: List[str] = []
    duplicate_ids: List[str] = []

    for idx, item in enumerate(notes):
        if not isinstance(item, dict):
            stats["is_valid"] = False
            stats["validation_errors"].append(f"Item #{idx} is not a JSON object")
            continue

        note_id = item.get("id")
        note_text = item.get("text")

        if not note_id or not isinstance(note_id, str):
            stats["missing_fields_count"] += 1
            stats["is_valid"] = False
            stats["validation_errors"].append(f"Item #{idx} missing valid 'id'")
        else:
            if note_id in ids_seen:
                duplicate_ids.append(note_id)
            ids_seen.append(note_id)

        if note_text is None or not isinstance(note_text, str) or note_text.strip() == "":
            stats["empty_text_records"] += 1
            stats["is_valid"] = False
            stats["validation_errors"].append(f"Note '{note_id or idx}' has empty or non-string 'text'")
        elif "₹" in note_text:
            stats["rupee_symbol_count"] += 1

    stats["unique_ids_count"] = len(set(ids_seen))
    stats["duplicate_ids"] = list(set(duplicate_ids))

    if stats["duplicate_ids"]:
        stats["is_valid"] = False
        stats["validation_errors"].append(f"Duplicate starter note IDs found: {stats['duplicate_ids']}")

    if expected_ids is not None:
        missing_ids = [eid for eid in expected_ids if eid not in ids_seen]
        if missing_ids:
            stats["is_valid"] = False
            stats["validation_errors"].append(f"Expected starter note IDs missing: {missing_ids}")
        else:
            stats["all_expected_ids_present"] = True

    return stats


def report_dataset_statistics(stats: Dict[str, Any]) -> None:
    """
    Format and display human-readable inspection results to stdout.
    """
    name = stats.get("dataset_name", "Unknown Dataset")
    print("=" * 70)
    print(f"DATASET INSPECTION REPORT: {name}")
    print("=" * 70)
    print(f"Total Records           : {stats.get('record_count')}")
    
    if "columns" in stats:
        print(f"Columns                 : {stats.get('columns')}")
        print(f"Data Types              : {stats.get('dtypes')}")
        print(f"Missing Values          : {stats.get('missing_values')}")
        print(f"Duplicate Rows          : {stats.get('duplicate_rows_count')}")

    if "unique_ids_count" in stats:
        print(f"Unique Note IDs         : {stats.get('unique_ids_count')}")
        print(f"Duplicate IDs           : {stats.get('duplicate_ids')}")
        print(f"Expected IDs Present    : {stats.get('all_expected_ids_present')}")

    print(f"Empty Text Records      : {stats.get('empty_text_records')}")
    print(f"Records Containing '₹'  : {stats.get('rupee_symbol_count')}")

    if "category_distribution" in stats:
        print("Category Distribution   :")
        for cat, cnt in stats["category_distribution"].items():
            print(f"  - {cat:12s}: {cnt:3d} ({cnt / stats['record_count'] * 100:.1f}%)")
        if stats.get("unexpected_categories"):
            print(f"Unexpected Categories   : {stats['unexpected_categories']}")

    print(f"Validation Status       : {'PASSED' if stats.get('is_valid') else 'FAILED'}")
    if stats.get("validation_errors"):
        print("Validation Errors:")
        for err in stats["validation_errors"]:
            print(f"  [!] {err}")
    print("-" * 70 + "\n")


def run_full_ingestion(
    data_dir: Optional[Union[str, Path]] = None,
    verbose: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Run full ingestion, inspection, and integrity validation on all 4 assessment datasets.
    
    Returns:
        Tuple of (overall_success: bool, dict_of_all_stats)
    """
    root = get_project_root()
    target_data_dir = Path(data_dir) if data_dir else (root / "data")
    
    all_stats: Dict[str, Any] = {}
    overall_success = True

    # 1. train.csv
    try:
        train_path = target_data_dir / "train.csv"
        df_train = load_csv(train_path, required_columns=["text", "category"])
        train_stats = validate_csv_dataset(
            df_train,
            dataset_name="data/train.csv",
            required_columns=["text", "category"],
            check_categories=True
        )
    except Exception as e:
        train_stats = {"dataset_name": "data/train.csv", "is_valid": False, "validation_errors": [str(e)]}
    all_stats["train"] = train_stats
    if not train_stats.get("is_valid", False):
        overall_success = False

    # 2. validation.csv
    try:
        val_path = target_data_dir / "validation.csv"
        df_val = load_csv(val_path, required_columns=["text", "category"])
        val_stats = validate_csv_dataset(
            df_val,
            dataset_name="data/validation.csv",
            required_columns=["text", "category"],
            check_categories=True
        )
    except Exception as e:
        val_stats = {"dataset_name": "data/validation.csv", "is_valid": False, "validation_errors": [str(e)]}
    all_stats["validation"] = val_stats
    if not val_stats.get("is_valid", False):
        overall_success = False

    # 3. out_of_scope_examples.csv
    try:
        oos_path = target_data_dir / "out_of_scope_examples.csv"
        df_oos = load_csv(oos_path, required_columns=["text"])
        oos_stats = validate_csv_dataset(
            df_oos,
            dataset_name="data/out_of_scope_examples.csv",
            required_columns=["text"],
            check_categories=False
        )
    except Exception as e:
        oos_stats = {"dataset_name": "data/out_of_scope_examples.csv", "is_valid": False, "validation_errors": [str(e)]}
    all_stats["out_of_scope"] = oos_stats
    if not oos_stats.get("is_valid", False):
        overall_success = False

    # 4. starter_notes.json
    try:
        starter_path = target_data_dir / "starter_notes.json"
        starter_data = load_starter_notes(starter_path)
        starter_stats = validate_starter_notes(
            starter_data,
            dataset_name="data/starter_notes.json"
        )
    except Exception as e:
        starter_stats = {"dataset_name": "data/starter_notes.json", "is_valid": False, "validation_errors": [str(e)]}
    all_stats["starter_notes"] = starter_stats
    if not starter_stats.get("is_valid", False):
        overall_success = False

    if verbose:
        for stats in all_stats.values():
            report_dataset_statistics(stats)

    return overall_success, all_stats


def main() -> None:
    """CLI entrypoint for standalone data ingestion execution."""
    # Ensure stdout handles UTF-8 characters cleanly on Windows
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    print("\nStarting Smart Notes Assistant - Dataset Ingestion & Validation...\n")
    success, _ = run_full_ingestion(verbose=True)

    if success:
        print("[SUCCESS] All 4 assessment datasets passed integrity validation.\n")
        sys.exit(0)
    else:
        print("[FAILURE] One or more datasets failed integrity validation.\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

