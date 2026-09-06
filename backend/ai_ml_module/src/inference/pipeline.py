"""
Unified AI/ML inference engine for SIH PS54.

Combines:
    - ML-based anomaly detection
    - ML-based multi-label fault classification
    - deterministic health / degradation scoring
    - formula-based remaining useful life (RUL) estimation

Input:
    An ALREADY FEATURED telemetry dataframe.

The RUL calculation is deterministic and does not use a trained
RUL regression model or rul_regressor.joblib.
"""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.degradation.degradation_score import score_health
from src.faults.predictor import top_fault_per_row
from src.rul.formula import (
    apply_rul_gate,
    estimate_rul_seconds,
)


class UnifiedInferenceEngine:
    """
    Unified production inference engine.

    Models used:
        - anomaly_detector.joblib
        - fault_classifier.joblib

    RUL:
        - deterministic formula from current health/degradation state
        - no ML RUL model
    """

    def __init__(
        self,
        anomaly_model_path: str,
        fault_model_path: str,
    ) -> None:

        # ------------------------------------------------------------
        # Load anomaly model
        # ------------------------------------------------------------

        self.anomaly_detector = joblib.load(
            anomaly_model_path
        )

        # ------------------------------------------------------------
        # Load fault classifier
        # ------------------------------------------------------------

        self.fault_classifier = joblib.load(
            fault_model_path
        )

        # ------------------------------------------------------------
        # Recover the exact feature order used during fault training
        # ------------------------------------------------------------

        if not hasattr(
            self.fault_classifier,
            "feature_cols_",
        ):
            raise TypeError(
                "Loaded fault classifier does not expose "
                "'feature_cols_'."
            )

        self.fault_feature_columns = list(
            self.fault_classifier.feature_cols_
        )

        # ------------------------------------------------------------
        # Validate anomaly model
        # ------------------------------------------------------------

        if not hasattr(
            self.anomaly_detector,
            "score",
        ):
            raise TypeError(
                "Loaded anomaly model does not expose "
                "'score(df)'."
            )

    # ==================================================================
    # INPUT CLEANING
    # ==================================================================

    @staticmethod
    def _clean_frame(
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Clean inference dataframe without changing its schema.
        """

        if df is None:
            raise ValueError(
                "featured_df is None."
            )

        if df.empty:
            raise ValueError(
                "featured_df is empty."
            )

        return (
            df.copy()
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .reset_index(drop=True)
        )

    # ==================================================================
    # FAULT MODEL INPUT
    # ==================================================================

    def _fault_input(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build the exact input dataframe expected by the trained
        multi-label fault classifier.
        """

        missing = [
            column
            for column in self.fault_feature_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing fault-model features: "
                f"{missing[:20]}"
            )

        return (
            df[self.fault_feature_columns]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
            .fillna(0.0)
        )

    # ==================================================================
    # MAIN PREDICTION
    # ==================================================================

    def predict(
        self,
        featured_df: pd.DataFrame,
        rul_gate_fault_probability: float = 0.30,
    ) -> pd.DataFrame:
        """
        Run the complete AI/ML + deterministic RUL pipeline.

        Parameters
        ----------
        featured_df:
            Dataframe that has already passed through feature engineering.

        rul_gate_fault_probability:
            Minimum top-fault probability required to expose the
            formula-based RUL estimate independently of the health gate.
        """

        df = self._clean_frame(
            featured_df
        )

        # ============================================================
        # 1. ANOMALY DETECTION
        # ============================================================

        anomaly_result = (
            self.anomaly_detector.score(df)
        )

        if "anomaly_score" not in anomaly_result:
            raise KeyError(
                "Anomaly model result does not contain "
                "'anomaly_score'."
            )

        anomaly_score = pd.Series(
            anomaly_result["anomaly_score"],
            index=df.index,
            dtype=float,
        ).clip(
            0.0,
            1.0,
        )

        # ============================================================
        # 2. MULTI-LABEL FAULT CLASSIFICATION
        # ============================================================

        fault_input = self._fault_input(
            df
        )

        fault_proba = (
            self.fault_classifier.predict_proba(
                fault_input
            )
        )

        fault_view = (
            top_fault_per_row(
                fault_proba
            )
            .reset_index(drop=True)
        )

        # ============================================================
        # 3. HEALTH / DEGRADATION SCORE
        # ============================================================

        health = (
            score_health(
                df,
                anomaly_score,
                fault_proba,
            )
            .reset_index(drop=True)
        )

        # Make sure the expected health column exists.
        if "health_score" not in health.columns:
            raise KeyError(
                "Health calculation did not return "
                "'health_score'."
            )

        # ============================================================
        # 4. FORMULA-BASED RUL
        # ============================================================

        raw_rul = estimate_rul_seconds(
            df,
            health_score=health["health_score"],
            anomaly_score=anomaly_score,
            fault_probability=(
                fault_view[
                    "top_fault_probability"
                ]
            ),
        )

        # ============================================================
        # 5. RUL GATING
        # ============================================================
        #
        # RUL is exposed only when the engine shows meaningful
        # degradation or a sufficiently strong fault indication.
        #
        # This avoids presenting an arbitrary RUL value for a
        # healthy engine.
        #

        predicted_rul, rul_status = apply_rul_gate(
            raw_rul,
            health_score=health["health_score"],
            fault_probability=(
                fault_view[
                    "top_fault_probability"
                ]
            ),
            health_threshold=60.0,
            fault_threshold=(
                rul_gate_fault_probability
            ),
        )

        # ============================================================
        # 6. STANDARDIZED OUTPUT
        # ============================================================

        return pd.DataFrame(
            {
                "timestamp_s": (
                    df["timestamp_s"].to_numpy()
                    if "timestamp_s" in df.columns
                    else np.full(
                        len(df),
                        np.nan,
                    )
                ),

                "mission_id": (
                    df["mission_id"].to_numpy()
                    if "mission_id" in df.columns
                    else np.full(
                        len(df),
                        None,
                        dtype=object,
                    )
                ),

                "engine_id": (
                    df["engine_id"].to_numpy()
                    if "engine_id" in df.columns
                    else np.full(
                        len(df),
                        None,
                        dtype=object,
                    )
                ),

                # ------------------------------
                # Anomaly
                # ------------------------------

                "anomaly_score": (
                    anomaly_score.to_numpy()
                ),

                # ------------------------------
                # Fault
                # ------------------------------

                "top_fault": (
                    fault_view[
                        "top_fault"
                    ].to_numpy()
                ),

                "fault_probability": (
                    fault_view[
                        "top_fault_probability"
                    ].to_numpy()
                ),

                "fault_severity": (
                    fault_view[
                        "severity"
                    ].to_numpy()
                ),

                # ------------------------------
                # Health
                # ------------------------------

                "health_score": (
                    health[
                        "health_score"
                    ].to_numpy()
                ),

                "health_status": (
                    health[
                        "health_status"
                    ].to_numpy()
                ),

                # ------------------------------
                # Formula RUL
                # ------------------------------

                "predicted_rul_seconds": (
                    predicted_rul
                ),

                "predicted_rul_minutes": (
                    predicted_rul / 60.0
                ),

                "rul_status": (
                    rul_status
                ),
            }
        )

    # ==================================================================
    # SINGLE-ROW PREDICTION
    # ==================================================================

    def predict_row(
        self,
        featured_row: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convenience wrapper for one telemetry point.
        """

        result = self.predict(
            pd.DataFrame(
                [featured_row]
            )
        )

        return result.iloc[0].to_dict()