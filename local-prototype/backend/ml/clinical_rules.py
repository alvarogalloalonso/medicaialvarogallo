"""
Medic AI — Reglas Clínicas Deterministas

Este módulo contiene patrones de alarma clínica que se evalúan
independientemente del motor ML. Si se detecta un patrón crítico (ej. apendicitis),
se fuerza una urgencia alta y se asegura la detección aunque el dataset ML no lo cubra.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schemas.medical import BAYES_FEATURE_KEYS, SYMPTOM_LABELS_ES

# ══════════════════════════════════════
# Patrones de Alarma (Reglas Duras)
# ══════════════════════════════════════

ALARM_PATTERNS = [
    {
        "name": "Síndrome Coronario Agudo (Posible Infarto)",
        "requires": ["chest_pain"],
        "supports": ["breathlessness", "sweating", "vomiting", "palpitations", "nausea"],
        "min_supports": 1,
        "urgency_override": 90,
        "specialty_override": "respiratorio_cardio",
    },
    {
        "name": "Sospecha de ACV / Ictus",
        "requires": ["weakness_of_one_body_side"],
        "supports": ["slurred_speech", "headache", "loss_of_balance", "altered_sensorium", "dizziness"],
        "min_supports": 1,
        "urgency_override": 95,
        "specialty_override": "neurologico",
    },
    {
        "name": "Alerta: sospecha de abdomen agudo. Valorar clínicamente.",
        "requires": ["abdominal_pain"],
        "supports": ["vomiting", "nausea", "high_fever"],
        "min_supports": 2,
        "urgency_override": 60,
        "specialty_override": "digestivo",
    },
    {
        "name": "Alerta respiratoria: disnea con síntomas acompañantes",
        "requires": ["breathlessness"],
        "supports": ["cough", "chest_pain", "high_fever", "phlegm", "fatigue"],
        "min_supports": 2,
        "urgency_override": 75,
        "specialty_override": "respiratorio_cardio",
    },
    {
        "name": "Alerta crítica de triaje: patrón compatible con meningitis / infección del SNC. Requiere valoración médica urgente.",
        "requires": ["high_fever", "stiff_neck"],
        "supports": ["headache", "vomiting", "altered_sensorium", "nausea"],
        "min_supports": 1,
        "urgency_override": 85,
        "specialty_override": "neurologico",
    },
    {
        "name": "Hemorragia Digestiva",
        "requires": ["bloody_stool", "stomach_bleeding"], # Evaluado como OR lógico
        "supports": ["vomiting", "fatigue", "dizziness", "loss_of_appetite", "nausea"],
        "min_supports": 1,
        "urgency_override": 80,
        "specialty_override": "digestivo",
    },
    {
        "name": "Anafilaxia / Reacción Alérgica Grave",
        "requires": ["breathlessness", "skin_rash"], # Evaluado como AND si hay múltiples, pero las features se cruzan
        "supports": ["swelling_of_stomach", "itching", "vomiting", "palpitations"],
        "min_supports": 1,
        "urgency_override": 90,
        "specialty_override": "piel_alergia",
    },
]


def evaluate_clinical_rules(bayes_features_dict: dict) -> dict:
    """
    Evalúa las reglas deterministas contra los síntomas del paciente.
    Devuelve un diccionario con los overrides y señales si se activan.
    """
    rule_hypotheses = []
    max_urgency = None
    target_specialty = None
    alarm_signals = []

    for pattern in ALARM_PATTERNS:
        # Check requirements (treating multiple requires as OR if specifically configured, else AND)
        reqs = pattern["requires"]
        
        # Para Hemorragia digestiva u otros donde requires es OR
        if "Hemorragia" in pattern["name"]:
            req_met = any(bayes_features_dict.get(r) == "present" for r in reqs)
        else:
            req_met = all(bayes_features_dict.get(r) == "present" for r in reqs)
            
        if not req_met:
            continue
            
        # Check supports
        sups = pattern["supports"]
        sups_met = sum(1 for s in sups if bayes_features_dict.get(s) == "present")
        
        if sups_met >= pattern["min_supports"]:
            matched_reqs = [r for r in reqs if bayes_features_dict.get(r) == "present"]
            matched_sups = [s for s in sups if bayes_features_dict.get(s) == "present"]
            
            severity = "critical" if pattern["urgency_override"] >= 80 else "high" if pattern["urgency_override"] >= 60 else "moderate"
            rec = "Urgencias inmediatas" if severity == "critical" else "Valoración urgente" if severity == "high" else "Seguimiento médico"
            
            evidence_list = matched_reqs + matched_sups
            rule_evidence_translated = [
                {"key": e, "label": SYMPTOM_LABELS_ES.get(e, e.replace("_", " ").title())}
                for e in evidence_list
            ]
            
            rule_hypotheses.append({
                "disease_name": pattern["name"],
                "severity": severity,
                "recommendation": rec,
                "rule_evidence": rule_evidence_translated,
                "probability": None,
                "match_type": "clinical_rule"
            })
            
            if max_urgency is None or pattern["urgency_override"] > max_urgency:
                max_urgency = pattern["urgency_override"]
                target_specialty = pattern["specialty_override"]
                
            alarm_signals.append({
                "signal": f"Patrón clínico detectado: {pattern['name']}",
                "severity": "critical" if pattern["urgency_override"] >= 80 else "high"
            })

    return {
        "rule_hypotheses": rule_hypotheses,
        "urgency_override": max_urgency,
        "specialty_override": target_specialty,
        "alarm_signals": alarm_signals
    }

