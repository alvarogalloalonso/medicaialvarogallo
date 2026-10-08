# Verification — 8 October 2026

Completed locally before publication:

- 31 Python regression tests passed (Python 3.12).
- 2 JavaScript DOM tests passed: hostile symptom fields, generated reports, user chat and streamed text remain text and create no executable HTML nodes.
- React production build completed; TypeScript application check passed.
- Revised training CLI completed on a temporary fictional fixture, produced a held-out evaluation manifest and kept the single-class urinary specialist unavailable. The fixture and its artifacts are not published.
- Offline demo tests confirmed no extraction/report LLM calls, all three fixed-case flows, report retrieval, expiration and rejection of remote clients/untrusted origins.

Native SHAP imports caused a process-level bus error in this environment even with pinned native dependencies. SHAP is now an optional, disabled-by-default extra and is not imported by the demo or core tests. The optional explanation path has not been revalidated here.

Not verified: live Ollama/Gemini/OpenAI conversations, the hosted transcription deployment, historical models, medical accuracy or clinical benefit. No external service was deployed. Tests validate software behaviour, not clinical reliability.
