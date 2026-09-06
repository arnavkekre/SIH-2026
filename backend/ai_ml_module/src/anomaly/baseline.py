"""
Robust z-score baseline.

Fits median + MAD for each anomaly feature using NORMAL training data only,
then scores new telemetry rows by robust deviation from that baseline.

The detector is intentionally simple and deterministic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import joblib


class RobustZScoreDetector:
    def __init__(
        self,
        feature_threshold: float = 3.5,
        score_threshold: float = 0.5,
    ):
        self.feature_threshold = float(feature_threshold)
        self.score_threshold = float(score_threshold)

        self.median_: pd.Series | None = None
        self.mad_: pd.Series | None = None
        self.feature_cols_: list[str] | None = None

    def fit(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
    ) -> "RobustZScoreDetector":

        self.feature_cols_ = list(feature_cols)

        X = (
            df[self.feature_cols_]
            .apply(pd.to_numeric, errors="coerce")
        )

        if X.empty:
            raise ValueError(
                "Cannot fit RobustZScoreDetector on an empty dataframe."
            )

        self.median_ = X.median()

        mad = (
            X
            .sub(self.median_, axis="columns")
            .abs()
            .median()
        )

        # Avoid divide-by-zero for constant features.
        self.mad_ = (
            mad
            .replace(
                [0.0, -0.0],
                1e-6,
            )
            .fillna(1e-6)
        )

        return self

    def _validate_fitted(self) -> None:
        if (
            self.feature_cols_ is None
            or self.median_ is None
            or self.mad_ is None
        ):
            raise RuntimeError(
                "RobustZScoreDetector has not been fitted."
            )

    def _robust_z(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        self._validate_fitted()

        missing = [
            col
            for col in self.feature_cols_
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing anomaly-model features: "
                f"{missing[:20]}"
            )

        X = (
            df[self.feature_cols_]
            .apply(pd.to_numeric, errors="coerce")
        )

        # Invalid runtime values become NaN, then contribute zero
        # deviation instead of crashing numerical operations.
        X = X.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        X = X.fillna(
            self.median_
        )

        z = (
            X
            .sub(self.median_, axis="columns")
            .abs()
            .div(
                self.mad_ * 1.4826,
                axis="columns",
            )
        )

        return z.astype(float)

    def score(
        self,
        df: pd.DataFrame,
    ) -> np.ndarray:

        z = self._robust_z(df)

        # Aggregate across the five most deviant features.
        # This prevents one noisy sensor from dominating the score
        # while avoiding dilution across all features.
        z_values = z.to_numpy(
            dtype=np.float64,
        )

        if z_values.ndim != 2:
            raise ValueError(
                "Anomaly feature matrix must be 2-dimensional."
            )

        k = min(
            5,
            z_values.shape[1],
        )

        top_k = np.partition(
            z_values,
            kth=z_values.shape[1] - k,
            axis=1,
        )[:, -k:]

        agg_z = np.mean(
            top_k,
            axis=1,
            dtype=np.float64,
        )

        # Squash robust deviation into [0, 1].
        score = (
            1.0
            - np.exp(
                -agg_z
                / (
                    2.0
                    * self.feature_threshold
                )
            )
        )

        return np.clip(
            np.asarray(
                score,
                dtype=np.float64,
            ),
            0.0,
            1.0,
        )

    def predict(
        self,
        df: pd.DataFrame,
    ) -> np.ndarray:

        return (
            self.score(df)
            >= self.score_threshold
        ).astype(int)

    def save(
        self,
        path: str,
    ) -> None:

        joblib.dump(
            self,
            path,
        )

    @staticmethod
    def load(
        path: str,
    ) -> "RobustZScoreDetector":

        return joblib.load(path)