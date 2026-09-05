"""
Production ML service.

Backend:
    raw telemetry JSON
        ↓
    TelemetryMLService
        ↓
    unified AI/ML prediction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.inference.telemetry_inference import TelemetryInference
from src.inference.telemetry_schema import TelemetryPoint


class TelemetryMLService:

    def __init__(
        self,
        anomaly_model_path: str | Path,
        fault_model_path: str | Path,
        rul_model_path: str | Path,
    ) -> None:

        self.inference = TelemetryInference(
            anomaly_model_path=anomaly_model_path,
            fault_model_path=fault_model_path,
            rul_model_path=rul_model_path,
        )

    def predict(
        self,
        telemetry: list[TelemetryPoint],
    ) -> dict[str, Any]:

        if not telemetry:
            raise ValueError(
                "At least one telemetry point is required."
            )

        # Pydantic models → dataframe
        df = pd.DataFrame(
            [point.model_dump() for point in telemetry]
        )

        # Run complete ML pipeline.
        return self.inference.predict(df)

    def predict_dicts(
        self,
        telemetry: list[dict[str, Any]],
    ) -> dict[str, Any]:

        points = [
            TelemetryPoint.model_validate(point)
            for point in telemetry
        ]

        return self.predict(points)