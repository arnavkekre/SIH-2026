from __future__ import annotations

import sys
from pathlib import Path


# -------------------------------------------------------------------
# Make backend/src importable when pytest is run from the repository
# root.
# -------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))


from backend.pipeline import process_telemetry


def make_telemetry() -> dict:
    return {
        "timestamp_s": 0.0,
        "engine_id": "TEST-ENGINE",
        "mission_id": "TEST-MISSION",
        "mission_phase": "CRUISE",

        "throttle_pct": 60.0,
        "altitude_m": 5000.0,
        "ambient_temperature_c": 20.0,

        "rpm": 2480.0,
        "cht_c": 150.0,
        "egt_c": 640.0,

        "oil_pressure_kpa": 370.0,
        "oil_temperature_c": 69.0,

        "fuel_flow_lph": 17.2,
        "vibration_g": 0.24,

        "alternator_voltage_v": 28.0,
        "battery_voltage_v": 25.5,

        "injection_timing_deg": 23.8,
    }


def test_backend_pipeline_returns_prediction():
    result = process_telemetry(
        make_telemetry()
    )

    assert result["engine_id"] == "TEST-ENGINE"
    assert result["mission_id"] == "TEST-MISSION"

    assert "anomaly_score" in result
    assert "health_score" in result
    assert "health_status" in result
    assert "fault" in result
    assert "rul_status" in result

    assert "type" in result["fault"]
    assert "confidence" in result["fault"]
    assert "active" in result["fault"]

    assert "true_fault_type" not in result
    assert "true_rul_hours" not in result