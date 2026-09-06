from __future__ import annotations

from pathlib import Path
import json
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.inference.service import TelemetryMLService


DATA_PATH = (
    ROOT
    / "data"
    / "synthetic"
    / "retrain_dataset_240.csv"
)

ANOMALY_MODEL = (
    ROOT
    / "models"
    / "anomaly"
    / "anomaly_detector.joblib"
)

FAULT_MODEL = (
    ROOT
    / "models"
    / "faults"
    / "fault_classifier.joblib"
)


def main() -> None:

    print("=" * 60)
    print("BACKEND <-> AI/ML CONTRACT TEST")
    print("=" * 60)

    # ------------------------------------------------------------
    # Load raw telemetry.
    # ------------------------------------------------------------

    raw = pd.read_csv(DATA_PATH)

    mission_id = str(
        raw["mission_id"].iloc[0]
    )

    mission = (
        raw[
            raw["mission_id"] == mission_id
        ]
        .sort_values("timestamp_s")
        .reset_index(drop=True)
    )

    if mission.empty:
        raise ValueError(
            f"Mission {mission_id} was not found in {DATA_PATH}"
        )

    print(f"Mission             : {mission_id}")
    print(f"Telemetry points    : {len(mission)}")

    # ------------------------------------------------------------
    # Convert dataframe rows to backend-style dictionaries.
    #
    # Ground-truth columns are deliberately removed.
    # This ensures inference does not use true_* labels.
    # ------------------------------------------------------------

    telemetry_columns = [
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_phase",
        "throttle_pct",
        "altitude_m",
        "ambient_temperature_c",
        "rpm",
        "cht_c",
        "egt_c",
        "oil_pressure_kpa",
        "oil_temperature_c",
        "fuel_flow_lph",
        "vibration_g",
        "alternator_voltage_v",
        "battery_voltage_v",
        "injection_timing_deg",
    ]

    missing_columns = [
        column
        for column in telemetry_columns
        if column not in mission.columns
    ]

    if missing_columns:
        raise ValueError(
            "Telemetry dataset is missing required columns: "
            f"{missing_columns}"
        )

    payload = (
        mission[telemetry_columns]
        .to_dict(orient="records")
    )

    # ------------------------------------------------------------
    # Create ML service.
    #
    # Only anomaly + fault model artifacts are loaded.
    # RUL is formula-based and therefore requires no joblib.
    # ------------------------------------------------------------

    service = TelemetryMLService(
        anomaly_model_path=ANOMALY_MODEL,
        fault_model_path=FAULT_MODEL,
    )

    # ------------------------------------------------------------
    # Simulate backend sending JSON-style dictionaries.
    # ------------------------------------------------------------

    result = service.predict_dicts(payload)

    # ------------------------------------------------------------
    # Validate basic response contract.
    # ------------------------------------------------------------

    if not isinstance(result, dict):
        raise TypeError(
            "AIML service must return a dictionary."
        )

    required_fields = {
        "anomaly_score",
        "top_fault",
        "fault_probability",
        "fault_severity",
        "health_score",
        "health_status",
        "predicted_rul_seconds",
        "predicted_rul_minutes",
        "rul_status",
    }

    missing_result_fields = (
        required_fields - set(result.keys())
    )

    if missing_result_fields:
        raise AssertionError(
            "AIML response is missing required fields: "
            f"{sorted(missing_result_fields)}"
        )

    # ------------------------------------------------------------
    # Ensure the response contains no ground-truth labels.
    # ------------------------------------------------------------

    forbidden_fields = [
        key
        for key in result.keys()
        if key.startswith("true_")
    ]

    if forbidden_fields:
        raise AssertionError(
            "Ground-truth fields leaked into inference response: "
            f"{forbidden_fields}"
        )

    # ------------------------------------------------------------
    # Print backend response.
    # ------------------------------------------------------------

    print()
    print("--- BACKEND RESPONSE ---")

    print(
        json.dumps(
            result,
            indent=2,
            allow_nan=False,
        )
    )

    print()
    print("=" * 60)
    print("BACKEND CONTRACT TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()