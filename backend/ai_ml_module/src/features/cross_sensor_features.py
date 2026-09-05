"""
Ratios that encode known engine physics relationships. A fault that affects
one sensor's ABSOLUTE value but keeps these ratios normal is a different
signature than a fault that breaks the ratio itself.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def add_cross_sensor_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    eps = 1e-6

    df["egt_cht_ratio"] = df["egt_c"] / (df["cht_c"] + eps)
    df["fuel_per_rpm"] = df["fuel_flow_lph"] / (df["rpm"] + eps)
    df["vibration_per_rpm"] = df["vibration_g"] / (df["rpm"] + eps)
    df["oil_pressure_per_rpm"] = df["oil_pressure_kpa"] / (df["rpm"] + eps)
    df["cht_ambient_delta"] = df["cht_c"] - df["ambient_temperature_c"]
    df["egt_ambient_delta"] = df["egt_c"] - df["ambient_temperature_c"]

    return df.replace([np.inf, -np.inf], 0).fillna(0)
