"""
Automated Test Suite for Smart Notes Assistant - Uncertainty Detection Module
Phase 4: Production-Ready Uncertainty Detection and Evaluation

Tests all 20 required scenarios including:
- High/low confidence decisions
- Exact threshold equality boundary testing
- Input validation (empty, whitespace, non-string, None)
- Threshold validation (negative, >1.0, NaN, +/-inf, bool, non-numeric)
- Model probability integrity checks (shape, finite, range, sum to 1.0)
- Metric calculations (uncertainty rate, detection rate, incorrect but confident)
- Saved artifact loading without retraining
"""

from __future__ import annotations

import math
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.uncertainty import (
    ALLOWED_CATEGORIES,
    UncertaintyModelError,
    validate_threshold,
    validate_note_text,
    validate_model_probabilities,
    load_uncertainty_model,
    predict_with_uncertainty,
    evaluate_labeled_dataset,
    evaluate_out_of_scope_dataset,
    evaluate_uncertainty_thresholds,
    compute_decision_score_contributions,
)


class MockModel:
    """Mock model providing deterministic probability distributions for unit tests."""

    def __init__(self, classes=ALLOWED_CATEGORIES, probs=None):
        self.classes_ = list(classes)
        # Default to uniform if None
        if probs is None:
            self._probs = np.array([1.0 / len(self.classes_)] * len(self.classes_))
        else:
            self._probs = np.array(probs, dtype=float)

    def set_probs(self, probs):
        self._probs = np.array(probs, dtype=float)

    def predict_proba(self, texts):
        return np.tile(self._probs, (len(texts), 1))


@pytest.fixture
def mock_model():
    return MockModel(classes=["Study", "Money", "Travel", "Shopping"])


@pytest.fixture
def saved_model():
    """Load the existing Phase 3 artifact without retraining."""
    project_root = Path(__file__).resolve().parent.parent
    model_path = project_root / "models" / "notes_pipeline.joblib"
    return load_uncertainty_model(model_path)


# ---------------------------------------------------------------------------
# 1. High-confidence prediction
# ---------------------------------------------------------------------------
def test_high_confidence_prediction(mock_model):
    mock_model.set_probs([0.80, 0.10, 0.05, 0.05])
    res = predict_with_uncertainty("Study for exam", mock_model, threshold=0.40)

    assert res["category"] == "Study"
    assert res["confidence"] == 0.80
    assert res["uncertain"] is False


# ---------------------------------------------------------------------------
# 2. Low-confidence prediction
# ---------------------------------------------------------------------------
def test_low_confidence_prediction(mock_model):
    mock_model.set_probs([0.30, 0.25, 0.25, 0.20])
    res = predict_with_uncertainty("Some ambiguous note", mock_model, threshold=0.40)

    assert res["category"] == "Study"
    assert res["confidence"] == 0.30
    assert res["uncertain"] is True


# ---------------------------------------------------------------------------
# 3. Confidence exactly equal to threshold (Boundary condition)
# ---------------------------------------------------------------------------
def test_confidence_exactly_equal_to_threshold(mock_model):
    # Rule: confidence == threshold -> uncertain = False
    mock_model.set_probs([0.40, 0.20, 0.20, 0.20])
    res = predict_with_uncertainty("Threshold boundary note", mock_model, threshold=0.40)

    assert res["confidence"] == 0.40
    assert res["uncertain"] is False

    # Also test strictly below threshold
    mock_model.set_probs([0.3999, 0.2001, 0.20, 0.20])
    res_below = predict_with_uncertainty("Below boundary note", mock_model, threshold=0.40)
    assert res_below["uncertain"] is True


# ---------------------------------------------------------------------------
# 4. Correct category selection
# ---------------------------------------------------------------------------
def test_correct_category_selection(mock_model):
    categories = ["Study", "Money", "Travel", "Shopping"]
    for i, cat in enumerate(categories):
        probs = [0.10, 0.10, 0.10, 0.10]
        probs[i] = 0.70
        mock_model.set_probs(probs)

        res = predict_with_uncertainty("Test note", mock_model, threshold=0.40)
        assert res["category"] == cat
        assert res["confidence"] == 0.70


# ---------------------------------------------------------------------------
# 5. Correct class-to-probability mapping
# ---------------------------------------------------------------------------
def test_class_to_probability_mapping(mock_model):
    mock_model.set_probs([0.15, 0.55, 0.20, 0.10])
    res = predict_with_uncertainty("Check bank account", mock_model, threshold=0.40)

    assert res["probabilities"]["Study"] == 0.15
    assert res["probabilities"]["Money"] == 0.55
    assert res["probabilities"]["Travel"] == 0.20
    assert res["probabilities"]["Shopping"] == 0.10


# ---------------------------------------------------------------------------
# 6. Confidence range validation
# ---------------------------------------------------------------------------
def test_confidence_range_validation(mock_model):
    mock_model.set_probs([0.25, 0.25, 0.25, 0.25])
    res = predict_with_uncertainty("Balanced note", mock_model, threshold=0.40)
    assert 0.0 <= res["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 7. Invalid thresholds: negative, >1.0, NaN, +inf, -inf, bool
# ---------------------------------------------------------------------------
def test_invalid_thresholds():
    with pytest.raises(ValueError, match="within \\[0.0, 1.0\\]"):
        validate_threshold(-0.1)

    with pytest.raises(ValueError, match="within \\[0.0, 1.0\\]"):
        validate_threshold(1.05)

    with pytest.raises(ValueError, match="cannot be NaN"):
        validate_threshold(float("nan"))

    with pytest.raises(ValueError, match="cannot be infinite"):
        validate_threshold(float("inf"))

    with pytest.raises(ValueError, match="cannot be infinite"):
        validate_threshold(float("-inf"))

    with pytest.raises(TypeError, match="got boolean"):
        validate_threshold(True)

    with pytest.raises(TypeError, match="Threshold must be a float or int"):
        validate_threshold("0.40")


# ---------------------------------------------------------------------------
# 8. Empty text validation
# ---------------------------------------------------------------------------
def test_empty_text_rejection(mock_model):
    with pytest.raises(ValueError, match="cannot be empty"):
        predict_with_uncertainty("", mock_model)


# ---------------------------------------------------------------------------
# 9. Whitespace-only text validation
# ---------------------------------------------------------------------------
def test_whitespace_text_rejection(mock_model):
    with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
        predict_with_uncertainty("    \t\n  ", mock_model)


# ---------------------------------------------------------------------------
# 10. Non-string text validation
# ---------------------------------------------------------------------------
def test_non_string_text_rejection(mock_model):
    with pytest.raises(TypeError, match="Note text cannot be None"):
        predict_with_uncertainty(None, mock_model)

    with pytest.raises(TypeError, match="Note text must be a string"):
        predict_with_uncertainty(12345, mock_model)

    with pytest.raises(TypeError, match="Note text must be a string"):
        predict_with_uncertainty(["List of words"], mock_model)


# ---------------------------------------------------------------------------
# 11. Invalid probability array shape
# ---------------------------------------------------------------------------
def test_invalid_probability_array_shape():
    classes = ["Study", "Money", "Travel", "Shopping"]

    # Only 3 probabilities for 4 classes
    with pytest.raises(UncertaintyModelError, match="shape mismatch"):
        validate_model_probabilities([0.5, 0.3, 0.2], classes)

    # 2D array instead of 1D
    with pytest.raises(UncertaintyModelError, match="shape mismatch"):
        validate_model_probabilities([[0.25, 0.25, 0.25, 0.25]], classes)


# ---------------------------------------------------------------------------
# 12. NaN or infinite probabilities
# ---------------------------------------------------------------------------
def test_nan_or_infinite_probabilities():
    classes = ["Study", "Money", "Travel", "Shopping"]

    with pytest.raises(UncertaintyModelError, match="contains NaN or Inf"):
        validate_model_probabilities([0.25, float("nan"), 0.25, 0.25], classes)

    with pytest.raises(UncertaintyModelError, match="contains NaN or Inf"):
        validate_model_probabilities([float("inf"), 0.25, 0.25, 0.25], classes)


# ---------------------------------------------------------------------------
# 13. Probabilities outside the valid range [0, 1]
# ---------------------------------------------------------------------------
def test_probabilities_outside_valid_range():
    classes = ["Study", "Money", "Travel", "Shopping"]

    with pytest.raises(UncertaintyModelError, match="within \\[0.0, 1.0\\]"):
        validate_model_probabilities([-0.1, 0.5, 0.3, 0.3], classes)

    with pytest.raises(UncertaintyModelError, match="within \\[0.0, 1.0\\]"):
        validate_model_probabilities([1.2, 0.0, 0.0, 0.0], classes)


# ---------------------------------------------------------------------------
# 14. Probability distributions that do not sum approximately to 1.0
# ---------------------------------------------------------------------------
def test_probabilities_sum_validation():
    classes = ["Study", "Money", "Travel", "Shopping"]

    # Sums to 0.70 (far from 1.0)
    with pytest.raises(UncertaintyModelError, match="does not sum to 1.0"):
        validate_model_probabilities([0.20, 0.20, 0.20, 0.10], classes)

    # Sums to 1.50
    with pytest.raises(UncertaintyModelError, match="does not sum to 1.0"):
        validate_model_probabilities([0.50, 0.50, 0.30, 0.20], classes)


# ---------------------------------------------------------------------------
# 15. All four expected model classes are present
# ---------------------------------------------------------------------------
def test_model_missing_expected_classes():
    bad_model = MockModel(classes=["Study", "Money", "Other"])
    with pytest.raises(UncertaintyModelError, match="missing required classification label"):
        predict_with_uncertainty("Sample text", bad_model)


# ---------------------------------------------------------------------------
# 16. Correct uncertainty decisions for multiple thresholds
# ---------------------------------------------------------------------------
def test_multiple_thresholds_decisions(mock_model):
    mock_model.set_probs([0.42, 0.20, 0.20, 0.18])  # confidence = 0.42

    res_35 = predict_with_uncertainty("Note text", mock_model, threshold=0.35)
    res_40 = predict_with_uncertainty("Note text", mock_model, threshold=0.40)
    res_45 = predict_with_uncertainty("Note text", mock_model, threshold=0.45)

    assert res_35["uncertain"] is False  # 0.42 >= 0.35
    assert res_40["uncertain"] is False  # 0.42 >= 0.40
    assert res_45["uncertain"] is True   # 0.42 < 0.45


# ---------------------------------------------------------------------------
# 17. Correct validation dataset counts and metrics
# ---------------------------------------------------------------------------
def test_evaluate_labeled_dataset_metrics(mock_model):
    mock_model.set_probs([0.50, 0.20, 0.20, 0.10])
    df = pd.DataFrame({
        "text": ["Note 1", "Note 2", "Note 3", "Note 4"],
        "category": ["Study", "Study", "Money", "Travel"]  # 2 correct, 2 incorrect
    })

    # At threshold 0.40, confidence is 0.50 -> 0 uncertain, 4 confident
    # 2 incorrect predictions accepted as confident
    eval_res = evaluate_labeled_dataset(df, mock_model, threshold=0.40)

    assert eval_res["total_samples"] == 4
    assert eval_res["correct_predictions"] == 2
    assert eval_res["incorrect_predictions"] == 2
    assert eval_res["uncertain_predictions"] == 0
    assert eval_res["confident_predictions"] == 4
    assert eval_res["incorrect_and_confident_count"] == 2


# ---------------------------------------------------------------------------
# 18. Correct out-of-scope counts without category labels
# ---------------------------------------------------------------------------
def test_evaluate_out_of_scope_counts(mock_model):
    mock_model.set_probs([0.30, 0.30, 0.20, 0.20])  # conf = 0.30
    df_oos = pd.DataFrame({
        "text": ["Call grandma", "Feed the cat", "Doctor appointment"]
    })

    # At threshold 0.40, all 3 are flagged uncertain
    eval_res = evaluate_out_of_scope_dataset(df_oos, mock_model, threshold=0.40)

    assert eval_res["total_samples"] == 3
    assert eval_res["flagged_uncertain_count"] == 3
    assert eval_res["unflagged_count"] == 0
    assert eval_res["detection_rate"] == 100.0


# ---------------------------------------------------------------------------
# 19. Correct percentage calculations
# ---------------------------------------------------------------------------
def test_percentage_calculations(mock_model):
    mock_model.set_probs([0.30, 0.30, 0.20, 0.20])
    df = pd.DataFrame({
        "text": ["Note 1", "Note 2", "Note 3", "Note 4"],
        "category": ["Study", "Money", "Travel", "Shopping"]
    })

    res = evaluate_labeled_dataset(df, mock_model, threshold=0.40)
    # 4/4 uncertain -> 100.0%
    assert res["uncertainty_rate"] == 100.0


# ---------------------------------------------------------------------------
# 20. Existing saved model artifacts load without retraining
# ---------------------------------------------------------------------------
def test_saved_model_artifact_loading(saved_model):
    assert saved_model is not None

    test_note = "Check my bank statement tomorrow."
    result = predict_with_uncertainty(test_note, saved_model, threshold=0.40)

    assert result["category"] in ALLOWED_CATEGORIES
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["uncertain"], bool)
    assert len(result["probabilities"]) == 4


# ---------------------------------------------------------------------------
# 21. Model with additional (5th) category is rejected
# ---------------------------------------------------------------------------
def test_model_additional_category():
    bad_model = MockModel(classes=["Study", "Money", "Travel", "Shopping", "Extra"])
    with pytest.raises(UncertaintyModelError, match="unexpected additional classification label"):
        predict_with_uncertainty("Sample text", bad_model)


# ---------------------------------------------------------------------------
# 22. Model with duplicate categories is rejected
# ---------------------------------------------------------------------------
def test_model_duplicate_category():
    bad_model = MockModel(classes=["Study", "Money", "Travel", "Shopping", "Study"])
    with pytest.raises(UncertaintyModelError, match="duplicate labels"):
        predict_with_uncertainty("Sample text", bad_model)


# ---------------------------------------------------------------------------
# 23. Model with reordered classes maintains correct probability mapping
# ---------------------------------------------------------------------------
def test_model_reordered_classes():
    reordered_classes = ["Shopping", "Travel", "Money", "Study"]
    reordered_model = MockModel(classes=reordered_classes)
    # Probs aligned with reordered classes: Shopping=0.10, Travel=0.20, Money=0.60, Study=0.10
    reordered_model.set_probs([0.10, 0.20, 0.60, 0.10])

    res = predict_with_uncertainty("Check savings account", reordered_model)
    assert res["category"] == "Money"
    assert res["confidence"] == 0.60
    assert res["probabilities"]["Money"] == 0.60
    assert res["probabilities"]["Travel"] == 0.20
    assert res["probabilities"]["Shopping"] == 0.10
    assert res["probabilities"]["Study"] == 0.10


# ---------------------------------------------------------------------------
# 24. Validation dataset with unexpected category label is rejected
# ---------------------------------------------------------------------------
def test_evaluate_labeled_dataset_unexpected_category(mock_model):
    df_invalid = pd.DataFrame({
        "text": ["Read recipe book"],
        "category": ["Cooking"]
    })
    with pytest.raises(ValueError, match="unexpected category 'Cooking'"):
        evaluate_labeled_dataset(df_invalid, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 25. Validation dataset with missing category label is rejected
# ---------------------------------------------------------------------------
def test_evaluate_labeled_dataset_missing_category(mock_model):
    df_missing = pd.DataFrame({
        "text": ["Some text"],
        "category": [None]
    })
    with pytest.raises(ValueError, match="missing 'category' value"):
        evaluate_labeled_dataset(df_missing, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 26. Validation dataset with empty text is rejected
# ---------------------------------------------------------------------------
def test_evaluate_labeled_dataset_empty_text(mock_model):
    df_empty_text = pd.DataFrame({
        "text": ["   "],
        "category": ["Study"]
    })
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        evaluate_labeled_dataset(df_empty_text, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 27. Validation dataset with non-string text is rejected
# ---------------------------------------------------------------------------
def test_evaluate_labeled_dataset_non_string_text(mock_model):
    df_non_str = pd.DataFrame({
        "text": [12345],
        "category": ["Study"]
    })
    with pytest.raises(TypeError, match="must be a string"):
        evaluate_labeled_dataset(df_non_str, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 28. Out-of-scope dataset with missing text is rejected
# ---------------------------------------------------------------------------
def test_evaluate_oos_dataset_missing_text(mock_model):
    df_missing = pd.DataFrame({
        "text": [None]
    })
    with pytest.raises(ValueError, match="missing 'text' value"):
        evaluate_out_of_scope_dataset(df_missing, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 29. Out-of-scope dataset with empty text is rejected
# ---------------------------------------------------------------------------
def test_evaluate_oos_dataset_empty_text(mock_model):
    df_empty = pd.DataFrame({
        "text": ["   \t\n "]
    })
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        evaluate_out_of_scope_dataset(df_empty, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 30. Out-of-scope dataset with non-string text is rejected
# ---------------------------------------------------------------------------
def test_evaluate_oos_dataset_non_string_text(mock_model):
    df_non_str = pd.DataFrame({
        "text": [98765]
    })
    with pytest.raises(TypeError, match="must be a string"):
        evaluate_out_of_scope_dataset(df_non_str, mock_model, threshold=0.40)


# ---------------------------------------------------------------------------
# 31. Dynamic linear decision score contributions
# ---------------------------------------------------------------------------
def test_compute_decision_score_contributions(saved_model):
    contrib = compute_decision_score_contributions(
        "Charge the power bank tonight.",
        saved_model,
        "Money"
    )
    assert contrib["target_category"] == "Money"
    assert "bank" in contrib["active_tokens"]
    assert isinstance(contrib["intercept"], float)
    assert isinstance(contrib["linear_score"], float)
    assert len(contrib["contributions"]) > 0


