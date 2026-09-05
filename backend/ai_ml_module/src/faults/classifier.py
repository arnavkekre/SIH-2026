"""
One independent XGBoost binary classifier per fault code (see fault_labels.py
for why multi-label, not multi-class). Uses scale_pos_weight per fault to
handle class imbalance honestly rather than pretending the classes are
balanced.

Per the original spec: start with XGBoost/Random Forest using raw + rolling
+ digital-twin-residual features BEFORE reaching for an LSTM/GRU.
"""
from __future__ import annotations
import pandas as pd
import joblib
from xgboost import XGBClassifier

from src.faults.fault_labels import FAULT_CODES


class MultiLabelFaultClassifier:
    def __init__(self, fault_codes: list[str] = FAULT_CODES, **xgb_kwargs):
        self.fault_codes = fault_codes
        self.models: dict[str, XGBClassifier] = {}
        self.feature_cols_: list[str] | None = None
        self.xgb_kwargs = {
            "n_estimators": 200,
            "max_depth": 4,
            "learning_rate": 0.1,
            "eval_metric": "logloss",
            "random_state": 42,
            **xgb_kwargs,
        }

    def fit(self, X: pd.DataFrame, Y: pd.DataFrame) -> "MultiLabelFaultClassifier":
        self.feature_cols_ = list(X.columns)
        for code in self.fault_codes:
            y = Y[code]
            pos, neg = y.sum(), len(y) - y.sum()
            scale_pos_weight = neg / max(pos, 1)
            model = XGBClassifier(scale_pos_weight=scale_pos_weight, **self.xgb_kwargs)
            model.fit(X, y)
            self.models[code] = model
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.feature_cols_]
        out = {code: self.models[code].predict_proba(X)[:, 1] for code in self.fault_codes}
        return pd.DataFrame(out, index=X.index)

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
        return (self.predict_proba(X) >= threshold).astype(int)

    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "MultiLabelFaultClassifier":
        return joblib.load(path)