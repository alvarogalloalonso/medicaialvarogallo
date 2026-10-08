"""
Medic AI — SHAP Explainer

Genera explicaciones de los modelos de Gradient Boosting para entender
por qué se han asignado ciertas probabilidades.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from .features import FEATURE_COLUMNS, feature_frame


class ModelExplainer:
    """Wrapper para generar explicaciones SHAP del modelo XGBoost subyacente."""

    def __init__(self, predictor):
        # predictor es un objeto DiseasePredictor (tiene predictor.model que es un CalibratedClassifierCV)
        self.predictor = predictor
        
        # CalibratedClassifierCV envuelve a XGBoost en una lista de estimadores calibrados.
        # Para SHAP rápido usamos el primer estimador base entrenado.
        if hasattr(self.predictor.model, "calibrated_classifiers_"):
            self.base_model = self.predictor.model.calibrated_classifiers_[0].estimator
        else:
            self.base_model = self.predictor.base_model
            
        # Intentar crear TreeExplainer
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.base_model)
            self._is_ready = True
        except Exception as e:
            print(f"⚠️ No se pudo inicializar SHAP explainer: {e}")
            self._is_ready = False

    def explain(self, feature_dict: dict, target_disease: str) -> dict[str, float]:
        """
        Devuelve el impacto (SHAP value) de las features activas para una enfermedad.
        """
        if not self._is_ready or len(self.predictor.classes_) == 0:
            return {}

        vector = feature_frame(feature_dict)
        
        try:
            # Obtener el índice de la clase
            class_idx = list(self.predictor.classes_).index(target_disease)
            
            # Calcular valores SHAP
            shap_values = self.explainer.shap_values(vector)
            
            # En multi-clase, shap_values es a veces una lista de arrays por clase
            if isinstance(shap_values, list):
                class_shap = shap_values[class_idx][0]
            elif len(shap_values.shape) == 3: # (n_samples, n_features, n_classes)
                class_shap = shap_values[0, :, class_idx]
            else:
                class_shap = shap_values[0]
                if len(self.predictor.classes_) == 2 and class_idx == 0:
                    class_shap = -class_shap
                
            # Mapear a features
            explanation = {}
            for i, feat in enumerate(FEATURE_COLUMNS):
                # Solo incluir features que aporten algo significativo
                if abs(class_shap[i]) > 0.05:
                    explanation[feat] = float(class_shap[i])
                    
            return explanation
            
        except Exception as e:
            print(f"⚠️ Error generando explicación SHAP: {e}")
            return {}

