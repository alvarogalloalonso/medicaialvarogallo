# Medic AI

**Independent project by Álvaro Gallo Alonso · original development September 2025–summer 2026**

An educational experiment combining conversational AI, structured symptom extraction and machine-learning routing. Development was paused when data availability and model reliability became limiting factors. The source was prepared for a portfolio in October 2026, including an offline demonstration and regression fixes.

> Experimental software. No clinical validation, diagnostic accuracy or healthcare benefit is claimed. Use fictional examples only.

## Try the offline demo

```bash
cd local-prototype
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
python backend/main.py
```

Open **http://127.0.0.1:8000** and select one of three fictional cases. View the generated report in the local report panel. The default demo contacts no LLM, loads no trained classifiers and needs no API keys or downloaded model weights. Reports expire after one hour.

## Two independent applications

| Location | Purpose | Status |
| --- | --- | --- |
| `local-prototype/` | FastAPI, WebSocket chat, symptom extraction, experimental rules, Naive Bayes/XGBoost integration | Offline fictional demo ready; live LLM and medical model quality not validated |
| Repository root | Earlier React/TypeScript/Vite presentation and optional audio-transcription experiment | Independent of Python; audio disabled by default |

The Google AI Studio prototype is part of the original project history; this repository does not contain a verified export of that hosted application.

## Implementation

- Conversation, extraction and report agents with adapters for Ollama, Gemini and OpenAI.
- Symptoms represented as present, absent or unknown; the model input separates presence from an observation mask.
- Bernoulli Naive Bayes router and XGBoost specialist classifiers with sigmoid calibration.
- Explicit unavailable-model states; incompatible historical artifacts are rejected.
- Optional SHAP explanations of one fitted base estimator, not the final calibrated ensemble probability.
- Local-only demo, expiring in-memory reports and text-only rendering of user/model content.

## Data and evaluation

Historical training relied at least partly on synthetic data. Exact artifact provenance, dataset licence and reliable quality metrics remain unresolved; those datasets and historical models are excluded.

The revised training script records dataset metadata and hash, deterministic partitions, held-out classification/calibration metrics, specialist failures and end-to-end routing outcomes. It refuses insufficient classes instead of inventing disease labels. Source zeros are treated as unobserved in the documented experiment; partial interviews are simulated by masking some positive symptoms. This is not clinical evaluation.

- [Local setup and providers](local-prototype/README.md)
- [Architecture](local-prototype/docs/ARCHITECTURE.md)
- [Data and evaluation protocol](local-prototype/docs/DATA_AND_EVALUATION.md)
- [Checks and limitations](local-prototype/docs/VERIFICATION.md)
- [Portfolio revision](docs/PORTFOLIO_REVISION.md)

## Earlier React application

```bash
npm ci
npm run dev
```

It renders without Supabase configuration. For the optional authenticated transcription experiment, read `supabase/README.md`. Audio is disabled by default and is not part of the offline Python demo. No external deployment was performed.

## Verification

```bash
python -m pytest local-prototype/backend/tests -q
npm test
npm run build
```

Tests verify software behaviour, fictional demo flows and hostile-text rendering; they do not establish model accuracy. Follow-up and production authentication remain future work. The backend deliberately refuses non-loopback clients and untrusted origins.

## Author

Álvaro Gallo Alonso — BSc student in Data Science and Artificial Intelligence, Universidad Politécnica de Madrid.
