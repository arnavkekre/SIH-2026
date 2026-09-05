"""
Rolling statistics computed PER MISSION (groupby mission_id) so one mission's
window never bleeds into another's. min_periods=1 so early-mission rows still
get a value (based on whatever history exists so far) rather than NaN.
"""
from __future__ import annotations
import pandas as pd


def add_rolling_features(df: pd.DataFrame, cols: list[str], windows: list[int],
                          group_col: str = "mission_id") -> pd.DataFrame:
    df = df.copy()
    new_cols = {}
    for col in cols:
        if col not in df.columns:
            continue
        grouped = df.groupby(group_col)[col]
        for w in windows:
            new_cols[f"{col}_roll_mean_{w}"] = grouped.transform(lambda s: s.rolling(w, min_periods=1).mean())
            new_cols[f"{col}_roll_std_{w}"] = grouped.transform(lambda s: s.rolling(w, min_periods=1).std()).fillna(0)
            new_cols[f"{col}_roll_min_{w}"] = grouped.transform(lambda s: s.rolling(w, min_periods=1).min())
            new_cols[f"{col}_roll_max_{w}"] = grouped.transform(lambda s: s.rolling(w, min_periods=1).max())
    return pd.concat([df, pd.DataFrame(new_cols, index=df.index)], axis=1)
