import pytest
import os
import sys

# Añadir el directorio base al path para importar correctamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.pipeline import MedicalPipeline, build_safe_clinical_fallback
from ml.clinical_rules import evaluate_clinical_rules
from schemas.medical import BAYES_FEATURE_KEYS

@pytest.fixture
def empty_features():
    """Genera un diccionario de features con todas en 'unknown'."""
    return {k: "unknown" for k in BAYES_FEATURE_KEYS}

@pytest.fixture
def pipeline():
    return MedicalPipeline(enable_ml=False)


def test_empty_features_returns_insufficient_data(pipeline, empty_features):
    """Prueba que si no hay features presentes, se pide más información (Bloque 6)."""
    result = pipeline.analyze(empty_features)
    assert result["insufficient_data"] is True
    assert result["urgency_score"] == 0
    assert len(result["clinical_alerts"]) == 0


def test_clinical_rules_chest_pain(empty_features):
    """Prueba que dolor de pecho + otro síntoma activa la regla de SCA."""
    features = empty_features.copy()
    features["chest_pain"] = "present"
    features["sweating"] = "present"
    
    rules = evaluate_clinical_rules(features)
    assert len(rules["rule_hypotheses"]) > 0
    
    alert = rules["rule_hypotheses"][0]
    assert "Coronario" in alert["disease_name"]
    assert rules["urgency_override"] == 90
    assert rules["specialty_override"] == "respiratorio_cardio"


def test_clinical_rules_stroke(empty_features):
    """Prueba que la regla de ictus se dispara con síntomas focales neurológicos."""
    features = empty_features.copy()
    features["weakness_of_one_body_side"] = "present"
    features["slurred_speech"] = "present"
    
    rules = evaluate_clinical_rules(features)
    assert len(rules["rule_hypotheses"]) > 0
    alert = rules["rule_hypotheses"][0]
    assert "ACV" in alert["disease_name"] or "Ictus" in alert["disease_name"]
    assert rules["urgency_override"] == 95


def test_pipeline_critical_rule_integration(pipeline, empty_features):
    """Prueba que el pipeline integra correctamente una regla crítica (Bloque 2)."""
    features = empty_features.copy()
    features["chest_pain"] = "present"
    features["sweating"] = "present"
    
    result = pipeline.analyze(features)
    
    # Aunque tenga pocos datos (2), al haber alerta clínica no debe dar insufficient_data
    assert result["insufficient_data"] is False
    assert result["urgency_score"] >= 90
    assert len(result["clinical_alerts"]) > 0
    assert "Coronario" in result["clinical_alerts"][0]["disease_name"]


def test_pipeline_absent_features(pipeline, empty_features):
    """Prueba que una feature 'absent' no se cuenta como activa."""
    features = empty_features.copy()
    # 3 features para evitar insufficient_data
    features["chest_pain"] = "absent"
    features["high_fever"] = "absent"
    features["cough"] = "absent"
    
    result = pipeline.analyze(features)
    # Como están ausentes, los datos activos son 0
    assert result["insufficient_data"] is True


def test_clinical_rules_softened_appendicitis(empty_features):
    """Prueba que la regla de apendicitis ya no tiene 95% probabilístico de forma ciega (Bloque 3)."""
    features = empty_features.copy()
    features["abdominal_pain"] = "present"
    features["nausea"] = "present"
    features["vomiting"] = "present"
    features["high_fever"] = "present"
    
    rules = evaluate_clinical_rules(features)
    assert len(rules["rule_hypotheses"]) > 0
    alert = rules["rule_hypotheses"][0]
    
    # Debe ser una alerta general de abdomen agudo y probability dummy 1.0 pero severidad high/moderate
    assert "abdomen agudo" in alert["disease_name"].lower()
    assert alert["severity"] in ("high", "moderate", "critical")
    assert rules["urgency_override"] == 60

def test_safe_fallback_preserves_critical_urgency_on_pipeline_failure(empty_features):
    """Prueba que el fallback asigna urgencia extrema si hay coma, incluso sin ML."""
    features = empty_features.copy()
    features["coma"] = "present"

    result = build_safe_clinical_fallback(features, error=Exception("boom"))

    assert result["urgency_label"] == "critical"
    assert result["recommended_destination"] == "urgencias_inmediatas"
    assert result["ml_hypotheses"] == []
    assert result["specialty_source"] == "clinical_fallback"

def test_safe_fallback_meningitis_rule(empty_features):
    """Prueba que el fallback evalúa reglas clínicas deterministas (ej. Meningitis)."""
    features = empty_features.copy()
    features["high_fever"] = "present"
    features["stiff_neck"] = "present"
    features["headache"] = "present"
    
    result = build_safe_clinical_fallback(features, error=Exception("ML roto"))
    
    assert len(result["clinical_alerts"]) > 0
    assert "meningitis" in result["clinical_alerts"][0]["disease_name"].lower()
    assert result["urgency_label"] in ("critical", "high")
    assert result["specialty_source"] == "clinical_fallback"
    assert result["analysis_degraded"] is True

def test_safe_fallback_with_full_rule(empty_features):
    """Test 2 — pipeline None con regla completa"""
    features = empty_features.copy()
    features["chest_pain"] = "present"
    features["sweating"] = "present"
    
    result = build_safe_clinical_fallback(features, error=Exception("Pipeline ML no disponible"))
    
    assert len(result["clinical_alerts"]) > 0
    assert result["insufficient_data"] is False
    assert result["urgency_label"] == "critical"
    assert result["ml_hypotheses"] == []
    assert result["analysis_degraded"] is True

def test_alarm_signal_critical_suppresses_ml(pipeline, empty_features):
    """Test 3 — alarm signal crítica suprime ML"""
    features = empty_features.copy()
    features["coma"] = "present"
    features["headache"] = "present"
    
    # We need enable_ml=True to test the suppression mechanism properly
    pipeline.enable_ml = True
    result = pipeline.analyze(features)
    
    assert result["urgency_label"] == "critical"
    assert result["ml_hypotheses"] == []
    assert result["ml_suppressed_reason"] is not None
    assert "omitido porque existe una alerta" in result["ml_suppressed_reason"].lower()

def test_pydantic_complete_report_validation():
    """Test 5 — Pydantic report completo"""
    from schemas.medical import MedicalReport, ClinicalAlert, EvidenceItem
    
    # This should not raise an exception
    report = MedicalReport(
        report_id="test-123",
        assigned_specialty="neurologico",
        specialty_confidence=None,
        specialty_source="clinical_rule",
        urgency_score=95,
        urgency_level="critical",
        clinical_alerts=[
            ClinicalAlert(
                disease_name="Sospecha de ACV / Ictus",
                severity="critical",
                rule_evidence=[
                    EvidenceItem(
                        key="slurred_speech",
                        label="Dificultad para hablar"
                    )
                ],
                recommendation="Urgencias inmediatas"
            )
        ],
        ml_hypotheses=[],
        ml_suppressed_reason="ML omitido porque existe una alerta clínica determinista prioritaria.",
    )
    
    assert report.specialty_confidence is None
    assert report.clinical_alerts[0].rule_evidence[0].key == "slurred_speech"
    assert report.urgency_level == "critical"


