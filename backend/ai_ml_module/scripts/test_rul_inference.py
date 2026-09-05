"""
Test runtime RUL inference on a single telemetry/feature row.

Usage:
    python scripts/test_rul_inference.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rul.predictor import RULPredictor


FEATURES_PATH = ROOT / "data" / "features" / "test.csv"
MODEL_PATH = ROOT / "models" / "rul" / "rul_regressor.joblib"


def main() -> None:
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Feature data not found: {FEATURES_PATH}"
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"RUL model not found: {MODEL_PATH}"
        )

    df = pd.read_csv(FEATURES_PATH)

    # Pick a valid fault/degrading row.
    valid = (
        df["true_rul_seconds"].notna()
        & (df["true_rul_seconds"] > 0)
        & (df["true_fault_type"] != "NORMAL")
    )

    if not valid.any():
        raise ValueError(
            "No valid fault/degrading RUL rows found in test.csv."
        )

    row = df.loc[valid].iloc[0]

    predictor = RULPredictor(MODEL_PATH)

    result = predictor.predict_row(
        row.to_dict()
    )

    print("=" * 60)
    print("RUL RUNTIME INFERENCE TEST")
    print("=" * 60)

    print(f"Mission ID          : {row['mission_id']}")
    print(f"Timestamp           : {row['timestamp_s']} s")
    print(f"Fault type          : {row['true_fault_type']}")
    print()

    print(f"Predicted RUL       : {result.rul_seconds:.2f} s")
    print(f"Predicted RUL       : {result.rul_minutes:.2f} min")
    print(f"RUL status          : {result.status}")

    # Ground truth shown ONLY for testing.
    print()
    print(f"True RUL            : {row['true_rul_seconds']:.2f} s")
    print(
        f"Absolute error      : "
        f"{abs(result.rul_seconds - row['true_rul_seconds']):.2f} s"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()