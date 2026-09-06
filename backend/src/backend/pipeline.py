from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import numpy as np


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Self-contained AIML module.
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


# ============================================================
# AI/ML SERVICE
# ============================================================

_aiml_service: Optional[Any] = None
_aiml_load_attempted = False

_aiml_load_lock = threading.Lock()


def load_aiml_service() -> Optional[Any]:
    """
    Lazily construct the integrated AIML telemetry service.

    The AIML module provides:

        - anomaly detection
        - multi-label fault classification
        - health / degradation scoring
        - formula-based RUL

    No RUL regression model or RUL joblib is required.
    """

    global _aiml_service
    global _aiml_load_attempted

    if _aiml_service is not None:
        return _aiml_service

    with _aiml_load_lock:

        if _aiml_service is not None:
            return _aiml_service

        if _aiml_load_attempted:
            return None

        _aiml_load_attempted = True

        # --------------------------------------------------------
        # Validate AIML module
        # --------------------------------------------------------

        if not AIML_ROOT.exists():
            print(
                f"[AIML] Module not found: {AIML_ROOT}"
            )
            return None

        # --------------------------------------------------------
        # Validate required model artifacts
        # --------------------------------------------------------

        required_models = [
            AIML_ANOMALY_MODEL_PATH,
            AIML_FAULT_MODEL_PATH,
        ]

        missing_models = [
            path
            for path in required_models
            if not path.exists()
        ]

        if missing_models:
            print(
                "[AIML] Missing required model artifact(s):"
            )

            for path in missing_models:
                print(f"       {path}")

            return None

        # --------------------------------------------------------
        # AIML uses its internal top-level `src` package.
        # --------------------------------------------------------

        if str(AIML_ROOT) not in sys.path:
            sys.path.insert(
                0,
                str(AIML_ROOT),
            )

        original_cwd = os.getcwd()

        try:

            os.chdir(AIML_ROOT)

            from src.inference.service import (
                TelemetryMLService,
            )

            _aiml_service = TelemetryMLService(
                anomaly_model_path=AIML_ANOMALY_MODEL_PATH,
                fault_model_path=AIML_FAULT_MODEL_PATH,
            )

            print(
                "[AIML] Loaded anomaly model, "
                "fault model and formula-based RUL."
            )

            return _aiml_service

        except Exception as exc:

            print(
                f"[AIML] Failed to load AI/ML module: {exc}"
            )

            return None

        finally:

            os.chdir(original_cwd)


# ============================================================
# TELEMETRY TRAJECTORY BUFFER
# ============================================================
#
# AIML temporal features use:
#
#   rolling windows
#   slopes
#   lags
#   EWMA
#   degradation trends
#
# Therefore the backend keeps recent telemetry history
# separately for each mission.
# ============================================================

AIML_TELEMETRY_FIELDS = [

    # --------------------------------------------------------
    # Identity / time
    # --------------------------------------------------------

    "timestamp_s",
    "engine_id",
    "mission_id",
    "mission_phase",

    # --------------------------------------------------------
    # Operating context
    # --------------------------------------------------------

    "throttle_pct",
    "altitude_m",
    "ambient_temperature_c",

    # --------------------------------------------------------
    # Raw telemetry
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Digital Twin expected values
    # --------------------------------------------------------

    "expected_rpm",
    "expected_cht_c",
    "expected_egt_c",
    "expected_oil_pressure_kpa",
    "expected_oil_temperature_c",
    "expected_fuel_flow_lph",
    "expected_vibration_g",
    "expected_injection_timing_deg",

    # --------------------------------------------------------
    # Digital Twin residuals
    # --------------------------------------------------------

    "residual_rpm",
    "residual_cht_c",
    "residual_egt_c",
    "residual_oil_pressure_kpa",
    "residual_oil_temperature_c",
    "residual_fuel_flow_lph",
    "residual_vibration_g",
    "residual_injection_timing_deg",
]


_mission_buffers: dict[
    str,
    list[dict[str, Any]],
] = {}

_mission_buffers_lock = threading.Lock()

MAX_TRAJECTORY_BUFFER = 300


def _buffer_telemetry(
    telemetry: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Add the current telemetry point to the mission history.

    Returns a copy of the current trajectory.
    """

    mission_id = str(
        telemetry.get(
            "mission_id"
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

        if len(buffer) > MAX_TRAJECTORY_BUFFER:

            del buffer[
                : len(buffer)
                - MAX_TRAJECTORY_BUFFER
            ]

        return list(buffer)


def clear_mission_buffer(
    mission_id: str,
) -> None:
    """
    Clear the buffered telemetry for one mission.

    Useful when a mission ends or a replay is restarted.
    """

    with _mission_buffers_lock:

        _mission_buffers.pop(
            str(mission_id),
            None,
        )


def clear_all_mission_buffers() -> None:
    """
    Clear all in-memory mission trajectories.
    """

    with _mission_buffers_lock:

        _mission_buffers.clear()


# ============================================================
# AIML INFERENCE
# ============================================================

def run_aiml(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the integrated AIML module using the mission trajectory
    accumulated so far.

    Returns only the latest prediction.
    """

    service = load_aiml_service()

    if service is None:

        return {
            "available": False,
            "error": (
                "AI/ML service is unavailable."
            ),
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

            # ------------------------------------------------
            # Anomaly
            # ------------------------------------------------

            "anomaly_score": latest.get(
                "anomaly_score"
            ),

            # ------------------------------------------------
            # Fault
            # ------------------------------------------------

            "top_fault": latest.get(
                "top_fault"
            ),

            "fault_probability": latest.get(
                "fault_probability"
            ),

            "fault_severity": latest.get(
                "fault_severity"
            ),

            # ------------------------------------------------
            # Health
            # ------------------------------------------------

            "health_score": latest.get(
                "health_score"
            ),

            "health_status": latest.get(
                "health_status"
            ),

            # ------------------------------------------------
            # Formula RUL
            # ------------------------------------------------

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
    Convert a value to float.

    Returns None for invalid, missing, NaN or infinite values.
    """

    if value is None:
        return None

    try:

        converted = float(value)

        if not np.isfinite(
            converted
        ):
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
# DIGITAL-TWIN RESIDUALS
# ============================================================

RESIDUAL_PARAMETERS = {

    "rpm": "expected_rpm",

    "cht_c": (
        "expected_cht_c"
    ),

    "egt_c": (
        "expected_egt_c"
    ),

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


def calculate_residuals(
    telemetry: dict[str, Any],
    expected: Optional[
        dict[str, Any]
    ] = None,
) -> dict[str, Optional[float]]:
    """
    Calculate actual-vs-expected Digital-Twin residuals.

    Existing residuals supplied by the simulator/generator
    are preserved.

    Otherwise:

        residual = actual - expected
    """

    working = dict(
        telemetry
    )

    # --------------------------------------------------------
    # Optional explicit expected values
    # --------------------------------------------------------

    if expected is not None:

        for parameter, value in expected.items():

            working[
                f"expected_{parameter}"
            ] = value

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
        # Preserve supplied residual
        # ----------------------------------------------------

        if residual_key in working:

            existing = _safe_float(
                working.get(
                    residual_key
                )
            )

            if existing is not None:

                residuals[
                    residual_key
                ] = existing

                # Backward-compatible bare alias.
                residuals[
                    parameter
                ] = existing

                continue

        # ----------------------------------------------------
        # Calculate residual
        # ----------------------------------------------------

        value = _calculate_residual(
            working.get(
                parameter
            ),
            working.get(
                expected_parameter
            ),
        )

        residuals[
            residual_key
        ] = value

        # Backward-compatible bare alias.
        residuals[
            parameter
        ] = value

    return residuals


# ============================================================
# MAIN TELEMETRY PROCESSOR
# ============================================================

def process_telemetry(
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    """
    Main backend telemetry processing pipeline.

    Flow:

        raw telemetry
             ↓
        validation
             ↓
        Digital-Twin residuals
             ↓
        trajectory buffering
             ↓
        anomaly ML
             ↓
        fault ML
             ↓
        health / degradation
             ↓
        formula-based RUL
             ↓
        structured backend result

    The backend does NOT load or execute an independent
    legacy ML model.

    The AIML module is the single source of prediction logic.
    """

    # ========================================================
    # 1. BASIC VALIDATION
    # ========================================================

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
    # 2. DIGITAL-TWIN RESIDUALS
    # ========================================================

    residuals = calculate_residuals(
        telemetry
    )

    # ========================================================
    # 3. FULL AIML INFERENCE
    # ========================================================

    aiml_result = run_aiml(
        telemetry
    )

    if not aiml_result.get(
        "available",
        False,
    ):

        raise RuntimeError(
            "AI/ML inference unavailable: "
            f"{aiml_result.get('error', 'unknown error')}"
        )

    # ========================================================
    # 4. EXTRACT PREDICTIONS
    # ========================================================

    anomaly_score = (
        aiml_result.get(
            "anomaly_score"
        )
    )

    predicted_fault = (
        aiml_result.get(
            "top_fault"
        )
    )

    confidence = (
        aiml_result.get(
            "fault_probability"
        )
    )

    fault_severity = (
        aiml_result.get(
            "fault_severity"
        )
    )

    health_score = (
        aiml_result.get(
            "health_score"
        )
    )

    health_status = (
        aiml_result.get(
            "health_status"
        )
    )

    rul_seconds = (
        aiml_result.get(
            "predicted_rul_seconds"
        )
    )

    rul_minutes = (
        aiml_result.get(
            "predicted_rul_minutes"
        )
    )

    rul_status = (
        aiml_result.get(
            "rul_status"
        )
    )

    # ========================================================
    # 5. RUL HOURS
    # ========================================================

    rul_hours = None

    if rul_seconds is not None:

        rul_seconds_numeric = (
            _safe_float(
                rul_seconds
            )
        )

        if rul_seconds_numeric is not None:

            rul_hours = round(
                rul_seconds_numeric
                / 3600.0,
                3,
            )

    # ========================================================
    # 6. TREND STATUS
    # ========================================================

    if rul_status in (
        None,
        "NOT_APPLICABLE",
        "NORMAL",
    ):

        trend = "STABLE"

    else:

        trend = "DEGRADING"

    # ========================================================
    # 7. FAULT ACTIVE FLAG
    # ========================================================

    fault_active = (

        predicted_fault is not None

        and str(
            predicted_fault
        ).upper()
        not in {
            "",
            "NONE",
            "NORMAL",
            "NAN",
        }

    )

    # ========================================================
    # 8. AIML RESULT METADATA
    # ========================================================

    ml_result = {

        "source": (
            "ai_ml_module"
        ),

        "available": True,

        "prediction": (
            predicted_fault
        ),

        "confidence": (
            confidence
        ),

        "anomaly_score": (
            anomaly_score
        ),
    }

    # ========================================================
    # 9. STRUCTURED BACKEND RESULT
    # ========================================================

    result = {

        "engine_id": (
            engine_id
        ),

        "mission_id": (
            mission_id
        ),

        "timestamp_s": (
            timestamp_s
        ),

        "mission_phase": (
            telemetry.get(
                "mission_phase"
            )
        ),

        # ----------------------------------------------------
        # Health
        # ----------------------------------------------------

        "health_score": (
            health_score
        ),

        "health_status": (
            health_status
        ),

        "anomaly_score": (
            anomaly_score
        ),

        # ----------------------------------------------------
        # Digital Twin
        # ----------------------------------------------------

        "residuals": (
            residuals
        ),

        # ----------------------------------------------------
        # ML
        # ----------------------------------------------------

        "ml": (
            ml_result
        ),

        # ----------------------------------------------------
        # Fault
        # ----------------------------------------------------

        "fault": {

            "type": (
                predicted_fault
            ),

            "confidence": (
                confidence
            ),

            "severity": (
                fault_severity
            ),

            "active": (
                fault_active
            ),
        },

        # ----------------------------------------------------
        # Formula-based RUL
        # ----------------------------------------------------

        "rul_seconds": (
            rul_seconds
        ),

        "rul_minutes": (
            rul_minutes
        ),

        "rul_hours": (
            rul_hours
        ),

        "rul_status": (
            rul_status
        ),

        # ----------------------------------------------------
        # Trend
        # ----------------------------------------------------

        "trend": (
            trend
        ),

        # ----------------------------------------------------
        # Maintenance recommendation
        # ----------------------------------------------------

        "maintenance_recommendation": None,
    }

    # ========================================================
    # 10. LOG
    # ========================================================

    print(
        "[PIPELINE]"
        f" mission={mission_id}"
        f" engine={engine_id}"
        f" timestamp={timestamp_s}"
        f" health={health_score}"
        f" status={health_status}"
        f" fault={predicted_fault}"
        f" fault_probability={confidence}"
        f" rul={rul_seconds}"
        f" rul_status={rul_status}"
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

    result = process_telemetry(
        test_telemetry
    )

    print(
        "\nResult:"
    )

    print(
        result
    )