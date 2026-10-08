"""
Medic AI — Gradient Boosting Predictors

Modelos XGBoost por especialidad, calibrados para estimar probabilidades de enfermedades.
"""
from __future__ import annotations

import os
import joblib
from pathlib import Path
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schemas.medical import BAYES_FEATURE_KEYS
from .features import FEATURE_SCHEMA, FEATURE_COLUMNS, feature_frame


class DiseasePredictor:
    """Modelo XGBoost Calibrado para una especialidad específica."""

    def __init__(self, specialty: str):
        self.specialty = specialty
        
        # Base XGBoost
        self.base_model = xgb.XGBClassifier(
            objective="multi:softprob",
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            eval_metric="mlogloss",
            use_label_encoder=False,
            n_jobs=1,
            random_state=42
        )
        
        # Calibrador (Isotonic funciona mejor si hay suficientes datos, sino Sigmoid)
        self.model = CalibratedClassifierCV(
            estimator=self.base_model,
            method="sigmoid",
            cv=3
        )
        
        self.classes_ = []
        self._is_trained = False

    def train(self, X: pd.DataFrame, y: pd.Series):
        """Entrena y calibra el modelo."""
        if len(y.unique()) < 2:
            print(f"⚠️ {self.specialty}: No hay suficientes clases para entrenar.")
            return

        from sklearn.preprocessing import LabelEncoder
        self.le = LabelEncoder()
        y_encoded = self.le.fit_transform(y)
        
        num_classes = len(self.le.classes_)
        if num_classes == 2:
            self.base_model.set_params(objective="binary:logistic")
        else:
            self.base_model.set_params(objective="multi:softprob", num_class=num_classes)

        self.model.fit(X, y_encoded)
        self.classes_ = self.le.classes_
        self._is_trained = True

        print(f"Reporte XGBoost ({self.specialty}):")
        y_pred = self.model.predict(X)
        y_pred_decoded = self.le.inverse_transform(y_pred)
        print(classification_report(y, y_pred_decoded, zero_division=0))

    def predict_top_diseases(self, feature_dict: dict, top_k: int = 3) -> list[tuple[str, float]]:
        """Devuelve las top_k enfermedades y sus probabilidades calibradas."""
        if not self._is_trained:
            return []

        vector = feature_frame(feature_dict)
        probs = self.model.predict_proba(vector)[0]
        
        # Combinar clases y probabilidades, ordenar descendente
        results = list(zip(self.classes_, probs))
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Filtrar los top_k que tengan más de un 1% de probabilidad
        return [(cls, float(p)) for cls, p in results[:top_k] if p > 0.01]

    def save(self, filepath: str | Path):
        joblib.dump({"feature_schema": FEATURE_SCHEMA, "model": self.model, "classes": getattr(self, "classes_", []), "le": getattr(self, "le", None)}, filepath)

    def load(self, filepath: str | Path):
        data = joblib.load(filepath)
        if data.get("feature_schema") != FEATURE_SCHEMA:
            raise ValueError("Incompatible model schema; retrain with presence-observed-v2")
        self.model = data["model"]
        self.classes_ = data.get("classes", [])
        self.le = data.get("le", None)
        self._is_trained = True

