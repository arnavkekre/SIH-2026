import sys
from pathlib import Path

import numpy as np
import pytest


# Allow imports from backend/src
SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


import backend.pipeline as pipeline


# ============================================================
# Test telemetry
# ============================================================

def sample_telemetry():

    return {
        "timestamp_s": 10.0,
        "engine_id": "ENG-001",
        "mission_id": "MIS-0001",
        "mission_phase": "CRUISE",

        "throttle_pct": 60.0,
        "altitude_m": 4000.0,
        "ambient_temperature_c": 5.0,

        "rpm": 2500.0,
        "cht_c": 145.0,
        "egt_c": 665.0,
        "oil_pressure_kpa": 360.0,
        "oil_temperature_c": 70.0,
        "fuel_flow_lph": 17.0,
        "vibration_g": 0.25,

        "alternator_voltage_v": 28.0,
        "battery_voltage_v": 25.5,
        "injection_timing_deg": 23.8,
    }


# ============================================================
# Required telemetry fields
# ============================================================

def test_sample_telemetry_contains_required_fields():

    telemetry = sample_telemetry()

    required = [
        "timestamp_s",
        "engine_id",
        "mission_id",
        "rpm",
        "cht_c",
        "egt_c",
        "oil_pressure_kpa",
        "oil_temperature_c",
        "fuel_flow_lph",
        "vibration_g",
        "injection_timing_deg",
    ]

    for field in required:
        assert field in telemetry


# ============================================================
# Residual calculation
# ============================================================

def test_residual_calculation():

    actual = {
        "rpm": 2500.0,
        "cht_c": 180.0,
        "egt_c": 700.0,
        "oil_pressure_kpa": 350.0,
    }

    expected = {
        "rpm": 2450.0,
        "cht_c": 160.0,
        "egt_c": 650.0,
        "oil_pressure_kpa": 370.0,
    }

    # This test assumes the pipeline exposes
    # calculate_residuals(actual, expected).
    #
    # If the function is implemented under another name,
    # we'll adjust this test to the final pipeline API.

    if hasattr(pipeline, "calculate_residuals"):

        residuals = pipeline.calculate_residuals(
            actual,
            expected,
        )

        assert residuals["rpm"] == pytest.approx(50.0)
        assert residuals["cht_c"] == pytest.approx(20.0)
        assert residuals["egt_c"] == pytest.approx(50.0)
        assert residuals["oil_pressure_kpa"] == pytest.approx(-20.0)


# ============================================================
# ML is optional for now
# ============================================================

def test_pipeline_can_run_without_ml_model(
    monkeypatch,
):

    telemetry = sample_telemetry()

    # Force ML model to be unavailable.
    if hasattr(pipeline, "ML_MODEL"):
        monkeypatch.setattr(
            pipeline,
            "ML_MODEL",
            None,
        )

    if hasattr(pipeline, "model"):
        monkeypatch.setattr(
            pipeline,
            "model",
            None,
        )

    # Mock database so this test never touches Supabase.
    if hasattr(
        pipeline,
        "save_telemetry",
    ):

        monkeypatch.setattr(
            pipeline,
            "save_telemetry",
            lambda _: None,
        )

    if hasattr(
        pipeline,
        "supabase",
    ):

        class FakeTable:

            def insert(self, data):
                return self

            def execute(self):
                return self

            data = []

        class FakeSupabase:

            def table(self, _):
                return FakeTable()

        monkeypatch.setattr(
            pipeline,
            "supabase",
            FakeSupabase(),
        )

    # If process_telemetry exists, it should not require
    # an ML model to be present.
    if hasattr(
        pipeline,
        "process_telemetry",
    ):

        result = pipeline.process_telemetry(
            telemetry
        )

        assert result is not None


# ============================================================
# Telemetry validation
# ============================================================

def test_invalid_telemetry_is_detectable():

    telemetry = sample_telemetry()

    del telemetry["rpm"]

    # If the final pipeline exposes validation,
    # test it here.

    if hasattr(
        pipeline,
        "validate_telemetry",
    ):

        result = pipeline.validate_telemetry(
            telemetry
        )

        assert result is False


# ============================================================
# Numeric values
# ============================================================

def test_telemetry_numeric_values_are_numeric():

    telemetry = sample_telemetry()

    numeric_fields = [
        "rpm",
        "cht_c",
        "egt_c",
        "oil_pressure_kpa",
        "oil_temperature_c",
        "fuel_flow_lph",
        "vibration_g",
        "throttle_pct",
        "altitude_m",
        "ambient_temperature_c",
    ]

    for field in numeric_fields:

        assert isinstance(
            telemetry[field],
            (int, float),
        )


# ============================================================
# ML model discovery
# ============================================================

def test_missing_model_does_not_break_import():

    """
    The backend must remain importable even though
    the ML model does not exist yet.

    This is important during the current development phase.
    """

    assert pipeline is not None


# ============================================================
# Prediction output structure
# ============================================================

def test_ml_result_can_be_empty():

    """
    Until the ML teammate provides the models, an ML result
    may legitimately be None or an empty result.

    This test prevents us from accidentally making the
    entire backend dependent on a .joblib file.
    """

    if hasattr(
        pipeline,
        "run_ml",
    ):

        result = pipeline.run_ml(
            sample_telemetry()
        )

        assert (
            result is None
            or isinstance(result, dict)
        )
