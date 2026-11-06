"""
Automated Test Suite for Smart Notes Assistant - Search Engine Module
Phase 6: Search Engine Development, Retrieval Benchmarking & Selection

Tests:
- Input validation (empty, whitespace, non-string, invalid top_k, empty corpus).
- Keyword search baseline (token matching, coverage, frequency density, tie-breaking).
- TF-IDF cosine similarity search (zero vector, empty vocabulary, similarity ranking).
- Dynamic integration with NotesManager (add, update, delete, reinitialize).
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.notes_manager import NotesManager
from src.search_engine import (
    DEFAULT_SEARCH_METHOD,
    keyword_search,
    search_notes,
    tfidf_search,
    validate_search_inputs,
)


@pytest.fixture
def sample_notes():
    """Deterministic sample notes corpus for testing."""
    return [
        {
            "id": "N001",
            "text": "My Python test is on Friday at 10 AM.",
            "category": "Study",
            "confidence": 0.88,
            "uncertain": False
        },
        {
            "id": "N002",
            "text": "Pay the electricity bill by the 28th.",
            "category": "Money",
            "confidence": 0.92,
            "uncertain": False
        },
        {
            "id": "N003",
            "text": "Our flight to Delhi is on Monday morning.",
            "category": "Travel",
            "confidence": 0.85,
            "uncertain": False
        },
        {
            "id": "N004",
            "text": "Buy a new laptop stand this weekend.",
            "category": "Shopping",
            "confidence": 0.89,
            "uncertain": False
        }
    ]


# ---------------------------------------------------------------------------
# 1. Input Validation
# ---------------------------------------------------------------------------
def test_search_input_validation():
    # Empty and whitespace queries
    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        validate_search_inputs("", 3)

    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        validate_search_inputs("   \t\n  ", 3)

    # Non-string queries
    with pytest.raises(TypeError, match="must be a string"):
        validate_search_inputs(None, 3)

    with pytest.raises(TypeError, match="must be a string"):
        validate_search_inputs(12345, 3)

    # Invalid top_k
    with pytest.raises(ValueError, match="must be a positive integer"):
        validate_search_inputs("query", 0)

    with pytest.raises(ValueError, match="must be a positive integer"):
        validate_search_inputs("query", -5)

    with pytest.raises(TypeError, match="must be an integer"):
        validate_search_inputs("query", "3")

    with pytest.raises(TypeError, match="must be an integer"):
        validate_search_inputs("query", True)


def test_search_empty_corpus():
    assert keyword_search("Python test", []) == []
    assert tfidf_search("Python test", []) == []
    assert search_notes("Python test", [], method="keyword") == []
    assert search_notes("Python test", [], method="tfidf") == []


def test_search_invalid_method(sample_notes):
    with pytest.raises(ValueError, match="Unsupported search method"):
        search_notes("Python test", sample_notes, method="unsupported_method")


# ---------------------------------------------------------------------------
# 2. Keyword Search
# ---------------------------------------------------------------------------
def test_keyword_search_exact_and_partial_match(sample_notes):
    # Exact phrase match
    results = keyword_search("Python test", sample_notes, top_k=3)
    assert len(results) >= 1
    assert results[0]["id"] == "N001"
    assert results[0]["rank"] == 1
    assert results[0]["score"] > 1.0  # Receives exact phrase bonus

    # Partial / subset match
    res_partial = keyword_search("electricity", sample_notes, top_k=3)
    assert len(res_partial) == 1
    assert res_partial[0]["id"] == "N002"
    assert res_partial[0]["rank"] == 1


def test_keyword_search_case_insensitivity_and_punctuation(sample_notes):
    # Mixed case with punctuation
    results = keyword_search("pYtHoN, tEsT!?!", sample_notes, top_k=3)
    assert len(results) >= 1
    assert results[0]["id"] == "N001"


def test_keyword_search_no_match_returns_empty(sample_notes):
    results = keyword_search("completely unrelated query terms", sample_notes, top_k=3)
    assert results == []


def test_keyword_search_deterministic_tie_breaking():
    # Two notes sharing the same query word with identical frequency
    tied_notes = [
        {"id": "N020", "text": "Alpha project discussion.", "category": "Study", "confidence": 0.8, "uncertain": False},
        {"id": "N010", "text": "Beta project discussion.", "category": "Study", "confidence": 0.8, "uncertain": False},
    ]
    results = keyword_search("project discussion", tied_notes, top_k=2)
    assert len(results) == 2
    # Tie broken by ID ascending: N010 before N020
    assert results[0]["id"] == "N010"
    assert results[1]["id"] == "N020"


def test_keyword_search_top_k_limit(sample_notes):
    # Note N001 and N004 both have matches if we query common terms
    results = keyword_search("laptop electricity python flight", sample_notes, top_k=2)
    assert len(results) <= 2


# ---------------------------------------------------------------------------
# 3. TF-IDF Cosine Similarity Search
# ---------------------------------------------------------------------------
def test_tfidf_search_exact_and_ranking(sample_notes):
    results = tfidf_search("Python test", sample_notes, top_k=3)
    assert len(results) >= 1
    assert results[0]["id"] == "N001"
    assert results[0]["rank"] == 1
    assert 0.0 < results[0]["score"] <= 1.0


def test_tfidf_search_zero_vector_query(sample_notes):
    # Query with words not present in the notes corpus
    results = tfidf_search("xylophone zeppelin kangaroo", sample_notes, top_k=3)
    assert results == []


def test_tfidf_search_all_stopwords_query(sample_notes):
    # Query containing only English stop words -> transformed vector is all zeros
    results = tfidf_search("the is on at", sample_notes, top_k=3)
    assert results == []


def test_tfidf_search_empty_vocabulary():
    # Corpus with only empty texts
    empty_notes = [
        {"id": "N001", "text": "   ", "category": "Study", "confidence": 0.5, "uncertain": True}
    ]
    assert tfidf_search("any query", empty_notes) == []


def test_tfidf_search_deterministic_tie_breaking():
    tied_notes = [
        {"id": "N025", "text": "Database indexing notes.", "category": "Study", "confidence": 0.8, "uncertain": False},
        {"id": "N015", "text": "Database indexing notes.", "category": "Study", "confidence": 0.8, "uncertain": False},
    ]
    results = tfidf_search("database indexing", tied_notes, top_k=2)
    assert len(results) == 2
    # Tie broken by ID ascending: N015 before N025
    assert results[0]["id"] == "N015"
    assert results[1]["id"] == "N025"


# ---------------------------------------------------------------------------
# 4. Dynamic NotesManager Integration
# ---------------------------------------------------------------------------
def test_notes_manager_search_starter_notes(tmp_path: Path):
    storage_path = tmp_path / "test_notes.json"
    mgr = NotesManager(storage_path=storage_path)
    mgr.load_starter_notes()

    # Search using default (tfidf)
    res_default = mgr.search_notes("Delhi flight Monday")
    assert len(res_default) >= 1
    assert res_default[0]["id"] == "N003"
    assert res_default[0]["category"] == "Travel"

    # Search using explicit keyword method
    res_kw = mgr.search_notes("Delhi flight Monday", method="keyword")
    assert len(res_kw) >= 1
    assert res_kw[0]["id"] == "N003"


def test_notes_manager_search_dynamic_add_update_delete(tmp_path: Path):
    storage_path = tmp_path / "dynamic_notes.json"
    mgr = NotesManager(storage_path=storage_path)
    mgr.load_starter_notes()

    # 1. Add new note
    new_note = mgr.add_note("Schedule quarterly tax audit review with accountant.")
    new_id = new_note["id"]

    # Newly added note must be immediately searchable
    res_add = mgr.search_notes("tax audit review accountant")
    assert any(r["id"] == new_id for r in res_add)
    assert res_add[0]["id"] == new_id

    # 2. Update note
    mgr.update_note(new_id, "Schedule dentist appointment for tooth cleaning.")

    # Old text should no longer match
    res_old = mgr.search_notes("tax audit review accountant")
    assert not any(r["id"] == new_id for r in res_old)

    # New text should match
    res_updated = mgr.search_notes("dentist tooth cleaning")
    assert any(r["id"] == new_id for r in res_updated)

    # 3. Delete note
    mgr.delete_note(new_id)

    # Deleted note must immediately disappear from search
    res_deleted = mgr.search_notes("dentist tooth cleaning")
    assert not any(r["id"] == new_id for r in res_deleted)


def test_notes_manager_search_persists_across_restart(tmp_path: Path):
    storage_path = tmp_path / "persistent_search.json"

    # Session 1: Add note
    mgr1 = NotesManager(storage_path=storage_path)
    mgr1.load_starter_notes()
    note = mgr1.add_note("Kubernetes cluster deployment automation script.")
    note_id = note["id"]

    # Session 2: Fresh instance
    mgr2 = NotesManager(storage_path=storage_path)
    res = mgr2.search_notes("Kubernetes cluster deployment")
    assert len(res) >= 1
    assert res[0]["id"] == note_id

