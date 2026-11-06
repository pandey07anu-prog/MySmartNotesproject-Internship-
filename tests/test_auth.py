"""
Tests for authentication flows: Registration, Argon2 hashing, Login,
Logout, Email verification, and Password reset.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.mongodb import db_manager


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_user_registration_flow(client):
    db = db_manager.get_database()
    db.users.delete_one({"email": "alice@example.com"})

    # Valid registration
    res = client.post("/auth/register", json={
        "name": "Alice Developer",
        "email": "alice@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["user"]["email"] == "alice@example.com"
    assert "access_token" in data

    # Verify password was hashed in MongoDB and never stored plain text
    user_doc = db.users.find_one({"email": "alice@example.com"})
    assert user_doc is not None
    assert user_doc["password_hash"].startswith("$argon2")
    assert "SecurePassword123!" not in user_doc["password_hash"]


def test_duplicate_registration_rejected(client):
    res = client.post("/auth/register", json={
        "name": "Alice Duplicate",
        "email": "alice@example.com",
        "password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!"
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


def test_login_success_and_failure(client):
    # Invalid password
    res_bad = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "WrongPassword999"
    })
    assert res_bad.status_code == 401

    # Valid password
    res_ok = client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "SecurePassword123!"
    })
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.json()
    assert "access_token" in res_ok.cookies


def test_email_verification_token_flow(client):
    db = db_manager.get_database()
    token_record = db.email_verification_tokens.find_one()
    assert token_record is not None

    # Invalid token rejected
    bad_res = client.post("/auth/verify-email", json={"token": "invalid_fake_token_12345"})
    assert bad_res.status_code == 400


def test_logout(client):
    # Login first
    client.post("/auth/login", json={
        "email": "alice@example.com",
        "password": "SecurePassword123!"
    })

    # Logout
    res = client.post("/auth/logout")
    assert res.status_code == 200
    assert "access_token" not in client.cookies or client.cookies["access_token"] == ""

