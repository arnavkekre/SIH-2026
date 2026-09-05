"""
Multi-label, not multi-class: two faults can co-occur (e.g. OVERHEATING_TREND
and COOLING_DEGRADATION are correlated, not mutually exclusive), so we train
one independent binary classifier per fault code rather than a single softmax
over 8 classes. Current synthetic missions only inject one dominant fault at
a time, but the architecture supports co-occurring faults once the generator
is extended to inject combinations.
"""
from __future__ import annotations
import pandas as pd

FAULT_CODES = [
    "MISFIRE",
    "INJECTOR_ABNORMALITY",
    "COOLING_DEGRADATION",
    "LUBRICATION_ISSUE",
    "SENSOR_DRIFT",
    "COMBUSTION_INSTABILITY",
    "OVERHEATING_TREND",
    "ABNORMAL_VIBRATION",
]


def build_multilabel_targets(df: pd.DataFrame, severity_threshold: float = 0.05,
                              severity_col: str = "true_effective_severity") -> pd.DataFrame:
    """
    A row is a positive label for a fault code if that fault is the mission's
    injected fault type AND its EFFECTIVE (actually-detectable) severity has
    crossed a minimum threshold at that timestep. Uses true_effective_severity,
    not true_severity - the latter is a smooth underlying degradation ramp
    used for RUL/health-index ground truth, but doesn't reflect that some
    faults (MISFIRE) only manifest stochastically, or (SENSOR_DRIFT)
    accumulate gradually as a bias rather than tracking the ramp directly.
    Falls back to true_severity if the effective column isn't present, for
    compatibility with older generated datasets.
    """
    col = severity_col if severity_col in df.columns else "true_severity"
    targets = pd.DataFrame(index=df.index)
    for code in FAULT_CODES:
        targets[code] = (
            (df["true_fault_type"] == code) & (df[col] >= severity_threshold)
        ).astype(int)
    return targets