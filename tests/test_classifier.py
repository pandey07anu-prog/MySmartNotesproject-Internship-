"""
Tests for ML classification model, uncertainty thresholding, and metrics verification.
"""

import pytest
import pandas as pd
from app.services.classifier import classifier_service, ALLOWED_CATEGORIES
from app.config import PROJECT_ROOT


def test_classifier_loaded():
    assert classifier_service.is_loaded is True
    assert set(classifier_service._classes) == set(ALLOWED_CATEGORIES)


def test_classifier_predictions():
    # In-scope test notes
    study_note = classifier_service.classify("My statistics assignment is due next Wednesday.")
    assert study_note["category"] == "Study"
    assert study_note["confidence"] > 0.50
    assert study_note["uncertain"] is False

    money_note = classifier_service.classify("Move ₹2,000 into the savings account this month.")
    assert money_note["category"] == "Money"
    assert money_note["confidence"] > 0.50
    assert money_note["uncertain"] is False

    travel_note = classifier_service.classify("Our flight to Delhi is on Monday morning.")
    assert travel_note["category"] == "Travel"
    assert travel_note["confidence"] > 0.50
    assert travel_note["uncertain"] is False

    shopping_note = classifier_service.classify("Buy a new laptop stand this weekend.")
    assert shopping_note["category"] == "Shopping"
    assert shopping_note["confidence"] > 0.50
    assert shopping_note["uncertain"] is False


def test_out_of_scope_notes_flagged_uncertain():
    oos_examples = [
        "Call grandma this weekend.",
        "Feed the cat before 8 AM.",
        "Clean the balcony on Saturday.",
        "Go for a walk after dinner.",
    ]
    uncertain_count = 0
    for note in oos_examples:
        res = classifier_service.classify(note)
        assert res["category"] in ALLOWED_CATEGORIES  # Must always return best guess
        if res["uncertain"]:
            uncertain_count += 1

    # At least 3 of 4 must be flagged uncertain at 0.50 threshold
    assert uncertain_count >= 3

