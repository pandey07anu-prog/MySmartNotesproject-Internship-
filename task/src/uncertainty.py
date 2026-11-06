"""
Smart Notes Assistant - Confidence-Based Uncertainty Detection Module
Phase 4: Production-Ready Uncertainty Detection and Evaluation

This module implements two decoupled decisions for note classification:
1. Predict the most likely category from the 4 allowed categories (Study, Money, Travel, Shopping).
2. Determine whether model confidence (max predicted probability) meets an acceptable threshold.

Boundary rule:
    uncertain = (confidence < threshold)
    equal to threshold -> uncertain = False
    above threshold    -> uncertain = False

Never introduces a fifth category (e.g. 'Out of Scope').
Never retrains the model.
Does not use heuristic keyword lists or external LLM APIs.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd

# The 4 mandatory categories defined in CATEGORY_GUIDE.md
ALLOWED_CATEGORIES: Tuple[str, ...] = ("Study", "Money", "Travel", "Shopping")

# Floating-point tolerance for probability sum validation
PROBABILITY_SUM_TOLERANCE: float = 1e-3


class UncertaintyModelError(Exception):
    """Raised when model loading, structure, classes, or probability outputs are invalid."""
    pass


def validate_threshold(threshold: Any) -> float:
    """
    Validate that the threshold is a finite float within [0.0, 1.0].
    
    Args:
        threshold: Candidate threshold value.
        
    Returns:
        float: Validated threshold.
        
    Raises:
        TypeError: If threshold is not numeric or is a boolean.
        ValueError: If threshold is NaN, infinite, or outside [0.0, 1.0].
    """
    if isinstance(threshold, bool):
        raise TypeError(f"Threshold must be numeric, got boolean: {threshold!r}")
    if not isinstance(threshold, (int, float)):
        raise TypeError(f"Threshold must be a float or int, got {type(threshold).__name__}: {threshold!r}")

    t_val = float(threshold)
    if math.isnan(t_val):
        raise ValueError("Threshold cannot be NaN.")
    if math.isinf(t_val):
        raise ValueError(f"Threshold cannot be infinite: {t_val}")
    if t_val < 0.0 or t_val > 1.0:
        raise ValueError(f"Threshold must be within [0.0, 1.0], got {t_val}")

    return t_val


def validate_note_text(text: Any) -> str:
    """
    Validate that input text is a non-empty, non-whitespace string.
    
    Args:
        text: Candidate note text.
        
    Returns:
        str: Validated note text.
        
    Raises:
        TypeError: If text is not a string.
        ValueError: If text is empty or whitespace-only.
    """
    if text is None:
        raise TypeError("Note text cannot be None.")
    if not isinstance(text, str):
        raise TypeError(f"Note text must be a string, got {type(text).__name__}: {text!r}")
    if not text.strip():
        raise ValueError("Note text cannot be empty or whitespace-only.")

    return text


def validate_model_probabilities(probs: Sequence[float], classes: Sequence[str]) -> np.ndarray:
    """
    Validate that the probability vector output by the model is well-formed.
    
    Args:
        probs: Array or sequence of class probabilities.
        classes: Sequence of class labels.
        
    Returns:
        np.ndarray: Validated 1D numpy array of probabilities.
        
    Raises:
        UncertaintyModelError: If shape, finiteness, range, or sum is invalid.
    """
    try:
        p_arr = np.asarray(probs, dtype=float)
    except (ValueError, TypeError) as e:
        raise UncertaintyModelError(f"Cannot convert model output to float array: {e}") from e

    if p_arr.ndim != 1 or len(p_arr) != len(classes):
        raise UncertaintyModelError(
            f"Probability array shape mismatch: expected 1D array of length {len(classes)}, "
            f"got shape {p_arr.shape}"
        )

    if not np.all(np.isfinite(p_arr)):
        raise UncertaintyModelError(f"Probability array contains NaN or Inf values: {p_arr}")

    if np.any(p_arr < -1e-6) or np.any(p_arr > 1.0 + 1e-6):
        raise UncertaintyModelError(f"Probabilities must be within [0.0, 1.0], got: {p_arr}")

    # Clip minor floating-point inaccuracies
    p_arr = np.clip(p_arr, 0.0, 1.0)

    prob_sum = float(np.sum(p_arr))
    if not np.isclose(prob_sum, 1.0, atol=PROBABILITY_SUM_TOLERANCE):
        raise UncertaintyModelError(
            f"Probability distribution does not sum to 1.0 (sum={prob_sum:.6f}): {p_arr}"
        )

    return p_arr


def get_model_classes(model: Any) -> List[str]:
    """
    Extract and rigorously validate class labels from the model.
    
    Enforces:
    - Model must define 'classes_' either directly or on a 'classifier' step.
    - Exactly four unique labels.
    - Allowed labels: Study, Money, Travel, Shopping.
    - Rejects missing categories.
    - Rejects additional categories (5+ classes).
    - Rejects duplicate labels.
    - Rejects invalid class names.
    - Preserves classifier's original class ordering.
    """
    if hasattr(model, "classes_"):
        raw_classes = model.classes_
    elif hasattr(model, "named_steps") and "classifier" in model.named_steps:
        clf_step = model.named_steps["classifier"]
        if hasattr(clf_step, "classes_"):
            raw_classes = clf_step.classes_
        else:
            raise UncertaintyModelError("Classifier step does not contain 'classes_' attribute.")
    else:
        raise UncertaintyModelError("Unable to extract 'classes_' from model.")

    if raw_classes is None or len(raw_classes) == 0:
        raise UncertaintyModelError("Model 'classes_' attribute is empty or None.")

    classes_list = list(raw_classes)

    # 1. Reject duplicate labels
    seen = set()
    duplicates = [c for c in classes_list if c in seen or seen.add(c)]
    if duplicates:
        raise UncertaintyModelError(
            f"Model classes contain duplicate labels: {duplicates}. Found: {classes_list}"
        )

    classes_set = set(classes_list)
    allowed_set = set(ALLOWED_CATEGORIES)

    # 2. Reject missing categories
    missing = allowed_set - classes_set
    if missing:
        raise UncertaintyModelError(
            f"Model is missing required classification label(s): {sorted(missing)}. Found: {classes_list}"
        )

    # 3. Reject additional / unexpected categories (e.g. 5 classes)
    extra = classes_set - allowed_set
    if extra:
        raise UncertaintyModelError(
            f"Model contains unexpected additional classification label(s): {sorted(extra)}. "
            f"Expected exactly {list(ALLOWED_CATEGORIES)}, got: {classes_list}"
        )

    # 4. Enforce exact count
    if len(classes_list) != len(ALLOWED_CATEGORIES):
        raise UncertaintyModelError(
            f"Model must contain exactly {len(ALLOWED_CATEGORIES)} classes, got {len(classes_list)}: {classes_list}"
        )

    return classes_list


def load_uncertainty_model(model_path: Optional[Union[str, Path]] = None) -> Any:
    """
    Load the saved Phase 3 model artifact without retraining.
    
    Args:
        model_path: Optional path to saved model artifact. If None, defaults to
                    models/notes_pipeline.joblib.
                    
    Returns:
        Fitted scikit-learn Pipeline or Classifier.
        
    Raises:
        FileNotFoundError: If model file does not exist.
        UncertaintyModelError: If model is missing required attributes or valid classes.
    """
    if model_path is not None:
        target_path = Path(model_path)
    else:
        project_root = Path(__file__).resolve().parent.parent
        target_path = project_root / "models" / "notes_pipeline.joblib"

    if not target_path.exists():
        raise FileNotFoundError(f"Model artifact not found at: {target_path}")

    try:
        model = joblib.load(target_path)
    except Exception as e:
        raise UncertaintyModelError(f"Failed to deserialize model at {target_path}: {e}") from e

    # Verify model supports probability prediction
    if not hasattr(model, "predict_proba"):
        raise UncertaintyModelError("Loaded model does not implement 'predict_proba()'.")

    # Rigorously validate classes
    get_model_classes(model)

    return model


def compute_decision_score_contributions(
    text: str,
    model: Any,
    target_category: str
) -> Dict[str, Any]:
    """
    Calculate the genuinely computed linear decision score contributions:
        z_c = b_c + sum_i (x_i * w_{c,i})
        
    Args:
        text: Input note text.
        model: Fitted Pipeline with 'vectorizer' and 'classifier'.
        target_category: Class label c to evaluate.
        
    Returns:
        Dict[str, Any]:
            - target_category: Category evaluated.
            - intercept: Class intercept b_c.
            - active_tokens: Tokens present in text and vocabulary.
            - contributions: List of (token, x_i * w_{c,i}) sorted descending.
            - linear_score: Total decision score z_c.
            - is_all_zero: True if no vocabulary tokens matched.
    """
    if not hasattr(model, "named_steps") or "vectorizer" not in model.named_steps:
        return {
            "target_category": target_category,
            "intercept": 0.0,
            "active_tokens": [],
            "contributions": [],
            "linear_score": 0.0,
            "is_all_zero": True
        }

    vectorizer = model.named_steps["vectorizer"]
    classifier = model.named_steps["classifier"]
    feature_names = np.array(vectorizer.get_feature_names_out())
    classes = list(classifier.classes_)

    if target_category not in classes:
        raise UncertaintyModelError(f"Target category {target_category} not in classes {classes}")

    c_idx = classes.index(target_category)
    x_vec = vectorizer.transform([text]).toarray()[0]
    active_indices = np.where(x_vec > 0)[0]
    active_tokens = feature_names[active_indices].tolist()

    b_c = float(classifier.intercept_[c_idx])
    if len(active_indices) == 0:
        return {
            "target_category": target_category,
            "intercept": round(b_c, 4),
            "active_tokens": [],
            "contributions": [],
            "linear_score": round(b_c, 4),
            "is_all_zero": True
        }

    contribs = [
        (tok, round(float(x_vec[i] * classifier.coef_[c_idx][i]), 4))
        for i, tok in zip(active_indices, active_tokens)
    ]
    contribs.sort(key=lambda item: item[1], reverse=True)
    z_c = b_c + sum(c[1] for c in contribs)

    return {
        "target_category": target_category,
        "intercept": round(b_c, 4),
        "active_tokens": active_tokens,
        "contributions": contribs,
        "linear_score": round(z_c, 4),
        "is_all_zero": False
    }


def predict_with_uncertainty(
    text: Any,
    model: Any,
    threshold: float = 0.40
) -> Dict[str, Any]:
    """
    Predict note category and determine uncertainty status based on maximum probability.
    
    Args:
        text: Note text string.
        model: Fitted model implementing predict_proba.
        threshold: Confidence cutoff within [0.0, 1.0]. Default: 0.40.
        
    Returns:
        Dict[str, Any]:
            - category (str): Best guess category (Study, Money, Travel, Shopping).
            - confidence (float): Maximum predicted probability.
            - uncertain (bool): True if confidence < threshold, False if >= threshold.
            - probabilities (Dict[str, float]): Class-to-probability mapping preserving class order.
    """
    valid_text = validate_note_text(text)
    valid_threshold = validate_threshold(threshold)

    classes = get_model_classes(model)

    try:
        raw_probs = model.predict_proba([valid_text])[0]
    except Exception as e:
        raise UncertaintyModelError(f"Model failed during predict_proba: {e}") from e

    probs_arr = validate_model_probabilities(raw_probs, classes)

    best_idx = int(np.argmax(probs_arr))
    best_category = str(classes[best_idx])
    confidence = float(probs_arr[best_idx])

    # Strict boundary rule:
    # confidence < threshold  -> uncertain = True
    # confidence == threshold -> uncertain = False
    # confidence > threshold  -> uncertain = False
    is_uncertain = bool(confidence < valid_threshold)

    # Preserve the exact classifier class mapping
    prob_dict = {str(cls_name): round(float(probs_arr[i]), 4) for i, cls_name in enumerate(classes)}

    return {
        "category": best_category,
        "confidence": round(confidence, 4),
        "uncertain": is_uncertain,
        "probabilities": prob_dict
    }


def evaluate_labeled_dataset(
    df: pd.DataFrame,
    model: Any,
    threshold: float
) -> Dict[str, Any]:
    """
    Evaluate uncertainty and error trade-offs on a labeled dataset (e.g. validation.csv).
    
    Rigorously validates:
    - 'text' and 'category' columns exist.
    - At least 1 row.
    - Rejects missing, non-string, empty, or whitespace-only text.
    - Rejects missing, non-string, or unexpected category values.
    """
    valid_threshold = validate_threshold(threshold)

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")
    if "text" not in df.columns or "category" not in df.columns:
        raise ValueError("Labeled dataset must contain 'text' and 'category' columns.")

    total_samples = len(df)
    if total_samples == 0:
        raise ValueError("Dataset cannot be empty. Must contain at least one row.")

    correct_count = 0
    incorrect_count = 0
    uncertain_count = 0
    confident_count = 0
    incorrect_and_confident_count = 0
    incorrect_and_confident_records = []

    for idx, row in df.iterrows():
        # Validate text
        if "text" not in row or pd.isna(row["text"]):
            raise ValueError(f"Row {idx}: missing 'text' value in validation dataset.")
        text_val = row["text"]
        if not isinstance(text_val, str):
            raise TypeError(f"Row {idx}: 'text' must be a string, got {type(text_val).__name__}: {text_val!r}")
        if not text_val.strip():
            raise ValueError(f"Row {idx}: 'text' cannot be empty or whitespace-only.")

        # Validate category without silent string conversion
        if "category" not in row or pd.isna(row["category"]):
            raise ValueError(f"Row {idx}: missing 'category' value in validation dataset.")
        cat_val = row["category"]
        if not isinstance(cat_val, str):
            raise TypeError(f"Row {idx}: 'category' must be a string, got {type(cat_val).__name__}: {cat_val!r}")
        if cat_val not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Row {idx}: unexpected category {cat_val!r}. Must be one of {list(ALLOWED_CATEGORIES)}"
            )

        pred_res = predict_with_uncertainty(text_val, model, threshold=valid_threshold)
        predicted = pred_res["category"]
        conf = pred_res["confidence"]
        is_uncertain = pred_res["uncertain"]

        is_correct = (cat_val == predicted)
        if is_correct:
            correct_count += 1
        else:
            incorrect_count += 1

        if is_uncertain:
            uncertain_count += 1
        else:
            confident_count += 1
            if not is_correct:
                incorrect_and_confident_count += 1
                incorrect_and_confident_records.append({
                    "row_index": int(idx),
                    "text": text_val,
                    "actual_category": cat_val,
                    "predicted_category": predicted,
                    "confidence": conf,
                    "probabilities": pred_res["probabilities"]
                })

    uncertainty_rate = (uncertain_count / total_samples) * 100.0

    return {
        "threshold": valid_threshold,
        "total_samples": total_samples,
        "correct_predictions": correct_count,
        "incorrect_predictions": incorrect_count,
        "uncertain_predictions": uncertain_count,
        "confident_predictions": confident_count,
        "uncertainty_rate": round(uncertainty_rate, 2),
        "incorrect_and_confident_count": incorrect_and_confident_count,
        "incorrect_and_confident_records": incorrect_and_confident_records
    }


def evaluate_out_of_scope_dataset(
    df: pd.DataFrame,
    model: Any,
    threshold: float
) -> Dict[str, Any]:
    """
    Evaluate uncertainty rejection on an unlabeled out-of-scope dataset (e.g. out_of_scope_examples.csv).
    
    Rigorously validates:
    - 'text' column exists.
    - At least 1 row.
    - Rejects missing, non-string, empty, or whitespace-only text.
    - Does NOT compute classification accuracy (OOS notes have no 4-class ground truth).
    """
    valid_threshold = validate_threshold(threshold)

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}")
    if "text" not in df.columns:
        raise ValueError("Out-of-scope dataset must contain 'text' column.")

    total_samples = len(df)
    if total_samples == 0:
        raise ValueError("Dataset cannot be empty. Must contain at least one row.")

    flagged_uncertain_count = 0
    unflagged_count = 0
    unflagged_records = []

    for idx, row in df.iterrows():
        if "text" not in row or pd.isna(row["text"]):
            raise ValueError(f"Row {idx}: missing 'text' value in out-of-scope dataset.")
        text_val = row["text"]
        if not isinstance(text_val, str):
            raise TypeError(f"Row {idx}: 'text' must be a string, got {type(text_val).__name__}: {text_val!r}")
        if not text_val.strip():
            raise ValueError(f"Row {idx}: 'text' cannot be empty or whitespace-only.")

        pred_res = predict_with_uncertainty(text_val, model, threshold=valid_threshold)
        conf = pred_res["confidence"]
        is_uncertain = pred_res["uncertain"]
        predicted_cat = pred_res["category"]

        if is_uncertain:
            flagged_uncertain_count += 1
        else:
            unflagged_count += 1
            # Compute dynamic decision score contributions for unflagged false acceptances
            contributions = compute_decision_score_contributions(text_val, model, predicted_cat)
            unflagged_records.append({
                "row_index": int(idx),
                "text": text_val,
                "predicted_category": predicted_cat,
                "confidence": conf,
                "probabilities": pred_res["probabilities"],
                "decision_contributions": contributions
            })

    detection_rate = (flagged_uncertain_count / total_samples) * 100.0
    unflagged_rate = (unflagged_count / total_samples) * 100.0

    return {
        "threshold": valid_threshold,
        "total_samples": total_samples,
        "flagged_uncertain_count": flagged_uncertain_count,
        "unflagged_count": unflagged_count,
        "detection_rate": round(detection_rate, 2),
        "unflagged_rate": round(unflagged_rate, 2),
        "unflagged_records": unflagged_records
    }


def evaluate_uncertainty_thresholds(
    val_df: pd.DataFrame,
    oos_df: pd.DataFrame,
    model: Any,
    thresholds: Sequence[float] = (0.35, 0.40, 0.45)
) -> Dict[float, Dict[str, Any]]:
    """
    Execute fixed-threshold evaluation across validation and out-of-scope datasets.
    
    Args:
        val_df: Validation DataFrame (50 rows).
        oos_df: Out-of-scope DataFrame (12 rows).
        model: Fitted model.
        thresholds: Fixed sequence of thresholds (default: 0.35, 0.40, 0.45).
        
    Returns:
        Dict[float, Dict[str, Any]]: Mapping of threshold to metric dictionaries.
    """
    results: Dict[float, Dict[str, Any]] = {}
    for t in thresholds:
        val_res = evaluate_labeled_dataset(val_df, model, threshold=t)
        oos_res = evaluate_out_of_scope_dataset(oos_df, model, threshold=t)
        results[t] = {
            "validation": val_res,
            "out_of_scope": oos_res
        }
    return results
