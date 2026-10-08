import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.pipeline import MedicalPipeline
from ml.clinical_rules import evaluate_clinical_rules
from schemas.medical import BAYES_FEATURE_KEYS, PatientIntake
from main import create_session
from agents.extractor import normalize_feature_value
from agents.report_generator import ReportGeneratorAgent

@pytest.fixture
def empty_features():
    return {k: "unknown" for k in BAYES_FEATURE_KEYS}

@pytest.fixture
def pipeline():
    return MedicalPipeline(enable_ml=False)


@pytest.mark.parametrize("symptom", [
    "chest_pain",
    "breathlessness",
    "coma",
    "weakness_of_one_body_side",
    "bloody_stool"
])
def test_isolated_red_flags_do_not_generate_ml(pipeline, empty_features, symptom):
    features = empty_features.copy()
    features[symptom] = "present"
    result = pipeline.analyze(features)
    
    assert result["insufficient_data"] is True
    assert result["urgency_score"] > 0
    assert result["ml_hypotheses"] == []
    assert result.get("ml_suppressed_reason") is not None
    assert len(result["alarm_signals"]) > 0

def test_full_rule_triggers_alert(pipeline, empty_features):
    features = empty_features.copy()
    features["chest_pain"] = "present"
    features["sweating"] = "present"
    result = pipeline.analyze(features)
    
    assert result["insufficient_data"] is False
    assert len(result["clinical_alerts"]) > 0
    assert result["clinical_alerts"][0]["disease_name"] == "Síndrome Coronario Agudo (Posible Infarto)"

def test_isolated_non_critical_symptom(pipeline, empty_features):
    features = empty_features.copy()
    features["headache"] = "present"
    result = pipeline.analyze(features)
    
    assert result["insufficient_data"] is True
    assert result["urgency_score"] == 0
    assert result["ml_hypotheses"] == []
    assert result.get("ml_suppressed_reason") is not None


def test_create_session_initializes_unknown():
    session = create_session()
    features = session["bayes_features"]
    # All features should be unknown
    for k, v in features.items():
        assert v == "unknown"


def test_active_features_detect_present_not_1():
    assert normalize_feature_value(1) == "present"
    assert normalize_feature_value("1") == "present"
    assert normalize_feature_value("present") == "present"
    assert normalize_feature_value(0) == "absent"
    assert normalize_feature_value("unknown") == "unknown"


def test_report_generator_reads_clinical_alerts_and_ml_hypotheses():
    # Mocking LLMProvider is too complex here, we'll test the non-LLM version
    from agents.llm_provider import OllamaProvider
    # Just creating instance with None LLM since we use without_llm
    agent = ReportGeneratorAgent(llm=None)
    
    ml_results = {
        "clinical_alerts": [{"disease_name": "Alerta de prueba", "severity": "critical", "rule_evidence": [{"key": "high_fever", "label": "Fiebre alta"}], "recommendation": "Urgencias"}],
        "ml_hypotheses": [{"disease_name": "Hipótesis 1", "probability": 0.8, "recommended_tests": [], "shap_explanation": {}}],
        "assigned_specialty": "general",
        "specialty_confidence": 0.9,
        "urgency_score": 90,
        "alarm_signals": []
    }
    
    report_text = agent.generate_report_without_llm({}, ml_results)
    
    assert "Alerta de prueba" in report_text
    assert "Hipótesis 1" in report_text
    assert "ALERTAS CLÍNICAS (DETERMINISTAS)" in report_text


def test_rest_websocket_schema_consistency():
    import asyncio
    from main import get_session
    session = create_session()
    session["bayes_features"]["high_fever"] = "present"
    
    rest_data = asyncio.run(get_session(session["session_id"]))
    assert "bayes_features_active" in rest_data
    assert isinstance(rest_data["bayes_features_active"], list)
    assert len(rest_data["bayes_features_active"]) == 1
    assert "key" in rest_data["bayes_features_active"][0]
    assert "label" in rest_data["bayes_features_active"][0]


def test_report_generator_returns_string():
    import asyncio
    from agents.report_generator import ReportGeneratorAgent
    from agents.llm_provider import OllamaProvider
    # Usamos un mock provider simple que devuelve un string
    class MockProvider:
        async def generate(self, messages, **kwargs):
            return "Este es un reporte de prueba simulado."
    
    agent = ReportGeneratorAgent(llm=MockProvider())
    
    # Simulate generate_report execution
    report_text = asyncio.run(agent.generate_report(
        patient_intake={"main_symptom": "coma"},
        ml_results={
            "clinical_alerts": [{"disease_name": "Alerta", "rule_evidence": [{"key": "coma", "label": "Coma"}]}],
            "ml_hypotheses": [], "urgency_score": 50, "assigned_specialty": "general_musculoesqueletico"
        },
        conversation_history=[]
    ))
    
    assert isinstance(report_text, str)
    assert "Este es un reporte de prueba simulado." in report_text

