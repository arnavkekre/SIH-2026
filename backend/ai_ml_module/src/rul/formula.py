from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


MAX_RUL_SECONDS = 3600.0
EOL_HEALTH_SCORE = 0.0
SLOPE_WINDOW = 10
MIN_NEGATIVE_HEALTH_SLOPE = 0.01


def _safe_numeric(values: Iterable[float]) -> np.ndarray:
    return (
        pd.to_numeric(pd.Series(values), errors="coerce")
        .fillna(0.0)
        .to_numpy(float)
    )


def estimate_rul_seconds(
    df: pd.DataFrame,
    health_score: Iterable[float],
    anomaly_score: Iterable[float],
    fault_probability: Iterable[float],
) -> np.ndarray:

    health = np.clip(_safe_numeric(health_score), 0, 100)
    anomaly = np.clip(_safe_numeric(anomaly_score), 0, 1)
    fault = np.clip(_safe_numeric(fault_probability), 0, 1)

    if not (
        len(df)
        == len(health)
        == len(anomaly)
        == len(fault)
    ):
        raise ValueError("RUL inputs must have matching lengths.")

    # Current degradation/risk state
    risk = np.maximum.reduce([
        1.0 - health / 100.0,
        anomaly,
        fault,
    ])

    state_rul = MAX_RUL_SECONDS * (1.0 - risk)

    timestamps = _safe_numeric(
        df["timestamp_s"]
        if "timestamp_s" in df.columns
        else np.arange(len(df))
    )

    result = state_rul.copy()

    groups = (
        df.groupby("mission_id", sort=False).groups.values()
        if "mission_id" in df.columns
        else [df.index]
    )

    # Trend-based RUL
    for group_indices in groups:

        positions = np.asarray(
            list(group_indices),
            dtype=int
        )
        positions.sort()

        for i, pos in enumerate(positions):

            window = positions[
                max(0, i - SLOPE_WINDOW + 1):
                i + 1
            ]

            if len(window) < 3:
                continue

            x = timestamps[window]
            y = health[window]

            valid = np.isfinite(x) & np.isfinite(y)

            if valid.sum() < 3:
                continue

            x = x[valid]
            y = y[valid]

            if x[-1] <= x[0]:
                continue

            slope = float(
                np.polyfit(x, y, 1)[0]
            )

            # Only use the trend estimate when health is actually declining.
            if slope < -MIN_NEGATIVE_HEALTH_SLOPE:

                trend_rul = max(
                    0.0,
                    (
                        health[pos]
                        - EOL_HEALTH_SCORE
                    )
                    / (-slope),
                )

                result[pos] = min(
                    result[pos],
                    trend_rul,
                )

    return np.clip(
        result,
        0.0,
        MAX_RUL_SECONDS,
    )


def apply_rul_gate(
    rul_seconds: np.ndarray,
    health_score: Iterable[float],
    fault_probability: Iterable[float],
    health_threshold: float = 80.0,
    fault_threshold: float = 0.30,
):
    rul = np.asarray(
        rul_seconds,
        dtype=float,
    )

    health = np.clip(
        _safe_numeric(health_score),
        0,
        100,
    )

    fault = np.clip(
        _safe_numeric(fault_probability),
        0,
        1,
    )

    gate = (
        (health < health_threshold)
        | (fault >= fault_threshold)
    )

    gated = np.where(
        gate,
        rul,
        np.nan,
    )

    status = np.full(
        len(rul),
        "NOT_APPLICABLE",
        dtype=object,
    )

    active = gate & np.isfinite(gated)

    status[active] = np.where(
        gated[active] <= 10,
        "CRITICAL",
        np.where(
            gated[active] <= 30,
            "WARNING",
            "NORMAL",
        ),
    )

    return gated, status