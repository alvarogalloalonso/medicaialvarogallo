"""
Medic AI — Schemas Médicos (Pydantic)

Define todos los tipos de datos del sistema: PatientIntake, BayesFeatures,
DiagnosticHypothesis, MedicalReport, etc.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ══════════════════════════════════════
# Enums
# ══════════════════════════════════════

class MedicalSpecialty(str, Enum):
    RESPIRATORIO_CARDIO = "respiratorio_cardio"
    NEUROLOGICO = "neurologico"
    DIGESTIVO = "digestivo"
    URINARIO_GENITAL = "urinario_genital"
    PIEL_ALERGIA = "piel_alergia"
    GENERAL_MUSCULOESQUELETICO = "general_musculoesqueletico"
    SIN_CLASIFICAR = "sin_clasificar"

SPECIALTIES = [s.value for s in MedicalSpecialty]


class UrgencyLevel(str, Enum):
    LOW = "low"           # 0-25
    MODERATE = "moderate" # 26-50
    HIGH = "high"         # 51-75
    CRITICAL = "critical" # 76-100


# ══════════════════════════════════════
# Bayes Features — 132 claves binarias
# ══════════════════════════════════════

BAYES_FEATURE_KEYS = [
    "itching",
    "skin_rash",
    "nodal_skin_eruptions",
    "continuous_sneezing",
    "shivering",
    "chills",
    "joint_pain",
    "stomach_pain",
    "acidity",
    "ulcers_on_tongue",
    "muscle_wasting",
    "vomiting",
    "burning_micturition",
    "spotting_ urination",
    "fatigue",
    "weight_gain",
    "anxiety",
    "cold_hands_and_feets",
    "mood_swings",
    "weight_loss",
    "restlessness",
    "lethargy",
    "patches_in_throat",
    "irregular_sugar_level",
    "cough",
    "high_fever",
    "sunken_eyes",
    "breathlessness",
    "sweating",
    "dehydration",
    "indigestion",
    "headache",
    "yellowish_skin",
    "dark_urine",
    "nausea",
    "loss_of_appetite",
    "pain_behind_the_eyes",
    "back_pain",
    "constipation",
    "abdominal_pain",
    "diarrhoea",
    "mild_fever",
    "yellow_urine",
    "yellowing_of_eyes",
    "acute_liver_failure",
    "fluid_overload",
    "swelling_of_stomach",
    "swelled_lymph_nodes",
    "malaise",
    "blurred_and_distorted_vision",
    "phlegm",
    "throat_irritation",
    "redness_of_eyes",
    "sinus_pressure",
    "runny_nose",
    "congestion",
    "chest_pain",
    "weakness_in_limbs",
    "fast_heart_rate",
    "pain_during_bowel_movements",
    "pain_in_anal_region",
    "bloody_stool",
    "irritation_in_anus",
    "neck_pain",
    "dizziness",
    "cramps",
    "bruising",
    "obesity",
    "swollen_legs",
    "swollen_blood_vessels",
    "puffy_face_and_eyes",
    "enlarged_thyroid",
    "brittle_nails",
    "swollen_extremeties",
    "excessive_hunger",
    "extra_marital_contacts",
    "drying_and_tingling_lips",
    "slurred_speech",
    "knee_pain",
    "hip_joint_pain",
    "muscle_weakness",
    "stiff_neck",
    "swelling_joints",
    "movement_stiffness",
    "spinning_movements",
    "loss_of_balance",
    "unsteadiness",
    "weakness_of_one_body_side",
    "loss_of_smell",
    "bladder_discomfort",
    "foul_smell_of urine",
    "continuous_feel_of_urine",
    "passage_of_gases",
    "internal_itching",
    "toxic_look_(typhos)",
    "depression",
    "irritability",
    "muscle_pain",
    "altered_sensorium",
    "red_spots_over_body",
    "belly_pain",
    "abnormal_menstruation",
    "dischromic _patches",
    "watering_from_eyes",
    "increased_appetite",
    "polyuria",
    "family_history",
    "mucoid_sputum",
    "rusty_sputum",
    "lack_of_concentration",
    "visual_disturbances",
    "receiving_blood_transfusion",
    "receiving_unsterile_injections",
    "coma",
    "stomach_bleeding",
    "distention_of_abdomen",
    "history_of_alcohol_consumption",
    "fluid_overload.1",
    "blood_in_sputum",
    "prominent_veins_on_calf",
    "palpitations",
    "painful_walking",
    "pus_filled_pimples",
    "blackheads",
    "scurring",
    "skin_peeling",
    "silver_like_dusting",
    "small_dents_in_nails",
    "inflammatory_nails",
    "blister",
    "red_sore_around_nose",
    "yellow_crust_ooze"
]


SYMPTOM_LABELS_ES = {
    "itching": "Picor",
    "skin_rash": "Erupción cutánea",
    "nodal_skin_eruptions": "Erupciones cutáneas nodulares",
    "continuous_sneezing": "Estornudos continuos",
    "shivering": "Escalofríos",
    "chills": "Escalofríos severos",
    "joint_pain": "Dolor articular",
    "stomach_pain": "Dolor de estómago",
    "acidity": "Acidez",
    "ulcers_on_tongue": "Úlceras en la lengua",
    "muscle_wasting": "Desgaste muscular",
    "vomiting": "Vómitos",
    "burning_micturition": "Ardor al orinar",
    "spotting_ urination": "Manchas al orinar",
    "fatigue": "Fatiga / Cansancio",
    "weight_gain": "Aumento de peso",
    "anxiety": "Ansiedad",
    "cold_hands_and_feets": "Manos y pies fríos",
    "mood_swings": "Cambios de humor",
    "weight_loss": "Pérdida de peso",
    "restlessness": "Inquietud",
    "lethargy": "Letargo",
    "patches_in_throat": "Manchas en la garganta",
    "irregular_sugar_level": "Nivel de azúcar irregular",
    "cough": "Tos",
    "high_fever": "Fiebre alta",
    "sunken_eyes": "Ojos hundidos",
    "breathlessness": "Dificultad respiratoria (Disnea)",
    "sweating": "Sudoración",
    "dehydration": "Deshidratación",
    "indigestion": "Indigestión",
    "headache": "Dolor de cabeza (Cefalea)",
    "yellowish_skin": "Piel amarillenta (Ictericia)",
    "dark_urine": "Orina oscura",
    "nausea": "Náuseas",
    "loss_of_appetite": "Pérdida de apetito",
    "pain_behind_the_eyes": "Dolor detrás de los ojos",
    "back_pain": "Dolor de espalda",
    "constipation": "Estreñimiento",
    "abdominal_pain": "Dolor abdominal",
    "diarrhoea": "Diarrea",
    "mild_fever": "Fiebre leve",
    "yellow_urine": "Orina amarilla",
    "yellowing_of_eyes": "Ojos amarillentos",
    "acute_liver_failure": "Fallo hepático agudo",
    "fluid_overload": "Sobrecarga de líquidos",
    "swelling_of_stomach": "Hinchazón de estómago",
    "swelled_lymph_nodes": "Ganglios linfáticos inflamados",
    "malaise": "Malestar general",
    "blurred_and_distorted_vision": "Visión borrosa o distorsionada",
    "phlegm": "Flema",
    "throat_irritation": "Irritación de garganta",
    "redness_of_eyes": "Enrojecimiento de ojos",
    "sinus_pressure": "Presión sinusal",
    "runny_nose": "Secreción nasal",
    "congestion": "Congestión nasal",
    "chest_pain": "Dolor de pecho",
    "weakness_in_limbs": "Debilidad en extremidades",
    "fast_heart_rate": "Ritmo cardíaco rápido (Taquicardia)",
    "pain_during_bowel_movements": "Dolor al defecar",
    "pain_in_anal_region": "Dolor en región anal",
    "bloody_stool": "Heces con sangre",
    "irritation_in_anus": "Irritación en el ano",
    "neck_pain": "Dolor de cuello",
    "dizziness": "Mareos",
    "cramps": "Calambres",
    "bruising": "Moretones",
    "obesity": "Obesidad",
    "swollen_legs": "Piernas hinchadas",
    "swollen_blood_vessels": "Vasos sanguíneos hinchados",
    "puffy_face_and_eyes": "Cara y ojos hinchados",
    "enlarged_thyroid": "Tiroides agrandada",
    "brittle_nails": "Uñas quebradizas",
    "swollen_extremeties": "Extremidades hinchadas",
    "excessive_hunger": "Hambre excesiva",
    "extra_marital_contacts": "Contactos extramatrimoniales",
    "drying_and_tingling_lips": "Labios secos y con hormigueo",
    "slurred_speech": "Dificultad para hablar",
    "knee_pain": "Dolor de rodilla",
    "hip_joint_pain": "Dolor en articulación de la cadera",
    "muscle_weakness": "Debilidad muscular",
    "stiff_neck": "Rigidez de cuello",
    "swelling_joints": "Inflamación de articulaciones",
    "movement_stiffness": "Rigidez de movimiento",
    "spinning_movements": "Sensación de giro (Vértigo)",
    "loss_of_balance": "Pérdida de equilibrio",
    "unsteadiness": "Inestabilidad",
    "weakness_of_one_body_side": "Debilidad en un lado del cuerpo",
    "loss_of_smell": "Pérdida de olfato",
    "bladder_discomfort": "Molestia en la vejiga",
    "foul_smell_of urine": "Mal olor de orina",
    "continuous_feel_of_urine": "Sensación continua de orinar",
    "passage_of_gases": "Paso de gases",
    "internal_itching": "Picor interno",
    "toxic_look_(typhos)": "Aspecto tóxico (tífus)",
    "depression": "Depresión",
    "irritability": "Irritabilidad",
    "muscle_pain": "Dolor muscular",
    "altered_sensorium": "Alteración del sensorio / Confusión",
    "red_spots_over_body": "Manchas rojas en el cuerpo",
    "belly_pain": "Dolor de barriga",
    "abnormal_menstruation": "Menstruación anormal",
    "dischromic _patches": "Manchas discrómicas",
    "watering_from_eyes": "Lagrimeo",
    "increased_appetite": "Aumento de apetito",
    "polyuria": "Poliuria (exceso de orina)",
    "family_history": "Antecedentes familiares",
    "mucoid_sputum": "Esputo mucoide",
    "rusty_sputum": "Esputo herrumbroso",
    "lack_of_concentration": "Falta de concentración",
    "visual_disturbances": "Alteraciones visuales",
    "receiving_blood_transfusion": "Recepción de transfusión de sangre",
    "receiving_unsterile_injections": "Recepción de inyecciones no estériles",
    "coma": "Coma / Pérdida de conciencia",
    "stomach_bleeding": "Sangrado estomacal",
    "distention_of_abdomen": "Distensión abdominal",
    "history_of_alcohol_consumption": "Historial de consumo de alcohol",
    "fluid_overload.1": "Sobrecarga de líquidos (2)",
    "blood_in_sputum": "Sangre en esputo",
    "prominent_veins_on_calf": "Venas prominentes en pantorrilla",
    "palpitations": "Palpitaciones",
    "painful_walking": "Dolor al caminar",
    "pus_filled_pimples": "Granos con pus",
    "blackheads": "Espinillas / Puntos negros",
    "scurring": "Cicatrices",
    "skin_peeling": "Descamación de la piel",
    "silver_like_dusting": "Polvillo plateado en piel",
    "small_dents_in_nails": "Pequeñas hendiduras en uñas",
    "inflammatory_nails": "Uñas inflamadas",
    "blister": "Ampollas",
    "red_sore_around_nose": "Llaga roja alrededor de la nariz",
    "yellow_crust_ooze": "Costra amarilla supurante"
}


class BayesFeatures(BaseModel):
    """Vector fijo de 132 features categóricas para el clasificador (present, absent, unknown)."""
    features: Dict[str, str] = Field(
        default_factory=lambda: {k: "unknown" for k in BAYES_FEATURE_KEYS}
    )

    def to_vector(self) -> list[int]:
        """Devuelve el vector binario para ML (presencia y máscara de observación separadas)."""
        from ml.features import encode_features, FEATURE_COLUMNS
        encoded = encode_features(self.features)
        return [encoded[k] for k in FEATURE_COLUMNS]

    def active_features(self) -> list[str]:
        """Devuelve las features activas (=present)."""
        return [k for k, v in self.features.items() if v == "present"]

    def absent_features(self) -> list[str]:
        """Devuelve las features negadas explícitamente (=absent)."""
        return [k for k, v in self.features.items() if v == "absent"]



# ══════════════════════════════════════
# Patient Intake — Informe rico
# ══════════════════════════════════════

class LifestyleFactors(BaseModel):
    smoking: str = ""
    alcohol: str = ""
    drugs: str = ""
    exercise: str = ""
    diet: str = ""


class PatientIntake(BaseModel):
    age: str = ""
    sex: str = ""
    main_symptom: str = ""
    duration: str = ""
    associated_symptoms: List[str] = Field(default_factory=list)
    medical_history: List[str] = Field(default_factory=list)
    medication: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    lifestyle_factors: LifestyleFactors = Field(default_factory=LifestyleFactors)


# ══════════════════════════════════════
# Diagnostic Hypothesis
# ══════════════════════════════════════

class EvidenceItem(BaseModel):
    key: str
    label: str

class MLHypothesis(BaseModel):
    disease_name: str
    probability: float = Field(ge=0.0, le=1.0)
    shap_explanation: Dict[str, float] = Field(default_factory=dict)
    recommended_tests: List[str] = Field(default_factory=list)
    justification: str = ""

class ClinicalAlert(BaseModel):
    disease_name: str
    severity: str = "moderate"
    recommendation: str = "Evaluación médica presencial"
    rule_evidence: List[EvidenceItem] = Field(default_factory=list)
    probability: Optional[float] = None
    match_type: str = "clinical_rule"


class AlarmSignal(BaseModel):
    signal: str
    severity: str = "high"  # "moderate", "high", "critical"


# ══════════════════════════════════════
# Medical Report — Informe final
# ══════════════════════════════════════

class MedicalReport(BaseModel):
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    urgency_score: int = Field(ge=0, le=100)
    urgency_level: UrgencyLevel = UrgencyLevel.LOW
    assigned_specialty: MedicalSpecialty = MedicalSpecialty.GENERAL_MUSCULOESQUELETICO
    specialty_confidence: Optional[float] = None
    specialty_source: str = "unknown"

    patient_intake: PatientIntake = Field(default_factory=PatientIntake)
    bayes_features: BayesFeatures = Field(default_factory=BayesFeatures)

    alarm_signals: List[AlarmSignal] = Field(default_factory=list)
    clinical_alerts: List[ClinicalAlert] = Field(default_factory=list)
    ml_hypotheses: List[MLHypothesis] = Field(default_factory=list)
    
    analysis_degraded: bool = False
    ml_suppressed_reason: Optional[str] = None

    clinical_summary: str = ""
    doctor_narrative: str = ""

    conversation_turns: int = 0


# ══════════════════════════════════════
# Session State — Estado de la sesión de chat
# ══════════════════════════════════════

class SessionState(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "active"  # "active", "extracting", "analyzing", "completed"

    messages: List[Dict[str, str]] = Field(default_factory=list)
    turn_count: int = 0
    last_extracted_turn: int = 0

    patient_intake: PatientIntake = Field(default_factory=PatientIntake)
    bayes_features: BayesFeatures = Field(default_factory=BayesFeatures)

    report: Optional[MedicalReport] = None

