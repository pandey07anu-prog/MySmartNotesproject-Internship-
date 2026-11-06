"""
Smart Notes Assistant - Machine Learning Model Development Module
Phase 3: Baseline, Improvement Experiment, Evaluation, and Serialization.

This module provides reusable, deterministic, and modular ML functionality:
1. Training a baseline TF-IDF + Logistic Regression pipeline.
2. Training an improved TF-IDF + Logistic Regression pipeline with justified enhancements.
3. Evaluating performance (Accuracy, Macro-F1, Precision, Recall, Confusion Matrix).
4. Extracting empirical error analysis with predicted probabilities and feature evidence.
5. Saving and loading serialized Joblib artifacts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline

# Standard 4 classification categories defined in CATEGORY_GUIDE.md
ALLOWED_CATEGORIES: Tuple[str, ...] = ("Study", "Money", "Travel", "Shopping")

# Default random seed for reproducibility
RANDOM_STATE = 42


def build_baseline_pipeline() -> Pipeline:
    """
    Build the baseline scikit-learn Pipeline.
    
    Standard word-level TF-IDF (default unigrams, default token pattern, no stop-word filtering)
    paired with standard Logistic Regression (C=1.0, lbfgs solver, random_state=42).
    """
    vectorizer = TfidfVectorizer()
    classifier = LogisticRegression(
        C=1.0,
        solver="lbfgs",
        random_state=RANDOM_STATE,
        max_iter=1000
    )
    return Pipeline([
        ("vectorizer", vectorizer),
        ("classifier", classifier)
    ])


def build_improved_pipeline() -> Pipeline:
    r"""
    Build the improved scikit-learn Pipeline.
    
    Justified ML Enhancements:
    1. Stop-word filtering ('english'): Removes noisy function words ('the', 'to', 'my', 'at')
       that dominate short notes and blur category distinctions.
    2. Currency token preservation (r'(?u)\b\w+\b|₹'): Captures the Indian Rupee symbol '₹'
       which appears in Money notes but is discarded by scikit-learn's default token pattern.
    3. Regularization tuning (C=2.0): Less aggressive L2 shrinkage allows informative domain
       features in small datasets (156 samples) to carry higher weights.
    """
    vectorizer = TfidfVectorizer(
        stop_words="english",
        token_pattern=r"(?u)\b\w+\b|₹",
        ngram_range=(1, 1),
        sublinear_tf=False
    )
    classifier = LogisticRegression(
        C=2.0,
        solver="lbfgs",
        random_state=RANDOM_STATE,
        max_iter=1000
    )
    return Pipeline([
        ("vectorizer", vectorizer),
        ("classifier", classifier)
    ])


def train_model(pipeline: Pipeline, df_train: pd.DataFrame) -> Pipeline:
    """
    Fit the supplied pipeline strictly on training data.
    
    Args:
        pipeline: scikit-learn Pipeline with 'vectorizer' and 'classifier'.
        df_train: DataFrame containing 'text' and 'category' columns.
        
    Returns:
        Fitted scikit-learn Pipeline.
    """
    if "text" not in df_train.columns or "category" not in df_train.columns:
        raise ValueError("df_train must contain 'text' and 'category' columns.")
    
    X_train = df_train["text"].astype(str)
    y_train = df_train["category"].astype(str)
    
    pipeline.fit(X_train, y_train)
    return pipeline


def evaluate_model(
    pipeline: Pipeline,
    df_eval: pd.DataFrame,
    labels: Sequence[str] = ALLOWED_CATEGORIES
) -> Dict[str, Any]:
    """
    Evaluate a fitted pipeline on an unseen evaluation dataset (e.g. validation.csv).
    
    Args:
        pipeline: Fitted scikit-learn Pipeline.
        df_eval: Evaluation DataFrame with 'text' and 'category'.
        labels: Expected class labels.
        
    Returns:
        Dictionary containing overall metrics, classification report dict,
        confusion matrix, per-class metrics, and detailed error analysis records.
    """
    if "text" not in df_eval.columns or "category" not in df_eval.columns:
        raise ValueError("df_eval must contain 'text' and 'category' columns.")

    X_eval = df_eval["text"].astype(str).tolist()
    y_true = df_eval["category"].astype(str).tolist()

    y_pred = pipeline.predict(X_eval)
    y_proba = pipeline.predict_proba(X_eval)

    classes_ = list(pipeline.named_steps["classifier"].classes_)

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # Per-category metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class_metrics = {}
    for i, label in enumerate(labels):
        per_class_metrics[label] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i])
        }

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    # Detailed classification report text and dict
    report_dict = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    report_text = classification_report(
        y_true, y_pred, labels=labels, zero_division=0
    )

    # Detailed mistake extraction with mathematical feature evidence
    mistakes = []
    vectorizer = pipeline.named_steps["vectorizer"]
    classifier = pipeline.named_steps["classifier"]
    feature_names = np.array(vectorizer.get_feature_names_out())
    classes_list = list(classifier.classes_)

    for idx, (text, actual, pred) in enumerate(zip(X_eval, y_true, y_pred)):
        if actual != pred:
            prob_dist = {cls_name: round(float(y_proba[idx][j]), 4) for j, cls_name in enumerate(classes_)}
            
            # Inspect features present in this note
            transformed_vec = vectorizer.transform([text]).toarray()[0]
            active_feature_indices = np.where(transformed_vec > 0)[0]
            active_tokens = feature_names[active_feature_indices].tolist()

            # Mathematical feature evidence
            pred_idx = classes_list.index(pred)
            act_idx = classes_list.index(actual)

            if len(active_tokens) == 0:
                evidence = "Input vector is all-zero (all tokens are Out-of-Vocabulary or stop words)."
                highest_intercept_class = classes_list[int(np.argmax(classifier.intercept_))]
                reason = (
                    f"Zero active features; prediction was determined entirely by the class intercepts "
                    f"('{highest_intercept_class}' has the highest prior intercept of {float(np.max(classifier.intercept_)):.3f})."
                )
            else:
                pred_contribs = [
                    (tok, float(transformed_vec[f_idx] * classifier.coef_[pred_idx][f_idx]))
                    for f_idx, tok in zip(active_feature_indices, active_tokens)
                ]
                act_contribs = [
                    (tok, float(transformed_vec[f_idx] * classifier.coef_[act_idx][f_idx]))
                    for f_idx, tok in zip(active_feature_indices, active_tokens)
                ]
                pred_contribs.sort(key=lambda x: x[1], reverse=True)
                act_contribs.sort(key=lambda x: x[1], reverse=True)

                top_pred_tok, top_pred_val = pred_contribs[0]
                top_act_tok, top_act_val = act_contribs[0] if act_contribs else ("none", 0.0)

                evidence = (
                    f"Active tokens: {active_tokens}. "
                    f"Top token favoring '{pred}': '{top_pred_tok}' (log-weight {top_pred_val:+.3f})."
                )

                if len(active_tokens) == 1:
                    reason = (
                        f"Extreme feature sparsity: only one recognized token ('{top_pred_tok}') exists in note; "
                        f"its highest positive coefficient belongs to class '{pred}'."
                    )
                elif top_pred_tok == top_act_tok:
                    reason = (
                        f"Shared token '{top_pred_tok}' has ambiguous associations across '{actual}' and '{pred}' in training data."
                    )
                else:
                    diff = top_pred_val - top_act_val
                    reason = (
                        f"Cross-domain token '{top_pred_tok}' (favoring '{pred}') outweighed '{top_act_tok}' "
                        f"(favoring '{actual}') by a margin of {diff:+.3f} in linear logit score."
                    )

            mistakes.append({
                "index": idx,
                "text": text,
                "actual_category": actual,
                "predicted_category": pred,
                "confidence": round(float(np.max(y_proba[idx])), 4),
                "probabilities": prob_dist,
                "active_tokens": active_tokens,
                "evidence": evidence,
                "reason": reason
            })

    return {
        "total_samples": len(y_true),
        "correct_count": int(np.sum(np.array(y_true) == np.array(y_pred))),
        "incorrect_count": len(mistakes),
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": cm,
        "labels": list(labels),
        "report_dict": report_dict,
        "report_text": report_text,
        "mistakes": mistakes
    }


def save_model_artifacts(
    pipeline: Pipeline,
    output_dir: Union[str, Path]
) -> Dict[str, Path]:
    """
    Save the vectorizer, classifier, and full pipeline to disk using Joblib.
    
    Args:
        pipeline: Fitted scikit-learn Pipeline.
        output_dir: Destination directory.
        
    Returns:
        Dictionary of saved artifact file paths.
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    vectorizer = pipeline.named_steps["vectorizer"]
    classifier = pipeline.named_steps["classifier"]

    vec_path = target_dir / "tfidf_vectorizer.joblib"
    clf_path = target_dir / "notes_classifier.joblib"
    pipe_path = target_dir / "notes_pipeline.joblib"

    joblib.dump(vectorizer, vec_path)
    joblib.dump(classifier, clf_path)
    joblib.dump(pipeline, pipe_path)

    return {
        "vectorizer": vec_path,
        "classifier": clf_path,
        "pipeline": pipe_path
    }


def load_model_artifacts(
    model_dir: Union[str, Path]
) -> Tuple[Any, Any, Pipeline]:
    """
    Load saved artifacts from disk.
    
    Returns:
        Tuple of (vectorizer, classifier, pipeline).
    """
    target_dir = Path(model_dir)
    vec_path = target_dir / "tfidf_vectorizer.joblib"
    clf_path = target_dir / "notes_classifier.joblib"
    pipe_path = target_dir / "notes_pipeline.joblib"

    if not vec_path.exists():
        raise FileNotFoundError(f"Vectorizer artifact missing at: {vec_path}")
    if not clf_path.exists():
        raise FileNotFoundError(f"Classifier artifact missing at: {clf_path}")

    vectorizer = joblib.load(vec_path)
    classifier = joblib.load(clf_path)

    if pipe_path.exists():
        pipeline = joblib.load(pipe_path)
    else:
        pipeline = Pipeline([("vectorizer", vectorizer), ("classifier", classifier)])

    return vectorizer, classifier, pipeline


def predict_note_category(
    text: str,
    pipeline: Optional[Pipeline] = None,
    vectorizer: Optional[Any] = None,
    classifier: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate category prediction and probabilities for a single note string.
    """
    if pipeline is not None:
        pred = str(pipeline.predict([text])[0])
        probs = pipeline.predict_proba([text])[0]
        classes_ = list(pipeline.named_steps["classifier"].classes_)
    elif vectorizer is not None and classifier is not None:
        vec = vectorizer.transform([text])
        pred = str(classifier.predict(vec)[0])
        probs = classifier.predict_proba(vec)[0]
        classes_ = list(classifier.classes_)
    else:
        raise ValueError("Must provide either 'pipeline' or both 'vectorizer' and 'classifier'.")

    prob_dict = {cls_name: round(float(probs[i]), 4) for i, cls_name in enumerate(classes_)}
    max_p = float(np.max(probs))

    return {
        "category": pred,
        "confidence": round(max_p, 4),
        "probabilities": prob_dict
    }

