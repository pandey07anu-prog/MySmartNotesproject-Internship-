"""
Smart Notes Assistant - Machine Learning Training & Evaluation Pipeline
Trains the note classification pipeline on data/train.csv, evaluates against
data/validation.csv, performs error analysis and uncertainty benchmarking,
and serializes the trained model to model/classifier.joblib.

Usage:
    python train.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "model"
MODEL_PATH = MODEL_DIR / "classifier.joblib"

ALLOWED_CATEGORIES: Tuple[str, ...] = ("Study", "Money", "Travel", "Shopping")
UNCERTAINTY_THRESHOLD: float = 0.50
RANDOM_STATE: int = 42


def load_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate training, validation, and out-of-scope datasets."""
    train_path = DATA_DIR / "train.csv"
    val_path = DATA_DIR / "validation.csv"
    oos_path = DATA_DIR / "out_of_scope_examples.csv"

    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError(f"Missing train or validation datasets in {DATA_DIR}")

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    oos_df = pd.read_csv(oos_path) if oos_path.exists() else pd.DataFrame(columns=["text"])

    # Clean and validate
    train_df["text"] = train_df["text"].astype(str).str.strip()
    val_df["text"] = val_df["text"].astype(str).str.strip()

    assert not train_df["text"].isna().any(), "Training texts contain nulls"
    assert not val_df["text"].isna().any(), "Validation texts contain nulls"
    assert set(train_df["category"]).issubset(set(ALLOWED_CATEGORIES)), "Unknown category in train"
    assert set(val_df["category"]).issubset(set(ALLOWED_CATEGORIES)), "Unknown category in val"

    return train_df, val_df, oos_df


def build_baseline_pipeline() -> Pipeline:
    """Standard word-level TF-IDF with default Logistic Regression."""
    return Pipeline([
        ("tfidf", TfidfVectorizer()),
        ("clf", LogisticRegression(C=1.0, solver="lbfgs", random_state=RANDOM_STATE, max_iter=1000))
    ])


def build_improved_pipeline() -> Pipeline:
    """
    Improved ML Pipeline:
    1. Preserves currency symbols (₹, $, €, £) essential for Money classification.
    2. English stop-words filtering removes high-frequency non-informative words.
    3. Regularization C=3.5 balances high-information tokens in vocabulary.
    4. Unigram + Bigram (1, 2) features capture rich phrases (e.g. 'study tomorrow', 'electricity bill').
    """
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            stop_words="english",
            token_pattern=r"(?u)\b\w+\b|[₹$€£]",
            ngram_range=(1, 2),
            sublinear_tf=False,
        )),
        ("clf", LogisticRegression(
            C=3.5,
            solver="lbfgs",
            random_state=RANDOM_STATE,
            max_iter=1000,
        ))
    ])


def evaluate_pipeline(pipeline: Pipeline, df_val: pd.DataFrame) -> Dict[str, Any]:
    """Calculate accuracy, macro-F1, per-class metrics, confusion matrix, and mistakes."""
    X_val = df_val["text"]
    y_val = df_val["category"]

    preds = pipeline.predict(X_val)
    probs = pipeline.predict_proba(X_val)
    classes = list(pipeline.classes_)

    acc = float(accuracy_score(y_val, preds))
    macro_f1 = float(f1_score(y_val, preds, average="macro"))
    prec, rec, f1, _ = precision_recall_fscore_support(y_val, preds, labels=ALLOWED_CATEGORIES)
    cm = confusion_matrix(y_val, preds, labels=ALLOWED_CATEGORIES).tolist()

    # Collect mistakes
    mistakes = []
    for idx, (text, actual, pred, prob_arr) in enumerate(zip(X_val, y_val, preds, probs)):
        if actual != pred:
            prob_dict = {cls_name: round(float(prob_arr[c_i]), 4) for c_i, cls_name in enumerate(classes)}
            confidence = float(np.max(prob_arr))
            mistakes.append({
                "index": idx,
                "text": text,
                "actual": actual,
                "predicted": pred,
                "confidence": round(confidence, 4),
                "probabilities": prob_dict,
            })

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "precision": {cat: round(float(p), 4) for cat, p in zip(ALLOWED_CATEGORIES, prec)},
        "recall": {cat: round(float(r), 4) for cat, r in zip(ALLOWED_CATEGORIES, rec)},
        "f1": {cat: round(float(f), 4) for cat, f in zip(ALLOWED_CATEGORIES, f1)},
        "confusion_matrix": cm,
        "mistakes": mistakes,
        "predictions": preds,
        "probabilities": probs,
    }


def analyze_feature_evidence(pipeline: Pipeline, note_text: str) -> Dict[str, Any]:
    """Examine TF-IDF features and logistic regression coefficients for evidence."""
    tfidf: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clf: LogisticRegression = pipeline.named_steps["clf"]
    feature_names = np.array(tfidf.get_feature_names_out())
    classes = list(clf.classes_)

    vec = tfidf.transform([note_text]).toarray()[0]
    present_indices = np.where(vec > 0)[0]
    active_tokens = feature_names[present_indices]

    contributions: Dict[str, Dict[str, float]] = {c: {} for c in classes}
    for c_idx, c_name in enumerate(classes):
        weights = clf.coef_[c_idx]
        for token_idx in present_indices:
            token = feature_names[token_idx]
            token_score = float(vec[token_idx] * weights[token_idx])
            contributions[c_name][token] = round(token_score, 4)

    return {
        "active_tokens": list(active_tokens),
        "contributions": contributions,
    }


def evaluate_uncertainty(pipeline: Pipeline, df_val: pd.DataFrame, df_oos: pd.DataFrame) -> Dict[str, Any]:
    """Evaluate out-of-scope rejection and validation ambiguity at different thresholds."""
    val_probs = np.max(pipeline.predict_proba(df_val["text"]), axis=1)
    oos_probs = np.max(pipeline.predict_proba(df_oos["text"]), axis=1) if len(df_oos) > 0 else np.array([])

    thresholds = [0.45, 0.50, 0.55, 0.60]
    results = {}
    for th in thresholds:
        oos_flagged = float(np.mean(oos_probs < th)) if len(oos_probs) > 0 else 0.0
        val_flagged = float(np.mean(val_probs < th))
        results[th] = {
            "oos_flagged_pct": round(oos_flagged * 100, 1),
            "oos_flagged_count": int(np.sum(oos_probs < th)) if len(oos_probs) > 0 else 0,
            "val_flagged_pct": round(val_flagged * 100, 1),
            "val_flagged_count": int(np.sum(val_probs < th)),
        }
    return results


def main() -> None:
    print("=" * 70)
    print("SMART NOTES ASSISTANT - MODEL TRAINING & EVALUATION")
    print("=" * 70)

    train_df, val_df, oos_df = load_datasets()
    print(f"Loaded {len(train_df)} training rows, {len(val_df)} validation rows, {len(oos_df)} out-of-scope rows.")

    # 1. Baseline Model
    print("\n[1/5] Training Baseline Pipeline (Default TF-IDF + Logistic Regression C=1.0)...")
    baseline = build_baseline_pipeline()
    baseline.fit(train_df["text"], train_df["category"])
    base_eval = evaluate_pipeline(baseline, val_df)
    print(f"  -> Baseline Accuracy: {base_eval['accuracy']:.4f} | Macro-F1: {base_eval['macro_f1']:.4f}")

    # 2. Improved Model
    print("\n[2/5] Training Improved Pipeline (Currency-preserving TF-IDF + Stopwords + C=2.0)...")
    improved = build_improved_pipeline()
    improved.fit(train_df["text"], train_df["category"])
    imp_eval = evaluate_pipeline(improved, val_df)
    print(f"  -> Improved Accuracy: {imp_eval['accuracy']:.4f} | Macro-F1: {imp_eval['macro_f1']:.4f}")

    # 3. Serialize Selected Pipeline
    print(f"\n[3/5] Saving Trained Model to {MODEL_PATH}...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "pipeline": improved,
        "classes": list(improved.classes_),
        "uncertainty_threshold": UNCERTAINTY_THRESHOLD,
        "metrics": {
            "baseline_accuracy": base_eval["accuracy"],
            "baseline_macro_f1": base_eval["macro_f1"],
            "improved_accuracy": imp_eval["accuracy"],
            "improved_macro_f1": imp_eval["macro_f1"],
        }
    }
    joblib.dump(payload, MODEL_PATH)
    print("  -> Saved model artifact successfully.")

    # 4. Error Analysis
    print("\n[4/5] Detailed Error Analysis (Validation Set Mistakes)...")
    print(f"Total validation mistakes: {len(imp_eval['mistakes'])} out of {len(val_df)} examples.")
    for m in imp_eval["mistakes"][:3]:
        evidence = analyze_feature_evidence(improved, m["text"])
        print(f"\n  - Note: \"{m['text']}\"")
        print(f"    Expected: {m['actual']} | Predicted: {m['predicted']} (Confidence: {m['confidence']:.2f})")
        print(f"    Probabilities: {m['probabilities']}")
        print(f"    Active Tokens: {evidence['active_tokens']}")

    # 5. Uncertainty Benchmark
    print("\n[5/5] Uncertainty Threshold Analysis (Out-of-Scope Detection)...")
    unc_res = evaluate_uncertainty(improved, val_df, oos_df)
    for th, stats in unc_res.items():
        chosen_marker = " <-- [CHOSEN THRESHOLD]" if th == UNCERTAINTY_THRESHOLD else ""
        print(f"  Threshold {th:.2f}: OOS Flagged = {stats['oos_flagged_pct']}% ({stats['oos_flagged_count']}/12) | "
              f"Val Flagged = {stats['val_flagged_pct']}% ({stats['val_flagged_count']}/50){chosen_marker}")

    print("\n" + "=" * 70)
    print("TRAINING & EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()

