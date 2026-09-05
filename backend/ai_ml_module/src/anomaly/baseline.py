"""
Robust z-score baseline: fit median + MAD (median absolute deviation) per
feature on NORMAL data only, then score new rows by how many robust-MADs
away they are. Robust to outliers in the fit set (unlike mean/std), which
matters since even "normal" missions have natural sensor noise.

This is intentionally simple - it's Phase 3's starting point, not the final
detector. Isolation Forest (isolation_forest.py) builds on top of this.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib


class RobustZScoreDetector:
    def __init__(self, feature_threshold: float = 3.5, score_threshold: float = 0.5):
        self.feature_threshold = feature_threshold
        self.score_threshold = score_threshold
        self.median_: pd.Series | None = None
        self.mad_: pd.Series | None = None
        self.feature_cols_: list[str] | None = None

    def fit(self, df: pd.DataFrame, feature_cols: list[str]) -> "RobustZScoreDetector":
        self.feature_cols_ = feature_cols
        X = df[feature_cols]
        self.median_ = X.median()
        mad = (X - self.median_).abs().median()
        # avoid divide-by-zero for constant features
        self.mad_ = mad.replace(0, 1e-6)
        return self

    def _robust_z(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.feature_cols_]
        # 0.6745 makes MAD consistent with std for normally distributed data
        return (X - self.median_).abs() / (self.mad_ * 1.4826) * 0.6745 / 0.6745

    def score(self, df: pd.DataFrame) -> np.ndarray:
        z = self._robust_z(df)
        # aggregate across features: mean of the top-5 most deviant features
        # per row (more robust than "max", less diluted than "mean over all")
        top_k = np.sort(z.to_numpy(), axis=1)[:, -5:]
        agg_z = top_k.mean(axis=1)
        # squash to 0-1: score approaches 1 as agg_z grows past ~2x threshold
        score = 1 - np.exp(-agg_z / (2 * self.feature_threshold))
        return np.clip(score, 0, 1)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (self.score(df) >= self.score_threshold).astype(int)

    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "RobustZScoreDetector":
        return joblib.load(path)