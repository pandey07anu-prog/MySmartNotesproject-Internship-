"""
Tests for security, authorization, and multi-user isolation.
Verifies that User A's notes cannot be read, updated, searched, or deleted by User B.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.mongodb import db_manager


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def register_and_get_token(client, email, name):
    db = db_manager.get_database()
    db.users.delete_one({"email": email})
    res = client.post("/auth/register", json={
        "name": name,
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    return res.json()["access_token"]


def test_cross_user_note_access_blocked(client):
    token_a = register_and_get_token(client, "usera@example.com", "User Alpha")
    token_b = register_and_get_token(client, "userb@example.com", "User Beta")

    # User A creates a private note
    create_res = client.post(
        "/notes",
        json={"text": "User A confidential financial report."},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert create_res.status_code == 201
    note_id = create_res.json()["note_id"]

    # User B attempts to GET User A's note -> MUST BE 404 (ownership denied)
    get_res = client.get(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert get_res.status_code == 404

    # User B attempts to UPDATE User A's note -> MUST BE 404
    put_res = client.put(
        f"/notes/{note_id}",
        json={"text": "Tampered by User B!"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert put_res.status_code == 404

    # User B attempts to DELETE User A's note -> MUST BE 404
    del_res = client.delete(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert del_res.status_code == 404

    # User B searches for words in User A's note -> must return 0 results!
    search_res = client.get(
        "/search?q=confidential",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert search_res.status_code == 200
    assert search_res.json()["total_matches"] == 0

    # User A CAN read their own note
    get_ok = client.get(
        f"/notes/{note_id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert get_ok.status_code == 200
    assert get_ok.json()["note_id"] == note_id


def test_unauthenticated_requests_blocked(client):
    # Clear client session cookies
    client.cookies.clear()

    res = client.get("/notes")
    assert res.status_code == 401

    res_user = client.get("/users/me")
    assert res_user.status_code == 401
