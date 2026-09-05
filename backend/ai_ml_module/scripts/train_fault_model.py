"""
Usage:
    python scripts/train_fault_model.py --features data/features --out models/faults

Uses the FULL feature set (raw + rolling + digital-twin residuals) - unlike
the anomaly detector, the fault classifier is supervised and benefits from
absolute operating-point context (e.g. knowing throttle_pct helps distinguish
INJECTOR_ABNORMALITY's fuel-flow deviation from a normal high-throttle climb).
"""
import argparse
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.faults.fault_labels import build_multilabel_targets, FAULT_CODES
from src.faults.classifier import MultiLabelFaultClassifier
from src.faults.predictor import top_fault_per_row
from src.features.feature_pipeline import get_model_feature_columns
from src.evaluation.fault_metrics import evaluate_fault_classifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=str, default="data/features")
    parser.add_argument("--out", type=str, default="models/faults")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    train = pd.read_csv(f"{args.features}/train.csv")
    val = pd.read_csv(f"{args.features}/val.csv")

    feature_cols = get_model_feature_columns(train)
    X_train, X_val = train[feature_cols], val[feature_cols]
    Y_train = build_multilabel_targets(train)
    Y_val = build_multilabel_targets(val)

    print(f"Training on {len(X_train)} rows, {len(feature_cols)} features, {len(FAULT_CODES)} fault heads")
    print("Positive row counts per fault (train):")
    print(Y_train.sum().to_string())

    clf = MultiLabelFaultClassifier()
    clf.fit(X_train, Y_train)
    clf.save(f"{args.out}/fault_classifier.joblib")
    print(f"\nSaved -> {args.out}/fault_classifier.joblib")

    proba_val = clf.predict_proba(X_val)
    pred_val = (proba_val >= 0.5).astype(int)

    print("\n=== Per-fault validation metrics (honest, unfiltered) ===")
    report = evaluate_fault_classifier(Y_val, pred_val)
    print(report.to_string(index=False))
    print(f"\nHamming loss (multi-label, lower is better): {report.attrs['hamming_loss']:.4f}")

    # sample prediction, formatted like the target output schema
    sample_idx = proba_val.max(axis=1).idxmax()  # most confident row in val set, for illustration
    print(f"\n=== Sample prediction (row {sample_idx}, true label: "
          f"{val.loc[sample_idx, 'true_fault_type']} @ severity {val.loc[sample_idx, 'true_severity']:.2f}) ===")
    print(proba_val.loc[sample_idx].sort_values(ascending=False).round(3).to_string())

    top = top_fault_per_row(proba_val)
    print(f"\nTop fault call: {top.loc[sample_idx, 'top_fault']} "
          f"(p={top.loc[sample_idx, 'top_fault_probability']:.3f}, "
          f"severity={top.loc[sample_idx, 'severity']})")