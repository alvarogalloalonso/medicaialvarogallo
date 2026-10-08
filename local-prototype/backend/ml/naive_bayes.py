"""
Medic AI — Naive Bayes Router

Clasificador Multinomial/Bernoulli para enrutar los síntomas a una especialidad.
"""
from __future__ import annotations

import os
import joblib
from pathlib import Path
from sklearn.naive_bayes import BernoulliNB
from sklearn.metrics import classification_report

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schemas.medical import BAYES_FEATURE_KEYS
from .features import FEATURE_SCHEMA, FEATURE_COLUMNS, feature_frame


class SpecialtyClassifier:
    """Clasificador Bernoulli Naive Bayes para especialidades médicas."""

    def __init__(self):
        self.model = BernoulliNB(alpha=0.1)
        self.classes_ = []
        self._is_trained = False

    def train(self, X, y):
        """Entrena el clasificador con datos (X: features, y: labels)."""
        self.model.fit(X, y)
        self.classes_ = self.model.classes_
        self._is_trained = True

        print("Reporte Naive Bayes (Especialidades):")
        y_pred = self.model.predict(X)
        print(classification_report(y, y_pred, zero_division=0))

    def predict_specialty(self, feature_dict: dict) -> tuple[str, float]:
        """Predice la especialidad y su nivel de confianza."""
        if not self._is_trained:
            raise RuntimeError("Router not trained")

        vector = feature_frame(feature_dict)
        probs = self.model.predict_proba(vector)[0]
        
        best_idx = probs.argmax()
        best_class = self.classes_[best_idx]
        best_prob = probs[best_idx]

        return best_class, float(best_prob)

    def save(self, filepath: str | Path):
        joblib.dump({"feature_schema": FEATURE_SCHEMA, "model": self.model, "classes": self.classes_}, filepath)

    def load(self, filepath: str | Path):
        data = joblib.load(filepath)
        if data.get("feature_schema") != FEATURE_SCHEMA:
            raise ValueError("Incompatible model schema; retrain with presence-observed-v2")
        self.model = data["model"]
        self.classes_ = data["classes"]
        self._is_trained = True

