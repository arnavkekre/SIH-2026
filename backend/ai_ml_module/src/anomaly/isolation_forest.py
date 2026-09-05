"""
Isolation Forest catches multivariate anomalies the z-score baseline misses
(e.g. a combination of individually-normal-looking readings that's jointly
implausible). Trained unsupervised on NORMAL data only, per standard
anomaly-detection convention - it never sees fault labels during fit.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05, score_threshold: float = 0.5,
                 n_estimators: int = 200, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self.score_threshold = score_threshold
        self.feature_cols_: list[str] | None = None
        self._score_min = None
        self._score_max = None

    def fit(self, df: pd.DataFrame, feature_cols: list[str]) -> "IsolationForestDetector":
        self.feature_cols_ = feature_cols
        X = df[feature_cols].to_numpy()
        self.model.fit(X)
        # calibrate min/max on the fit set so score() can normalize to 0-1
        raw = self.model.decision_function(X)
        self._score_min, self._score_max = raw.min(), raw.max()
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_cols_].to_numpy()
        raw = self.model.decision_function(X)  # higher = more normal
        span = max(1e-9, self._score_max - self._score_min)
        normalized = (raw - self._score_min) / span  # 0 (anomalous) - 1 (normal), roughly
        anomaly_score = 1 - np.clip(normalized, 0, 1)
        return anomaly_score

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (self.score(df) >= self.score_threshold).astype(int)

    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "IsolationForestDetector":
        return joblib.load(path)