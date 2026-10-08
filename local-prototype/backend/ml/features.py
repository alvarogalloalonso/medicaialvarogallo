"""Versioned symptom encoding: presence and observation are separate features."""
from schemas.medical import BAYES_FEATURE_KEYS
import pandas as pd

FEATURE_SCHEMA = "presence-observed-v2"
FEATURE_COLUMNS = list(BAYES_FEATURE_KEYS) + [f"{k}__observed" for k in BAYES_FEATURE_KEYS]

def encode_features(features):
    invalid = {k: v for k, v in features.items() if k in BAYES_FEATURE_KEYS and v not in ("present", "absent", "unknown")}
    if invalid:
        raise ValueError("Invalid categorical symptom state")
    return {**{k: int(features.get(k, "unknown") == "present") for k in BAYES_FEATURE_KEYS},
            **{f"{k}__observed": int(features.get(k, "unknown") in ("present", "absent")) for k in BAYES_FEATURE_KEYS}}

def feature_frame(features):
    return pd.DataFrame([encode_features(features)], columns=FEATURE_COLUMNS)

def training_frame(raw, seed=42):
    """Simulate partial interviews; zeros in the source are not confirmed denials.

    Randomly conceal present symptoms and leave all source zeros unobserved.
    This is an experimental augmentation, not evidence about real interviews.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    present = raw.loc[:, BAYES_FEATURE_KEYS].astype(int)
    observed = (present.eq(1) & (rng.random(present.shape) >= 0.2)).astype(int)
    values = present * observed
    mask = observed.rename(columns=lambda k: f"{k}__observed")
    return pd.concat([values, mask], axis=1).loc[:, FEATURE_COLUMNS]
