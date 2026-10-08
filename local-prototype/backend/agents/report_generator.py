"""
Medic AI — Agente Generador de Informes

Genera el informe clínico final combinando los datos del paciente,
los resultados del pipeline ML y las explicaciones SHAP.
"""
from __future__ import annotations

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from .llm_provider import LLMProvider

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from schemas.medical import BAYES_FEATURE_KEYS


# ══════════════════════════════════════
# Prompt de generación de informe
# ══════════════════════════════════════

REPORT_SYSTEM = """Eres un redactor de informes médicos de triaje. Tu tarea es generar un informe clínico estructurado y profesional para que un médico lo revise.

REGLAS:
- Usa lenguaje clínico profesional pero comprensible.
- NO diagnostiques ni prescribas.
- Presenta los datos de forma objetiva.
- Incluye TODAS las secciones del formato requerido.
- Las probabilidades y diagnósticos diferenciales vienen del sistema ML — preséntalos tal cual.
- Añade un "Razonamiento Resumido" que conecte los síntomas con las hipótesis.
- El informe es con FINES EDUCATIVOS y de apoyo al profesional."""


def format_rule_evidence(rule_evidence: List[Any]) -> str:
    """Extrae las etiquetas de la evidencia clínica, manejando diccionarios y strings."""
    labels = []
    for ev in rule_evidence or []:
        if isinstance(ev, dict):
            labels.append(ev.get("label") or ev.get("key", ""))
        else:
            labels.append(str(ev))
    return ", ".join(x for x in labels if x)

def _build_report_prompt(
    patient_intake: Dict[str, Any],
    ml_results: Dict[str, Any],
    conversation_summary: str = "",
) -> str:
    """Construye el prompt para generar el informe narrativo."""

    clinical_alerts_text = ""
    for i, alert in enumerate(ml_results.get("clinical_alerts", []), 1):
        evidence_text = format_rule_evidence(alert.get("rule_evidence", []))
        rec = alert.get("recommendation", "Evaluación médica")
        sev = alert.get("severity", "high").upper()
        clinical_alerts_text += f"  {i}. [{sev}] {alert.get('disease_name', 'Desconocida')}\n     Recomendación: {rec}\n     Evidencia: {evidence_text}\n"

    hypotheses_text = ""
    for i, h in enumerate(ml_results.get("ml_hypotheses", []), 1):
        prob_pct = h.get("probability", 0) * 100
        shap_text = ""
        if h.get("shap_explanation"):
            top_shap = sorted(
                h["shap_explanation"].items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:5]
            shap_lines = []
            for feat, val in top_shap:
                direction = "aumenta" if val > 0 else "disminuye"
                shap_lines.append(f"    - {feat}: {direction} la probabilidad ({val:+.3f})")
            shap_text = "\n".join(shap_lines)

        tests_text = ", ".join(h.get("recommended_tests", [])) or "No especificadas"

        hypotheses_text += f"""
  {i}. {h.get('disease_name', 'Desconocida')} ({prob_pct:.1f}%)
     Pruebas recomendadas: {tests_text}
     Factores clave (SHAP):
{shap_text}
"""

    alarms_text = ""
    for alarm in ml_results.get("alarm_signals", []):
        alarms_text += f"  - [{alarm.get('severity', 'high').upper()}] {alarm.get('signal', '')}\n"

    lifestyle = patient_intake.get("lifestyle_factors", {})
    lifestyle_values = [v for v in lifestyle.values() if v.strip()]
    if lifestyle_values:
        lifestyle_text = f"""=== ESTILO DE VIDA ===
  Tabaco: {lifestyle.get('smoking', 'No refiere')}
  Alcohol: {lifestyle.get('alcohol', 'No refiere')}
  Drogas: {lifestyle.get('drugs', 'No refiere')}
  Ejercicio: {lifestyle.get('exercise', 'No refiere')}
  Dieta: {lifestyle.get('diet', 'No refiere')}
"""
    else:
        lifestyle_text = ""

    suppressed_text = ""
    if ml_results.get('ml_suppressed_reason'):
        suppressed_text = f"\nML Omitido: {ml_results.get('ml_suppressed_reason')}\n"

    spec_conf = ml_results.get('specialty_confidence')
    spec_conf_text = f"{spec_conf * 100:.1f}%" if spec_conf is not None else "No aplicable"
    spec_source = ml_results.get('specialty_source', 'unknown')
    
    degraded_text = "\n[!] ADVERTENCIA: Análisis en modo degradado o ML desactivado/suprimido.\n" if ml_results.get("analysis_degraded") else ""

    return f"""Genera un informe clínico de triaje con el siguiente formato. Usa los datos proporcionados:{degraded_text}

=== DATOS DEL PACIENTE ===
Edad: {patient_intake.get('age', 'No informada')}
Sexo: {patient_intake.get('sex', 'No informado')}
Síntoma Principal: {patient_intake.get('main_symptom', 'No informado')}
Duración: {patient_intake.get('duration', 'No informada')}
Síntomas Asociados: {', '.join(patient_intake.get('associated_symptoms', [])) or 'Ninguno reportado'}
Medicación: {', '.join(patient_intake.get('medication', [])) or 'No refiere'}
Alergias: {', '.join(patient_intake.get('allergies', [])) or 'No refiere'}
Historial Médico: {', '.join(patient_intake.get('medical_history', [])) or 'Sin antecedentes relevantes'}

{lifestyle_text}

=== RESULTADOS DEL ANÁLISIS ML ===
Especialidad Asignada: {ml_results.get('assigned_specialty', 'No determinada')}
Origen Especialidad: {spec_source}
Confianza: {spec_conf_text}
Nivel de Urgencia (Label): {ml_results.get('urgency_label', 'low').upper()}
Destino Recomendado: {ml_results.get('destination_label', 'Seguimiento')}

=== SEÑALES DE ALARMA ===
{alarms_text or '  Ninguna detectada'}

=== ALERTAS CLÍNICAS (DETERMINISTAS) ===
{clinical_alerts_text or '  Ninguna alerta crítica/alta detectada'}

=== DIAGNÓSTICO DIFERENCIAL (Hipótesis ML) ===
{hypotheses_text or '  Sin hipótesis generadas'}
{suppressed_text}

=== RESUMEN DE LA CONVERSACIÓN ===
{conversation_summary or 'No disponible'}

---

GENERA el informe con estas secciones:
1. Motivo de Consulta (1-2 frases)
2. Historia de la Enfermedad Actual (párrafo narrativo clínico)
3. Hallazgos Relevantes (lista de puntos)
4. Alertas Clínicas (si existen, destacar prioridad y acción, NO PROBABILIDADES)
5. Diagnóstico Diferencial ML (subordinado a las alertas si existen)
6. Razonamiento Resumido (conecta síntomas con las alertas y/o hipótesis)
7. Recomendaciones (claras: derivar a urgencias si hay alerta crítica)

IMPORTANTE: 
- Añade siempre el aviso: "Las probabilidades son estimaciones generadas por un sistema ML con fines educativos y no representan un diagnóstico médico."
- No mezcles alertas deterministas con predicciones ML.
- No presentes porcentajes de reglas como probabilidad diagnóstica.
- Si hay alerta crítica, priorízala sobre hipótesis ML.

Devuelve SOLO el texto del informe, sin JSON ni formato extra."""


# ══════════════════════════════════════
# Agente Generador de Informes
# ══════════════════════════════════════

class ReportGeneratorAgent:
    """
    Genera el informe clínico final en texto narrativo para el médico.
    """

    def __init__(
        self,
        llm: LLMProvider,
        temperature: float = 0.1,
        max_tokens: int = 3000,
    ):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate_report(
        self,
        patient_intake: Dict[str, Any],
        ml_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        """
        Genera el informe narrativo completo.
        
        Args:
            patient_intake: Datos del paciente extraídos
            ml_results: Resultados del pipeline ML (hipótesis, urgencia, etc.)
            conversation_history: Historial de conversación (opcional, para resumen)
        
        Returns:
            Texto del informe clínico
        """
        # Crear resumen de conversación si hay historial
        conversation_summary = ""
        if conversation_history:
            user_messages = [
                msg["content"] for msg in conversation_history
                if msg["role"] == "user"
            ]
            if user_messages:
                conversation_summary = "El paciente reportó: " + " | ".join(
                    msg[:200] for msg in user_messages[-8:]
                )

        prompt = _build_report_prompt(patient_intake, ml_results, conversation_summary)

        messages = [
            {"role": "system", "content": REPORT_SYSTEM},
            {"role": "user", "content": prompt},
        ]

        report_text = await self.llm.generate(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return report_text.strip()

    def generate_report_without_llm(
        self,
        patient_intake: Dict[str, Any],
        ml_results: Dict[str, Any],
    ) -> str:
        """
        Genera un informe estructurado SIN usar LLM (fallback determinista).
        Útil cuando el LLM no está disponible o para pruebas.
        """
        now = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

        lifestyle = patient_intake.get("lifestyle_factors", {})
        if not isinstance(lifestyle, dict):
            lifestyle = {}

        sections = []
        sections.append("=" * 45)
        sections.append("       INFORME MEDIC AI")
        sections.append("=" * 45)
        sections.append(f"Generado el: {now}")

        if ml_results.get("analysis_degraded"):
            sections.append("[!] ADVERTENCIA: Análisis en modo degradado o ML desactivado/suprimido.")

        urgency_label = ml_results.get("urgency_label", "low")
        priority = urgency_label.upper()

        sections.append(f"Prioridad (Label): {priority}")
        sections.append(f"Destino Recomendado: {ml_results.get('destination_label', 'Seguimiento')}")
        sections.append(f"Score Numérico: {ml_results.get('urgency_score', 0)} / 100")
        sections.append("")

        # Datos recopilados
        sections.append("--- DATOS RECOPILADOS ---")
        sections.append(f"Edad: {patient_intake.get('age', 'No informada')}")
        sections.append(f"Sexo: {patient_intake.get('sex', 'No informado')}")
        sections.append(f"Síntoma Principal: {patient_intake.get('main_symptom', 'No informado')}")
        sections.append(f"Duración: {patient_intake.get('duration', 'No informada')}")
        sections.append(f"Síntomas Asociados: {', '.join(patient_intake.get('associated_symptoms', [])) or 'Ninguno'}")
        sections.append(f"Medicación Actual: {', '.join(patient_intake.get('medication', [])) or 'No refiere'}")
        sections.append(f"Alergias: {', '.join(patient_intake.get('allergies', [])) or 'No refiere'}")
        sections.append(f"Historial Médico: {', '.join(patient_intake.get('medical_history', [])) or 'Sin antecedentes'}")
        sections.append("")

        # Estilo de vida
        lifestyle_values = [v for v in lifestyle.values() if v.strip()]
        if lifestyle_values:
            sections.append("--- ESTILO DE VIDA ---")
            sections.append(f"Tabaco: {lifestyle.get('smoking', 'No refiere')}")
            sections.append(f"Alcohol: {lifestyle.get('alcohol', 'No refiere')}")
            sections.append(f"Drogas: {lifestyle.get('drugs', 'No refiere')}")
            sections.append(f"Ejercicio: {lifestyle.get('exercise', 'No refiere')}")
            sections.append(f"Dieta: {lifestyle.get('diet', 'No refiere')}")
            sections.append("")

        # Señales de alarma
        alarms = ml_results.get("alarm_signals", [])
        if alarms:
            sections.append("--- SEÑALES DE ALARMA DETECTADAS ---")
            for alarm in alarms:
                sections.append(f"- [{alarm.get('severity', 'HIGH').upper()}] {alarm.get('signal', '')}")
            sections.append("")

        # Especialidad
        spec_conf = ml_results.get('specialty_confidence')
        spec_conf_text = f"{spec_conf * 100:.1f}%" if spec_conf is not None else "No aplicable"
        spec_source = ml_results.get('specialty_source', 'unknown')
        sections.append(f"--- ESPECIALIDAD ASIGNADA ---")
        sections.append(f"Rama: {ml_results.get('assigned_specialty', 'No determinada')}")
        sections.append(f"Origen: {spec_source}")
        sections.append(f"Confianza: {spec_conf_text}")
        sections.append("")

        # Alertas clínicas
        clinical_alerts = ml_results.get("clinical_alerts", [])
        if clinical_alerts:
            sections.append("--- ALERTAS CLÍNICAS (DETERMINISTAS) ---")
            for alert in clinical_alerts:
                sev = alert.get("severity", "HIGH").upper()
                sections.append(f"- [{sev}] {alert.get('disease_name', '?')}")
                sections.append(f"  Recomendación: {alert.get('recommendation', '')}")
                sections.append(f"  Evidencia: {format_rule_evidence(alert.get('rule_evidence', []))}")
            sections.append("")

        # Diagnóstico diferencial
        hypotheses = ml_results.get("ml_hypotheses", [])
        if hypotheses:
            sections.append("--- DIAGNÓSTICO DIFERENCIAL (ML) ---")
            for h in hypotheses:
                prob_pct = h.get("probability", 0) * 100
                sections.append(f"\n- {h.get('disease_name', '?')} ({prob_pct:.1f}%)")
                if h.get("recommended_tests"):
                    sections.append(f"  Pruebas: {', '.join(h['recommended_tests'])}")
                if h.get("shap_explanation"):
                    top_shap = sorted(
                        h["shap_explanation"].items(),
                        key=lambda x: abs(x[1]),
                        reverse=True
                    )[:3]
                    for feat, val in top_shap:
                        direction = "↑" if val > 0 else "↓"
                        sections.append(f"  {direction} {feat}: {val:+.3f}")
            sections.append("")

        if ml_results.get("ml_suppressed_reason"):
            sections.append(f"--- ML OMITIDO ---")
            sections.append(ml_results.get("ml_suppressed_reason"))
            sections.append("")

        sections.append("")
        sections.append("Aviso: Las probabilidades son estimaciones generadas por un sistema ML")
        sections.append("con fines educativos y no representan un diagnóstico médico.")
        sections.append("")

        return "\n".join(sections)

