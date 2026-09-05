"""
Unified AI/ML inference engine for SIH PS54.
Combines anomaly detection, multi-label fault classification,
deterministic health index, and RUL estimation.
Input is an ALREADY FEATURED dataframe.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.degradation.degradation_score import score_health
from src.faults.predictor import top_fault_per_row
from src.rul.rul_model import RULRegressor


class UnifiedInferenceEngine:
    def __init__(
        self,
        anomaly_model_path: str | Path,
        fault_model_path: str | Path,
        rul_model_path: str | Path,
    ) -> None:
        self.anomaly_detector = joblib.load(anomaly_model_path)
        self.fault_classifier = joblib.load(fault_model_path)
        self.rul_model = RULRegressor.load(rul_model_path)

        self.fault_feature_columns = list(
            self.fault_classifier.feature_cols_
        )
        self.rul_feature_columns = list(
            self.rul_model.feature_columns_
        )

        if not hasattr(self.anomaly_detector, "score"):
            raise TypeError(
                "Loaded anomaly model does not expose score(df)."
            )

    @staticmethod
    def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
        return df.copy().replace([np.inf, -np.inf], np.nan).reset_index(drop=True)

    def _fault_input(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in self.fault_feature_columns if c not in df.columns]
        if missing:
            raise ValueError(f"Missing fault-model features: {missing[:20]}")
        return (
            df[self.fault_feature_columns]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
        )

    def predict(
        self,
        featured_df: pd.DataFrame,
        rul_gate_anomaly: float = 0.50,
        rul_gate_fault_probability: float = 0.30,
    ) -> pd.DataFrame:
        if featured_df.empty:
            raise ValueError("featured_df is empty.")

        df = self._clean_frame(featured_df)

        anomaly_result = self.anomaly_detector.score(df)
        if "anomaly_score" not in anomaly_result:
            raise KeyError(
                "Anomaly model result does not contain 'anomaly_score'."
            )

        anomaly_score = pd.Series(
            anomaly_result["anomaly_score"],
            index=df.index,
            dtype=float,
        ).clip(0.0, 1.0)

        fault_proba = self.fault_classifier.predict_proba(
            self._fault_input(df)
        )
        fault_view = top_fault_per_row(fault_proba).reset_index(drop=True)

        health = score_health(
            df,
            anomaly_score,
            fault_proba,
        ).reset_index(drop=True)

        rul_input = (
            df[self.rul_feature_columns]
            .apply(pd.to_numeric, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        raw_rul = np.maximum(
            self.rul_model.model.predict(rul_input),
            0.0,
        )

        # Do not show an arbitrary RUL estimate for clearly healthy rows.
        gate = (
            (anomaly_score >= rul_gate_anomaly)
            | (
                fault_view["top_fault_probability"]
                >= rul_gate_fault_probability
            )
            | (health["health_status"] != "HEALTHY")
        )

        predicted_rul = np.where(gate, raw_rul, np.nan)

        rul_status = np.where(
            ~gate,
            "NOT_APPLICABLE",
            np.where(
                predicted_rul <= 10.0,
                "CRITICAL",
                np.where(
                    predicted_rul <= 30.0,
                    "WARNING",
                    "NORMAL",
                ),
            ),
        )

        return pd.DataFrame(
            {
                "timestamp_s": (
                    df["timestamp_s"].values
                    if "timestamp_s" in df.columns else np.nan
                ),
                "mission_id": (
                    df["mission_id"].values
                    if "mission_id" in df.columns else None
                ),
                "engine_id": (
                    df["engine_id"].values
                    if "engine_id" in df.columns else None
                ),
                "anomaly_score": anomaly_score.values,
                "top_fault": fault_view["top_fault"].values,
                "fault_probability": (
                    fault_view["top_fault_probability"].values
                ),
                "fault_severity": fault_view["severity"].values,
                "health_score": health["health_score"].values,
                "health_status": health["health_status"].values,
                "predicted_rul_seconds": predicted_rul,
                "predicted_rul_minutes": predicted_rul / 60.0,
                "rul_status": rul_status,
            }
        )

    def predict_row(self, featured_row: dict[str, Any]) -> dict[str, Any]:
        return self.predict(pd.DataFrame([featured_row])).iloc[0].to_dict()
