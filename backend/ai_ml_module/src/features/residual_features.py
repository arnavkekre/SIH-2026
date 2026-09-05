"""
These are the features that make this "Digital-Twin-assisted AI" rather than
plain ML on raw sensors. A relative residual normalizes for operating point:
a 20-degree EGT deviation means something different at idle vs. full throttle.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

PRIMARY_WITH_EXPECTED = [
    "rpm", "cht_c", "egt_c", "oil_pressure_kpa", "oil_temperature_c",
    "fuel_flow_lph", "vibration_g", "injection_timing_deg",
]


def add_relative_residuals(df: pd.DataFrame, cols: list[str] = PRIMARY_WITH_EXPECTED) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        res_col, exp_col = f"residual_{col}", f"expected_{col}"
        if res_col in df.columns and exp_col in df.columns:
            df[f"rel_{res_col}"] = (df[res_col] / df[exp_col].replace(0, np.nan)).fillna(0)
    return df


def add_persistent_bias_flag(df: pd.DataFrame, cols: list[str] = PRIMARY_WITH_EXPECTED,
                              window: int = 15, group_col: str = "mission_id") -> pd.DataFrame:
    """
    Flags SENSOR_DRIFT-like behavior: a residual that stays consistently
    non-zero in ONE direction over a long window, without the corresponding
    rate-of-change spikes you'd expect from a real mechanical fault.
    Computed as: rolling mean of residual sign-consistency.
    """
    df = df.copy()
    for col in cols:
        res_col = f"residual_{col}"
        if res_col not in df.columns:
            continue
        signed = np.sign(df[res_col])
        df[f"{res_col}_bias_consistency_{window}"] = (
            signed.groupby(df[group_col]).transform(
                lambda s: s.rolling(window, min_periods=1).mean()
            )
        )  # close to +1 or -1 = persistent one-directional bias (drift-like)
    return df
