"""
End-to-end Phase 7 inference test.

Usage:
    python scripts/test_unified_inference.py

Ground-truth fields are used only for evaluation/printing.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.inference.pipeline import UnifiedInferenceEngine


FEATURES = ROOT / "data" / "features" / "test.csv"
ANOMALY_MODEL = ROOT / "models" / "anomaly" / "anomaly_detector.joblib"
FAULT_MODEL = ROOT / "models" / "faults" / "fault_classifier.joblib"
RUL_MODEL = ROOT / "models" / "rul" / "rul_regressor.joblib"


def main() -> None:
    for path in (FEATURES, ANOMALY_MODEL, FAULT_MODEL, RUL_MODEL):
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

    df = pd.read_csv(FEATURES)

    fault_mask = (
        df["true_fault_type"].ne("NORMAL")
        & df["true_rul_seconds"].notna()
        & (df["true_rul_seconds"] > 0)
    )

    if not fault_mask.any():
        raise ValueError("No suitable fault row found in test.csv.")

    row = df.loc[fault_mask].iloc[0]

    engine = UnifiedInferenceEngine(
        anomaly_model_path=ANOMALY_MODEL,
        fault_model_path=FAULT_MODEL,
        rul_model_path=RUL_MODEL,
    )

    output = engine.predict(pd.DataFrame([row])).iloc[0]

    print("=" * 70)
    print("PHASE 7 — UNIFIED AI/ML INFERENCE")
    print("=" * 70)
    print(f"Mission             : {output['mission_id']}")
    print(f"Timestamp           : {output['timestamp_s']} s")
    print()
    print(f"Anomaly score       : {output['anomaly_score']:.3f}")
    print(f"Top fault           : {output['top_fault']}")
    print(f"Fault probability   : {output['fault_probability']:.3f}")
    print(f"Fault severity      : {output['fault_severity']}")
    print()
    print(f"Health score        : {output['health_score']:.2f}")
    print(f"Health status       : {output['health_status']}")

    if pd.isna(output["predicted_rul_seconds"]):
        print("Predicted RUL       : N/A")
        print("RUL status          : NOT_APPLICABLE")
    else:
        print(
            f"Predicted RUL       : "
            f"{output['predicted_rul_seconds']:.2f} s"
        )
        print(
            f"Predicted RUL       : "
            f"{output['predicted_rul_minutes']:.2f} min"
        )
        print(f"RUL status          : {output['rul_status']}")

    print()
    print("--- Evaluation only (NOT model input) ---")
    print(f"True fault          : {row['true_fault_type']}")
    print(f"True RUL            : {row['true_rul_seconds']:.2f} s")

    if not pd.isna(output["predicted_rul_seconds"]):
        print(
            f"RUL absolute error  : "
            f"{abs(output['predicted_rul_seconds'] - row['true_rul_seconds']):.2f} s"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
