"""
Medic AI — Backend Principal (FastAPI + WebSocket)

Servidor que orquesta:
- Chat en tiempo real con el paciente via WebSocket
- API REST para gestión de sesiones y reportes
- Servicio de archivos estáticos del frontend
"""
from __future__ import annotations

import uuid
import json
import asyncio
import traceback
import time
from contextlib import asynccontextmanager
from ipaddress import ip_address
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ── Config ──
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from schemas.medical import (
    BAYES_FEATURE_KEYS, PatientIntake, BayesFeatures,
    MedicalReport, SessionState, UrgencyLevel, MedicalSpecialty,
    SYMPTOM_LABELS_ES
)
from agents.llm_provider import create_provider, OllamaProvider
from agents.conversational import ConversationalAgent, is_non_informative
from agents.extractor import ExtractorAgent
from agents.report_generator import ReportGeneratorAgent


# ══════════════════════════════════════
# App Setup
# ══════════════════════════════════════

def purge_expired():
    now = time.monotonic()
    for sid, session in list(sessions.items()):
        if now - session.get("started_monotonic", now) >= config.SESSION_TTL_SECONDS:
            sessions.pop(sid, None)
            reports.pop(sid, None)

@asynccontextmanager
async def lifespan(app):
    async def cleanup():
        while True:
            await asyncio.sleep(30)
            purge_expired()
    task = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Medic AI",
    description="Prototipo educativo; demo offline con casos ficticios",
    lifespan=lifespan,
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

def is_loopback(client):
    if not client:
        return False
    try:
        return ip_address(client.host).is_loopback
    except ValueError:
        return False

def allowed_origin(origin):
    return not origin or origin in config.ALLOWED_ORIGINS

@app.middleware("http")
async def local_only(request: Request, call_next):
    host = request.url.hostname
    if not is_loopback(request.client) or host not in ("localhost", "127.0.0.1", "::1") or not allowed_origin(request.headers.get("origin")):
        return JSONResponse({"detail": "Local educational demo only"}, status_code=403)
    purge_expired()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response

# ── Static files ──
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


# ══════════════════════════════════════
# LLM Providers (Ollama local por defecto)
# ══════════════════════════════════════

def _get_llm_ask():
    return create_provider(
        provider_type=config.LLM_PROVIDER,
        model=getattr(config, f"{config.LLM_PROVIDER.upper()}_MODEL_ASK"),
        api_key=getattr(config, f"{config.LLM_PROVIDER.upper()}_API_KEY", ""),
        base_url=config.OLLAMA_BASE_URL,
    )

def _get_llm_extract():
    return create_provider(
        provider_type=config.LLM_PROVIDER,
        model=getattr(config, f"{config.LLM_PROVIDER.upper()}_MODEL_EXTRACT"),
        api_key=getattr(config, f"{config.LLM_PROVIDER.upper()}_API_KEY", ""),
        base_url=config.OLLAMA_BASE_URL,
    )

def _get_llm_report():
    return create_provider(
        provider_type=config.LLM_PROVIDER,
        model=getattr(config, f"{config.LLM_PROVIDER.upper()}_MODEL_REPORT"),
        api_key=getattr(config, f"{config.LLM_PROVIDER.upper()}_API_KEY", ""),
        base_url=config.OLLAMA_BASE_URL,
    )


# ══════════════════════════════════════
# Agents
# ══════════════════════════════════════

conv_agent = ConversationalAgent(
    llm=_get_llm_ask(),
    temperature=config.TEMPERATURE_ASK,
    max_tokens=config.MAX_TOKENS_ASK,
    window_size=config.WINDOW_ASK,
)

extract_agent = ExtractorAgent(
    llm=_get_llm_extract(),
    temperature=config.TEMPERATURE_EXTRACT,
    max_tokens=config.MAX_TOKENS_EXTRACT,
    window_size=config.WINDOW_EXTRACT,
)

report_agent = ReportGeneratorAgent(
    llm=_get_llm_report(),
    temperature=config.TEMPERATURE_REPORT,
    max_tokens=config.MAX_TOKENS_REPORT,
)


# ══════════════════════════════════════
# ML Pipeline (carga lazy)
# ══════════════════════════════════════

_ml_pipeline = None

def get_ml_pipeline():
    global _ml_pipeline
    if _ml_pipeline is None:
        try:
            from ml.pipeline import MedicalPipeline
            _ml_pipeline = MedicalPipeline(enable_ml=not config.DEMO_MODE)
            print("[Medic AI] Model status:", _ml_pipeline.availability())
        except Exception as e:
            print(f"[Medic AI] ⚠️ Pipeline ML no disponible: {e}")
            _ml_pipeline = None
    return _ml_pipeline


# ══════════════════════════════════════
# Session Store (en memoria)
# ══════════════════════════════════════

sessions: Dict[str, Dict[str, Any]] = {}
reports: Dict[str, Dict[str, Any]] = {}


def create_session() -> Dict[str, Any]:
    purge_expired()
    if len(sessions) >= config.MAX_SESSIONS:
        raise HTTPException(status_code=429, detail="Session limit reached; wait for expiry")
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "started_monotonic": time.monotonic(),
        "status": "active",
        "messages": [],
        "turn_count": 0,
        "last_extracted_turn": 0,
        "patient_intake": {
            "age": "", "sex": "", "main_symptom": "", "duration": "",
            "associated_symptoms": [], "medical_history": [],
            "medication": [], "allergies": [],
            "lifestyle_factors": {"smoking": "", "alcohol": "", "drugs": "", "exercise": "", "diet": ""},
        },
        "bayes_features": {k: "unknown" for k in BAYES_FEATURE_KEYS},
        "report": None,
    }
    sessions[session_id] = session
    return session


# ══════════════════════════════════════
# WebSocket — Chat en Tiempo Real
# ══════════════════════════════════════

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    if not is_loopback(websocket.client) or websocket.url.hostname not in ("localhost", "127.0.0.1", "::1") or not allowed_origin(websocket.headers.get("origin")):
        await websocket.close(code=1008)
        return
    if config.DEMO_MODE:
        await websocket.close(code=1008, reason="Use fictional demo cases")
        return
    purge_expired()
    if len(sessions) >= config.MAX_SESSIONS:
        await websocket.close(code=1013)
        return
    await websocket.accept()
    session = create_session()
    sid = session["session_id"]
    print(f"[Medic AI] 🔗 Nueva sesión: {sid}")

    try:
        # Enviar saludo inicial
        greeting = conv_agent.get_greeting()
        session["messages"].append({"role": "assistant", "content": greeting})

        await websocket.send_json({
            "type": "session_start",
            "session_id": sid,
        })
        await websocket.send_json({
            "type": "message",
            "role": "assistant",
            "content": greeting,
        })

        while True:
            # Recibir mensaje del paciente
            data = await websocket.receive_json()
            purge_expired()
            if sid not in sessions:
                await websocket.close(code=1008, reason="Session expired")
                return
            if not isinstance(data, dict):
                continue
            msg_type = data.get("type", "message")

            if msg_type == "finalize":
                # Forzar finalización
                await _finalize_session(sid, websocket)
                break

            user_text = data.get("message", "")
            if not isinstance(user_text, str) or len(user_text) > 4000:
                await websocket.send_json({"type": "error", "message": "El mensaje debe tener entre 1 y 4000 caracteres."})
                continue
            user_text = user_text.strip()
            if session["turn_count"] >= 40:
                await websocket.close(code=1008, reason="Turn limit")
                return
            if not user_text:
                continue

            # Verificar si es informativo
            if is_non_informative(user_text):
                await websocket.send_json({
                    "type": "message",
                    "role": "assistant",
                    "content": "Para poder ayudarte, necesito que respondas a la pregunta clínica anterior. 😊",
                })
                continue

            # Guardar mensaje del usuario
            session["messages"].append({"role": "user", "content": user_text})
            session["turn_count"] += 1

            # Indicar que está "pensando"
            await websocket.send_json({"type": "thinking"})

            # Extracción periódica en background (cada N turnos)
            if (session["turn_count"] - session["last_extracted_turn"]) >= config.EXTRACT_EVERY_N_TURNS:
                try:
                    result = await extract_agent.extract(
                        conversation_history=session["messages"],
                        current_intake=session["patient_intake"],
                        current_features=session["bayes_features"],
                    )
                    session["patient_intake"] = result["patient_intake"]
                    session["bayes_features"] = result["bayes_features"]
                    session["last_extracted_turn"] = session["turn_count"]

                    # Enviar actualización de estado
                    await websocket.send_json({
                        "type": "state_update",
                        "patient_intake": session["patient_intake"],
                        "bayes_features_active": [
                            {"key": k, "label": SYMPTOM_LABELS_ES.get(k, k.replace("_", " ").title())}
                            for k, v in session["bayes_features"].items() if v == "present"
                        ],
                        "turn_count": session["turn_count"],
                    })
                except Exception as e:
                    print(f"[Medic AI] ⚠️ Error en extracción: {e}")

            # Generar siguiente pregunta (streaming)
            full_response = ""
            try:
                async for token in conv_agent.stream_question(session["messages"]):
                    full_response += token
                    await websocket.send_json({
                        "type": "token",
                        "content": token,
                    })
            except Exception as e:
                # Fallback a generación sin streaming
                print(f"[Medic AI] ⚠️ Stream falló, usando generate: {e}")
                full_response = await conv_agent.generate_question(session["messages"])
                await websocket.send_json({
                    "type": "token",
                    "content": full_response,
                })

            await websocket.send_json({"type": "stream_end"})

            # Guardar respuesta del asistente
            session["messages"].append({"role": "assistant", "content": full_response})

            # Verificar si debería ofrecer finalizar
            if conv_agent.should_end_interview(session["turn_count"], session["messages"], session["patient_intake"]):
                await websocket.send_json({
                    "type": "can_finalize",
                    "message": "Ya tengo suficiente información. Puedes finalizar la entrevista cuando quieras.",
                })

    except WebSocketDisconnect:
        print(f"[Medic AI] 🔌 Sesión {sid} desconectada")
    except Exception as e:
        print(f"[Medic AI] ❌ Error en sesión {sid}: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": "No se pudo completar la operación. Revisa la configuración local.",
            })
        except:
            pass


async def _finalize_session(session_id: str, websocket: WebSocket):
    await websocket.send_json({"type": "status", "message": "Generando informe experimental..."})
    report = await finalize_session_rest(session_id)
    await websocket.send_json({"type": "report_ready", "report": report})


# ══════════════════════════════════════
# REST API
# ══════════════════════════════════════

@app.get("/api/reports")
async def list_reports():
    purge_expired()
    """Lista todos los informes generados."""
    report_list = []
    for rid, report in reports.items():
        report_list.append({
            "report_id": report["report_id"],
            "generated_at": report["generated_at"],
            "urgency_score": report["urgency_score"],
            "urgency_level": report["urgency_level"],
            "assigned_specialty": report["assigned_specialty"],
            "patient_age": report.get("patient_intake", {}).get("age", ""),
            "patient_sex": report.get("patient_intake", {}).get("sex", ""),
            "main_symptom": report.get("patient_intake", {}).get("main_symptom", ""),
        })
    # Ordenar por urgencia descendente
    report_list.sort(key=lambda x: x["urgency_score"], reverse=True)
    return {"reports": report_list}


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    purge_expired()
    """Obtiene un informe específico."""
    report = reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return report


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    purge_expired()
    """Obtiene el estado actual de una sesión."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "turn_count": session["turn_count"],
        "patient_intake": session["patient_intake"],
        "bayes_features_active": [
            {"key": k, "label": SYMPTOM_LABELS_ES.get(k, k.replace("_", " ").title())}
            for k, v in session["bayes_features"].items() if v == "present"
        ],
    }


@app.post("/api/sessions/{session_id}/finalize")
async def finalize_session_rest(session_id: str):
    """Finaliza una sesión via REST (alternativa al WebSocket)."""
    purge_expired()
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session["status"] == "completed":
        return session["report"]
    if config.DEMO_MODE:
        raise HTTPException(status_code=409, detail="Use the fictional demo cases")
    if session["status"] != "active":
        raise HTTPException(status_code=409, detail="Session is already being finalized")
    session["status"] = "finalizing"

    # Hacer extracción y ML sin WebSocket
    try:
        result = await extract_agent.extract(
            conversation_history=session["messages"],
            current_intake=session["patient_intake"],
            current_features=session["bayes_features"],
        )
        session["patient_intake"] = result["patient_intake"]
        session["bayes_features"] = result["bayes_features"]
    except Exception:
        pass

    pipeline = get_ml_pipeline()
    from ml.pipeline import build_safe_clinical_fallback

    if pipeline is None:
        ml_results = build_safe_clinical_fallback(session["bayes_features"], Exception("Pipeline ML no disponible"))
    else:
        try:
            ml_results = pipeline.analyze(session["bayes_features"])
        except Exception as e:
            print(f"[Medic AI] ⚠️ Error en pipeline ML (REST): {e}")
            ml_results = build_safe_clinical_fallback(session["bayes_features"], e)

    try:
        narrative = await report_agent.generate_report(session["patient_intake"], ml_results, session["messages"])
    except Exception:
        narrative = report_agent.generate_report_without_llm(session["patient_intake"], ml_results)

    urgency_level = ml_results.get("urgency_label", "low")
    urgency_score = ml_results.get("urgency_score", 0)
    
    report = {
        "report_id": session_id,
        "generated_at": datetime.now().isoformat(),
        "urgency_score": urgency_score,
        "urgency_level": urgency_level,
        "assigned_specialty": ml_results.get("assigned_specialty", ""),
        "specialty_confidence": ml_results.get("specialty_confidence", 0.0),
        "specialty_source": ml_results.get("specialty_source", "unknown"),
        "patient_intake": session["patient_intake"],
        "bayes_features": session["bayes_features"],
        "bayes_features_active": [
            {"key": k, "label": SYMPTOM_LABELS_ES.get(k, k.replace("_", " ").title())}
            for k, v in session["bayes_features"].items() if v == "present"
        ],
        "bayes_features_absent": [
            {"key": k, "label": SYMPTOM_LABELS_ES.get(k, k.replace("_", " ").title())}
            for k, v in session["bayes_features"].items() if v == "absent"
        ],
        "alarm_signals": ml_results.get("alarm_signals", []),
        "clinical_alerts": ml_results.get("clinical_alerts", []),
        "ml_hypotheses": ml_results.get("ml_hypotheses", []),
        "insufficient_data": ml_results.get("insufficient_data", False),
        "ml_suppressed_reason": ml_results.get("ml_suppressed_reason"),
        "recommended_destination": ml_results.get("recommended_destination"),
        "destination_label": ml_results.get("destination_label"),
        "clinical_summary": narrative,
        "analysis_degraded": ml_results.get("analysis_degraded", True),
        "model_status": pipeline.availability() if pipeline else {"ready": False},
        "experimental": True,
        "conversation_turns": session["turn_count"],
    }
    purge_expired()
    if session_id not in sessions:
        raise HTTPException(status_code=410, detail="Session expired during processing")
    session["report"] = report
    session["status"] = "completed"
    reports[session_id] = report
    return report


DEMO_CASES = {
    "insufficient": {"label": "Información insuficiente", "text": "Caso ficticio: dolor de cabeza; el resto no se ha preguntado.", "features": {"headache": "present"}},
    "alert": {"label": "Regla de alerta experimental", "text": "Caso ficticio: dolor de pecho y sudoración; niega fiebre.", "features": {"chest_pain": "present", "sweating": "present", "high_fever": "absent"}},
    "missing_model": {"label": "Modelo no disponible", "text": "Caso ficticio: picor y erupción; niega tos.", "features": {"itching": "present", "skin_rash": "present", "cough": "absent"}},
}

@app.get("/api/demo/cases")
async def demo_cases():
    return {"cases": [{"id": key, "label": value["label"], "text": value["text"]} for key, value in DEMO_CASES.items()]}

@app.post("/api/demo/{case_id}")
async def run_demo(case_id: str):
    if case_id not in DEMO_CASES:
        raise HTTPException(status_code=404, detail="Unknown fictional case")
    from ml.pipeline import MedicalPipeline
    case = DEMO_CASES[case_id]
    session = create_session()
    session["bayes_features"].update(case["features"])
    session["patient_intake"]["main_symptom"] = case["text"]
    pipeline = MedicalPipeline(enable_ml=False)
    result = pipeline.analyze(session["bayes_features"])
    report = {**result, "report_id": session["session_id"], "generated_at": datetime.now().isoformat(),
              "urgency_level": result["urgency_label"], "patient_intake": session["patient_intake"],
              "bayes_features": session["bayes_features"],
              "bayes_features_active": [{"key": k, "label": SYMPTOM_LABELS_ES.get(k, k)} for k, v in session["bayes_features"].items() if v == "present"],
              "bayes_features_absent": [{"key": k, "label": SYMPTOM_LABELS_ES.get(k, k)} for k, v in session["bayes_features"].items() if v == "absent"],
              "clinical_summary": "CASO FICTICIO. Demo offline de reglas y estructura del informe. Sin LLM, sin predicciones de enfermedades y sin validación clínica.",
              "model_status": pipeline.availability(), "demo": True, "experimental": True}
    session["report"] = report
    session["status"] = "completed"
    reports[session["session_id"]] = report
    return report


# ══════════════════════════════════════
# Frontend Pages
# ══════════════════════════════════════

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Medic AI Backend — Frontend no encontrado"}


@app.get("/doctor")
async def serve_doctor():
    doctor_path = FRONTEND_DIR / "doctor.html"
    if doctor_path.exists():
        return FileResponse(str(doctor_path))
    return {"message": "Panel Doctor — Archivo no encontrado"}


# ══════════════════════════════════════
# Health Check
# ══════════════════════════════════════

@app.get("/api/health")
async def health_check():
    pipeline = get_ml_pipeline()
    return {
        "status": "ok",
        "llm_provider": config.LLM_PROVIDER,
        "demo_mode": config.DEMO_MODE,
        "ml_pipeline_loaded": bool(pipeline and pipeline.availability()["ready"]),
        "models": pipeline.availability() if pipeline else {"ready": False},
        "session_ttl_seconds": config.SESSION_TTL_SECONDS,
        "active_sessions": len(sessions),
        "total_reports": len(reports),
    }


# ══════════════════════════════════════
# Entrypoint
# ══════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 50)
    print("  🏥 MEDIC AI — Sistema de Triaje Médico con IA")
    print("  Prototipo educativo — casos ficticios — sin validación clínica")
    print("=" * 50)
    print(f"  LLM Provider: {config.LLM_PROVIDER}")
    print(f"  Frontend: http://localhost:{config.PORT}")
    print(f"  Panel Doctor: http://localhost:{config.PORT}/doctor")
    print(f"  API Health: http://localhost:{config.PORT}/api/health")
    print("=" * 50 + "\n")

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
    )

