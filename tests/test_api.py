"""
Tests for POST /classify endpoint strictly verifying API_CONTRACT.md compliance.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_classify_valid_notes(client):
    samples = [
        ("Revise Python loops before Friday.", "Study", False),
        ("Pay the electricity bill by the 28th.", "Money", False),
        ("Book flight to Delhi for Monday.", "Travel", False),
        ("Buy a new laptop stand this weekend.", "Shopping", False),
    ]
    for text, expected_category, expected_uncertain in samples:
        res = client.post("/classify", json={"text": text})
        assert res.status_code == 200, f"Failed on: {text}"
        data = res.json()
        assert data["category"] in {"Study", "Money", "Travel", "Shopping"}
        assert isinstance(data["uncertain"], bool)
        assert isinstance(data["confidence"], (int, float))
        assert 0.0 <= data["confidence"] <= 1.0


def test_classify_out_of_scope_note_uncertain(client):
    # 'Call grandma this weekend' should have uncertain = True
    res = client.post("/classify", json={"text": "Call grandma this weekend."})
    assert res.status_code == 200
    data = res.json()
    assert data["uncertain"] is True
    assert data["confidence"] < 0.50


def test_classify_invalid_inputs(client):
    # Empty string
    res = client.post("/classify", json={"text": ""})
    assert 400 <= res.status_code < 500

    # Whitespace only
    res = client.post("/classify", json={"text": "   "})
    assert 400 <= res.status_code < 500

    # Missing field
    res = client.post("/classify", json={"note": "Pay rent"})
    assert 400 <= res.status_code < 500

    # Number
    res = client.post("/classify", json={"text": 42})
    assert 400 <= res.status_code < 500

    # Null
    res = client.post("/classify", json={"text": None})
    assert 400 <= res.status_code < 500


def test_classify_repeatability(client):
    note = "The chemistry lab report is due Tuesday."
    res1 = client.post("/classify", json={"text": note}).json()
    res2 = client.post("/classify", json={"text": note}).json()
    assert res1 == res2

