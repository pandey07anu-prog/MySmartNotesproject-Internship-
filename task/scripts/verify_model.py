"""
Smart Notes Assistant - Independent Artifact Verification Script
Phase 3: Machine Learning Model Development

This script runs in an isolated Python process to verify that:
1. Saved vectorizer can be loaded from disk.
2. Saved classifier can be loaded from disk.
3. A new sentence transforms correctly without errors.
4. The prediction belongs to the four allowed categories.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure stdout handles UTF-8 on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
from src.model_trainer import ALLOWED_CATEGORIES, predict_note_category


def main() -> None:
    models_dir = PROJECT_ROOT / "models"
    vec_path = models_dir / "tfidf_vectorizer.joblib"
    clf_path = models_dir / "notes_classifier.joblib"

    print("Verifying saved artifacts in a separate Python process...")
    print(f"Loading vectorizer from: {vec_path}")
    print(f"Loading classifier from: {clf_path}")

    if not vec_path.exists() or not clf_path.exists():
        print("[!] Error: Model artifacts do not exist. Run python train.py first.", file=sys.stderr)
        sys.exit(1)

    vectorizer = joblib.load(vec_path)
    classifier = joblib.load(clf_path)

    test_samples = [
        ("Final exam for economics is scheduled next Monday.", "Study"),
        ("Send ₹5,000 to John for monthly rent payment.", "Money"),
        ("Flight ticket to Goa is confirmed for Sunday.", "Travel"),
        ("Buy milk, bread, and groceries from the supermarket.", "Shopping")
    ]

    all_passed = True
    for text, expected in test_samples:
        result = predict_note_category(text, vectorizer=vectorizer, classifier=classifier)
        pred_cat = result["category"]
        conf = result["confidence"]

        if pred_cat not in ALLOWED_CATEGORIES:
            print(f"[FAIL] Category '{pred_cat}' is not in allowed categories {ALLOWED_CATEGORIES}")
            all_passed = False
        else:
            status = "MATCH" if pred_cat == expected else "DIFFER"
            print(f"[PASS] ({status}) \"{text[:40]}...\" -> {pred_cat} (conf={conf:.2f})")

    if all_passed:
        print("\n[SUCCESS] Independent process verification passed completely.")
        sys.exit(0)
    else:
        print("\n[FAILURE] Independent process verification failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
