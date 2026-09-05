"""
Single entry point: raw telemetry dataframe -> fully featured dataframe.

Production flow:

RAW TELEMETRY
      ↓
Digital-Twin expected values
      ↓
Residual features
      ↓
Rolling / trend / lag / EWMA features
      ↓
RUL temporal features
      ↓
AI/ML models

The backend only needs to provide raw telemetry.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.rolling_features import add_rolling_features
from src.features.trend_features import (
    add_slope_features,
    add_rate_of_change,
    add_lag_features,
    add_ewma,
)
from src.features.residual_features import (
    add_relative_residuals,
    add_persistent_bias_flag,
    PRIMARY_WITH_EXPECTED,
)
from src.features.cross_sensor_features import add_cross_sensor_features
from src.features.rul_features import add_rul_temporal_features


# ============================================================================
# RAW TELEMETRY
# ============================================================================

PRIMARY_COLS = [
    "rpm",
    "cht_c",
    "egt_c",
    "oil_pressure_kpa",
    "oil_temperature_c",
    "fuel_flow_lph",
    "vibration_g",
    "injection_timing_deg",
]


# ============================================================================
# DIGITAL-TWIN EXPECTED COLUMNS
# ============================================================================

EXPECTED_COLS = [
    "expected_rpm",
    "expected_cht_c",
    "expected_egt_c",
    "expected_oil_pressure_kpa",
    "expected_oil_temperature_c",
    "expected_fuel_flow_lph",
    "expected_vibration_g",
    "expected_injection_timing_deg",
]


RESIDUAL_COLS = [
    f"residual_{c}"
    for c in PRIMARY_WITH_EXPECTED
]


# ============================================================================
# FEATURE PARAMETERS
# ============================================================================

DEFAULT_ROLL_WINDOWS = [5, 10]
DEFAULT_SLOPE_WINDOW = 10
DEFAULT_LAGS = [1, 3, 5]
DEFAULT_EWMA_SPAN = 5
DEFAULT_BIAS_WINDOW = 15


# ============================================================================
# DIGITAL TWIN
# ============================================================================

def _build_expected_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build Digital-Twin expected telemetry from raw operating conditions.

    This mirrors the healthy baseline used by the synthetic telemetry
    generator.

    The backend therefore sends only raw telemetry and AIML reconstructs
    the healthy expected operating point internally.

    Required operating conditions:

        throttle_pct
        altitude_m
        ambient_temperature_c

    If expected_* columns are already present, they are preserved.
    """

    out = df.copy()

    # ------------------------------------------------------------------------
    # If all expected columns already exist, do nothing.
    # This keeps compatibility with offline/training datasets.
    # ------------------------------------------------------------------------

    if all(c in out.columns for c in EXPECTED_COLS):
        return out

    # ------------------------------------------------------------------------
    # Required operating conditions
    # ------------------------------------------------------------------------

    required = [
        "throttle_pct",
        "altitude_m",
        "ambient_temperature_c",
    ]

    missing_context = [
        c for c in required
        if c not in out.columns
    ]

    if missing_context:
        raise ValueError(
            "Raw telemetry is missing operating-condition columns required "
            "to calculate Digital-Twin expected values: "
            f"{missing_context}"
        )

    throttle = pd.to_numeric(
        out["throttle_pct"],
        errors="coerce",
    ).fillna(0.0)

    altitude = pd.to_numeric(
        out["altitude_m"],
        errors="coerce",
    ).fillna(0.0)

    ambient = pd.to_numeric(
        out["ambient_temperature_c"],
        errors="coerce",
    ).fillna(25.0)

    # ------------------------------------------------------------------------
    # Healthy Digital-Twin baseline
    # ------------------------------------------------------------------------

    # RPM
    expected_rpm = (
        800.0
        + throttle * 28.0
    )

    # CHT
    expected_cht = (
        90.0
        + throttle * 0.9
        + np.maximum(
            0.0,
            ambient - 20.0,
        ) * 0.6
    )

    # EGT
    expected_egt = (
        350.0
        + throttle * 5.2
        + np.maximum(
            0.0,
            ambient - 20.0,
        ) * 1.2
    )

    # Oil pressure
    #
    # Runtime does not have the simulator's internal oil temperature state,
    # so use the measured oil temperature as the closest observable proxy.
    oil_temperature = pd.to_numeric(
        out["oil_temperature_c"],
        errors="coerce",
    ).fillna(90.0)

    expected_oil_pressure = (
        200.0
        + throttle * 3.0
        - np.maximum(
            0.0,
            oil_temperature - 90.0,
        ) * 1.5
    )

    # Oil temperature
    #
    # Runtime cannot reproduce the generator's hidden state exactly.
    # A stable healthy operating-point estimate is therefore used.
    expected_oil_temperature = (
        70.0
        + throttle * 0.05
        + np.maximum(
            0.0,
            ambient - 20.0,
        ) * 0.2
    )

    # Fuel flow
    expected_fuel_flow = (
        4.0
        + throttle * 0.22
    )

    # Vibration
    expected_vibration = (
        0.15
        + (expected_rpm / 4000.0) * 0.15
    )

    # Injection timing
    expected_injection_timing = (
        22.0
        + throttle * 0.03
    )

    # ------------------------------------------------------------------------
    # Write expected columns
    # ------------------------------------------------------------------------

    out["expected_rpm"] = expected_rpm
    out["expected_cht_c"] = expected_cht
    out["expected_egt_c"] = expected_egt
    out["expected_oil_pressure_kpa"] = expected_oil_pressure
    out["expected_oil_temperature_c"] = expected_oil_temperature
    out["expected_fuel_flow_lph"] = expected_fuel_flow
    out["expected_vibration_g"] = expected_vibration
    out["expected_injection_timing_deg"] = expected_injection_timing

    return out


# ============================================================================
# RESIDUAL SAFETY
# ============================================================================

def _ensure_residuals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure Digital-Twin expected values AND raw residual columns exist.

    residual = actual telemetry - Digital-Twin expected value

    Training data:
        expected_* and residual_* already exist, so they are preserved.

    Production raw telemetry:
        expected_* are generated by _build_expected_values()
        residual_* are calculated here.
    """

    out = _build_expected_values(df)

    # ------------------------------------------------------------------------
    # Make sure all expected columns exist.
    # ------------------------------------------------------------------------

    missing_expected = [
        c
        for c in EXPECTED_COLS
        if c not in out.columns
    ]

    if missing_expected:
        raise ValueError(
            "Unable to construct Digital-Twin expected columns: "
            f"{missing_expected}"
        )

    # ------------------------------------------------------------------------
    # Calculate the canonical raw residuals.
    #
    # These are required by:
    #   - relative residual features
    #   - anomaly detection
    #   - health index
    #   - RUL temporal features
    # ------------------------------------------------------------------------

    for actual_col in PRIMARY_COLS:

        expected_col = f"expected_{actual_col}"
        residual_col = f"residual_{actual_col}"

        # Preserve residuals already present in training data.
        if residual_col not in out.columns:

            actual = pd.to_numeric(
                out[actual_col],
                errors="coerce",
            )

            expected = pd.to_numeric(
                out[expected_col],
                errors="coerce",
            )

            out[residual_col] = (
                actual - expected
            )

    # ------------------------------------------------------------------------
    # Final safety check.
    # ------------------------------------------------------------------------

    missing_residuals = [
        c
        for c in RESIDUAL_COLS
        if c not in out.columns
    ]

    if missing_residuals:
        raise ValueError(
            "Unable to construct Digital-Twin residual columns: "
            f"{missing_residuals}"
        )

    return out

# ============================================================================
# MAIN FEATURE PIPELINE
# ============================================================================

def build_features(
    df: pd.DataFrame,
    roll_windows: list[int] = DEFAULT_ROLL_WINDOWS,
    slope_window: int = DEFAULT_SLOPE_WINDOW,
    lags: list[int] = DEFAULT_LAGS,
    ewma_span: int = DEFAULT_EWMA_SPAN,
    bias_window: int = DEFAULT_BIAS_WINDOW,
) -> pd.DataFrame:

    if df is None or df.empty:
        raise ValueError("Input dataframe is empty.")

    df = df.copy()

    # ------------------------------------------------------------------------
    # Required identifiers
    # ------------------------------------------------------------------------

    if "mission_id" not in df.columns:
        df["mission_id"] = "API-MISSION"

    if "timestamp_s" not in df.columns:
        df["timestamp_s"] = np.arange(len(df), dtype=float)

    # ------------------------------------------------------------------------
    # Sort chronologically inside mission
    # ------------------------------------------------------------------------

    df = df.sort_values(
        ["mission_id", "timestamp_s"]
    ).reset_index(drop=True)

    # ------------------------------------------------------------------------
    # 1. Construct Digital-Twin expected values
    # ------------------------------------------------------------------------

    df = _ensure_residuals(df)

    # ------------------------------------------------------------------------
    # 2. Calculate residuals FIRST
    #
    # This is important.
    #
    # Raw telemetry
    #      ↓
    # Expected telemetry
    #      ↓
    # Residuals
    #      ↓
    # Temporal features
    # ------------------------------------------------------------------------

    df = add_relative_residuals(df)

    # ------------------------------------------------------------------------
    # 3. Persistent residual bias
    # ------------------------------------------------------------------------

    df = add_persistent_bias_flag(
        df,
        window=bias_window,
    )

    # ------------------------------------------------------------------------
    # 4. Primary + residual temporal features
    # ------------------------------------------------------------------------

    feature_cols = PRIMARY_COLS + RESIDUAL_COLS

    df = add_rolling_features(
        df,
        feature_cols,
        roll_windows,
    )

    df = add_slope_features(
        df,
        feature_cols,
        slope_window,
    )

    df = add_rate_of_change(
        df,
        feature_cols,
    )

    df = add_lag_features(
        df,
        feature_cols,
        lags,
    )

    df = add_ewma(
        df,
        feature_cols,
        ewma_span,
    )

    # ------------------------------------------------------------------------
    # 5. Cross-sensor relationships
    # ------------------------------------------------------------------------

    df = add_cross_sensor_features(df)

    # ------------------------------------------------------------------------
    # 6. RUL-specific degradation trajectory features
    # ------------------------------------------------------------------------

    df = add_rul_temporal_features(df)

    return df


# ============================================================================
# MODEL FEATURE COLUMNS
# ============================================================================

def get_model_feature_columns(
    df: pd.DataFrame,
) -> list[str]:

    exclude_prefixes = (
        "true_",
        "eol_",
    )

    exclude_exact = {
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_phase",
    }

    return [
        c
        for c in df.columns
        if c not in exclude_exact
        and not c.startswith(exclude_prefixes)
    ]


# ============================================================================
# ANOMALY FEATURE COLUMNS
# ============================================================================

def get_anomaly_feature_columns(
    df: pd.DataFrame,
) -> list[str]:

    keep_markers = (
        "residual_",
        "rel_residual_",
        "_ratio",
        "_per_rpm",
        "_delta",
        "bias_consistency",
    )

    exclude_exact = {
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_phase",
    }

    exclude_prefixes = (
        "true_",
        "eol_",
        "rul_",
    )

    cols = []

    for c in df.columns:

        if c in exclude_exact:
            continue

        if c.startswith(exclude_prefixes):
            continue

        if any(
            marker in c
            for marker in keep_markers
        ):
            cols.append(c)

    return cols