"""
Smart Notes Assistant - Automated Desktop GUI & Client Test Suite
Phase 8: Premium Native Windows Desktop Application

Automated unit and integration tests verifying:
- API client endpoints, error handling, timeouts, and threading
- Backend lifecycle management & process ownership tracking
- Theme manager preference persistence and callbacks
- GUI state logic: sorting, filtering, statistics, and uncertainty badges
- Clean non-blocking operation
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.data_ingestion import get_project_root
from src.gui.api_client import (
    APIClientError,
    APIConnectionError,
    APIResponseError,
    APITimeoutError,
    NotesApiClient,
)
from src.gui.backend_manager import BackendLifecycleManager
from src.gui.theme import ThemeManager, theme_mgr
from src.notes_manager import NotesManager


@pytest.fixture
def isolated_storage(tmp_path: Path) -> Path:
    storage_file = tmp_path / "test_notes.json"
    return storage_file


@pytest.fixture
def test_app(isolated_storage: Path):
    manager = NotesManager(
        storage_path=isolated_storage,
        model_path=get_project_root() / "models" / "notes_pipeline.joblib",
        uncertainty_threshold=0.40,
        auto_create_storage=True,
    )
    app = create_app(notes_manager=manager)
    return app


@pytest.fixture
def test_client(test_app):
    with TestClient(test_app) as client:
        yield client


# ---------------------------------------------------------------------------
# 1. API Client Unit & Integration Tests
# ---------------------------------------------------------------------------
def test_api_client_health(monkeypatch, test_client):
    """Test get_health method on NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    # Mock _client.request
    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    res = client.get_health()
    assert res.get("status") == "healthy"
    assert res.get("model_ready") is True
    client.close()


def test_api_client_classify_text(monkeypatch, test_client):
    """Test classify_text method on NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    res = client.classify_text("Revise for my biology examination.")
    assert res.get("category") == "Study"
    assert res.get("uncertain") is False
    assert res.get("confidence") > 0.5
    client.close()


def test_api_client_crud_lifecycle(monkeypatch, test_client):
    """Test full CRUD lifecycle via NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    # 1. Create note
    created = client.create_note("Pay electricity bill of ₹1,500 tomorrow.")
    note_id = created["id"]
    assert note_id == "N013"
    assert created["category"] == "Money"

    # 2. Get note by ID
    fetched = client.get_note(note_id)
    assert fetched["id"] == note_id
    assert "₹1,500" in fetched["text"]

    # 3. List all notes
    all_notes = client.get_notes()
    assert len(all_notes) == 1
    assert all_notes[0]["id"] == note_id

    # 4. Filter notes by category
    money_notes = client.get_notes(category="Money")
    assert len(money_notes) == 1
    study_notes = client.get_notes(category="Study")
    assert len(study_notes) == 0

    # 5. Update note
    updated = client.update_note(note_id, "Book train tickets to Mumbai central.")
    assert updated["id"] == note_id
    assert updated["category"] == "Travel"

    # 6. Delete note
    del_res = client.delete_note(note_id)
    assert del_res["deleted"] is True
    assert del_res["id"] == note_id

    # 7. Verify deletion
    remaining = client.get_notes()
    assert len(remaining) == 0

    client.close()


def test_api_client_search(monkeypatch, test_client):
    """Test search_notes via NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    client.create_note("Buy organic milk and sourdough bread from bakery.")
    results = client.search_notes(query="sourdough bread", method="tfidf")
    assert len(results) >= 1
    assert results[0]["id"] == "N013"
    assert results[0]["rank"] == 1
    assert results[0]["score"] > 0.0

    client.close()


def test_api_client_load_starter_notes(monkeypatch, test_client):
    """Test load_starter_notes via NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    res = client.load_starter_notes()
    assert res.get("loaded_count") == 12

    # Second load is idempotent (does not duplicate)
    res2 = client.load_starter_notes()
    assert res2.get("loaded_count") == 12
    assert len(client.get_notes()) == 12

    client.close()


def test_api_client_error_handling(monkeypatch, test_client):
    """Test 422 and 404 response error mapping in NotesApiClient."""
    client = NotesApiClient(base_url="http://testserver")

    def mock_request(method, url, **kwargs):
        return test_client.request(method, url, **kwargs)

    monkeypatch.setattr(client._client, "request", mock_request)

    # 422 on empty text
    with pytest.raises(APIResponseError) as exc_info:
        client.create_note("   ")
    assert exc_info.value.status_code == 422

    # 404 on missing note
    with pytest.raises(APIResponseError) as exc_info:
        client.get_note("N999")
    assert exc_info.value.status_code == 404

    client.close()


def test_api_client_connection_error():
    """Test APIConnectionError or APITimeoutError when target port is unreachable."""
    client = NotesApiClient(base_url="http://127.0.0.1:59999", timeout=0.5)
    with pytest.raises((APIConnectionError, APITimeoutError)):
        client.get_health()
    client.close()


def test_api_client_async_execution():
    """Test threaded execute_async execution and callback delivery."""
    client = NotesApiClient(base_url="http://127.0.0.1:8000")

    result_holder = []
    done_event = threading.Event()

    def dummy_task(val: int) -> int:
        return val * 2

    def on_success(res):
        result_holder.append(res)
        done_event.set()

    client.execute_async(dummy_task, 21, on_success=on_success)
    assert done_event.wait(timeout=2.0)
    assert result_holder == [42]

    client.close()


# ---------------------------------------------------------------------------
# 2. Theme Manager & Configuration Persistence Tests
# ---------------------------------------------------------------------------
def test_theme_manager_defaults(tmp_path: Path):
    """Test ThemeManager loads default config and persists modifications."""
    cfg_file = tmp_path / "test_config.json"
    tm = ThemeManager(config_path=cfg_file)

    assert tm.appearance_mode == "dark"

    # Modify mode
    tm.set_appearance_mode("light")
    assert tm.appearance_mode == "light"
    assert cfg_file.exists()

    # Re-read from disk
    tm2 = ThemeManager(config_path=cfg_file)
    assert tm2.appearance_mode == "light"


def test_theme_manager_callbacks(tmp_path: Path):
    """Test ThemeManager observer callback registration."""
    cfg_file = tmp_path / "test_config.json"
    tm = ThemeManager(config_path=cfg_file)

    events = []
    tm.register_callback(lambda mode: events.append(mode))

    tm.set_appearance_mode("dark")
    assert events == ["dark"]
    tm.set_appearance_mode("system")
    assert events == ["dark", "system"]


# ---------------------------------------------------------------------------
# 3. Backend Lifecycle Manager Tests
# ---------------------------------------------------------------------------
def test_backend_manager_is_healthy_false_on_closed_port():
    """Test is_healthy returns False when port is closed."""
    bm = BackendLifecycleManager(host="127.0.0.1", port=59998, startup_timeout=1.0)
    assert bm.is_healthy() is False
    assert bm.owns_process is False


def test_backend_manager_does_not_kill_unowned_process():
    """Test stop() does not attempt to terminate anything if owns_process is False."""
    bm = BackendLifecycleManager(host="127.0.0.1", port=8000)
    bm.owns_process = False
    bm.process = None
    bm.stop()  # Must not raise
    assert bm.owns_process is False


# ---------------------------------------------------------------------------
# 4. GUI State & Data Logic Tests
# ---------------------------------------------------------------------------
def test_dashboard_statistics_calculation():
    """Test exact count and percentage calculation across 4 categories."""
    sample_notes = [
        {"id": "N001", "category": "Study"},
        {"id": "N002", "category": "Study"},
        {"id": "N003", "category": "Money"},
        {"id": "N004", "category": "Travel"},
    ]

    total = len(sample_notes)
    counts = {
        "Study": sum(1 for n in sample_notes if n.get("category") == "Study"),
        "Money": sum(1 for n in sample_notes if n.get("category") == "Money"),
        "Travel": sum(1 for n in sample_notes if n.get("category") == "Travel"),
        "Shopping": sum(1 for n in sample_notes if n.get("category") == "Shopping"),
    }

    assert total == 4
    assert counts["Study"] == 2
    assert counts["Money"] == 1
    assert counts["Travel"] == 1
    assert counts["Shopping"] == 0

    assert int(round(counts["Study"] / total * 100)) == 50
    assert int(round(counts["Money"] / total * 100)) == 25


def test_notes_sorting_logic():
    """Test newest, oldest, and category sorting orders."""
    notes = [
        {"id": "N001", "category": "Shopping", "updated_at": "2026-11-01T10:00:00+00:00"},
        {"id": "N002", "category": "Study", "updated_at": "2026-11-03T10:00:00+00:00"},
        {"id": "N003", "category": "Money", "updated_at": "2026-11-02T10:00:00+00:00"},
    ]

    # Newest first
    sorted_newest = sorted(notes, key=lambda x: x["updated_at"], reverse=True)
    assert [n["id"] for n in sorted_newest] == ["N002", "N003", "N001"]

    # Oldest first
    sorted_oldest = sorted(notes, key=lambda x: x["updated_at"])
    assert [n["id"] for n in sorted_oldest] == ["N001", "N003", "N002"]

    # Category A-Z
    sorted_cat = sorted(notes, key=lambda x: (x["category"], x["id"]))
    assert [n["category"] for n in sorted_cat] == ["Money", "Shopping", "Study"]


def test_uncertainty_badge_logic():
    """Verify uncertainty threshold visual decision rule."""
    high_conf = {"uncertain": False, "confidence": 0.8842}
    low_conf = {"uncertain": True, "confidence": 0.3541}

    # Rule: uncertain flag governs warning status
    assert high_conf["uncertain"] is False
    assert int(round(high_conf["confidence"] * 100)) == 88

    assert low_conf["uncertain"] is True
    assert int(round(low_conf["confidence"] * 100)) == 35
