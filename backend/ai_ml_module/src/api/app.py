from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.inference.telemetry_inference import TelemetryInference


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

ANOMALY_MODEL = ROOT / "models" / "anomaly" / "anomaly_detector.joblib"
FAULT_MODEL = ROOT / "models" / "faults" / "fault_classifier.joblib"
RUL_MODEL = ROOT / "models" / "rul" / "rul_regressor.joblib"


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="AIML Engine Health API",
    description=(
        "AI/ML inference service for engine telemetry. "
        "Accepts raw telemetry and returns anomaly, fault, "
        "health and RUL predictions."
    ),
    version="1.0.0",
)


# ============================================================
# MODEL LOADING
# ============================================================

try:
    inference = TelemetryInference(
        anomaly_model_path=ANOMALY_MODEL,
        fault_model_path=FAULT_MODEL,
        rul_model_path=RUL_MODEL,
    )

    MODEL_STATUS = "loaded"

except Exception as exc:
    inference = None
    MODEL_STATUS = f"error: {exc}"


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class TelemetryPoint(BaseModel):
    timestamp_s: float

    mission_id: str
    engine_id: str

    throttle_pct: float
    altitude_m: float
    ambient_temperature_c: float

    rpm: float
    cht_c: float
    egt_c: float

    oil_pressure_kpa: float
    oil_temperature_c: float

    fuel_flow_lph: float
    vibration_g: float

    alternator_voltage_v: float
    battery_voltage_v: float

    injection_timing_deg: float


class PredictionRequest(BaseModel):
    mission_id: str
    engine_id: str

    telemetry: list[TelemetryPoint] = Field(
        ...,
        min_length=1,
    )


# ============================================================
# HEALTH / ROOT
# ============================================================

@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "AIML Engine Health API",
        "version": "1.0.0",
        "status": "running",
        "model_status": MODEL_STATUS,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if inference is not None else "error",
        "service": "aiml-engine-health",
        "models": MODEL_STATUS,
    }


# ============================================================
# MAIN INFERENCE ENDPOINT
# ============================================================

@app.post("/api/v1/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:

    if inference is None:
        raise HTTPException(
            status_code=503,
            detail=f"AI/ML models are not available: {MODEL_STATUS}",
        )

    try:

        records = [
            point.model_dump()
            for point in request.telemetry
        ]

        df = pd.DataFrame(records)

        # Ensure backend-level identifiers are consistent.
        df["mission_id"] = request.mission_id
        df["engine_id"] = request.engine_id

        result = inference.predict(df)

        return {
            "success": True,
            "mission_id": request.mission_id,
            "engine_id": request.engine_id,
            "prediction": result,
            "telemetry_points": len(df),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# TRAJECTORY ENDPOINT
# ============================================================

@app.post("/api/v1/predict/trajectory")
def predict_trajectory(
    request: PredictionRequest,
) -> dict[str, Any]:

    if inference is None:
        raise HTTPException(
            status_code=503,
            detail=f"AI/ML models are not available: {MODEL_STATUS}",
        )

    try:

        records = [
            point.model_dump()
            for point in request.telemetry
        ]

        df = pd.DataFrame(records)

        df["mission_id"] = request.mission_id
        df["engine_id"] = request.engine_id

        result = inference.predict_trajectory(df)

        return {
            "success": True,
            "mission_id": request.mission_id,
            "engine_id": request.engine_id,
            "telemetry_points": len(df),
            "predictions": result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )