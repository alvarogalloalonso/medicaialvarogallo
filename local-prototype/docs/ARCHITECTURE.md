# Architecture

Two applications are kept separate: the root React presentation and `local-prototype/` Python application.

## Default offline demo

Browser selects a fixed fictional case → FastAPI constructs known symptom states → experimental deterministic rules run with ML disabled → structured report is retained in memory → text-only report viewer. No LLM, training artifact or external AI call is used.

## Experimental conversation

WebSocket interview → conversation agent → extraction agent → categorical symptom states → versioned presence/observed encoding → available Naive Bayes router/XGBoost specialist → report agent. Rules are evaluated separately and can suppress ML. Missing/incompatible models yield explicit unavailable/degraded states.

Optional SHAP explains one calibrated fold's fitted base estimator. It is not an explanation of the ensemble's final calibrated probability. Urgency is an experimental rule output; arbitrary classifier probability no longer increases it.

## Boundaries

HTTP and WebSocket clients must be loopback; browser origins and Host names are checked. Sessions use full UUIDs, bounded storage and time-based expiry. This is not a production authentication design. Hosted providers transmit configured fictional conversation content externally. All report and chat content is rendered as text; Markdown/HTML output is not executed.
