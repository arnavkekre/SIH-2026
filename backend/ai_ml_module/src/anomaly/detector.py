"""
Ensemble wrapper: final anomaly score = max(zscore_score, isolation_forest_score).
Using max (not average) is deliberate - we want to flag a row if EITHER
detector is confident, since they catch different failure modes
(z-score = single-feature extreme, IF = joint multivariate implausibility).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib

from src.anomaly.baseline import RobustZScoreDetector
from src.anomaly.isolation_forest import IsolationForestDetector


class AnomalyDetector:
    def __init__(self, feature_threshold: float = 3.5, if_contamination: float = 0.05,
                 detection_threshold: float = 0.5):
        self.zscore = RobustZScoreDetector(feature_threshold=feature_threshold)
        self.iforest = IsolationForestDetector(contamination=if_contamination)
        self.detection_threshold = detection_threshold
        self.feature_cols_: list[str] | None = None

    def fit(self, normal_df: pd.DataFrame, feature_cols: list[str]) -> "AnomalyDetector":
        """Fit on NORMAL rows only - standard unsupervised anomaly detection practice."""
        self.feature_cols_ = feature_cols
        self.zscore.fit(normal_df, feature_cols)
        self.iforest.fit(normal_df, feature_cols)
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        z_score = self.zscore.score(df)
        if_score = self.iforest.score(df)
        combined = np.maximum(z_score, if_score)
        return pd.DataFrame({
            "zscore_anomaly_score": z_score,
            "if_anomaly_score": if_score,
            "anomaly_score": combined,
            "anomaly_detected": (combined >= self.detection_threshold).astype(int),
        }, index=df.index)

    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "AnomalyDetector":
        return joblib.load(path)