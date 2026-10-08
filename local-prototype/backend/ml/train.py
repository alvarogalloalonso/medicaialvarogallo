"""Reproducible experimental evaluation. No invented disease labels."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, log_loss
import sklearn, xgboost
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import MODELS_DIR
from schemas.medical import BAYES_FEATURE_KEYS
from ml.features import FEATURE_SCHEMA, training_frame
from ml.naive_bayes import SpecialtyClassifier
from ml.gradient_boosting import DiseasePredictor

DISEASE_TO_SPECIALTY = {
    'Bronchial Asthma': 'respiratorio_cardio',
    'Hypertension ': 'respiratorio_cardio',
    'Tuberculosis': 'respiratorio_cardio',
    'Common Cold': 'respiratorio_cardio',
    'Pneumonia': 'respiratorio_cardio',
    'Heart attack': 'respiratorio_cardio',
    
    'Migraine': 'neurologico',
    'Paralysis (brain hemorrhage)': 'neurologico',
    '(vertigo) Paroymsal  Positional Vertigo': 'neurologico',
    
    'GERD': 'digestivo',
    'Chronic cholestasis': 'digestivo',
    'Peptic ulcer diseae': 'digestivo',
    'Gastroenteritis': 'digestivo',
    'Jaundice': 'digestivo',
    'hepatitis A': 'digestivo',
    'Hepatitis B': 'digestivo',
    'Hepatitis C': 'digestivo',
    'Hepatitis D': 'digestivo',
    'Hepatitis E': 'digestivo',
    'Alcoholic hepatitis': 'digestivo',
    'Dimorphic hemmorhoids(piles)': 'digestivo',
    
    'Urinary tract infection': 'urinario_genital',
    
    'Fungal infection': 'piel_alergia',
    'Allergy': 'piel_alergia',
    'Drug Reaction': 'piel_alergia',
    'Chicken pox': 'piel_alergia',
    'Acne': 'piel_alergia',
    'Psoriasis': 'piel_alergia',
    'Impetigo': 'piel_alergia',
    
    'AIDS': 'general_musculoesqueletico',
    'Diabetes ': 'general_musculoesqueletico',
    'Cervical spondylosis': 'general_musculoesqueletico',
    'Malaria': 'general_musculoesqueletico',
    'Dengue': 'general_musculoesqueletico',
    'Typhoid': 'general_musculoesqueletico',
    'Varicose veins': 'general_musculoesqueletico',
    'Hypothyroidism': 'general_musculoesqueletico',
    'Hyperthyroidism': 'general_musculoesqueletico',
    'Hypoglycemia': 'general_musculoesqueletico',
    'Osteoarthristis': 'general_musculoesqueletico',
    'Arthritis': 'general_musculoesqueletico'
}


def prepare_dataset(path):
    df = pd.read_csv(path).dropna(axis=1, how="all")
    df.columns = df.columns.str.strip()
    expected = set(BAYES_FEATURE_KEYS) | {"prognosis"}
    if set(df.columns) != expected:
        raise ValueError("Dataset columns must exactly match the documented 132 symptoms and prognosis")
    if df.isna().any().any() or not df[BAYES_FEATURE_KEYS].isin([0, 1]).all().all():
        raise ValueError("Symptoms must be non-missing binary values")
    df["prognosis"] = df["prognosis"].str.strip()
    if df["prognosis"].isna().any() or df["prognosis"].eq("").any():
        raise ValueError("Missing disease label")
    if df.groupby(BAYES_FEATURE_KEYS, dropna=False)["prognosis"].nunique().gt(1).any():
        raise ValueError("Identical symptom vectors have conflicting disease labels")
    return df.drop_duplicates(subset=BAYES_FEATURE_KEYS).reset_index(drop=True)


def split_dataset(df, seed):
    counts = df.prognosis.value_counts()
    if counts.min() < 5:
        raise ValueError("At least five distinct symptom patterns per disease are required")
    train, test = train_test_split(df.index.to_numpy(), test_size=0.2, random_state=seed, stratify=df.prognosis)
    return train, test


def evaluate(model, X, y):
    predicted = model.predict(X)
    probabilities = model.predict_proba(X)
    labels = list(model.classes_)
    truth = np.array([[float(value == label) for label in labels] for value in y])
    return {"n_test": len(y), "classification_report": classification_report(y, predicted, output_dict=True, zero_division=0),
            "confusion_labels": [str(x) for x in labels], "confusion_matrix": confusion_matrix(y, predicted, labels=labels).tolist(),
            "log_loss": float(log_loss(y, probabilities, labels=labels)),
            "multiclass_brier_sum": float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True, help="JSON with source, licence, collection_method, zero_semantics")
    parser.add_argument("--output", type=Path, default=MODELS_DIR)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    for key in ("source", "licence", "collection_method", "zero_semantics"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"Metadata missing: {key}")
    if metadata["zero_semantics"] != "unobserved":
        raise ValueError("This experiment treats source zeros as unobserved; use a different protocol for confirmed absences")
    df = prepare_dataset(args.data)
    mapping = {k.strip(): v for k, v in DISEASE_TO_SPECIALTY.items()}
    specialties = df.prognosis.map(mapping)
    if specialties.isna().any():
        raise ValueError("Unmapped disease label; explicitly update the mapping")
    train, test = split_dataset(df, args.seed)
    X = training_frame(df[BAYES_FEATURE_KEYS], seed=args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": metadata, "sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                "feature_schema": FEATURE_SCHEMA, "seed": args.seed, "distinct_rows": len(df),
                "train_indices": train.tolist(), "test_indices": test.tolist(),
                "python": platform.python_version(), "sklearn": sklearn.__version__, "xgboost": xgboost.__version__,
                "augmentation": "Conceal 20% of positive symptoms; all source zeros unobserved",
                "limitations": "Internal pattern holdout only; no clinical validation or live LLM evaluation", "specialists": {}}
    router = SpecialtyClassifier()
    router.train(X.iloc[train], specialties.iloc[train])
    manifest["router"] = evaluate(router.model, X.iloc[test], specialties.iloc[test])
    router.save(args.output / "naive_bayes_router.joblib")
    for spec in specialties.unique():
        artifact = args.output / f"gb_{spec}.joblib"
        # Avoid an old artifact remaining active when this run skips a specialty.
        if artifact.exists():
            artifact.unlink()
        tr = [i for i in train if specialties.iloc[i] == spec]
        te = [i for i in test if specialties.iloc[i] == spec]
        y_train = df.prognosis.iloc[tr]
        if y_train.nunique() < 2 or y_train.value_counts().min() < 3 or not te:
            manifest["specialists"][spec] = {"status": "unavailable", "reason": "Insufficient classes or calibration samples"}
            continue
        predictor = DiseasePredictor(spec)
        predictor.train(X.iloc[tr], y_train)
        y_test = predictor.le.transform(df.prognosis.iloc[te])
        metrics = evaluate(predictor.model, X.iloc[te], y_test)
        metrics["disease_labels"] = predictor.classes_.tolist()
        manifest["specialists"][spec] = {"status": "trained", "oracle_routing_evaluation": metrics}
        predictor.save(artifact)
    # End-to-end routing can fail; report those failures instead of conditioning them away.
    predictions = []
    for i in test:
        spec = router.model.predict(X.iloc[[i]])[0]
        artifact = args.output / f"gb_{spec}.joblib"
        if not artifact.exists():
            predictions.append("UNAVAILABLE")
        else:
            predictor = DiseasePredictor(spec)
            predictor.load(artifact)
            predictions.append(str(predictor.le.inverse_transform(predictor.model.predict(X.iloc[[i]]))[0]))
    manifest["end_to_end"] = classification_report(df.prognosis.iloc[test], predictions, output_dict=True, zero_division=0)
    (args.output / "evaluation.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("Saved artifacts and evaluation.json. These are experimental internal-holdout metrics.")

if __name__ == "__main__":
    main()
