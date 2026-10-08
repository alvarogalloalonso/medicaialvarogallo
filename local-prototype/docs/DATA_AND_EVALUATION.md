# Data and evaluation protocol

## Historical provenance

The author recalls synthetic-data experiments and poor model behaviour. The original archive contained a synthetic CSV (11,400 rows, 122 columns, 7,201 distinct rows) and a public-labelled symptom CSV (4,920 rows, 134 columns, 304 distinct rows). Neither an exact historical training run nor the public-labelled file's source, licence or real-patient origin was verified. These are descriptive counts, not performance evidence. CSVs and historical artifacts are excluded.

## Revised protocol

1. Supply a documented permitted dataset and metadata (`source`, `licence`, `collection_method`, `zero_semantics`). Record its SHA-256 hash and package versions.
2. Require exactly the documented symptom columns and label. Reject missing/nonbinary values and conflicting labels for identical symptom vectors. Remove exact duplicate symptom vectors before splitting.
3. Save a reproducible disease-stratified 80/20 partition before any model fit. Labels with fewer than five distinct patterns fail explicitly. Related/near-duplicate patterns still require a separate provenance audit; exact deduplication alone cannot establish independent patients.
4. Encode two bits per symptom: presence and observed state. Unknown=(0,0), absent=(0,1), present=(1,1). Historical v1 models are rejected.
5. For this symptom-pattern experiment, source zeros are unobserved. Conceal 20% of positive symptoms with a fixed seed to simulate partial input. This simulation is not evidence about actual interviews and provides no real negative-symptom training examples. A dataset with confirmed denials needs its own protocol.
6. Fit routing and specialist models on training rows only. Sigmoid calibration uses three folds within the training partition. Skip single-class or insufficient specialists; never add fake disease labels. Remove obsolete specialist artifacts when a run skips them.
7. Record held-out precision/recall/F1, confusion matrices, log loss and the sum-form multiclass Brier score. Specialist metrics assume correct routing and are labelled accordingly. Also record end-to-end routing/classification failures as `UNAVAILABLE`, rather than dropping them.

`evaluation.json` contains partitions, versions, source metadata and metrics. Training-set reports are debugging output only, never model quality evidence. The script trusts supplied provenance metadata; it cannot verify a licence or patient-level independence automatically.

## Separate extraction evaluation

`backend/evaluate_extraction.py` evaluates the configured extraction agent on fictional, manually labelled conversations in `backend/examples/extraction_cases.json`. It records feature-state mismatches separately from classifier metrics. Running it can contact the configured provider. The initial fixtures are a small regression set, not a benchmark of medical accuracy; extend them with paraphrases, negations, corrections, ambiguous statements and out-of-scope inputs.

## What was actually run

Only a fictional structural training fixture was used to verify the CLI, artifact writing, holdout report generation and single-class refusal. No medical dataset was retrained and no model accuracy figures are claimed. Live extraction evaluation was not run.
