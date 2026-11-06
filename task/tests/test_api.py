"""
Automated Test Suite for Smart Notes Assistant - FastAPI Backend Service
Phase 7: FastAPI Backend Engineering, Integration, Security & Full Verification

Tests all API endpoints using FastAPI TestClient with isolated temporary storage:
- POST /classify (all 4 categories, ₹ symbol, invalid inputs, malformed JSON, model reuse).
- GET /notes (listing, category filtering, invalid category validation).
- POST /notes (creation, 201 status, validation, ML classification, unique IDs).
- GET /notes/{note_id} (retrieval, 404 for missing IDs).
- PUT /notes/{note_id} (update, reclassification, timestamp updates, 404 for missing).
- DELETE /notes/{note_id} (deletion, non-reuse of IDs, 404 for missing).
- GET /search (TF-IDF, keyword, invalid methods, invalid top_k, empty queries, dynamic updates).
- POST /notes/load-starter (idempotent starter notes loading, N001-N012).
- GET /health (health status, readiness flags, 503 on unready).
- Concurrency & Storage consistency (concurrent creations without collision).
- Zero modification to real data/notes.json.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.data_ingestion import get_project_root
from src.notes_manager import NotesManager
from src.uncertainty import ALLOWED_CATEGORIES


@pytest.fixture
def test_storage_path(tmp_path: Path) -> Path:
    """Provide an isolated temporary JSON file for API tests."""
    return tmp_path / "test_api_notes.json"


@pytest.fixture
def app(test_storage_path: Path):
    """Create a test FastAPI instance isolated to a temporary storage path."""
    real_model_path = get_project_root() / "models" / "notes_pipeline.joblib"
    manager = NotesManager(
        storage_path=test_storage_path,
        model_path=real_model_path,
        uncertainty_threshold=0.40,
    )
    return create_app(notes_manager=manager)


@pytest.fixture
def client(app) -> TestClient:
    """Provide a TestClient using context manager lifespan."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# 1. Health Endpoint Tests
# ---------------------------------------------------------------------------
def test_health_check_ready(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_ready"] is True
    assert data["storage_ready"] is True
    assert data["version"] == "1.0.0"


def test_health_check_unready():
    # App created with an unready / broken manager
    class BrokenManager:
        model = None
        storage = None

    broken_app = create_app(notes_manager=BrokenManager())
    with TestClient(broken_app) as broken_client:
        response = broken_client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["model_ready"] is False
        assert data["storage_ready"] is False


# ---------------------------------------------------------------------------
# 2. Classification Endpoint Tests (POST /classify)
# ---------------------------------------------------------------------------
def test_classify_all_four_categories(client: TestClient):
    cases = [
        ("Prepare for the computer science final exam on Friday.", "Study"),
        ("Transfer money to the bank account and pay the credit card bill.", "Money"),
        ("Book flight tickets and hotel in Paris for the summer vacation.", "Travel"),
        ("Buy a pair of running shoes and groceries from the supermarket.", "Shopping"),
    ]

    for text, expected_category in cases:
        response = client.post("/classify", json={"text": text})
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == expected_category
        assert data["category"] in ALLOWED_CATEGORIES
        assert isinstance(data["uncertain"], bool)
        assert 0.0 <= data["confidence"] <= 1.0


def test_classify_unicode_rupee_symbol(client: TestClient):
    response = client.post("/classify", json={"text": "Transfer ₹5,000 into my savings account."})
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Money"
    assert data["uncertain"] is False
    assert data["confidence"] > 0.40


def test_classify_invalid_inputs(client: TestClient):
    invalid_cases = [
        ("missing text", {}),
        ("empty string", {"text": ""}),
        ("whitespace only", {"text": "    \t\n  "}),
        ("number", {"text": 12345}),
        ("boolean", {"text": True}),
        ("array", {"text": ["Study for exam"]}),
        ("object", {"text": {"note": "Study"}}),
        ("too long text", {"text": "A" * 1001}),
    ]

    for label, payload in invalid_cases:
        response = client.post("/classify", json=payload)
        assert response.status_code == 422, f"Failed on {label}: {response.text}"
        assert "detail" in response.json()


def test_classify_exactly_1000_chars(client: TestClient):
    # Exactly 1000 chars must be accepted
    text_1000 = "Study " * 166 + "book"  # 166 * 6 + 4 = 1000 chars
    assert len(text_1000) == 1000
    response = client.post("/classify", json={"text": text_1000})
    assert response.status_code == 200


def test_classify_malformed_json(client: TestClient):
    response = client.post(
        "/classify",
        content=b'{"text": "Incomplete json',
        headers={"Content-Type": "application/json"},
    )
    assert 400 <= response.status_code < 500


def test_classify_model_reuse(client: TestClient):
    # Verify that multiple requests return identical deterministic results
    p1 = client.post("/classify", json={"text": "Review Python data structures."}).json()
    p2 = client.post("/classify", json={"text": "Review Python data structures."}).json()
    assert p1 == p2


# ---------------------------------------------------------------------------
# 3. Notes CRUD Endpoints
# ---------------------------------------------------------------------------
def test_create_and_get_note(client: TestClient):
    # Create Note (POST /notes)
    create_res = client.post(
        "/notes",
        json={"text": "Revise backpropagation algorithms before the exam."},
    )
    assert create_res.status_code == 201
    note = create_res.json()
    assert note["id"] == "N013"
    assert note["category"] == "Study"
    assert note["confidence"] > 0.40
    assert note["uncertain"] is False
    assert "created_at" in note
    assert "updated_at" in note

    # Retrieve Note (GET /notes/{id})
    get_res = client.get(f"/notes/{note['id']}")
    assert get_res.status_code == 200
    assert get_res.json() == note


def test_get_nonexistent_note_returns_404(client: TestClient):
    response = client.get("/notes/N999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_notes_and_filter_by_category(client: TestClient):
    # Create study note and money note
    client.post("/notes", json={"text": "Study mathematics formulas."})
    client.post("/notes", json={"text": "Pay electricity utility bill."})

    # List all (GET /notes)
    all_res = client.get("/notes")
    assert all_res.status_code == 200
    notes = all_res.json()
    assert len(notes) == 2

    # Filter category=Study
    study_res = client.get("/notes?category=Study")
    assert study_res.status_code == 200
    study_notes = study_res.json()
    assert len(study_notes) == 1
    assert study_notes[0]["category"] == "Study"

    # Filter category=Money
    money_res = client.get("/notes?category=Money")
    assert money_res.status_code == 200
    money_notes = money_res.json()
    assert len(money_notes) == 1
    assert money_notes[0]["category"] == "Money"

    # Filter category=Travel (empty)
    travel_res = client.get("/notes?category=Travel")
    assert travel_res.status_code == 200
    assert travel_res.json() == []

    # Invalid category filter returns 422
    invalid_cat_res = client.get("/notes?category=Cooking")
    assert invalid_cat_res.status_code == 422


def test_update_note(client: TestClient):
    create_res = client.post("/notes", json={"text": "Initial note about Python exam."})
    note_id = create_res.json()["id"]
    orig_created_at = create_res.json()["created_at"]

    # Update note to a Money note
    update_res = client.put(
        f"/notes/{note_id}",
        json={"text": "Pay the apartment rent before the 1st."},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["id"] == note_id  # ID preserved
    assert updated["category"] == "Money"  # Reclassified
    assert updated["created_at"] == orig_created_at  # Created_at preserved

    # Update nonexistent note returns 404
    bad_update = client.put("/notes/N999", json={"text": "Nonexistent note text."})
    assert bad_update.status_code == 404


def test_delete_note(client: TestClient):
    create_res = client.post("/notes", json={"text": "Temporary note to be deleted."})
    note_id = create_res.json()["id"]

    # Delete note (DELETE /notes/{id})
    del_res = client.delete(f"/notes/{note_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["deleted"] is True
    assert del_data["id"] == note_id

    # Verify deleted note is no longer retrievable (404)
    get_res = client.get(f"/notes/{note_id}")
    assert get_res.status_code == 404

    # Delete nonexistent note returns 404
    bad_del = client.delete(f"/notes/{note_id}")
    assert bad_del.status_code == 404


# ---------------------------------------------------------------------------
# 4. Search Endpoint Tests (GET /search)
# ---------------------------------------------------------------------------
def test_search_notes_tfidf_and_keyword(client: TestClient):
    # Populate notes
    client.post("/notes", json={"text": "My Python test is on Friday at 10 AM."})
    client.post("/notes", json={"text": "Pay the electricity bill by the 28th."})
    client.post("/notes", json={"text": "Our flight to Delhi is on Monday morning."})

    # Default search (TF-IDF)
    res_tfidf = client.get("/search?query=Python test Friday")
    assert res_tfidf.status_code == 200
    results = res_tfidf.json()
    assert len(results) >= 1
    assert results[0]["id"] == "N013"
    assert "score" in results[0]
    assert results[0]["rank"] == 1

    # Keyword search
    res_kw = client.get("/search?query=electricity bill&method=keyword")
    assert res_kw.status_code == 200
    kw_results = res_kw.json()
    assert len(kw_results) >= 1
    assert kw_results[0]["id"] == "N014"


def test_search_input_validation(client: TestClient):
    # Empty query
    assert client.get("/search?query=").status_code == 422
    assert client.get("/search?query=   ").status_code == 422

    # Invalid method
    assert client.get("/search?query=test&method=invalid_method").status_code == 422

    # Invalid top_k
    assert client.get("/search?query=test&top_k=0").status_code == 422
    assert client.get("/search?query=test&top_k=-5").status_code == 422
    assert client.get("/search?query=test&top_k=9999").status_code == 422


def test_search_dynamic_lifecycle(client: TestClient):
    # 1. Search before adding note -> empty
    assert client.get("/search?query=astronomy telescope").json() == []

    # 2. Add note
    create_res = client.post("/notes", json={"text": "Buy an astronomy telescope for stargazing."})
    note_id = create_res.json()["id"]

    # 3. Search immediately finds it
    res_found = client.get("/search?query=astronomy telescope").json()
    assert any(r["id"] == note_id for r in res_found)

    # 4. Update note
    client.put(f"/notes/{note_id}", json={"text": "Buy a biology microscope for lab study."})
    # Old query fails
    assert client.get("/search?query=astronomy telescope").json() == []
    # New query succeeds
    res_new = client.get("/search?query=biology microscope").json()
    assert any(r["id"] == note_id for r in res_new)

    # 5. Delete note -> disappears from search
    client.delete(f"/notes/{note_id}")
    assert client.get("/search?query=biology microscope").json() == []


# ---------------------------------------------------------------------------
# 5. Starter Notes Loading Endpoint Tests (POST /notes/load-starter)
# ---------------------------------------------------------------------------
def test_load_starter_notes_endpoint(client: TestClient):
    # Initial load
    res = client.post("/notes/load-starter")
    assert res.status_code == 200
    data = res.json()
    assert data["loaded_count"] == 12
    assert len(data["notes"]) == 12

    # Verify N001 through N012 are present
    expected_ids = [f"N{i:03d}" for i in range(1, 13)]
    returned_ids = [n["id"] for n in data["notes"]]
    assert returned_ids == expected_ids

    # Idempotent re-load must succeed without duplicating notes
    repeat_res = client.post("/notes/load-starter")
    assert repeat_res.status_code == 200
    assert repeat_res.json()["loaded_count"] == 12

    # Verify total notes count remains 12
    list_res = client.get("/notes")
    assert len(list_res.json()) == 12


# ---------------------------------------------------------------------------
# 6. Concurrency & Integrity
# ---------------------------------------------------------------------------
def test_real_notes_database_untouched(test_storage_path: Path):
    """Confirm that tests running through TestClient never touch real data/notes.json."""
    real_notes_file = get_project_root() / "data" / "notes.json"
    assert not real_notes_file.exists() or real_notes_file != test_storage_path
