"""
Production-facing telemetry inference adapter.

Backend sends RAW telemetry.

RAW TELEMETRY
      ↓
Digital Twin expected values
      ↓
Feature engineering
      ↓
Unified AI/ML inference
      ↓
Backend-friendly JSON
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.features.feature_pipeline import build_features
from src.inference.pipeline import UnifiedInferenceEngine


class TelemetryInference:
    """
    Single production entry point for backend integration.

    Backend:
        RAW TELEMETRY -> this class

    AIML:
        RAW TELEMETRY
            -> expected values
            -> residuals
            -> features
            -> anomaly model
            -> fault model
            -> health score
            -> RUL model
    """

    def __init__(
        self,
        anomaly_model_path: str | Path,
        fault_model_path: str | Path,
        rul_model_path: str | Path,
    ) -> None:

        self.engine = UnifiedInferenceEngine(
            anomaly_model_path=anomaly_model_path,
            fault_model_path=fault_model_path,
            rul_model_path=rul_model_path,
        )

    @staticmethod
    def _json_safe(value: Any) -> Any:

        if value is None:
            return None

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):

            if np.isnan(value) or np.isinf(value):
                return None

            return float(value)

        if isinstance(value, float):

            if np.isnan(value) or np.isinf(value):
                return None

            return value

        if isinstance(value, np.ndarray):
            return value.tolist()

        if pd.isna(value):
            return None

        return value

    @staticmethod
    def _prepare_dataframe(
        telemetry_df: pd.DataFrame,
    ) -> pd.DataFrame:

        if telemetry_df is None:
            raise ValueError(
                "telemetry_df is None."
            )

        if telemetry_df.empty:
            raise ValueError(
                "telemetry_df is empty."
            )

        df = telemetry_df.copy()

        # ------------------------------------------------------------
        # Backend may omit these because they can be generated here.
        # ------------------------------------------------------------

        if "timestamp_s" not in df.columns:
            df["timestamp_s"] = np.arange(
                len(df),
                dtype=float,
            )

        if "mission_id" not in df.columns:
            df["mission_id"] = "API-MISSION"

        if "engine_id" not in df.columns:
            df["engine_id"] = "API-ENGINE"

        return df

    def predict(
        self,
        telemetry_df: pd.DataFrame,
    ) -> dict[str, Any]:

        df = self._prepare_dataframe(
            telemetry_df
        )

        # ------------------------------------------------------------
        # RAW TELEMETRY -> FEATURES
        # ------------------------------------------------------------

        featured_df = build_features(df)

        # ------------------------------------------------------------
        # FEATURES -> AI/ML
        # ------------------------------------------------------------

        predictions = self.engine.predict(
            featured_df
        )

        # ------------------------------------------------------------
        # Latest/current state
        # ------------------------------------------------------------

        latest = predictions.iloc[-1].to_dict()

        return {
            key: self._json_safe(value)
            for key, value in latest.items()
        }

    def predict_trajectory(
        self,
        telemetry_df: pd.DataFrame,
    ) -> list[dict[str, Any]]:

        df = self._prepare_dataframe(
            telemetry_df
        )

        # ------------------------------------------------------------
        # RAW TELEMETRY -> FEATURES
        # ------------------------------------------------------------

        featured_df = build_features(df)

        # ------------------------------------------------------------
        # FEATURES -> AI/ML
        # ------------------------------------------------------------

        predictions = self.engine.predict(
            featured_df
        )

        records = predictions.to_dict(
            orient="records"
        )

        return [
            {
                key: self._json_safe(value)
                for key, value in record.items()
            }
            for record in records
        ]