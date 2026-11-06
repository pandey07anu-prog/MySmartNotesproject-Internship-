"""
Tests for MongoDB Atlas persistence, collections, indexes, and starter note idempotency.
"""

import pytest
from app.database.mongodb import db_manager
from app.services.note_service import note_service


def test_mongodb_collections_and_indexes():
    db = db_manager.get_database()
    collections = set(db.list_collection_names())

    assert "users" in collections
    assert "notes" in collections
    assert "sessions" in collections

    # Verify compound unique index or index keys
    index_info = db.notes.index_information()
    assert any("user_id" in k[0] for idx in index_info.values() for k in idx["key"])


def test_starter_note_idempotency():
    db = db_manager.get_database()
    test_user_id = "test_user_seed_42"

    # Clean test user notes
    db.notes.delete_many({"user_id": test_user_id})

    # Seed starter notes first time
    res1 = note_service.seed_starter_notes(db, test_user_id)
    assert res1["inserted"] == 12
    assert res1["existing"] == 0

    # Seed starter notes second time -> must not duplicate!
    res2 = note_service.seed_starter_notes(db, test_user_id)
    assert res2["inserted"] == 0
    assert res2["existing"] == 12

    # Verify count is exactly 12
    count = db.notes.count_documents({"user_id": test_user_id})
    assert count == 12

    # Clean up
    db.notes.delete_many({"user_id": test_user_id})

