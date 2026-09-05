"""
RUL-specific temporal degradation features for SIH PS54.

These features are derived only from observable telemetry / Digital Twin
residuals and are computed independently inside each mission.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


RUL_RESIDUALS = [
    "residual_rpm",
    "residual_cht_c",
    "residual_egt_c",
    "residual_oil_pressure_kpa",
    "residual_oil_temperature_c",
    "residual_fuel_flow_lph",
    "residual_vibration_g",
    "residual_injection_timing_deg",
]

# Approximate healthy residual scales, used only for normalization.
# They prevent a large-unit sensor (RPM) from dominating the aggregate.
RESIDUAL_SCALES = {
    "residual_rpm": 30.0,
    "residual_cht_c": 5.0,
    "residual_egt_c": 15.0,
    "residual_oil_pressure_kpa": 12.0,
    "residual_oil_temperature_c": 4.0,
    "residual_fuel_flow_lph": 2.0,
    "residual_vibration_g": 0.08,
    "residual_injection_timing_deg": 1.0,
}


def _safe_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)


def add_rul_temporal_features(
    df: pd.DataFrame,
    short_window: int = 5,
    trend_window: int = 10,
    long_window: int = 20,
) -> pd.DataFrame:
    """Add physically interpretable degradation-proxy features per mission."""
    out = df.copy()
    out = out.sort_values(["mission_id", "timestamp_s"]).copy()

    residual_cols = [c for c in RUL_RESIDUALS if c in out.columns]

    if not residual_cols:
        raise ValueError("No expected RUL residual columns found.")

    # 1) Normalize residuals by approximate sensor scale.
    norm_cols = []
    for col in residual_cols:
        name = f"rul_norm_{col.removeprefix('residual_')}"
        out[name] = _safe_series(out[col]) / RESIDUAL_SCALES[col]
        norm_cols.append(name)

    # 2) Aggregate current deviation magnitude.
    # RMS is robust to positive/negative residual direction.
    out["rul_residual_rms"] = np.sqrt(
        out[norm_cols].pow(2).mean(axis=1)
    )
    out["rul_residual_abs_mean"] = out[norm_cols].abs().mean(axis=1)
    out["rul_residual_max_abs"] = out[norm_cols].abs().max(axis=1)

    group = out.groupby("mission_id", sort=False)

    # 3) Mission-local rolling degradation.
    for window in (short_window, long_window):
        out[f"rul_rms_roll_mean_{window}"] = group["rul_residual_rms"].transform(
            lambda s: s.rolling(window, min_periods=2).mean()
        )
        out[f"rul_rms_roll_std_{window}"] = group["rul_residual_rms"].transform(
            lambda s: s.rolling(window, min_periods=2).std()
        ).fillna(0.0)

    # 4) Mission-local slope of aggregate degradation.
    # Use timestamp so this remains correct if sample interval changes later.
    def slope(series: pd.Series) -> pd.Series:
        x = np.arange(len(series), dtype=float)
        values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
        result = np.full(len(values), np.nan, dtype=float)
        for i in range(len(values)):
            lo = max(0, i - trend_window + 1)
            y = values[lo : i + 1]
            xx = x[lo : i + 1]
            valid = np.isfinite(y)
            if valid.sum() >= 3:
                result[i] = np.polyfit(xx[valid], y[valid], 1)[0]
        return pd.Series(result, index=series.index)

    out["rul_degradation_slope"] = group["rul_residual_rms"].transform(slope)
    out["rul_degradation_slope"] = out["rul_degradation_slope"].fillna(0.0)

    # 5) Persistence: fraction of recent samples showing elevated deviation.
    threshold = 1.0
    out["rul_abnormal_fraction"] = group["rul_residual_rms"].transform(
        lambda s: s.gt(threshold).rolling(short_window, min_periods=2).mean()
    )

    # 6) Accumulated degradation pressure. Keep mission-local cumulative sum;
    # normalize by elapsed samples so it is comparable across mission lengths.
    positive_excess = (out["rul_residual_rms"] - threshold).clip(lower=0.0)
    out["rul_accumulated_excess"] = positive_excess.groupby(
        out["mission_id"], sort=False
    ).cumsum()

    # 7) Momentum: recent deviation relative to the earlier part of the mission.
    baseline = group["rul_residual_rms"].transform(
        lambda s: s.rolling(long_window, min_periods=2).mean()
    )
    out["rul_deviation_momentum"] = (
        out["rul_rms_roll_mean_" + str(short_window)] - baseline
    )

    # 8) Clean numerical output.
    generated = [c for c in out.columns if c.startswith("rul_")]
    out[generated] = out[generated].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return out
