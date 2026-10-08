# Medic AI — local prototype

Independent Python application; not connected to the React frontend at the repository root.

## Offline fictional demo (default)

Use Python 3.11 or 3.12. From the repository root:

```bash
cd local-prototype
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
python backend/main.py
```

Open `http://127.0.0.1:8000`, choose a fictional example, and follow its report link. `/api/health` distinguishes application availability from classifier availability. The demo does not call any LLM or load model artifacts. Rule scores demonstrate software logic only.

## Experimental live conversation

Copy `backend/.env.example` to `backend/.env`. Set `DEMO_MODE=false` and configure your provider. For the default local provider, install Ollama and separately download `deepseek-r1:8b` and `qwen3:8b` (or configure other installed models). Hosted providers send conversation content externally; use fictional content only. Live provider calls were not exercised in this revision.

The server defaults to `127.0.0.1:8000` and refuses non-loopback clients, unexpected Host headers and untrusted browser origins. If the port changes, restart to update allowed origins. There is no production multi-user authentication. Sessions expire one hour after creation, with at most 100 retained sessions and 40 conversation turns. Data are memory-only.

## Experimental training

Read [the evaluation protocol](docs/DATA_AND_EVALUATION.md). Obtain a permitted dataset and create a metadata JSON containing nonempty `source`, `licence`, `collection_method` and `zero_semantics` fields. This experiment requires `zero_semantics` to be `unobserved`.

```bash
python backend/ml/train.py --data /path/to/permitted.csv --metadata /path/to/metadata.json
```

The dataset must contain the 132 symptom columns from `BAYES_FEATURE_KEYS` and `prognosis`. Exact duplicate symptom patterns are removed before splitting; conflicting labels are rejected. Disease labels require at least five distinct patterns for stratified holdout. Specialists require at least two classes and three training samples per class for calibration. Insufficient specialists stay unavailable.

Artifacts and `evaluation.json` are saved locally in `backend/models/`. Historical v1 artifacts are incompatible: retrain using the versioned presence/observation schema. No historical dataset was used for this revision.

## Optional SHAP

SHAP is separate because its native dependencies caused an import crash in the verification environment. The offline demo and core tests do not need it.

```bash
python -m pip install -r backend/requirements-shap.txt
```

Set `ENABLE_SHAP=true` only in an environment where its native imports work. This optional path was not validated in the current environment. Explanations concern one fitted base estimator, not the calibrated ensemble output.

## Tests

```bash
python -m pytest backend/tests -q
# From repository root:
# npm test
```

The tests cover absence/unknown encoding, legacy-model refusal, unavailable models, local access checks, expiry, offline fixtures and existing rule/report regressions. No clinical quality, live-provider behaviour or patient follow-up is established.
