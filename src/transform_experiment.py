"""Exercise 4: can a target transformation let the tree compete?

Not part of `make all`; committed reports/metrics.json is the untransformed
pipeline. Validation is used to choose; test is scored once, with --test.

Run: python -m src.transform_experiment [--test]
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import PROCESSED, TARGET
from src.features import feature_columns
from src.train import temporal_split


def hgb():
    return HistGradientBoostingRegressor(random_state=0, max_iter=300)


def ridge():
    return make_pipeline(StandardScaler(), Ridge(alpha=1.0))


# name -> (forward(y, part), inverse(pred, part)); `part` carries only
# information known on the day (cnt_roll_7 is built from strictly earlier days).
TRANSFORMS = {
    "identity": (lambda y, p: y, lambda z, p: z),
    "log": (lambda y, p: np.log(y), lambda z, p: np.exp(z)),
    "ratio_to_roll7": (lambda y, p: y / p.cnt_roll_7, lambda z, p: z * p.cnt_roll_7.to_numpy()),
}


def score(make_model, name, train, part, cols):
    fwd, inv = TRANSFORMS[name]
    m = make_model().fit(train[cols], fwd(train[TARGET], train))
    pred = inv(m.predict(part[cols]), part)
    return round(float(r2_score(part[TARGET], pred)), 4), round(float(mean_absolute_error(part[TARGET], pred)), 1)


if __name__ == "__main__":
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    part, label = (test, "TEST") if "--test" in sys.argv else (valid, "VALID")
    names = ["ratio_to_roll7"] if "--test" in sys.argv else list(TRANSFORMS)
    for mname, mk in [("hgb", hgb), ("ridge", ridge)]:
        for t in names:
            r2, mae = score(mk, t, train, part, cols)
            print(f"{label} {mname:6s} target={t:15s} R2={r2:7.4f} MAE={mae}")
