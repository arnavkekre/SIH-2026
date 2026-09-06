"""
Digital-Twin residual features.

Relative residuals normalize sensor deviation against the healthy
Digital-Twin operating point.

Persistent bias features capture sustained one-directional residuals
that are useful for detecting sensor-drift-like behavior.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


PRIMARY_WITH_EXPECTED = [
    "rpm",
    "cht_c",
    "egt_c",
    "oil_pressure_kpa",
    "oil_temperature_c",
    "fuel_flow_lph",
    "vibration_g",
    "injection_timing_deg",
]


def add_relative_residuals(
    df: pd.DataFrame,
    cols: list[str] = PRIMARY_WITH_EXPECTED,
) -> pd.DataFrame:
    """
    Add relative residuals:

        relative residual = residual / expected

    Invalid, missing, or zero-denominator values are converted to 0.
    """

    out = df.copy()

    for col in cols:
        res_col = f"residual_{col}"
        exp_col = f"expected_{col}"

        if res_col not in out.columns:
            continue

        if exp_col not in out.columns:
            continue

        residual = pd.to_numeric(
            out[res_col],
            errors="coerce",
        )

        expected = pd.to_numeric(
            out[exp_col],
            errors="coerce",
        )

        denominator = expected.replace(
            [0.0, -0.0],
            np.nan,
        )

        relative = (
            residual / denominator
        ).replace(
            [np.inf, -np.inf],
            np.nan,
        )

        out[f"rel_{res_col}"] = (
            relative.fillna(0.0)
        )

    return out


def add_persistent_bias_flag(
    df: pd.DataFrame,
    cols: list[str] = PRIMARY_WITH_EXPECTED,
    window: int = 15,
    group_col: str = "mission_id",
) -> pd.DataFrame:
    """
    Create persistent residual-bias features.

    A value near +1 or -1 indicates that the residual has remained
    predominantly in one direction over the rolling window.

    Missing/non-numeric residuals are safely converted to NaN and then
    treated as zero contribution to the sign-consistency calculation.
    """

    out = df.copy()

    if window < 1:
        raise ValueError(
            "window must be >= 1"
        )

    if group_col not in out.columns:
        out[group_col] = "API-MISSION"

    for col in cols:

        res_col = f"residual_{col}"

        if res_col not in out.columns:
            continue

        # ------------------------------------------------------------
        # Force residuals to numeric.
        # This prevents None/string/object values from reaching np.sign.
        # ------------------------------------------------------------

        residual = pd.to_numeric(
            out[res_col],
            errors="coerce",
        )

        residual = residual.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        signed = np.sign(
            residual.fillna(0.0)
        )

        # ------------------------------------------------------------
        # Calculate rolling sign consistency separately per mission.
        # ------------------------------------------------------------

        consistency = (
            signed
            .groupby(out[group_col], sort=False)
            .transform(
                lambda s: s.rolling(
                    window=window,
                    min_periods=1,
                ).mean()
            )
        )

        out[
            f"{res_col}_bias_consistency_{window}"
        ] = (
            consistency
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .fillna(0.0)
        )

    return out