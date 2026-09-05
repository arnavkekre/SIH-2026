"""
Ties together the Phase 3 anomaly detector and Phase 4 fault classifier
outputs into the single health index formula. This is what the inference
pipeline (Phase 7) will call for every incoming row.
"""
from __future__ import annotations
import yaml
import pandas as pd

from src.degradation.health_index import compute_health_index


def load_degradation_config(path: str = "configs/model_config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["degradation"]


def load_health_bands(path: str = "configs/fault_config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)["health_status_bands"]


def score_health(
    df: pd.DataFrame,
    anomaly_score: pd.Series,
    fault_proba_df: pd.DataFrame,
    config_path: str = "configs/model_config.yaml",
    bands_path: str = "configs/fault_config.yaml",
) -> pd.DataFrame:
    cfg = load_degradation_config(config_path)
    bands = load_health_bands(bands_path)
    return compute_health_index(
        df, anomaly_score, fault_proba_df,
        weights=cfg["weights"],
        residual_scale=cfg["residual_severity_scale"],
        trend_scale=cfg["trend_severity_scale"],
        health_bands=bands,
    )