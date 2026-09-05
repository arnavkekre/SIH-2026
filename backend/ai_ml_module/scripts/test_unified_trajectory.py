from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.inference.pipeline import UnifiedInferenceEngine


def main():
    df = pd.read_csv(ROOT / "data/features/test.csv")

    # Pick the same kind of injector-abnormality mission.
    mission_ids = df.loc[
        df["true_fault_type"] == "INJECTOR_ABNORMALITY",
        "mission_id",
    ].unique()

    if len(mission_ids) == 0:
        raise ValueError("No injector-abnormality mission found.")

    mission_id = mission_ids[0]
    mission = df[df["mission_id"] == mission_id].copy()

    engine = UnifiedInferenceEngine(
        ROOT / "models/anomaly/anomaly_detector.joblib",
        ROOT / "models/faults/fault_classifier.joblib",
        ROOT / "models/rul/rul_regressor.joblib",
    )

    result = engine.predict(mission)

    view = pd.DataFrame({
        "time": mission["timestamp_s"].values,
        "true_severity": mission["true_severity"].values,
        "anomaly": result["anomaly_score"].values,
        "fault_probability": result["fault_probability"].values,
        "health": result["health_score"].values,
        "health_status": result["health_status"].values,
        "rul": result["predicted_rul_seconds"].values,
    })

    print(f"\nMission: {mission_id}")
    print(mission["true_fault_type"].iloc[0])
    print()
    print(view.iloc[::5].to_string(index=False))


if __name__ == "__main__":
    main()