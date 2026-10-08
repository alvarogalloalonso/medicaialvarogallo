"""
Medic AI — Agente Extractor de JSON

Extrae patient_intake y bayes_features de la conversación de forma estructurada.
Incluye lógica de merge incremental y retry con auto-reparación de JSON.
"""
from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Optional

from .llm_provider import LLMProvider

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schemas.medical import BAYES_FEATURE_KEYS


# ══════════════════════════════════════
# Diccionario de traducción español → feature
# ══════════════════════════════════════

SYMPTOM_TRANSLATIONS = {
    "itching": "picor, picazón, me pica",
    "skin_rash": "erupción cutánea, sarpullido, granitos en la piel, ronchas",
    "nodal_skin_eruptions": "erupciones en ganglios, bultos en la piel",
    "continuous_sneezing": "estornudos continuos, no paro de estornudar",
    "shivering": "escalofríos, temblores, tiritando",
    "chills": "escalofríos, frío intenso",
    "joint_pain": "dolor articular, dolor de articulaciones, me duelen las articulaciones",
    "stomach_pain": "dolor de estómago, dolor estomacal",
    "acidity": "acidez, ardor de estómago, reflujo",
    "ulcers_on_tongue": "úlceras en la lengua, llagas en la boca",
    "muscle_wasting": "pérdida de masa muscular, atrofia muscular",
    "vomiting": "vómitos, vomitar, devolver",
    "burning_micturition": "ardor al orinar, escozor al orinar",
    "spotting_ urination": "manchado al orinar, sangre al orinar",
    "fatigue": "fatiga, cansancio, agotamiento, estoy muy cansado",
    "weight_gain": "aumento de peso, he engordado",
    "anxiety": "ansiedad, nerviosismo, estoy muy nervioso",
    "cold_hands_and_feets": "manos y pies fríos, extremidades frías",
    "mood_swings": "cambios de humor, irritabilidad",
    "weight_loss": "pérdida de peso, he adelgazado",
    "restlessness": "inquietud, no puedo estar quieto",
    "lethargy": "letargo, somnolencia, apatía",
    "patches_in_throat": "manchas en la garganta, placas en la garganta",
    "irregular_sugar_level": "azúcar irregular, glucosa alta/baja",
    "cough": "tos, tosiendo",
    "high_fever": "fiebre alta, fiebre, temperatura alta, tengo fiebre",
    "sunken_eyes": "ojos hundidos",
    "breathlessness": "dificultad para respirar, falta de aire, disnea, me ahogo, me cuesta respirar",
    "sweating": "sudoración, sudando mucho, sudores",
    "dehydration": "deshidratación, mucha sed, boca seca",
    "indigestion": "indigestión, mala digestión, empacho",
    "headache": "dolor de cabeza, cefalea, me duele la cabeza",
    "yellowish_skin": "piel amarillenta, ictericia, amarillo",
    "dark_urine": "orina oscura, pis oscuro",
    "nausea": "náuseas, ganas de vomitar, asco",
    "loss_of_appetite": "pérdida de apetito, no tengo hambre, inapetencia",
    "pain_behind_the_eyes": "dolor detrás de los ojos, presión ocular",
    "back_pain": "dolor de espalda, lumbago, dolor lumbar",
    "constipation": "estreñimiento, no puedo ir al baño",
    "abdominal_pain": "dolor abdominal, dolor de barriga, dolor de tripa, dolor en el abdomen, dolor en la fosa ilíaca",
    "diarrhoea": "diarrea, heces líquidas",
    "mild_fever": "febrícula, fiebre leve, décimas de fiebre",
    "yellow_urine": "orina amarilla, pis amarillo",
    "yellowing_of_eyes": "ojos amarillos, amarillo en los ojos",
    "acute_liver_failure": "fallo hepático, insuficiencia hepática",
    "fluid_overload": "retención de líquidos, hinchazón generalizada",
    "swelling_of_stomach": "hinchazón abdominal, barriga hinchada, distensión",
    "swelled_lymph_nodes": "ganglios inflamados, ganglios hinchados, bultos en cuello/axila",
    "malaise": "malestar general, me encuentro mal",
    "blurred_and_distorted_vision": "visión borrosa, veo borroso, visión distorsionada",
    "phlegm": "flema, mucosidad, esputo",
    "throat_irritation": "irritación de garganta, picor de garganta, carraspera",
    "redness_of_eyes": "ojos rojos, enrojecimiento ocular",
    "sinus_pressure": "presión sinusal, sinusitis, presión en la cara",
    "runny_nose": "nariz que gotea, moqueo, rinorrea",
    "congestion": "congestión nasal, nariz tapada",
    "chest_pain": "dolor de pecho, dolor torácico, opresión en el pecho, presión en el pecho, me duele el pecho",
    "weakness_in_limbs": "debilidad en extremidades, piernas/brazos débiles",
    "fast_heart_rate": "taquicardia, corazón acelerado, palpitaciones rápidas, latidos rápidos",
    "pain_during_bowel_movements": "dolor al defecar, duele al ir al baño",
    "pain_in_anal_region": "dolor anal, dolor en el ano",
    "bloody_stool": "sangre en las heces, heces con sangre, sangrado rectal",
    "irritation_in_anus": "irritación anal, picor anal",
    "neck_pain": "dolor de cuello, cervicalgia, tortícolis",
    "dizziness": "mareo, vértigo, me mareo, sensación de mareo",
    "cramps": "calambres, espasmos",
    "bruising": "moretones, hematomas, cardenales",
    "obesity": "obesidad, sobrepeso",
    "swollen_legs": "piernas hinchadas, edema en piernas",
    "swollen_blood_vessels": "varices, venas hinchadas, venas varicosas",
    "puffy_face_and_eyes": "cara hinchada, ojos hinchados",
    "enlarged_thyroid": "tiroides agrandado, bocio",
    "brittle_nails": "uñas frágiles, uñas quebradizas",
    "swollen_extremeties": "extremidades hinchadas, manos/pies hinchados",
    "excessive_hunger": "hambre excesiva, mucha hambre, polifagia",
    "extra_marital_contacts": "contactos sexuales de riesgo, relaciones extramatrimoniales",
    "drying_and_tingling_lips": "labios secos, hormigueo en labios",
    "slurred_speech": "habla arrastrada, dificultad para hablar, no articula bien",
    "knee_pain": "dolor de rodilla, me duele la rodilla",
    "hip_joint_pain": "dolor de cadera, dolor en la cadera",
    "muscle_weakness": "debilidad muscular, falta de fuerza",
    "stiff_neck": "rigidez de nuca, cuello rígido, no puedo mover el cuello",
    "swelling_joints": "articulaciones hinchadas, inflamación articular",
    "movement_stiffness": "rigidez al moverse, rigidez matutina",
    "spinning_movements": "sensación de giro, todo da vueltas, vértigo rotatorio",
    "loss_of_balance": "pérdida de equilibrio, me tambaleo, inestabilidad",
    "unsteadiness": "inestabilidad, falta de equilibrio al caminar",
    "weakness_of_one_body_side": "debilidad de un lado, hemiplejia, un brazo/pierna no responde",
    "loss_of_smell": "pérdida de olfato, no huelo, anosmia",
    "bladder_discomfort": "molestia en vejiga, presión en vejiga",
    "foul_smell_of urine": "orina con mal olor, pis huele mal",
    "continuous_feel_of_urine": "sensación continua de orinar, ganas de orinar todo el rato",
    "passage_of_gases": "gases, flatulencia, ventosidades",
    "internal_itching": "picor interno, comezón interna",
    "toxic_look_(typhos)": "aspecto tóxico, muy enfermo, aspecto grave",
    "depression": "depresión, tristeza, ánimo bajo",
    "irritability": "irritabilidad, estoy irritable",
    "muscle_pain": "dolor muscular, mialgias, me duelen los músculos",
    "altered_sensorium": "alteración del sensorio, confusión, desorientación",
    "red_spots_over_body": "manchas rojas, puntos rojos en el cuerpo, petequias",
    "belly_pain": "dolor de barriga, dolor de tripa, dolor abdominal bajo",
    "abnormal_menstruation": "menstruación anormal, regla irregular, sangrado menstrual anormal",
    "dischromic _patches": "manchas en la piel, despigmentación, manchas oscuras/claras",
    "watering_from_eyes": "lagrimeo, ojos llorosos",
    "increased_appetite": "aumento de apetito, como mucho",
    "polyuria": "orinar mucho, poliuria, orino mucho",
    "family_history": "antecedentes familiares, historia familiar",
    "mucoid_sputum": "esputo mucoso, flema transparente/blanca",
    "rusty_sputum": "esputo herrumbroso, esputo color óxido, flema con sangre",
    "lack_of_concentration": "falta de concentración, no me concentro",
    "visual_disturbances": "alteraciones visuales, veo cosas raras, destellos",
    "receiving_blood_transfusion": "transfusión de sangre, me han transfundido",
    "receiving_unsterile_injections": "inyecciones no estériles, pinchazos no seguros",
    "coma": "coma, pérdida de conciencia, inconsciencia",
    "stomach_bleeding": "sangrado estomacal, hemorragia digestiva, vómito con sangre",
    "distention_of_abdomen": "distensión abdominal, abdomen distendido, barriga muy hinchada",
    "history_of_alcohol_consumption": "consumo de alcohol, bebo alcohol, alcoholismo",
    "blood_in_sputum": "sangre en el esputo, esputo con sangre, hemoptisis",
    "prominent_veins_on_calf": "venas prominentes en pantorrilla, varices en pierna",
    "palpitations": "palpitaciones, noto el corazón, latidos fuertes",
    "painful_walking": "dolor al caminar, cojeo, me duele al andar",
    "pus_filled_pimples": "granos con pus, espinillas con pus",
    "blackheads": "puntos negros, comedones",
    "scurring": "costras, descamación",
    "skin_peeling": "piel que se pela, descamación de la piel",
    "silver_like_dusting": "descamación plateada, escamas plateadas (psoriasis)",
    "small_dents_in_nails": "pequeños hoyos en uñas, pitting ungueal",
    "inflammatory_nails": "uñas inflamadas, paroniquia",
    "blister": "ampollas, vesículas en la piel",
    "red_sore_around_nose": "herida roja alrededor de la nariz, llaga en la nariz",
    "yellow_crust_ooze": "costra amarillenta, supuración amarilla",
}


# ══════════════════════════════════════
# Prompt de extracción
# ══════════════════════════════════════

EXTRACT_SYSTEM = """Eres un extractor de datos médicos. Tu ÚNICA tarea es analizar una conversación médica y extraer los datos en formato JSON estructurado.

REGLAS ESTRICTAS:
- Devuelve SOLO un JSON válido, sin texto extra, sin explicaciones, sin markdown.
- No añadas ni renombres claves.
- patient_intake: rellena solo lo que el usuario haya confirmado; si no se mencionó, deja "" o [].
- bayes_features: 
  * "present" si el usuario confirmó explícitamente el síntoma.
  * "absent" si el paciente lo NEGÓ explícitamente (ej. "no tengo fiebre").
  * "unknown" si el síntoma NO se mencionó en absoluto.
- Si el paciente dice "no tengo fiebre", pon high_fever: "absent" y mild_fever: "absent".
- Si el paciente dice "sí, tengo dolor de pecho", pon chest_pain: "present".
- No deduzcas por sentido común. Solo lo confirmado o negado."""



def _build_extract_prompt() -> str:
    """Construye el prompt de extracción con todas las claves y traducciones."""
    features_str = ",\n    ".join(f'"{k}": "unknown"' for k in BAYES_FEATURE_KEYS)
    
    # Construir diccionario de ayuda para el LLM
    translation_lines = []
    for feat, desc in SYMPTOM_TRANSLATIONS.items():
        translation_lines.append(f"  - {feat}: {desc}")
    translations_block = "\n".join(translation_lines)

    return f"""Devuelve SOLO un JSON válido con EXACTAMENTE este formato:

{{
  "patient_intake": {{
    "age": "",
    "sex": "",
    "main_symptom": "",
    "duration": "",
    "associated_symptoms": [],
    "medical_history": [],
    "medication": [],
    "allergies": [],
    "lifestyle_factors": {{
      "smoking": "",
      "alcohol": "",
      "drugs": "",
      "exercise": "",
      "diet": ""
    }}
  }},
  "bayes_features": {{
    {features_str}
  }}
}}

DICCIONARIO DE SÍNTOMAS (español → clave):
{translations_block}

REGLAS:
- Solo las claves listadas arriba para bayes_features. No añadas nuevas.
- Valor "present" si lo confirmó. Valor "absent" si lo negó explícitamente. Valor "unknown" si no lo mencionó.
- Usa el diccionario para mapear lo que dice el paciente a la clave correcta.
- Devuelve SOLO el JSON, sin texto extra."""


# ══════════════════════════════════════
# Utilidades
# ══════════════════════════════════════

def _extract_first_json(text: str) -> Dict[str, Any]:
    """Extrae el primer bloque JSON válido de un texto."""
    # Eliminar etiquetas <think> de DeepSeek si existen
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Intentar primero con bloques de código
    code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, flags=re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # Intentar encontrar JSON directamente
    brace_count = 0
    start_idx = None
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                try:
                    return json.loads(text[start_idx:i+1])
                except json.JSONDecodeError:
                    start_idx = None
                    continue

    print(f"[Medic AI] Fallo al extraer JSON. Texto crudo:\n{text[:500]}...")
    return {}


def merge_patient_intake(current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merge incremental del patient_intake — solo actualiza campos no vacíos."""
    out = dict(current)
    for k, v in incoming.items():
        if k == "lifestyle_factors" and isinstance(v, dict):
            out.setdefault("lifestyle_factors", {})
            if isinstance(out["lifestyle_factors"], dict):
                for lk, lv in v.items():
                    if lv not in [None, ""]:
                        out["lifestyle_factors"][lk] = lv
            else:
                out["lifestyle_factors"] = v
        elif isinstance(v, list):
            if v:  # Solo actualizar si la lista no está vacía
                existing = out.get(k, [])
                if isinstance(existing, list):
                    # Merge sin duplicados
                    combined = list(existing)
                    for item in v:
                        if item not in combined:
                            combined.append(item)
                    out[k] = combined
                else:
                    out[k] = v
        else:
            if v not in [None, ""]:
                out[k] = v
    return out


def normalize_feature_value(value: Any) -> str:
    """Normaliza posibles salidas del LLM (1/0, True/False) al formato esperado."""
    if value in ("present", "1", 1, True, "true", "True", "yes", "sí", "si"):
        return "present"
    if value in ("absent", "0", 0, False, "false", "False", "no"):
        return "absent"
    return "unknown"

def merge_bayes_features(current: Dict[str, str], incoming: Dict[str, Any]) -> Dict[str, str]:
    """Merge de bayes_features — permite tanto activar como desactivar features."""
    out = dict(current)
    for k in BAYES_FEATURE_KEYS:
        if k in incoming:
            val = normalize_feature_value(incoming[k])
            # Solo actualizar si el nuevo valor es "present" o "absent"
            # Si el nuevo es "unknown", mantenemos el estado actual
            if val in ["present", "absent"]:
                out[k] = val
    return out


# ══════════════════════════════════════
# Agente Extractor
# ══════════════════════════════════════

class ExtractorAgent:
    """
    Extrae patient_intake y bayes_features de la conversación.
    
    Se ejecuta periódicamente (cada N turnos) o bajo demanda al finalizar.
    """

    def __init__(
        self,
        llm: LLMProvider,
        temperature: float = 0.0,
        max_tokens: int = 4000,
        window_size: int = 20,
        max_retries: int = 2,
    ):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.window_size = window_size
        self.max_retries = max_retries

    async def extract(
        self,
        conversation_history: List[Dict[str, str]],
        current_intake: Optional[Dict[str, Any]] = None,
        current_features: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Extrae datos de la conversación y los mergea con el estado actual.
        
        Returns:
            {
                "patient_intake": {...},
                "bayes_features": {...},
                "raw_extracted": {...}  # datos crudos extraídos
            }
        """
        if current_intake is None:
            current_intake = {}
        if current_features is None:
            current_features = {k: "unknown" for k in BAYES_FEATURE_KEYS}

        # Construir mensajes para extracción
        messages = [{"role": "system", "content": EXTRACT_SYSTEM}]

        # Añadir conversación reciente
        recent = conversation_history[-self.window_size:]
        messages.extend(recent)

        # Prompt de extracción
        messages.append({"role": "user", "content": _build_extract_prompt()})

        # Intentar extracción con retry
        repair_prompt = "Tu salida anterior NO era JSON válido. Devuelve SOLO JSON válido, sin texto extra, sin explicaciones."
        
        for attempt in range(self.max_retries):
            try:
                raw_response = await self.llm.generate(
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                data = _extract_first_json(raw_response)

                if isinstance(data, dict) and "patient_intake" in data and "bayes_features" in data:
                    # Merge exitoso
                    pi_incoming = data.get("patient_intake", {})
                    bf_incoming = data.get("bayes_features", {})

                    merged_intake = merge_patient_intake(current_intake, pi_incoming) if isinstance(pi_incoming, dict) else current_intake
                    merged_features = merge_bayes_features(current_features, bf_incoming) if isinstance(bf_incoming, dict) else current_features

                    return {
                        "patient_intake": merged_intake,
                        "bayes_features": merged_features,
                        "raw_extracted": data,
                    }

                # JSON no válido, añadir prompt de reparación
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": repair_prompt})

            except Exception as e:
                if attempt < self.max_retries - 1:
                    continue
                break

        # Si falla, devolver estado actual sin cambios
        return {
            "patient_intake": current_intake,
            "bayes_features": current_features,
            "raw_extracted": {},
        }

