"""
Medic AI — Agente Conversacional de Triaje

Implementa la entrevista médica estructurada siguiendo el esquema ALICIA.
Genera preguntas una por una, mantiene contexto y detecta respuestas vacías.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any

from .llm_provider import LLMProvider


# ══════════════════════════════════════
# Prompt del sistema de entrevista
# ══════════════════════════════════════

SYSTEM_INTERVIEW = """Eres Medic AI, un asistente conversacional de triaje médico con fines educativos y de apoyo a sistemas automáticos de clasificación.

LÍMITES:
- No diagnostiques.
- No prescribas.
- No recomiendes medicación ni tratamientos.
- No inventes: SOLO marca como presente lo que el usuario haya confirmado explícitamente.
- Haz preguntas breves, claras y UNA por una.

ENTREVISTA:
- Al inicio pregunta obligatoriamente: edad y sexo.
- Luego cubre: síntoma principal con ALICIA (Aparición, Localización, Irradiación, Carácter, Intensidad, Alivio/Agravantes) + evolución + síntomas asociados por grupos + antecedentes personales y familiares + medicación/alergias + estilo de vida (tabaco, alcohol, drogas, ejercicio, dieta) + señales de alarma dirigidas.
- No repitas preguntas ya respondidas.
- No repitas información que el usuario ya te ha dado.
- Pregunta en base a las respuestas del usuario, indagando en sus síntomas.
- Mantén siempre un tono amigable, cercano y respetuoso.
- Cuando creas que tienes suficiente información (mínimo 8-10 intercambios con información relevante), indica que vas a generar el informe."""


GENERATE_QUESTION_PROMPT = """Genera la SIGUIENTE mejor pregunta de triaje (UNA sola pregunta).
Breve, clara, lenguaje sencillo.
Si aún no se ha preguntado por edad y sexo, pregúntalo primero.
Sigue el orden: ALICIA + evolución + asociados por grupos + antecedentes + medicación/alergias + estilo de vida + señales de alarma dirigidas.
NO generes JSON. Devuelve SOLO la pregunta, sin comillas ni formato extra."""


# ══════════════════════════════════════
# Detección de respuestas vacías
# ══════════════════════════════════════

FILLERS = [
    "jaja", "jajaja", "ok", "vale", "bien", "genial", "perfecto",
    "gracias", "de acuerdo", "ajá", "bua", "espectacular", "lo mejor",
    "xd", "lol", "si", "sí", "no sé", "nose", "nada más", "eso es todo",
]

CLINICAL_HINTS = [
    "dolor", "fiebre", "tos", "vom", "diar", "mare", "náuse", "nause",
    "cabeza", "pecho", "barriga", "espalda", "pierna", "brazo", "sangr",
    "hinch", "erupci", "picaz", "mareo", "cansanc", "fatiga", "débil",
    "respir", "tragar", "orinar", "piel", "visión", "oído",
]


def is_non_informative(text: str) -> bool:
    """Dejamos que el LLM decida si la respuesta aporta información, a menos que esté vacía."""
    t = text.strip()
    # Solo bloquear si el usuario envía literalmente menos de 2 letras y no es 'si' ni 'no'
    if len(t) < 2 and t.lower() not in ["s", "n", "y"]:
        return True
    return False


# ══════════════════════════════════════
# Agente Conversacional
# ══════════════════════════════════════

class ConversationalAgent:
    """
    Agente de entrevista médica que genera preguntas de triaje.
    
    Usa un LLMProvider configurable (Ollama local por defecto).
    """

    def __init__(
        self,
        llm: LLMProvider,
        temperature: float = 0.3,
        max_tokens: int = 300,
        window_size: int = 10,
    ):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.window_size = window_size

    def _build_messages(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Construye el array de mensajes para el LLM con ventana de contexto."""
        messages = [{"role": "system", "content": SYSTEM_INTERVIEW}]

        # Ventana de los últimos N mensajes
        recent = conversation_history[-self.window_size:]
        messages.extend(recent)

        # Instrucción final para generar la pregunta
        messages.append({"role": "system", "content": GENERATE_QUESTION_PROMPT})

        return messages

    async def generate_question(self, conversation_history: List[Dict[str, str]]) -> str:
        """Genera la siguiente pregunta de triaje basada en el historial."""
        messages = self._build_messages(conversation_history)

        response = await self.llm.generate(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Limpiar comillas y formato extra
        cleaned = response.strip()
        cleaned = re.sub(r'^["\']+|["\']+$', "", cleaned).strip()
        # Quitar prefijos tipo "Medic AI:" o "Pregunta:"
        cleaned = re.sub(r'^(Medic\s*AI\s*:|Pregunta\s*:)\s*', "", cleaned, flags=re.IGNORECASE).strip()

        return cleaned

    async def stream_question(self, conversation_history: List[Dict[str, str]]):
        """Genera la siguiente pregunta en streaming (token a token)."""
        messages = self._build_messages(conversation_history)

        async for token in self.llm.stream(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        ):
            yield token

    def get_greeting(self) -> str:
        """Mensaje de bienvenida inicial."""
        return (
            "¡Hola! Soy **Medic AI**, tu asistente de triaje médico. "
            "Estoy aquí para ayudarte a recopilar información sobre tus síntomas "
            "y generar un informe para tu médico.\n\n"
            "Para empezar, ¿podrías decirme tu **edad** y tu **sexo**?"
        )

    def should_end_interview(self, turn_count: int, conversation_history: List[Dict[str, str]], patient_intake: dict = None) -> bool:
        """Determina si la entrevista tiene suficiente información para finalizar."""
        if turn_count < 8:
            return False

        # Verificar que los datos esenciales estén presentes
        if patient_intake:
            age = patient_intake.get("age", "")
            sex = patient_intake.get("sex", "")
            main_symptom = patient_intake.get("main_symptom", "")
            # No ofrecer finalizar si falta edad, sexo o síntoma principal
            if not age or not sex or not main_symptom:
                return False

        # Contar turnos con información clínica real del usuario
        informative_turns = 0
        for msg in conversation_history:
            if msg["role"] == "user" and not is_non_informative(msg["content"]):
                informative_turns += 1

        return informative_turns >= 8


