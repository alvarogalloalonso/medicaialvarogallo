"""
Medic AI — Configuración Global
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# ──────────────────────────────────────
# Paths
# ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────
# LLM Provider Configuration
# ──────────────────────────────────────
# Options: "ollama", "gemini", "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_ASK = os.getenv("OLLAMA_MODEL_ASK", "deepseek-r1:8b")
OLLAMA_MODEL_EXTRACT = os.getenv("OLLAMA_MODEL_EXTRACT", "qwen3:8b")
OLLAMA_MODEL_REPORT = os.getenv("OLLAMA_MODEL_REPORT", "qwen3:8b")

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_ASK = os.getenv("GEMINI_MODEL_ASK", "gemini-2.5-flash")
GEMINI_MODEL_EXTRACT = os.getenv("GEMINI_MODEL_EXTRACT", "gemini-2.5-flash")
GEMINI_MODEL_REPORT = os.getenv("GEMINI_MODEL_REPORT", "gemini-2.5-flash")

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_ASK = os.getenv("OPENAI_MODEL_ASK", "gpt-4o-mini")
OPENAI_MODEL_EXTRACT = os.getenv("OPENAI_MODEL_EXTRACT", "gpt-4o-mini")
OPENAI_MODEL_REPORT = os.getenv("OPENAI_MODEL_REPORT", "gpt-4o-mini")

# ──────────────────────────────────────
# LLM Parameters
# ──────────────────────────────────────
TEMPERATURE_ASK = 0.3           # Conversational agent — slight creativity
TEMPERATURE_EXTRACT = 0.0       # Extractor — deterministic JSON
TEMPERATURE_REPORT = 0.1        # Report — structured but readable

MAX_TOKENS_ASK = 500
MAX_TOKENS_EXTRACT = 4000
MAX_TOKENS_REPORT = 4000

# ──────────────────────────────────────
# Conversation Parameters
# ──────────────────────────────────────
WINDOW_ASK = 10                 # Messages window for asking
WINDOW_EXTRACT = 20             # Messages window for extraction
EXTRACT_EVERY_N_TURNS = 3       # Extract JSON every N turns
MIN_QUESTIONS_BEFORE_END = 8    # Minimum questions before allowing finalization

# ──────────────────────────────────────
# Medical Specialties
# ──────────────────────────────────────
SPECIALTIES = [
    "respiratorio_cardio",
    "neurologico",
    "digestivo",
    "urinario_genital",
    "piel_alergia",
    "general_musculoesqueletico",
]

# ──────────────────────────────────────
# Server
# ──────────────────────────────────────
HOST = os.getenv("HOST", "127.0.0.1")
ENABLE_SHAP = os.getenv("ENABLE_SHAP", "false").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_SESSIONS = 100
ALLOWED_ORIGINS = [f"http://127.0.0.1:{os.getenv('PORT', '8000')}", f"http://localhost:{os.getenv('PORT', '8000')}"]
PORT = int(os.getenv("PORT", "8000"))

