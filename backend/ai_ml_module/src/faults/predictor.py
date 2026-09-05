"""
Turns raw per-fault probabilities into the API-shaped output: top fault +
severity band. This is what feeds the P4 dashboard's fault_prediction block.
"""
from __future__ import annotations
import yaml
import pandas as pd


def load_severity_bands(config_path: str = "configs/fault_config.yaml") -> dict:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg["severity_bands"]


def severity_label(probability: float, bands: dict) -> str:
    for label, (lo, hi) in bands.items():
        if lo <= probability < hi or (label == "HIGH" and probability >= hi):
            return label
    return "LOW"


def top_fault_per_row(proba_df: pd.DataFrame, min_threshold: float = 0.3,
                       bands: dict | None = None) -> pd.DataFrame:
    """Returns one row per input: top_fault code (or None), its probability, and severity band."""
    bands = bands or {"LOW": [0.0, 0.4], "MEDIUM": [0.4, 0.7], "HIGH": [0.7, 1.0]}
    top_fault = proba_df.idxmax(axis=1)
    top_prob = proba_df.max(axis=1)

    result = pd.DataFrame({
        "top_fault": top_fault.where(top_prob >= min_threshold, other=None),
        "top_fault_probability": top_prob,
    })
    result["severity"] = result["top_fault_probability"].apply(lambda p: severity_label(p, bands))
    result.loc[result["top_fault"].isna(), "severity"] = "LOW"
    return result