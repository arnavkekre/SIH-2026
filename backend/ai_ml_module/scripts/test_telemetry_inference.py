from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.inference.telemetry_inference import TelemetryInference


DATA_PATH = ROOT / "data" / "synthetic" / "combined_dataset.csv"

ANOMALY_MODEL = ROOT / "models" / "anomaly" / "anomaly_detector.joblib"
FAULT_MODEL = ROOT / "models" / "faults" / "fault_classifier.joblib"
RUL_MODEL = ROOT / "models" / "rul" / "rul_regressor.joblib"


def main() -> None:

    print("=" * 60)
    print("RAW TELEMETRY -> UNIFIED AI/ML INFERENCE TEST")
    print("=" * 60)

    # ------------------------------------------------------------
    # Load raw telemetry.
    # ------------------------------------------------------------

    df = pd.read_csv(DATA_PATH)

    mission_id = df["mission_id"].iloc[0]

    mission_df = (
        df[df["mission_id"] == mission_id]
        .sort_values("timestamp_s")
        .reset_index(drop=True)
    )

    print(f"Mission             : {mission_id}")
    print(f"Raw telemetry rows  : {len(mission_df)}")

    # ------------------------------------------------------------
    # Create production inference object.
    # ------------------------------------------------------------

    inference = TelemetryInference(
        anomaly_model_path=ANOMALY_MODEL,
        fault_model_path=FAULT_MODEL,
        rul_model_path=RUL_MODEL,
    )

    # ------------------------------------------------------------
    # Run RAW telemetry directly.
    # ------------------------------------------------------------

    result = inference.predict(mission_df)

    print()
    print("--- CURRENT AI/ML RESULT ---")

    print(
        f"Timestamp           : "
        f"{result.get('timestamp_s')} s"
    )

    print(
        f"Anomaly score       : "
        f"{result.get('anomaly_score')}"
    )

    print(
        f"Top fault           : "
        f"{result.get('top_fault')}"
    )

    print(
        f"Fault probability   : "
        f"{result.get('fault_probability')}"
    )

    print(
        f"Fault severity      : "
        f"{result.get('fault_severity')}"
    )

    print(
        f"Health score        : "
        f"{result.get('health_score')}"
    )

    print(
        f"Health status       : "
        f"{result.get('health_status')}"
    )

    print(
        f"Predicted RUL       : "
        f"{result.get('predicted_rul_seconds')} s"
    )

    print(
        f"Predicted RUL       : "
        f"{result.get('predicted_rul_minutes')} min"
    )

    print(
        f"RUL status          : "
        f"{result.get('rul_status')}"
    )

    print()
    print("=" * 60)
    print("RAW TELEMETRY INFERENCE SUCCESS")
    print("=" * 60)


if __name__ == "__main__":
    main()