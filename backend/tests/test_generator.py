import sys
from pathlib import Path

import numpy as np
import pandas as pd


# Allow imports from backend/src
SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from digital_twin.generator import (
    FAULT_TYPES,
    MissionConfig,
    generate_dataset,
    generate_mission,
)


# ============================================================
# Basic generation
# ============================================================

def test_generate_mission_returns_dataframe():

    config = MissionConfig(
        engine_id="ENG-001",
        mission_id="MIS-0001",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=42,
    )

    df = generate_mission(config)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_expected_columns_exist():

    config = MissionConfig(
        engine_id="ENG-001",
        mission_id="MIS-0001",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=42,
    )

    df = generate_mission(config)

    required_columns = [
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
        "expected_rpm",
        "expected_cht_c",
        "expected_egt_c",
        "expected_oil_pressure_kpa",
        "expected_oil_temperature_c",
        "expected_fuel_flow_lph",
        "expected_vibration_g",
        "expected_injection_timing_deg",
        "true_fault_type",
        "true_fault_active",
        "true_severity",
    ]

    for column in required_columns:
        assert column in df.columns


def test_residual_columns_exist():

    config = MissionConfig(
        engine_id="ENG-001",
        mission_id="MIS-0001",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=42,
    )

    df = generate_mission(config)

    residual_columns = [
        "residual_rpm",
        "residual_cht_c",
        "residual_egt_c",
        "residual_oil_pressure_kpa",
        "residual_oil_temperature_c",
        "residual_fuel_flow_lph",
        "residual_vibration_g",
        "residual_injection_timing_deg",
    ]

    for column in residual_columns:
        assert column in df.columns


# ============================================================
# Residual correctness
# ============================================================

def test_residual_equals_actual_minus_expected():

    config = MissionConfig(
        engine_id="ENG-001",
        mission_id="MIS-0001",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=42,
    )

    df = generate_mission(config)

    valid = df[
        df["rpm"].notna()
        & df["cht_c"].notna()
        & df["egt_c"].notna()
    ]

    assert np.allclose(
        valid["residual_rpm"],
        valid["rpm"] - valid["expected_rpm"],
    )

    assert np.allclose(
        valid["residual_cht_c"],
        valid["cht_c"] - valid["expected_cht_c"],
    )

    assert np.allclose(
        valid["residual_egt_c"],
        valid["egt_c"] - valid["expected_egt_c"],
    )


# ============================================================
# Mission metadata
# ============================================================

def test_mission_metadata_is_correct():

    config = MissionConfig(
        engine_id="ENG-TEST",
        mission_id="MIS-TEST",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=123,
    )

    df = generate_mission(config)

    assert df["engine_id"].nunique() == 1
    assert df["engine_id"].iloc[0] == "ENG-TEST"

    assert df["mission_id"].nunique() == 1
    assert df["mission_id"].iloc[0] == "MIS-TEST"

    assert df["true_fault_type"].nunique() == 1
    assert df["true_fault_type"].iloc[0] == "NORMAL"


# ============================================================
# Fault types
# ============================================================

def test_all_fault_types_can_be_generated():

    for fault_type in FAULT_TYPES:

        config = MissionConfig(
            engine_id="ENG-001",
            mission_id=f"MIS-{fault_type}",
            duration_min=1.0,
            sample_interval_s=1.0,
            fault_type=fault_type,
            seed=42,
        )

        df = generate_mission(config)

        assert len(df) > 0

        assert (
            df["true_fault_type"] == fault_type
        ).all()


def test_normal_mission_has_no_active_fault():

    config = MissionConfig(
        engine_id="ENG-001",
        mission_id="MIS-NORMAL",
        duration_min=1.0,
        sample_interval_s=1.0,
        fault_type="NORMAL",
        seed=42,
    )

    df = generate_mission(config)

    assert (df["true_fault_active"] == 0).all()
    assert (df["true_severity"] == 0).all()


# ============================================================
# Dataset generation
# ============================================================

def test_generate_dataset_creates_requested_missions():

    df = generate_dataset(
        n_missions=10,
        seed=42,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    assert isinstance(df, pd.DataFrame)

    assert (
        df["mission_id"].nunique()
        == 10
    )


def test_generate_dataset_contains_multiple_fault_types():

    df = generate_dataset(
        n_missions=20,
        seed=42,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    fault_types = set(
        df["true_fault_type"].unique()
    )

    assert "NORMAL" in fault_types

    assert len(fault_types) > 1


# ============================================================
# Reproducibility
# ============================================================

def test_same_seed_produces_same_dataset():

    df1 = generate_dataset(
        n_missions=5,
        seed=123,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    df2 = generate_dataset(
        n_missions=5,
        seed=123,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    pd.testing.assert_frame_equal(
        df1,
        df2,
    )


def test_different_seed_produces_different_dataset():

    df1 = generate_dataset(
        n_missions=5,
        seed=123,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    df2 = generate_dataset(
        n_missions=5,
        seed=999,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    assert not df1.equals(df2)
