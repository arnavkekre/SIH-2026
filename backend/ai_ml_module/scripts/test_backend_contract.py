from __future__ import annotations

from pathlib import Path
import json
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.inference.service import TelemetryMLService


DATA_PATH = ROOT / "data" / "synthetic" / "combined_dataset.csv"

ANOMALY_MODEL = (
    ROOT / "models" / "anomaly" / "anomaly_detector.joblib"
)

FAULT_MODEL = (
    ROOT / "models" / "faults" / "fault_classifier.joblib"
)

RUL_MODEL = (
    ROOT / "models" / "rul" / "rul_regressor.joblib"
)


def main() -> None:

    print("=" * 60)
    print("BACKEND <-> AI/ML CONTRACT TEST")
    print("=" * 60)

    # ------------------------------------------------------------
    # Load raw telemetry.
    # ------------------------------------------------------------

    raw = pd.read_csv(DATA_PATH)

    mission_id = "MIS-0012"

    mission = (
        raw[raw["mission_id"] == mission_id]
        .sort_values("timestamp_s")
        .reset_index(drop=True)
    )

    print(f"Mission             : {mission_id}")
    print(f"Telemetry points    : {len(mission)}")

    # ------------------------------------------------------------
    # Convert dataframe rows to backend-style dictionaries.
    #
    # Ground-truth columns are deliberately removed.
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

    payload = (
        mission[telemetry_columns]
        .to_dict(orient="records")
    )

    # ------------------------------------------------------------
    # Create ML service.
    # ------------------------------------------------------------

    service = TelemetryMLService(
        anomaly_model_path=ANOMALY_MODEL,
        fault_model_path=FAULT_MODEL,
        rul_model_path=RUL_MODEL,
    )

    # ------------------------------------------------------------
    # Simulate backend sending JSON-style dictionaries.
    # ------------------------------------------------------------

    result = service.predict_dicts(payload)

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