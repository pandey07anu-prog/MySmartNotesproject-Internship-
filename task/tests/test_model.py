"""
Automated Test Suite for Smart Notes Assistant - Machine Learning Model Development
Phase 3: Baseline, Improvement Experiment, Evaluation, and Serialization.

All test artifacts use pytest's tmp_path fixture to preserve original datasets
and existing models completely untouched.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.model_trainer import (
    ALLOWED_CATEGORIES,
    build_baseline_pipeline,
    build_improved_pipeline,
    train_model,
    evaluate_model,
    save_model_artifacts,
    load_model_artifacts,
    predict_note_category,
)


@pytest.fixture
def synthetic_train_df() -> pd.DataFrame:
    """Create a minimal synthetic training dataset representing all 4 categories."""
    return pd.DataFrame({
        "text": [
            "Revise chapters for the statistics exam.",
            "Complete the biology assignment before Friday.",
            "Transfer ₹2,000 to my savings account.",
            "Pay the monthly electricity bill.",
            "Book a flight ticket to Delhi for vacation.",
            "Hotel reservation in Jaipur is confirmed.",
            "Buy fresh groceries and milk from the market.",
            "Return the defective laptop headphones."
        ],
        "category": [
            "Study",
            "Study",
            "Money",
            "Money",
            "Travel",
            "Travel",
            "Shopping",
            "Shopping"
        ]
    })


@pytest.fixture
def synthetic_eval_df() -> pd.DataFrame:
    """Create a minimal synthetic evaluation dataset."""
    return pd.DataFrame({
        "text": [
            "Review math formulas for the upcoming test.",
            "Deposit ₹500 into my bank account.",
            "Flight to Mumbai departs tomorrow.",
            "Order shoes from the online store."
        ],
        "category": [
            "Study",
            "Money",
            "Travel",
            "Shopping"
        ]
    })


# ---------------------------------------------------------------------------
# 1. Training pipeline execution and output category validity
# ---------------------------------------------------------------------------
def test_train_pipeline_and_predict(synthetic_train_df: pd.DataFrame):
    pipeline = build_baseline_pipeline()
    fitted_pipe = train_model(pipeline, synthetic_train_df)

    assert fitted_pipe is not None
    test_note = "Prepare revision notes for chemistry exam."
    result = predict_note_category(test_note, pipeline=fitted_pipe)

    assert result["category"] in ALLOWED_CATEGORIES
    assert 0.0 <= result["confidence"] <= 1.0
    assert set(result["probabilities"].keys()) == set(ALLOWED_CATEGORIES)


# ---------------------------------------------------------------------------
# 2. Correct output categories for improved pipeline
# ---------------------------------------------------------------------------
def test_improved_pipeline_output_categories(synthetic_train_df: pd.DataFrame):
    pipeline = build_improved_pipeline()
    fitted_pipe = train_model(pipeline, synthetic_train_df)

    sample_tests = [
        "Study economics chapters.",
        "Pay ₹1,000 for electricity.",
        "Flight booking to Paris.",
        "Purchase groceries."
    ]

    for sample in sample_tests:
        res = predict_note_category(sample, pipeline=fitted_pipe)
        assert res["category"] in ALLOWED_CATEGORIES
        assert isinstance(res["confidence"], float)


# ---------------------------------------------------------------------------
# 3. Model artifact creation and loading in fresh context
# ---------------------------------------------------------------------------
def test_model_artifact_save_and_load(synthetic_train_df: pd.DataFrame, tmp_path: Path):
    pipeline = build_improved_pipeline()
    train_model(pipeline, synthetic_train_df)

    # Save to isolated temporary directory
    saved_files = save_model_artifacts(pipeline, tmp_path)
    assert saved_files["vectorizer"].exists()
    assert saved_files["classifier"].exists()
    assert saved_files["pipeline"].exists()

    # Load from disk
    loaded_vec, loaded_clf, loaded_pipe = load_model_artifacts(tmp_path)

    sample_note = "Check flight timings for Delhi trip."
    # Predict using individual loaded artifacts
    res_indiv = predict_note_category(sample_note, vectorizer=loaded_vec, classifier=loaded_clf)
    # Predict using loaded pipeline
    res_pipe = predict_note_category(sample_note, pipeline=loaded_pipe)

    assert res_indiv["category"] == res_pipe["category"]
    assert res_indiv["category"] in ALLOWED_CATEGORIES
    assert abs(res_indiv["confidence"] - res_pipe["confidence"]) < 1e-4


# ---------------------------------------------------------------------------
# 4. Evaluation metrics computation
# ---------------------------------------------------------------------------
def test_evaluate_model_metrics(synthetic_train_df: pd.DataFrame, synthetic_eval_df: pd.DataFrame):
    pipeline = build_baseline_pipeline()
    train_model(pipeline, synthetic_train_df)

    eval_results = evaluate_model(pipeline, synthetic_eval_df)

    assert "accuracy" in eval_results
    assert "macro_f1" in eval_results
    assert "confusion_matrix" in eval_results
    assert "per_class_metrics" in eval_results
    assert 0.0 <= eval_results["accuracy"] <= 1.0
    assert 0.0 <= eval_results["macro_f1"] <= 1.0
    assert eval_results["total_samples"] == len(synthetic_eval_df)


# ---------------------------------------------------------------------------
# 5. Reproducibility test
# ---------------------------------------------------------------------------
def test_training_reproducibility(synthetic_train_df: pd.DataFrame):
    pipe1 = train_model(build_improved_pipeline(), synthetic_train_df)
    pipe2 = train_model(build_improved_pipeline(), synthetic_train_df)

    sample = "Revise statistics formulas for exam tomorrow."
    pred1 = predict_note_category(sample, pipeline=pipe1)
    pred2 = predict_note_category(sample, pipeline=pipe2)

    assert pred1["category"] == pred2["category"]
    assert pred1["confidence"] == pred2["confidence"]
    assert pred1["probabilities"] == pred2["probabilities"]


# ---------------------------------------------------------------------------
# 6. Invalid dataset handling
# ---------------------------------------------------------------------------
def test_invalid_dataset_handling():
    pipeline = build_baseline_pipeline()

    # Missing category column
    invalid_df1 = pd.DataFrame({"text": ["Hello world"]})
    with pytest.raises(ValueError, match="must contain 'text' and 'category'"):
        train_model(pipeline, invalid_df1)

    # Missing text column
    invalid_df2 = pd.DataFrame({"category": ["Study"]})
    with pytest.raises(ValueError, match="must contain 'text' and 'category'"):
        train_model(pipeline, invalid_df2)


# ---------------------------------------------------------------------------
# 7. Rupee character preservation in improved vectorizer
# ---------------------------------------------------------------------------
def test_rupee_token_preservation():
    df_rupee = pd.DataFrame({
        "text": [
            "Deposit ₹5,000 into account.",
            "Withdraw ₹200 cash.",
            "Study math chapters."
        ],
        "category": [
            "Money",
            "Money",
            "Study"
        ]
    })

    pipe = build_improved_pipeline()
    train_model(pipe, df_rupee)

    feature_names = pipe.named_steps["vectorizer"].get_feature_names_out()
    assert "₹" in feature_names
