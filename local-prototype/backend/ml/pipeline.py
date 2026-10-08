"""
Medic AI — Pipeline ML Orchestrator

Orquesta el flujo completo de inferencia:
1. Enrutador Naive Bayes (asigna especialidad)
2. Predictor XGBoost de la especialidad (calcula probabilidades de enfermedades)
3. SHAP Explainer (genera explicaciones para las predicciones top)
4. Evaluador de Alertas (calcula puntuación de urgencia)
5. Reglas clínicas deterministas (red de seguridad)
"""
from __future__ import annotations

import os
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.medical import BAYES_FEATURE_KEYS, SPECIALTIES
from config import MODELS_DIR, ENABLE_SHAP
from .naive_bayes import SpecialtyClassifier
from .gradient_boosting import DiseasePredictor
from .explainer import ModelExplainer
from .clinical_rules import evaluate_clinical_rules


# Señales que suman puntos de urgencia inmediatamente
URGENCY_WEIGHTS = {
    "chest_pain": 40,
    "breathlessness": 35,
    "loss_of_balance": 30,
    "weakness_of_one_body_side": 40,
    "slurred_speech": 40,
    "coma": 50,
    "stomach_bleeding": 30,
    "bloody_stool": 30,
    "blood_in_sputum": 30,
    "palpitations": 25,
    "high_fever": 25,
    "altered_sensorium": 40,
}

CRITICAL_SINGLE_FEATURES = {
    "chest_pain",
    "breathlessness",
    "weakness_of_one_body_side",
    "slurred_speech",
    "coma",
    "altered_sensorium",
    "stomach_bleeding",
    "bloody_stool",
    "blood_in_sputum",
}

URGENCY_MESSAGES = {
    "chest_pain": "Dolor de pecho detectado",
    "breathlessness": "Dificultad respiratoria activa",
    "weakness_of_one_body_side": "Pérdida de fuerza o sensibilidad focal",
    "slurred_speech": "Dificultad para hablar o comprender",
    "coma": "Estado de coma / Pérdida de conciencia",
    "stomach_bleeding": "Sangrado estomacal activo",
    "bloody_stool": "Heces con sangre",
    "blood_in_sputum": "Esputo con sangre",
    "altered_sensorium": "Alteración del sensorio",
}

def get_urgency_info(score: int, alarms: list, alerts: list):
    """Calcula etiquetas y destino en base a score y severidades."""
    has_critical = any(a.get("severity") == "critical" for a in alarms) or \
                   any(a.get("severity") == "critical" for a in alerts)
    has_high = any(a.get("severity") == "high" for a in alarms) or \
               any(a.get("severity") == "high" for a in alerts)
    
    if has_critical or score >= 80:
        return "critical", "urgencias_inmediatas", "Urgencias Inmediatas"
    elif has_high or score >= 60:
        return "high", "valoracion_urgente", "Valoración Médica Urgente"
    elif score >= 30:
        return "moderate", "consulta_medica", "Consulta Médica Prioritaria"
    else:
        return "low", "seguimiento", "Seguimiento Médico"

def build_safe_clinical_fallback(features: dict, error: Exception = None) -> dict:
    """Fallback robusto si el pipeline ML falla. Usa reglas y pesos básicos."""
    from .clinical_rules import evaluate_clinical_rules
    calc_urgency = 0
    alarms = []
    for k, v in features.items():
        if v == "present":
            if k in URGENCY_WEIGHTS: calc_urgency += URGENCY_WEIGHTS[k]
            if k in URGENCY_MESSAGES:
                alarms.append({"signal": URGENCY_MESSAGES[k], "severity": "critical" if URGENCY_WEIGHTS[k] >= 40 else "high"})
    
    rule_res = evaluate_clinical_rules(features)
    rule_urgency = rule_res.get("urgency_override") or 0
    urg_score = min(max(calc_urgency, rule_urgency), 100)
    
    combined_alarms = alarms + rule_res.get("alarm_signals", [])
    alerts = rule_res.get("rule_hypotheses", [])
    
    u_lbl, dest, d_lbl = get_urgency_info(urg_score, combined_alarms, alerts)
    spec = rule_res.get("specialty_override") or "sin_clasificar"
    
    err_str = type(error).__name__ if error else "unavailable"
    active_count = sum(1 for v in features.values() if v == "present")
    insufficient = active_count < 2 and not alerts
    
    return {
        "assigned_specialty": spec,
        "specialty_confidence": None,
        "specialty_source": "clinical_fallback",
        "clinical_alerts": alerts,
        "ml_hypotheses": [],
        "urgency_score": urg_score,
        "urgency_label": u_lbl,
        "recommended_destination": dest,
        "destination_label": d_lbl,
        "alarm_signals": combined_alarms,
        "insufficient_data": insufficient,
        "analysis_degraded": True,
        "ml_suppressed_reason": f"ML no disponible por error interno ({err_str}). Se aplicaron reglas experimentales no validadas."
    }

class MedicalPipeline:
    def __init__(self, enable_ml=True):
        self.enable_ml = enable_ml
        self.router = SpecialtyClassifier()
        self.gb_models = {}
        self.explainers = {}
        self.load_errors = {}
        if self.enable_ml:
            self._load_models()

    def _load_models(self):
        router_path = MODELS_DIR / "naive_bayes_router.joblib"
        if router_path.exists():
            try:
                self.router.load(router_path)
            except Exception as exc:
                self.load_errors["router"] = type(exc).__name__
            
        for spec in SPECIALTIES:
            gb_path = MODELS_DIR / f"gb_{spec}.joblib"
            if gb_path.exists():
                predictor = DiseasePredictor(spec)
                try:
                    predictor.load(gb_path)
                    self.gb_models[spec] = predictor
                    self.explainers[spec] = ModelExplainer(predictor) if ENABLE_SHAP else None
                except Exception as exc:
                    self.load_errors[spec] = type(exc).__name__

    def availability(self):
        return {"enabled": self.enable_ml, "router_ready": self.router._is_trained,
                "available_specialties": sorted(self.gb_models),
                "missing_specialties": [s for s in SPECIALTIES if s not in self.gb_models],
                "load_errors": self.load_errors,
                "ready": self.enable_ml and self.router._is_trained and bool(self.gb_models)}

    def analyze(self, bayes_features_dict: dict) -> dict:
        """
        Ejecuta el pipeline completo y devuelve el resultado analítico separado (Reglas vs ML).
        """
        # Adaptador para modelos XGBoost/NaiveBayes que esperan 0/1
        ml_features = bayes_features_dict
        active_count = sum(v == "present" for v in ml_features.values())

        # 1. Calcular urgencia base sobre síntomas
        calculated_urgency = 0
        alarm_signals = []
        for feat, val in bayes_features_dict.items():
            if val == "present" and feat in URGENCY_WEIGHTS:
                calculated_urgency += URGENCY_WEIGHTS[feat]
            
            if val == "present" and feat in URGENCY_MESSAGES:
                severity = "critical" if URGENCY_WEIGHTS[feat] >= 40 else "high"
                alarm_signals.append({"signal": URGENCY_MESSAGES[feat], "severity": severity})
                
        calculated_urgency = min(calculated_urgency, 100)

        # 2. Reglas clínicas deterministas (PRIMERO)
        rule_results = evaluate_clinical_rules(bayes_features_dict)
        clinical_alerts = rule_results.get("rule_hypotheses", [])
        
        # Merge alarm signals
        alarm_signals.extend(rule_results.get("alarm_signals", []))
        
        # Override fields
        rule_urgency = rule_results.get("urgency_override") or 0
        urgency_score = max(calculated_urgency, rule_urgency)
        specialty = rule_results.get("specialty_override") or "sin_clasificar"
        if specialty != "sin_clasificar":
            conf = None
            specialty_source = "clinical_rule"
        else:
            conf = None
            specialty_source = "ml_router"

        u_label, r_dest, d_label = get_urgency_info(urgency_score, alarm_signals, clinical_alerts)

        # 3. Early return si faltan datos y no hay alertas clínicas
        if active_count < 2 and not clinical_alerts:
            if active_count == 0:
                reason = "Datos insuficientes: no se han detectado síntomas estructurados suficientes."
            elif alarm_signals:
                reason = "Datos insuficientes para hipótesis ML, pero se detectó un síntoma de alarma aislado."
            elif not self.enable_ml:
                reason = "ML desactivado en este entorno o test."
            else:
                reason = "Datos insuficientes: se requiere más información antes de generar hipótesis ML."

            return {
                "assigned_specialty": specialty,
                "specialty_confidence": None,
                "specialty_source": specialty_source,
                "clinical_alerts": [],
                "ml_hypotheses": [],
                "ml_suppressed_reason": reason,
                "urgency_score": urgency_score,
                "urgency_label": u_label,
                "recommended_destination": r_dest,
                "destination_label": d_label,
                "alarm_signals": alarm_signals,
                "insufficient_data": True,
                "analysis_degraded": not self.availability()["ready"],
            }

        # 4. Enrutar a la especialidad correcta (si las reglas no la forzaron)
        if specialty == "sin_clasificar" and active_count > 0:
            if self.enable_ml and self.router._is_trained:
                specialty, conf = self.router.predict_specialty(ml_features)
                specialty_source = "ml_router"
            else:
                specialty_source = "unavailable_ml" if self.enable_ml else "disabled_ml"

        # 5. Predecir enfermedades usando el modelo ML específico
        ml_hypotheses = []
        suppressed_reason = None
        degraded = not self.enable_ml
        has_severe_alert = any(a.get("severity") in ("critical", "high") for a in clinical_alerts) or \
                           any(a.get("severity") == "critical" for a in alarm_signals)
        
        if has_severe_alert:
            suppressed_reason = "ML omitido porque existe una alerta clínica determinista prioritaria."
        elif not self.enable_ml:
            suppressed_reason = "ML desactivado en este entorno o test."
        elif specialty in self.gb_models and active_count > 0:
            predictor = self.gb_models[specialty]
            explainer = self.explainers[specialty]
            
            top_diseases = predictor.predict_top_diseases(ml_features, top_k=3)
            
            for disease_name, prob in top_diseases:
                # Generar explicaciones SHAP
                try:
                    shap_vals = explainer.explain(ml_features, disease_name) if explainer else {}
                except Exception as e:
                    print(f"Error en SHAP: {e}")
                    shap_vals = {}
                
                ml_hypotheses.append({
                    "disease_name": disease_name,
                    "probability": prob,
                    "shap_explanation": shap_vals,
                    "recommended_tests": ["Evaluación médica presencial"],
                    "is_rare": False
                })

        else:
            suppressed_reason = "Modelo compatible no disponible para esta especialidad; no se generan predicciones."
            degraded = True

        # Si hay pocos síntomas pero fue retenido por has_critical_single, indicamos datos insuficientes
        is_insufficient = False

        # Volver a evaluar la urgencia en caso de que las hipótesis hayan cambiado el score
        if ml_hypotheses:
            u_label, r_dest, d_label = get_urgency_info(urgency_score, alarm_signals, clinical_alerts)

        return {
            "assigned_specialty": specialty,
            "specialty_confidence": conf,
            "specialty_source": specialty_source,
            "clinical_alerts": clinical_alerts,
            "ml_hypotheses": ml_hypotheses,
            "ml_suppressed_reason": suppressed_reason,
            "urgency_score": urgency_score,
            "urgency_label": u_label,
            "recommended_destination": r_dest,
            "destination_label": d_label,
            "alarm_signals": alarm_signals,
            "insufficient_data": False,
            "analysis_degraded": degraded,
            "model_status": self.availability(),
        }

