"""
Trend-shape features. These matter more than raw rolling stats for catching
GRADUAL degradation (OVERHEATING_TREND, COOLING_DEGRADATION, LUBRICATION_ISSUE)
since those faults are defined by their trajectory, not a single bad reading.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _slope(values: np.ndarray) -> float:
    if len(values) < 2 or np.all(np.isnan(values)):
        return 0.0
    x = np.arange(len(values))
    mask = ~np.isnan(values)
    if mask.sum() < 2:
        return 0.0
    return float(np.polyfit(x[mask], values[mask], 1)[0])


def add_slope_features(df: pd.DataFrame, cols: list[str], window: int = 10,
                        group_col: str = "mission_id") -> pd.DataFrame:
    df = df.copy()
    new_cols = {}
    for col in cols:
        if col not in df.columns:
            continue
        new_cols[f"{col}_slope_{window}"] = (
            df.groupby(group_col)[col]
            .transform(lambda s: s.rolling(window, min_periods=2).apply(_slope, raw=True))
            .fillna(0)
        )
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)


def add_rate_of_change(df: pd.DataFrame, cols: list[str], group_col: str = "mission_id") -> pd.DataFrame:
    df = df.copy()
    new_cols = {}
    for col in cols:
        if col not in df.columns:
            continue
        new_cols[f"{col}_roc"] = df.groupby(group_col)[col].diff().fillna(0)
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)


def add_lag_features(df: pd.DataFrame, cols: list[str], lags: list[int] = [1, 3, 5],
                      group_col: str = "mission_id") -> pd.DataFrame:
    df = df.copy()
    new_cols = {}
    for col in cols:
        if col not in df.columns:
            continue
        for lag in lags:
            shifted = df.groupby(group_col)[col].shift(lag)
            new_cols[f"{col}_lag{lag}"] = shifted.bfill()
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)


def add_ewma(df: pd.DataFrame, cols: list[str], span: int = 5,
             group_col: str = "mission_id") -> pd.DataFrame:
    df = df.copy()
    new_cols = {}
    for col in cols:
        if col not in df.columns:
            continue
        new_cols[f"{col}_ewma{span}"] = df.groupby(group_col)[col].transform(
            lambda s: s.ewm(span=span, adjust=False).mean()
        )
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
