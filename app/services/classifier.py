"""
Smart Notes Assistant - ML Classification Service
Loads the trained TF-IDF + Logistic Regression model artifact, performs deterministic
inference, calculates confidence, and determines uncertainty based on threshold.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.pipeline import Pipeline

from app.config import settings

logger = logging.getLogger("smart_notes.classifier")
ALLOWED_CATEGORIES: Tuple[str, ...] = ("Study", "Money", "Travel", "Shopping")


class ClassifierService:
    _instance: Optional["ClassifierService"] = None
    _pipeline: Optional[Pipeline] = None
    _classes: List[str] = list(ALLOWED_CATEGORIES)
    _threshold: float = settings.UNCERTAINTY_THRESHOLD

    def __new__(cls) -> "ClassifierService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load model artifact into memory once."""
        path = Path(model_path or settings.MODEL_PATH)
        if not path.exists():
            logger.warning(f"Model artifact not found at {path}. Triggering training...")
            # Trigger train.py programmatically if artifact is missing
            try:
                from train import main as run_train
                run_train()
            except Exception as e:
                logger.error(f"Failed to auto-train model: {e}")

        if path.exists():
            try:
                payload = joblib.load(path)
                if isinstance(payload, dict):
                    self._pipeline = payload.get("pipeline")
                    self._classes = payload.get("classes", list(ALLOWED_CATEGORIES))
                    self._threshold = payload.get("uncertainty_threshold", settings.UNCERTAINTY_THRESHOLD)
                else:
                    self._pipeline = payload
                logger.info(f"Loaded ML model successfully from {path}. Classes: {self._classes}")
            except Exception as e:
                logger.error(f"Error loading model from {path}: {e}")
                raise RuntimeError(f"Unable to load classification model: {e}")
        else:
            raise FileNotFoundError(f"Model file does not exist at {path}")

    @property
    def is_loaded(self) -> bool:
        if self._pipeline is None:
            try:
                self.load_model()
            except Exception:
                pass
        return self._pipeline is not None

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify note text into one of the four categories.
        Returns category, confidence, and uncertain flag.
        """
        if self._pipeline is None:
            self.load_model()

        assert self._pipeline is not None, "Model pipeline is not initialized"

        cleaned_text = text.strip()
        probs = self._pipeline.predict_proba([cleaned_text])[0]
        max_idx = int(np.argmax(probs))
        category = str(self._classes[max_idx])
        confidence = float(probs[max_idx])

        # If probability is below threshold, mark uncertain
        uncertain = bool(confidence < self._threshold)

        return {
            "category": category,
            "confidence": round(confidence, 4),
            "uncertain": uncertain,
            "probabilities": {cls_name: round(float(probs[i]), 4) for i, cls_name in enumerate(self._classes)}
        }


classifier_service = ClassifierService()

