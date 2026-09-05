from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np


# ============================================================
# PATHS
# ============================================================

# pipeline.py
#
# backend/
# └── src/
#     └── backend/
#         └── pipeline.py
#
# parents[0] = backend/src/backend
# parents[1] = backend/src
# parents[2] = backend

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Legacy model location
MODEL_DIR = BACKEND_DIR / "models"
FAULT_MODEL_PATH = MODEL_DIR / "fault_classifier.joblib"

# New AI/ML module
AIML_ROOT = BACKEND_DIR / "ai_ml_module"

AIML_ANOMALY_MODEL_PATH = (
    AIML_ROOT
    / "models"
    / "anomaly"
    / "anomaly_detector.joblib"
)

AIML_FAULT_MODEL_PATH = (
    AIML_ROOT
    / "models"
    / "faults"
    / "fault_classifier.joblib"
)

AIML_RUL_MODEL_PATH = (
    AIML_ROOT
    / "models"
    / "rul"
    / "rul_regressor.joblib"
)


# ============================================================
# LEGACY ML MODEL
# ============================================================

_fault_model: Optional[Any] = None


def load_fault_model() -> Optional[Any]:
    """
    Load the legacy fault-classification model once.

    This model is used only as a fallback when the new
    AI/ML module is unavailable.
    """

    global _fault_model

    if _fault_model is not None:
        return _fault_model

    if not FAULT_MODEL_PATH.exists():
        print(
            f"[ML] Legacy model not found: "
            f"{FAULT_MODEL_PATH}"
        )
        print(
            "[ML] Continuing without legacy "
            "fault classification."
        )
        return None

    try:
        _fault_model = joblib.load(
            FAULT_MODEL_PATH
        )

        print(
            f"[ML] Loaded legacy model: "
            f"{FAULT_MODEL_PATH}"
        )

        return _fault_model

    except Exception as exc:
        print(
            f"[ML] Failed to load legacy model: "
            f"{exc}"
        )

        return None


# ============================================================
# FULL AI/ML MODULE
# ============================================================

_aiml_service: Optional[Any] = None
_aiml_load_attempted = False

_mission_buffers: dict[
    str,
    list[dict[str, Any]],
] = {}

_mission_buffers_lock = threading.Lock()

MAX_TRAJECTORY_BUFFER = 300


# ============================================================
# AI/ML TELEMETRY FIELDS
# ============================================================

AIML_TELEMETRY_FIELDS = [
    "timestamp_s",
    "engine_id",
    "mission_id",
    "mission_phase",
    "throttle_pct",
    "altitude_m",
    "ambient_temperature_c",
    "rpm",
    "cht_c",
    "egt_c",
    "oil_pressure_kpa",
    "oil_temperature_c",
    "fuel_flow_lph",
    "vibration_g",
    "alternator_voltage_v",
    "battery_voltage_v",
    "injection_timing_deg",
]


# ============================================================
# LOAD AI/ML SERVICE
# ============================================================

def load_aiml_service() -> Optional[Any]:
    """
    Lazily load the complete AI/ML service.

    The service contains:

    - anomaly detection
    - fault classification
    - health estimation
    - RUL prediction

    The service is loaded once and reused.
    """

    global _aiml_service
    global _aiml_load_attempted

    if _aiml_service is not None:
        return _aiml_service

    if _aiml_load_attempted:
        return None

    _aiml_load_attempted = True

    # --------------------------------------------------------
    # Check AI/ML project
    # --------------------------------------------------------

    if not AIML_ROOT.exists():
        print(
            f"[AIML] Module not found: "
            f"{AIML_ROOT}"
        )

        return None

    # --------------------------------------------------------
    # Check required models
    # --------------------------------------------------------

    required_models = [
        AIML_ANOMALY_MODEL_PATH,
        AIML_FAULT_MODEL_PATH,
        AIML_RUL_MODEL_PATH,
    ]

    missing_models = [
        path
        for path in required_models
        if not path.exists()
    ]

    if missing_models:
        print(
            "[AIML] Missing trained model(s):"
        )

        for path in missing_models:
            print(
                f"       {path}"
            )

        print(
            "[AIML] AI/ML module disabled."
        )

        return None

    # --------------------------------------------------------
    # Add AI/ML root to Python path
    # --------------------------------------------------------

    aiml_root_string = str(AIML_ROOT)

    if aiml_root_string not in sys.path:
        sys.path.insert(
            0,
            aiml_root_string,
        )

    original_cwd = os.getcwd()

    try:
        os.chdir(AIML_ROOT)

        from src.inference.service import (
            TelemetryMLService,
        )

        _aiml_service = TelemetryMLService(
            anomaly_model_path=(
                AIML_ANOMALY_MODEL_PATH
            ),
            fault_model_path=(
                AIML_FAULT_MODEL_PATH
            ),
            rul_model_path=(
                AIML_RUL_MODEL_PATH
            ),
        )

        print(
            "[AIML] Successfully loaded:"
        )
        print(
            "       - anomaly detector"
        )
        print(
            "       - fault classifier"
        )
        print(
            "       - RUL regressor"
        )

        return _aiml_service

    except Exception as exc:
        print(
            f"[AIML] Failed to load AI/ML module: "
            f"{exc}"
        )

        return None

    finally:
        os.chdir(original_cwd)


# ============================================================
# TRAJECTORY BUFFER
# ============================================================

def _buffer_telemetry(
    telemetry: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Store telemetry history for each mission.

    The AI/ML module requires a trajectory rather than only
    the current telemetry point because some features depend
    on temporal history.
    """

    mission_id = str(
        telemetry.get(
            "mission_id",
            "UNKNOWN",
        )
    )

    point = {
        field: telemetry.get(field)
        for field in AIML_TELEMETRY_FIELDS
    }

    with _mission_buffers_lock:

        buffer = _mission_buffers.setdefault(
            mission_id,
            [],
        )

        buffer.append(point)

        # Keep only the most recent records.
        if len(buffer) > MAX_TRAJECTORY_BUFFER:

            del buffer[
                : len(buffer)
                - MAX_TRAJECTORY_BUFFER
            ]

        return list(buffer)


# ============================================================
# CLEAR MISSION BUFFER
# ============================================================

def clear_mission_buffer(
    mission_id: str,
) -> None:
    """
    Clear stored telemetry history for a mission.

    Useful when a mission finishes.
    """

    with _mission_buffers_lock:
        _mission_buffers.pop(
            str(mission_id),
            None,
        )


def clear_all_mission_buffers() -> None:
    """
    Clear all stored mission trajectories.
    """

    with _mission_buffers_lock:
        _mission_buffers.clear()


# ============================================================
# RUN FULL AI/ML
# ============================================================

def run_aiml(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the complete AI/ML pipeline.

    Returns:

        anomaly_score
        top_fault
        fault_probability
        fault_severity
        health_score
        health_status
        predicted_rul_seconds
        predicted_rul_minutes
        rul_status
    """

    service = load_aiml_service()

    if service is None:
        return {
            "available": False,
        }

    trajectory = _buffer_telemetry(
        telemetry
    )

    original_cwd = os.getcwd()

    try:
        os.chdir(AIML_ROOT)

        latest = service.predict_dicts(
            trajectory
        )

        return {
            "available": True,

            "anomaly_score": latest.get(
                "anomaly_score"
            ),

            "top_fault": latest.get(
                "top_fault"
            ),

            "fault_probability": latest.get(
                "fault_probability"
            ),

            "fault_severity": latest.get(
                "fault_severity"
            ),

            "health_score": latest.get(
                "health_score"
            ),

            "health_status": latest.get(
                "health_status"
            ),

            "predicted_rul_seconds": latest.get(
                "predicted_rul_seconds"
            ),

            "predicted_rul_minutes": latest.get(
                "predicted_rul_minutes"
            ),

            "rul_status": latest.get(
                "rul_status"
            ),
        }

    except Exception as exc:

        print(
            f"[AIML] Inference failed: "
            f"{exc}"
        )

        return {
            "available": False,
            "error": str(exc),
        }

    finally:
        os.chdir(original_cwd)


# ============================================================
# UTILITY HELPERS
# ============================================================

def _safe_float(
    value: Any,
) -> Optional[float]:
    """
    Safely convert a value to float.

    Returns None for:

    - None
    - invalid strings
    - NaN
    - unsupported values
    """

    if value is None:
        return None

    try:
        converted = float(value)

        if np.isnan(converted):
            return None

        return converted

    except (
        TypeError,
        ValueError,
    ):
        return None


def _calculate_residual(
    actual: Any,
    expected: Any,
) -> Optional[float]:
    """
    Calculate:

        residual = actual - expected
    """

    actual_value = _safe_float(
        actual
    )

    expected_value = _safe_float(
        expected
    )

    if (
        actual_value is None
        or expected_value is None
    ):
        return None

    return (
        actual_value
        - expected_value
    )


# ============================================================
# RESIDUAL PARAMETERS
# ============================================================

RESIDUAL_PARAMETERS = {
    "rpm": "expected_rpm",
    "cht_c": "expected_cht_c",
    "egt_c": "expected_egt_c",
    "oil_pressure_kpa": (
        "expected_oil_pressure_kpa"
    ),
    "oil_temperature_c": (
        "expected_oil_temperature_c"
    ),
    "fuel_flow_lph": (
        "expected_fuel_flow_lph"
    ),
    "vibration_g": (
        "expected_vibration_g"
    ),
    "injection_timing_deg": (
        "expected_injection_timing_deg"
    ),
}


# ============================================================
# RESIDUAL CALCULATION
# ============================================================

def calculate_residuals(
    telemetry: dict[str, Any],
) -> dict[str, Optional[float]]:
    """
    Calculate actual-vs-expected residuals.

    If telemetry already contains a residual, that value
    is preserved.

    Otherwise:

        residual = actual - expected
    """

    residuals: dict[
        str,
        Optional[float],
    ] = {}

    for (
        parameter,
        expected_parameter,
    ) in RESIDUAL_PARAMETERS.items():

        residual_key = (
            f"residual_{parameter}"
        )

        # ----------------------------------------------------
        # Use supplied residual
        # ----------------------------------------------------

        if residual_key in telemetry:

            existing = _safe_float(
                telemetry.get(
                    residual_key
                )
            )

            if existing is not None:

                residuals[
                    residual_key
                ] = existing

                continue

        # ----------------------------------------------------
        # Calculate residual
        # ----------------------------------------------------

        residuals[
            residual_key
        ] = _calculate_residual(
            telemetry.get(
                parameter
            ),
            telemetry.get(
                expected_parameter
            ),
        )

    return residuals


# ============================================================
# LEGACY ML FEATURES
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


# ============================================================
# PREPARE LEGACY ML FEATURES
# ============================================================

def prepare_ml_features(
    telemetry: dict[str, Any],
    residuals: dict[
        str,
        Optional[float],
    ],
) -> np.ndarray:
    """
    Prepare features for the legacy fault model.

    The feature order must match the order used when the
    legacy model was trained.
    """

    values: list[float] = []

    for feature in ML_FEATURES:

        if feature.startswith(
            "residual_"
        ):

            value = residuals.get(
                feature
            )

        else:

            value = telemetry.get(
                feature
            )

        value = _safe_float(
            value
        )

        if value is None:
            value = 0.0

        values.append(value)

    return np.asarray(
        [values],
        dtype=float,
    )


# ============================================================
# LEGACY ML INFERENCE
# ============================================================

def run_ml(
    telemetry: dict[str, Any],
    residuals: dict[
        str,
        Optional[float],
    ],
) -> dict[str, Any]:
    """
    Run the legacy fault-classification model.

    This is used only when the full AI/ML module is unavailable.
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

        prediction_value = (
            prediction[0]
        )

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = None

        if hasattr(
            model,
            "predict_proba",
        ):

            probabilities = (
                model.predict_proba(
                    features
                )
            )

            confidence = float(
                np.max(
                    probabilities[0]
                )
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

                decision = (
                    model.decision_function(
                        features
                    )
                )

                anomaly_score = float(
                    np.asarray(
                        decision
                    )
                    .reshape(-1)[0]
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
# PROTOTYPE HEALTH CALCULATION
# ============================================================

def calculate_health(
    residuals: dict[
        str,
        Optional[float],
    ],
) -> float:
    """
    Calculate a temporary deterministic health score.

    Used only as fallback when the full AI/ML health model
    is unavailable.

    100 = healthy
    0   = severely abnormal
    """

    normalized_deviations: list[
        float
    ] = []

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

    for (
        key,
        scale,
    ) in scales.items():

        value = residuals.get(
            key
        )

        if value is None:
            continue

        normalized = (
            abs(value)
            / scale
        )

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

    health = (
        100.0
        * (
            1.0
            - min(
                average_deviation,
                1.0,
            )
        )
    )

    return round(
        max(
            0.0,
            health,
        ),
        2,
    )


# ============================================================
# FAULT SEVERITY
# ============================================================

def determine_severity(
    health_score: float,
) -> str:
    """
    Convert health score to severity.

    This is fallback/prototype logic only.
    """

    if health_score >= 85:
        return "LOW"

    if health_score >= 65:
        return "MEDIUM"

    if health_score >= 40:
        return "HIGH"

    return "CRITICAL"


# ============================================================
# RUL CONVERSION
# ============================================================

def rul_seconds_to_hours(
    rul_seconds: Any,
) -> Optional[float]:
    """
    Convert RUL seconds to hours.
    """

    value = _safe_float(
        rul_seconds
    )

    if value is None:
        return None

    return round(
        value / 3600.0,
        3,
    )


# ============================================================
# TREND
# ============================================================

def determine_trend(
    health_score: Optional[float],
    rul_status: Optional[str] = None,
) -> str:
    """
    Determine health trend.

    AI/ML RUL status takes priority when available.
    Otherwise fallback health thresholds are used.
    """

    if rul_status is not None:

        normalized_status = str(
            rul_status
        ).upper()

        if normalized_status in {
            "NOT_APPLICABLE",
            "NORMAL",
            "STABLE",
        }:
            return "STABLE"

        if normalized_status in {
            "DEGRADING",
            "WARNING",
            "CRITICAL",
        }:
            return "DEGRADING"

    if health_score is None:
        return "STABLE"

    if health_score >= 85:
        return "STABLE"

    return "DEGRADING"


# ============================================================
# MAIN TELEMETRY PROCESSOR
# ============================================================

def process_telemetry(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Main AeroTwin telemetry pipeline.

    Processing order:

        telemetry
             |
             v
        validation
             |
             v
        residual calculation
             |
             v
        full AI/ML module
             |
             +---- available ----> anomaly
             |                     fault
             |                     health
             |                     RUL
             |
             +---- unavailable ---> legacy ML
                                   prototype health
             |
             v
        structured result
    """

    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    if not isinstance(
        telemetry,
        dict,
    ):
        raise TypeError(
            "Telemetry must be a dictionary."
        )

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

    # ========================================================
    # RESIDUALS
    # ========================================================

    residuals = calculate_residuals(
        telemetry
    )

    # ========================================================
    # PRIMARY AI/ML PIPELINE
    # ========================================================

    aiml_result = run_aiml(
        telemetry
    )

    # ========================================================
    # AI/ML AVAILABLE
    # ========================================================

    if aiml_result.get(
        "available"
    ):

        health_score = _safe_float(
            aiml_result.get(
                "health_score"
            )
        )

        # ----------------------------------------------------
        # Health status / severity
        # ----------------------------------------------------

        severity = (
            aiml_result.get(
                "health_status"
            )
        )

        if not severity:

            severity = determine_severity(
                health_score
                if health_score is not None
                else 0.0
            )

        # ----------------------------------------------------
        # Fault
        # ----------------------------------------------------

        predicted_fault = (
            aiml_result.get(
                "top_fault"
            )
        )

        confidence = _safe_float(
            aiml_result.get(
                "fault_probability"
            )
        )

        # ----------------------------------------------------
        # RUL
        # ----------------------------------------------------

        rul_seconds = _safe_float(
            aiml_result.get(
                "predicted_rul_seconds"
            )
        )

        rul_hours = (
            rul_seconds_to_hours(
                rul_seconds
            )
        )

        # If seconds are unavailable, try minutes.
        if (
            rul_hours is None
            and aiml_result.get(
                "predicted_rul_minutes"
            ) is not None
        ):

            rul_minutes = _safe_float(
                aiml_result.get(
                    "predicted_rul_minutes"
                )
            )

            if rul_minutes is not None:

                rul_hours = round(
                    rul_minutes / 60.0,
                    3,
                )

        # ----------------------------------------------------
        # Trend
        # ----------------------------------------------------

        trend = determine_trend(
            health_score,
            aiml_result.get(
                "rul_status"
            ),
        )

        # ----------------------------------------------------
        # Unified ML result
        # ----------------------------------------------------

        ml_result = {
            "source": "ai_ml_module",
            "available": True,

            "prediction": predicted_fault,

            "confidence": confidence,

            "anomaly_score": (
                aiml_result.get(
                    "anomaly_score"
                )
            ),

            "fault_severity": (
                aiml_result.get(
                    "fault_severity"
                )
            ),

            "health_score": health_score,

            "health_status": (
                aiml_result.get(
                    "health_status"
                )
            ),

            "predicted_rul_seconds": (
                rul_seconds
            ),

            "predicted_rul_minutes": (
                aiml_result.get(
                    "predicted_rul_minutes"
                )
            ),

            "rul_status": (
                aiml_result.get(
                    "rul_status"
                )
            ),
        }

    # ========================================================
    # LEGACY FALLBACK
    # ========================================================

    else:

        # ----------------------------------------------------
        # Prototype health
        # ----------------------------------------------------

        health_score = calculate_health(
            residuals
        )

        severity = determine_severity(
            health_score
        )

        # ----------------------------------------------------
        # Legacy fault classifier
        # ----------------------------------------------------

        legacy_ml_result = run_ml(
            telemetry,
            residuals,
        )

        predicted_fault = (
            legacy_ml_result.get(
                "prediction"
            )
        )

        confidence = (
            legacy_ml_result.get(
                "confidence"
            )
        )

        # ----------------------------------------------------
        # Legacy pipeline does not provide RUL
        # ----------------------------------------------------

        rul_hours = None

        trend = determine_trend(
            health_score
        )

        # ----------------------------------------------------
        # Unified ML result
        # ----------------------------------------------------

        ml_result = {
            "source": "legacy_fallback",
            **legacy_ml_result,
        }

        if aiml_result.get(
            "error"
        ):

            ml_result[
                "ai_ml_error"
            ] = aiml_result[
                "error"
            ]

    # ========================================================
    # FAULT ACTIVE STATUS
    # ========================================================

    fault_active = (
        predicted_fault is not None
        and str(
            predicted_fault
        ).upper()
        not in {
            "NORMAL",
            "NONE",
            "NO_FAULT",
        }
    )

    # ========================================================
    # BUILD FINAL RESULT
    # ========================================================

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

            "active": fault_active,
        },

        "rul_hours": rul_hours,

        "trend": trend,

        "maintenance_recommendation": None,
    }

    # ========================================================
    # LOG
    # ========================================================

    print(
        "[PIPELINE]"
        f" mission={mission_id}"
        f" engine={engine_id}"
        f" health={health_score}"
        f" fault={predicted_fault}"
        f" severity={severity}"
        f" trend={trend}"
        f" rul_hours={rul_hours}"
    )

    return result


# ============================================================
# LOCAL TEST
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

    print()
    print(
        "========================================"
    )
    print(
        "       AEROTWIN PIPELINE TEST"
    )
    print(
        "========================================"
    )
    print()

    try:

        result = process_telemetry(
            test_telemetry
        )

        print()
        print(
            "Result:"
        )
        print(
            result
        )

    except Exception as exc:

        print()
        print(
            "[ERROR]"
        )
        print(
            exc
        )

