"""
Split by MISSION, not by row. A mission's timesteps must never be split
across train/val/test - that would leak the future into training (the model
would learn "this exact mission" rather than generalizable fault behavior).

Stratified by fault type so every split has a representative mix.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Tuple


def split_missions(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    seed: int = 42,
    mission_col: str = "mission_id",
    fault_col: str = "true_fault_type",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    mission_labels = df.groupby(mission_col)[fault_col].first()
    train_ids, val_ids, test_ids = [], [], []

    for fault_type, group in mission_labels.groupby(mission_labels):
        ids = group.index.to_numpy().copy()
        rng.shuffle(ids)
        n = len(ids)
        n_train = max(1, int(round(n * train_frac)))
        n_val = max(1, int(round(n * val_frac))) if n > 2 else 0
        train_ids.extend(ids[:n_train])
        val_ids.extend(ids[n_train:n_train + n_val])
        test_ids.extend(ids[n_train + n_val:])

    train_df = df[df[mission_col].isin(train_ids)].reset_index(drop=True)
    val_df = df[df[mission_col].isin(val_ids)].reset_index(drop=True)
    test_df = df[df[mission_col].isin(test_ids)].reset_index(drop=True)

    return train_df, val_df, test_df


def split_summary(train_df, val_df, test_df, fault_col="true_fault_type", mission_col="mission_id"):
    rows = []
    for name, d in [("train", train_df), ("val", val_df), ("test", test_df)]:
        n_missions = d[mission_col].nunique()
        n_rows = len(d)
        rows.append({"split": name, "missions": n_missions, "rows": n_rows})
    return pd.DataFrame(rows)
