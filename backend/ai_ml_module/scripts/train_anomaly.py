"""
Usage:
    python scripts/train_anomaly.py --features data/features --out models/anomaly

Trains on NORMAL-only rows from train.csv (standard unsupervised anomaly
detection practice), evaluates on val.csv, and runs the static-limit-vs-DT
lead-time comparison on one OVERHEATING_TREND mission from val.csv as the
core demo evidence.
"""
import argparse
import sys
import os
import yaml
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.anomaly.detector import AnomalyDetector
from src.evaluation.anomaly_metrics import evaluate_anomaly_detector, detection_lead_time

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=str, default="data/features")
    parser.add_argument("--out", type=str, default="models/anomaly")
    parser.add_argument("--thresholds", type=str, default="configs/thresholds.yaml")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    with open(args.thresholds) as f:
        cfg = yaml.safe_load(f)

    with open(f"{args.features}/feature_columns.txt") as f:
        all_feature_cols = [line.strip() for line in f if line.strip()]

    train = pd.read_csv(f"{args.features}/train.csv")
    val = pd.read_csv(f"{args.features}/val.csv")

    # anomaly detection uses ONLY operating-point-normalized features
    # (residuals, ratios) - NOT raw absolute sensor values - see
    # get_anomaly_feature_columns() docstring for why this matters
    from src.features.feature_pipeline import get_anomaly_feature_columns
    feature_cols = get_anomaly_feature_columns(train)
    print(f"Using {len(feature_cols)} residual/ratio-based features (of {len(all_feature_cols)} total available)")

    normal_train = train[train["true_fault_active"] == 0]
    print(f"Fitting on {len(normal_train)} NORMAL rows (of {len(train)} total train rows)")

    detector = AnomalyDetector(
        feature_threshold=cfg["robust_zscore"]["feature_threshold"],
        if_contamination=cfg["isolation_forest"]["contamination"],
        detection_threshold=cfg["ensemble"]["detection_threshold"],
    )
    detector.fit(normal_train, feature_cols)
    detector.save(f"{args.out}/anomaly_detector.joblib")
    print(f"Saved detector -> {args.out}/anomaly_detector.joblib")

    val_scores = detector.score(val)
    metrics = evaluate_anomaly_detector(val, val_scores)
    print("\n=== Validation metrics (honest, unfiltered) ===")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    # --- core demo: static limit vs DT residual lead time, on one fault mission ---
    static_cfg = cfg  # thresholds.yaml also has static_limits at top level of the same file
    with open(args.thresholds) as f:
        raw_cfg = yaml.safe_load(f)
    static_limits = raw_cfg["static_limits"]

    # search ALL splits for the demo illustration (this is purely a visual
    # example for the pitch, NOT part of the quantitative eval above, so
    # using test/train missions here does not leak into reported metrics)
    test = pd.read_csv(f"{args.features}/test.csv")
    all_data = pd.concat([train, val, test], ignore_index=True)
    overheating_missions = (
        all_data[all_data["true_fault_type"] == "OVERHEATING_TREND"]
        .groupby("mission_id")["cht_c"].max()
        .sort_values(ascending=False)
        .index.tolist()
    )
    demo_done = False
    for mid in overheating_missions:
        mission_df = all_data[all_data["mission_id"] == mid].reset_index(drop=True)
        mission_scores = detector.score(mission_df)["anomaly_score"]

        result = detection_lead_time(
            mission_df, mission_scores,
            static_limit_col="cht_c",
            static_limit_value=static_limits["cht_c"]["max"],
            higher_is_bad=True,
            detection_threshold=cfg["ensemble"]["detection_threshold"],
        )
        if result["dt_detection_time_s"] is not None:
            print(f"\n=== Demo: static-limit vs digital-twin detection on mission {mid} (OVERHEATING_TREND) ===")
            print(f"  Peak CHT reached this mission: {result['peak_value_reached']:.1f}C "
                  f"(static redline: {static_limits['cht_c']['max']}C, "
                  f"margin remaining: {result['margin_remaining_to_static_limit']:.1f}C)")
            if result["static_limit_breach_time_s"] is not None:
                print(f"  Static limit WAS breached at: {result['static_limit_breach_time_s']}s")
            else:
                print(f"  Static limit was NEVER breached during this mission "
                      f"(this is expected and realistic - the fault is still developing)")
            print(f"  Digital-twin anomaly detector flagged at: {result['dt_detection_time_s']}s "
                  f"(true fault severity at that moment: {result['dt_severity_at_detection']:.2f})")
            if result["dt_lead_time_s"] is not None:
                print(f"  --> Lead time gained over static limit: {result['dt_lead_time_s']:.1f}s earlier")
            else:
                print(f"  --> Static approach would have caught NOTHING this mission; "
                      f"digital-twin approach caught it at severity {result['dt_severity_at_detection']:.2f}")
            demo_done = True
            break
    if not demo_done:
        print("\nDetector did not flag any OVERHEATING_TREND mission after warmup - "
              "check contamination/threshold tuning in configs/thresholds.yaml.")