"""
Per-fault precision/recall/F1 (not just a single blended number - a judge
will ask "which faults does it actually catch"), plus macro averages and
Hamming loss for the multi-label set as a whole.
"""
from __future__ import annotations
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, hamming_loss


def evaluate_fault_classifier(Y_true: pd.DataFrame, Y_pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code in Y_true.columns:
        yt, yp = Y_true[code], Y_pred[code]
        rows.append({
            "fault": code,
            "n_positive": int(yt.sum()),
            "precision": precision_score(yt, yp, zero_division=0),
            "recall": recall_score(yt, yp, zero_division=0),
            "f1": f1_score(yt, yp, zero_division=0),
        })
    report = pd.DataFrame(rows)
    macro = {
        "fault": "MACRO_AVG",
        "n_positive": int(Y_true.sum().sum()),
        "precision": report["precision"].mean(),
        "recall": report["recall"].mean(),
        "f1": report["f1"].mean(),
    }
    report = pd.concat([report, pd.DataFrame([macro])], ignore_index=True)
    report.attrs["hamming_loss"] = hamming_loss(Y_true, Y_pred)
    return report