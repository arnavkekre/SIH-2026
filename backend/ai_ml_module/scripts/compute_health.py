"""
Usage:
    python scripts/compute_health.py --features data/features --anomaly-model models/anomaly/anomaly_detector.joblib --fault-model models/faults/fault_classifier.joblib

Since the health index is a FORMULA (not trained), we validate it by checking
rank correlation against the simulator's ground-truth degradation
(true_degradation_health) - a formula that doesn't track known ground truth
even directionally would be a red flag worth catching before the demo.
"""
import argparse
import sys
import os
import joblib
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.degradation.degradation_score import score_health
from src.features.feature_pipeline import get_model_feature_columns, get_anomaly_feature_columns

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=str, default="data/features")
    parser.add_argument("--anomaly-model", type=str, default="models/anomaly/anomaly_detector.joblib")
    parser.add_argument("--fault-model", type=str, default="models/faults/fault_classifier.joblib")
    args = parser.parse_args()

    val = pd.read_csv(f"{args.features}/val.csv")

    anomaly_detector = joblib.load(args.anomaly_model)
    fault_classifier = joblib.load(args.fault_model)

    anomaly_scores = anomaly_detector.score(val)["anomaly_score"]
    fault_proba = fault_classifier.predict_proba(val[fault_classifier.feature_cols_])

    health = score_health(val, anomaly_scores, fault_proba)

    print("=== Health index distribution ===")
    print(health["health_status"].value_counts())
    print()
    print(health[["health_score", "component_anomaly", "component_fault",
                  "component_residual", "component_trend"]].describe().round(2))

    corr = health["health_score"].corr(val["true_degradation_health"], method="spearman")
    print(f"\nSpearman rank correlation vs. ground-truth degradation: {corr:.3f}")
    print("(should be strongly positive - both should agree on WHICH rows are worse, "
          "even if the absolute scale differs)")

    fault_missions = val[val["true_fault_type"] != "NORMAL"]["mission_id"].unique()
    if len(fault_missions) > 0:
        mid = fault_missions[0]
        mask = val["mission_id"] == mid
        mission_view = pd.DataFrame({
            "timestamp_s": val.loc[mask, "timestamp_s"].values,
            "true_severity": val.loc[mask, "true_severity"].values,
            "health_score": health.loc[mask, "health_score"].values,
            "health_status": health.loc[mask, "health_status"].values,
        })
        print(f"\n=== Health trajectory for mission {mid} ({val.loc[mask, 'true_fault_type'].iloc[0]}) ===")
        print(mission_view.iloc[::5].to_string(index=False))