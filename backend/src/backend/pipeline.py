from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np


# ============================================================
# Paths
# ============================================================

# pipeline.py
#     backend/src/backend/pipeline.py
#
# parents[0] = backend/src/backend
# parents[1] = backend/src
# parents[2] = backend
#
BACKEND_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = BACKEND_DIR / "models"

FAULT_MODEL_PATH = MODEL_DIR / "fault_classifier.joblib"


# ============================================================
# ML model
# ============================================================

_fault_model: Optional[Any] = None


def load_fault_model() -> Optional[Any]:
    """
    Load the trained fault-classification model.

    The model is loaded once and then reused for subsequent
    telemetry records.

    If the model does not exist yet, the pipeline continues
    without ML inference.

    This is useful during development because your teammate
    may not have supplied the final .joblib model yet.
    """

    global _fault_model

    if _fault_model is not None:
        return _fault_model

    if not FAULT_MODEL_PATH.exists():
        print(
            f"[ML] Model not found: {FAULT_MODEL_PATH}"
        )
        print(
            "[ML] Continuing without fault classification."
        )
        return None

    try:
        _fault_model = joblib.load(
            FAULT_MODEL_PATH
        )

        print(
            f"[ML] Loaded model: {FAULT_MODEL_PATH}"
        )

        return _fault_model

    except Exception as exc:
        print(
            f"[ML] Failed to load model: {exc}"
        )
        return None


# ============================================================
# Utility helpers
# ============================================================

def _safe_float(
    value: Any,
) -> Optional[float]:
    """
    Convert a value to float.

    Returns None for missing/invalid/NaN values.
    """

    if value is None:
        return None

    try:
        value = float(value)

        if np.isnan(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _calculate_residual(
    actual: Any,
    expected: Any,
) -> Optional[float]:
    """
    Calculate:

        residual = actual - expected

    Returns None if either value is unavailable.
    """

    actual_value = _safe_float(actual)
    expected_value = _safe_float(expected)

    if actual_value is None or expected_value is None:
        return None

    return actual_value - expected_value


# ============================================================
# Residual calculation
# ============================================================

RESIDUAL_PARAMETERS = {
    "rpm": "expected_rpm",
    "cht_c": "expected_cht_c",
    "egt_c": "expected_egt_c",
    "oil_pressure_kpa": "expected_oil_pressure_kpa",
    "oil_temperature_c": "expected_oil_temperature_c",
    "fuel_flow_lph": "expected_fuel_flow_lph",
    "vibration_g": "expected_vibration_g",
    "injection_timing_deg": "expected_injection_timing_deg",
}


def calculate_residuals(
    telemetry: dict[str, Any],
) -> dict[str, Optional[float]]:
    """
    Calculate actual-vs-expected residuals.

    If generator.py already supplied residual values,
    those values are used.

    Otherwise they are calculated from:

        actual - expected

    Returns a dictionary containing residual values.
    """

    residuals: dict[str, Optional[float]] = {}

    for parameter, expected_parameter in RESIDUAL_PARAMETERS.items():

        residual_key = f"residual_{parameter}"

        # ----------------------------------------------------
        # Use residual already supplied by generator.py
        # ----------------------------------------------------

        if residual_key in telemetry:

            existing = _safe_float(
                telemetry.get(residual_key)
            )

            if existing is not None:
                residuals[residual_key] = existing
                continue

        # ----------------------------------------------------
        # Otherwise calculate it
        # ----------------------------------------------------

        residuals[residual_key] = _calculate_residual(
            telemetry.get(parameter),
            telemetry.get(expected_parameter),
        )

    return residuals


# ============================================================
# ML feature preparation
# ============================================================

ML_FEATURES = [
    "rpm",
    "cht_c",
    "egt_c",
    "oil_pressure_kpa",
    "oil_temperature_c",
    "fuel_flow_lph",
    "vibration_g",
    "injection_timing_deg",

    "throttle_pct",
    "altitude_m",
    "ambient_temperature_c",

    "residual_rpm",
    "residual_cht_c",
    "residual_egt_c",
    "residual_oil_pressure_kpa",
    "residual_oil_temperature_c",
    "residual_fuel_flow_lph",
    "residual_vibration_g",
    "residual_injection_timing_deg",
]


def prepare_ml_features(
    telemetry: dict[str, Any],
    residuals: dict[str, Optional[float]],
) -> np.ndarray:
    """
    Prepare the feature vector used by the ML model.

    IMPORTANT:

    The exact feature order must eventually match the order
    used when your teammate trained fault_classifier.joblib.

    For now this function provides a single central location
    where that mapping can be changed once the final model
    specification is available.
    """

    values: list[float] = []

    for feature in ML_FEATURES:

        if feature.startswith("residual_"):

            value = residuals.get(feature)

        else:

            value = telemetry.get(feature)

        value = _safe_float(value)

        # ----------------------------------------------------
        # Basic missing-value handling
        # ----------------------------------------------------

        if value is None:
            value = 0.0

        values.append(value)

    return np.asarray(
        [values],
        dtype=float,
    )


# ============================================================
# ML inference
# ============================================================

def run_ml(
    telemetry: dict[str, Any],
    residuals: dict[str, Optional[float]],
) -> dict[str, Any]:
    """
    Run fault-classification inference.

    Returns a structured ML result.

    If the model is unavailable, the result clearly indicates
    that inference was not performed.
    """

    model = load_fault_model()

    if model is None:

        return {
            "available": False,
            "prediction": None,
            "confidence": None,
            "anomaly_score": None,
        }

    features = prepare_ml_features(
        telemetry,
        residuals,
    )

    try:

        prediction = model.predict(
            features
        )

        prediction_value = prediction[0]

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = None

        if hasattr(
            model,
            "predict_proba",
        ):

            probabilities = model.predict_proba(
                features
            )

            confidence = float(
                np.max(probabilities[0])
            )

        # ----------------------------------------------------
        # Optional anomaly score
        # ----------------------------------------------------

        anomaly_score = None

        if hasattr(
            model,
            "decision_function",
        ):

            try:

                decision = model.decision_function(
                    features
                )

                anomaly_score = float(
                    np.asarray(decision).reshape(-1)[0]
                )

            except Exception:
                anomaly_score = None

        return {
            "available": True,
            "prediction": str(
                prediction_value
            ),
            "confidence": confidence,
            "anomaly_score": anomaly_score,
        }

    except Exception as exc:

        return {
            "available": True,
            "prediction": None,
            "confidence": None,
            "anomaly_score": None,
            "error": str(exc),
        }


# ============================================================
# Basic health calculation
# ============================================================

def calculate_health(
    residuals: dict[str, Optional[float]],
) -> float:
    """
    Produce a simple prototype health score from residuals.

    This is NOT the final ML health model.

    It provides a temporary deterministic health score so
    the backend has a useful value before the complete AI
    health/degradation model is integrated.

    Score:

        100 = healthy
          0 = severely abnormal

    The score is based on normalized residual magnitudes.
    """

    normalized_deviations: list[float] = []

    # Approximate engineering scales used only for the
    # prototype health indicator.

    scales = {
        "residual_rpm": 500.0,
        "residual_cht_c": 40.0,
        "residual_egt_c": 100.0,
        "residual_oil_pressure_kpa": 100.0,
        "residual_oil_temperature_c": 30.0,
        "residual_fuel_flow_lph": 15.0,
        "residual_vibration_g": 0.5,
        "residual_injection_timing_deg": 10.0,
    }

    for key, scale in scales.items():

        value = residuals.get(key)

        if value is None:
            continue

        normalized = abs(value) / scale

        normalized_deviations.append(
            normalized
        )

    if not normalized_deviations:
        return 100.0

    average_deviation = float(
        np.mean(
            normalized_deviations
        )
    )

    health = 100.0 * (
        1.0 - min(
            average_deviation,
            1.0,
        )
    )

    return round(
        max(0.0, health),
        2,
    )


# ============================================================
# Fault severity
# ============================================================

def determine_severity(
    health_score: float,
) -> str:
    """
    Convert health score into a simple severity category.

    This is temporary prototype logic.
    """

    if health_score >= 85:
        return "LOW"

    if health_score >= 65:
        return "MEDIUM"

    if health_score >= 40:
        return "HIGH"

    return "CRITICAL"


# ============================================================
# Main telemetry processor
# ============================================================

def process_telemetry(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Main AeroTwin processing pipeline.

    Flow:

        telemetry
             |
             v
        validation
             |
             v
        residual calculation
             |
             v
        ML features
             |
             v
        ML inference
             |
             v
        health calculation
             |
             v
        structured result

    Database storage will be connected through
    supabase_client.py after this pipeline is tested.
    """

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    engine_id = telemetry.get(
        "engine_id"
    )

    mission_id = telemetry.get(
        "mission_id"
    )

    timestamp_s = telemetry.get(
        "timestamp_s"
    )

    if not engine_id:
        raise ValueError(
            "Missing engine_id."
        )

    if not mission_id:
        raise ValueError(
            "Missing mission_id."
        )

    if timestamp_s is None:
        raise ValueError(
            "Missing timestamp_s."
        )

    # --------------------------------------------------------
    # Calculate actual-vs-expected behavior
    # --------------------------------------------------------

    residuals = calculate_residuals(
        telemetry
    )

    # --------------------------------------------------------
    # Health
    # --------------------------------------------------------

    health_score = calculate_health(
        residuals
    )

    severity = determine_severity(
        health_score
    )

    # --------------------------------------------------------
    # ML inference
    # --------------------------------------------------------

    ml_result = run_ml(
        telemetry,
        residuals,
    )

    # --------------------------------------------------------
    # Fault result
    # --------------------------------------------------------

    predicted_fault = ml_result.get(
        "prediction"
    )

    confidence = ml_result.get(
        "confidence"
    )

    # --------------------------------------------------------
    # Build result
    # --------------------------------------------------------

    result = {
        "engine_id": engine_id,
        "mission_id": mission_id,
        "timestamp_s": timestamp_s,

        "mission_phase": telemetry.get(
            "mission_phase"
        ),

        "health_score": health_score,

        "severity": severity,

        "residuals": residuals,

        "ml": ml_result,

        "fault": {
            "type": predicted_fault,
            "confidence": confidence,
            "active": (
                predicted_fault is not None
                and str(predicted_fault).upper()
                != "NORMAL"
            ),
        },

        # ----------------------------------------------------
        # These will be populated by the RUL/maintenance
        # components later.
        # ----------------------------------------------------

        "rul_hours": None,

        "trend": (
            "STABLE"
            if health_score >= 85
            else "DEGRADING"
        ),

        "maintenance_recommendation": None,
    }

    # --------------------------------------------------------
    # Log pipeline result
    # --------------------------------------------------------

    print(
        "[PIPELINE]"
        f" mission={mission_id}"
        f" engine={engine_id}"
        f" health={health_score:.1f}"
        f" fault={predicted_fault}"
    )

    return result


# ============================================================
# Local test
# ============================================================

if __name__ == "__main__":

    test_telemetry = {
        "timestamp_s": 10.0,

        "engine_id": "ENG-001",
        "mission_id": "MIS-0001",

        "mission_phase": "CRUISE",

        "throttle_pct": 60.0,
        "altitude_m": 5000.0,
        "ambient_temperature_c": 20.0,

        "rpm": 2450.0,
        "cht_c": 155.0,
        "egt_c": 650.0,

        "oil_pressure_kpa": 360.0,
        "oil_temperature_c": 70.0,

        "fuel_flow_lph": 17.0,
        "vibration_g": 0.25,

        "alternator_voltage_v": 28.0,
        "battery_voltage_v": 25.5,

        "injection_timing_deg": 24.0,

        "expected_rpm": 2480.0,
        "expected_cht_c": 150.0,
        "expected_egt_c": 640.0,

        "expected_oil_pressure_kpa": 370.0,
        "expected_oil_temperature_c": 69.0,

        "expected_fuel_flow_lph": 17.2,
        "expected_vibration_g": 0.24,

        "expected_injection_timing_deg": 23.8,
    }

    result = process_telemetry(
        test_telemetry
    )

    print("\nResult:")
    print(result)
