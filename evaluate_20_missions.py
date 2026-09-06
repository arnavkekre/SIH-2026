import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parent
AIML_ROOT = ROOT / "backend" / "ai_ml_module"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend" / "src"))

from backend.pipeline import load_aiml_service


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

CSV_PATH = (
    ROOT
    / "backend"
    / "data"
    / "generated"
    / "telemetry_20260905_024648_905564.csv"
)

OUTPUT_DIR = ROOT


# ------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------

if not CSV_PATH.exists():
    raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

df = pd.read_csv(CSV_PATH)

required = [
    "timestamp_s",
    "engine_id",
    "mission_id",
    "true_fault_type",
    "true_fault_active",
    "true_severity",
    "true_degradation_health",
    "true_rul_hours",
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")


print()
print("[DATA] CSV:", CSV_PATH)
print("[DATA] Rows:", len(df))
print("[DATA] Missions:", df["mission_id"].nunique())


# ------------------------------------------------------------
# Load AIML service
# ------------------------------------------------------------

os.chdir(AIML_ROOT)

service = load_aiml_service()

if service is None:
    raise RuntimeError("AIML service failed to load.")

print("[AIML] Service loaded successfully.")


# ------------------------------------------------------------
# Evaluate missions
# ------------------------------------------------------------

all_predictions = []
mission_results = []


for mission_id, mission_df in df.groupby("mission_id", sort=True):

    mission_df = (
        mission_df
        .sort_values("timestamp_s")
        .reset_index(drop=True)
    )

    telemetry_records = mission_df.to_dict("records")

    # --------------------------------------------------------
    # IMPORTANT:
    # TelemetryMLService.predict_dicts() returns a DICTIONARY
    # containing the prediction for the latest point.
    #
    # Therefore, we must replay rows sequentially.
    # --------------------------------------------------------

    mission_predictions = []

    for record in telemetry_records:

        prediction = service.predict_dicts([record])

        if not isinstance(prediction, dict):
            raise TypeError(
                f"Unexpected prediction type: {type(prediction)}"
            )

        mission_predictions.append(prediction)

    # --------------------------------------------------------
    # Convert predictions to DataFrame
    # --------------------------------------------------------

    prediction_df = pd.DataFrame(mission_predictions)

    prediction_df = prediction_df.reset_index(drop=True)

    if len(prediction_df) != len(mission_df):
        raise RuntimeError(
            f"{mission_id}: "
            f"prediction length {len(prediction_df)} "
            f"!= telemetry length {len(mission_df)}"
        )

    # --------------------------------------------------------
    # Build evaluation frame
    # --------------------------------------------------------

    result = mission_df[
        [
            "timestamp_s",
            "mission_id",
            "true_fault_type",
            "true_fault_active",
            "true_severity",
            "true_degradation_health",
            "true_rul_hours",
        ]
    ].copy()

    result["pred_fault"] = prediction_df.get(
        "top_fault",
        pd.Series([None] * len(result))
    )

    result["pred_fault_probability"] = pd.to_numeric(
        prediction_df.get(
            "fault_probability",
            pd.Series([0.0] * len(result))
        ),
        errors="coerce",
    ).fillna(0.0)

    result["pred_anomaly"] = pd.to_numeric(
        prediction_df.get(
            "anomaly_score",
            pd.Series([np.nan] * len(result))
        ),
        errors="coerce",
    )

    result["pred_health"] = pd.to_numeric(
        prediction_df.get(
            "health_score",
            pd.Series([np.nan] * len(result))
        ),
        errors="coerce",
    )

    result["pred_health_status"] = prediction_df.get(
        "health_status",
        pd.Series([None] * len(result))
    )

    result["pred_rul_seconds"] = pd.to_numeric(
        prediction_df.get(
            "predicted_rul_seconds",
            pd.Series([np.nan] * len(result))
        ),
        errors="coerce",
    )

    result["pred_rul_hours"] = (
        result["pred_rul_seconds"] / 3600.0
    )

    result["pred_rul_status"] = prediction_df.get(
        "rul_status",
        pd.Series([None] * len(result))
    )

    # --------------------------------------------------------
    # Classification labels
    # --------------------------------------------------------

    result["pred_class"] = np.where(
        result["pred_fault_probability"] >= 0.30,
        result["pred_fault"].fillna("NORMAL"),
        "NORMAL",
    )

    result["true_class"] = np.where(
        result["true_fault_active"].astype(int) == 1,
        result["true_fault_type"],
        "NORMAL",
    )

    all_predictions.append(result)

    # --------------------------------------------------------
    # Detection latency
    # --------------------------------------------------------

    fault_type = str(
        mission_df["true_fault_type"].iloc[0]
    )

    active_rows = mission_df[
        mission_df["true_fault_active"].astype(int) == 1
    ]

    if not active_rows.empty:

        onset_time = float(
            active_rows["timestamp_s"].iloc[0]
        )

        detected = result[
            (result["timestamp_s"] >= onset_time)
            & (result["pred_class"] == fault_type)
            & (result["pred_fault_probability"] >= 0.30)
        ]

        if not detected.empty:
            detection_time = float(
                detected["timestamp_s"].iloc[0]
            )
            latency = detection_time - onset_time
        else:
            detection_time = np.nan
            latency = np.nan

    else:
        onset_time = np.nan
        detection_time = np.nan
        latency = np.nan

    # --------------------------------------------------------
    # Health metrics
    # --------------------------------------------------------

    health_valid = result[
        result["pred_health"].notna()
        & result["true_degradation_health"].notna()
    ]

    health_mae = (
        float(
            np.mean(
                np.abs(
                    health_valid["pred_health"]
                    - health_valid["true_degradation_health"]
                )
            )
        )
        if not health_valid.empty
        else np.nan
    )

    health_rmse = (
        float(
            np.sqrt(
                np.mean(
                    (
                        health_valid["pred_health"]
                        - health_valid["true_degradation_health"]
                    )
                    ** 2
                )
            )
        )
        if not health_valid.empty
        else np.nan
    )

    # --------------------------------------------------------
    # RUL metrics
    # --------------------------------------------------------

    rul_eval = result[
        (result["true_fault_active"].astype(int) == 1)
        & result["pred_rul_seconds"].notna()
        & result["true_rul_hours"].notna()
    ]

    if not rul_eval.empty:

        true_rul_seconds = (
            rul_eval["true_rul_hours"] * 3600.0
        )

        rul_mae = float(
            np.mean(
                np.abs(
                    rul_eval["pred_rul_seconds"]
                    - true_rul_seconds
                )
            )
        )

        rul_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        rul_eval["pred_rul_seconds"]
                        - true_rul_seconds
                    )
                    ** 2
                )
            )
        )

    else:
        rul_mae = np.nan
        rul_rmse = np.nan

    # --------------------------------------------------------
    # Mission summary
    # --------------------------------------------------------

    print(
        f"{mission_id}: "
        f"{fault_type:28s} | "
        f"onset={onset_time if not np.isnan(onset_time) else '-'} | "
        f"detect={detection_time if not np.isnan(detection_time) else '-'} | "
        f"latency={latency if not np.isnan(latency) else '-'} | "
        f"health_MAE={health_mae:.2f} | "
        f"RUL_MAE_s="
        f"{rul_mae if not np.isnan(rul_mae) else '-'}"
    )

    mission_results.append(
        {
            "mission_id": mission_id,
            "fault_type": fault_type,
            "is_fault_mission": fault_type != "NORMAL",
            "fault_onset_s": onset_time,
            "fault_detection_s": detection_time,
            "detection_latency_s": latency,
            "health_mae": health_mae,
            "health_rmse": health_rmse,
            "rul_mae_seconds": rul_mae,
            "rul_rmse_seconds": rul_rmse,
        }
    )


# ------------------------------------------------------------
# Combine results
# ------------------------------------------------------------

evaluation = pd.concat(
    all_predictions,
    ignore_index=True,
)

mission_summary = pd.DataFrame(
    mission_results
)


# ------------------------------------------------------------
# Fault classification
# ------------------------------------------------------------

labels = sorted(
    set(evaluation["true_class"].unique())
    | set(evaluation["pred_class"].unique())
)

y_true = evaluation["true_class"]
y_pred = evaluation["pred_class"]

accuracy = accuracy_score(
    y_true,
    y_pred,
)

precision = precision_score(
    y_true,
    y_pred,
    labels=labels,
    average="macro",
    zero_division=0,
)

recall = recall_score(
    y_true,
    y_pred,
    labels=labels,
    average="macro",
    zero_division=0,
)

f1 = f1_score(
    y_true,
    y_pred,
    labels=labels,
    average="macro",
    zero_division=0,
)

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=labels,
)

confusion_df = pd.DataFrame(
    cm,
    index=[f"TRUE_{x}" for x in labels],
    columns=[f"PRED_{x}" for x in labels],
)


# ------------------------------------------------------------
# Active fault metrics
# ------------------------------------------------------------

fault_rows = evaluation[
    evaluation["true_fault_active"].astype(int) == 1
]

fault_accuracy = accuracy_score(
    fault_rows["true_class"],
    fault_rows["pred_class"],
) if not fault_rows.empty else np.nan

fault_precision = precision_score(
    fault_rows["true_class"],
    fault_rows["pred_class"],
    average="macro",
    zero_division=0,
) if not fault_rows.empty else np.nan

fault_recall = recall_score(
    fault_rows["true_class"],
    fault_rows["pred_class"],
    average="macro",
    zero_division=0,
) if not fault_rows.empty else np.nan

fault_f1 = f1_score(
    fault_rows["true_class"],
    fault_rows["pred_class"],
    average="macro",
    zero_division=0,
) if not fault_rows.empty else np.nan


# ------------------------------------------------------------
# False positives
# ------------------------------------------------------------

normal_rows = evaluation[
    evaluation["true_fault_active"].astype(int) == 0
]

false_positive_rows = normal_rows[
    normal_rows["pred_class"] != "NORMAL"
]

false_positive_rate = (
    len(false_positive_rows) / len(normal_rows)
    if not normal_rows.empty
    else np.nan
)


# ------------------------------------------------------------
# Per-fault recall
# ------------------------------------------------------------

per_fault_recall = {}

fault_types = sorted(
    evaluation.loc[
        evaluation["true_fault_active"].astype(int) == 1,
        "true_fault_type",
    ].unique()
)

for fault_type in fault_types:

    subset = evaluation[
        evaluation["true_fault_type"] == fault_type
    ]

    actual = (
        subset["true_fault_active"]
        .astype(int)
        == 1
    )

    predicted_correct = (
        (subset["pred_class"] == fault_type)
        & (
            subset["pred_fault_probability"]
            >= 0.30
        )
    )

    per_fault_recall[fault_type] = float(
        predicted_correct[actual].mean()
    )


# ------------------------------------------------------------
# Overall health
# ------------------------------------------------------------

health_eval = evaluation[
    evaluation["pred_health"].notna()
    & evaluation["true_degradation_health"].notna()
]

health_mae = float(
    np.mean(
        np.abs(
            health_eval["pred_health"]
            - health_eval["true_degradation_health"]
        )
    )
)

health_rmse = float(
    np.sqrt(
        np.mean(
            (
                health_eval["pred_health"]
                - health_eval["true_degradation_health"]
            )
            ** 2
        )
    )
)


# ------------------------------------------------------------
# Overall RUL
# ------------------------------------------------------------

rul_eval_all = evaluation[
    (evaluation["true_fault_active"].astype(int) == 1)
    & evaluation["pred_rul_seconds"].notna()
]

if not rul_eval_all.empty:

    true_rul_seconds = (
        rul_eval_all["true_rul_hours"] * 3600.0
    )

    rul_mae = float(
        np.mean(
            np.abs(
                rul_eval_all["pred_rul_seconds"]
                - true_rul_seconds
            )
        )
    )

    rul_rmse = float(
        np.sqrt(
            np.mean(
                (
                    rul_eval_all["pred_rul_seconds"]
                    - true_rul_seconds
                )
                ** 2
            )
        )
    )

else:
    rul_mae = np.nan
    rul_rmse = np.nan


# ------------------------------------------------------------
# Detection latency
# ------------------------------------------------------------

fault_missions = mission_summary[
    mission_summary["is_fault_mission"]
]

latency_valid = fault_missions[
    fault_missions["detection_latency_s"].notna()
]

mean_latency = (
    float(
        latency_valid["detection_latency_s"].mean()
    )
    if not latency_valid.empty
    else np.nan
)

median_latency = (
    float(
        latency_valid["detection_latency_s"].median()
    )
    if not latency_valid.empty
    else np.nan
)

detection_success_rate = (
    len(latency_valid) / len(fault_missions)
    if not fault_missions.empty
    else np.nan
)


# ------------------------------------------------------------
# Save results
# ------------------------------------------------------------

evaluation.to_csv(
    OUTPUT_DIR / "evaluation_predictions_20missions.csv",
    index=False,
)

mission_summary.to_csv(
    OUTPUT_DIR / "evaluation_mission_summary.csv",
    index=False,
)

confusion_df.to_csv(
    OUTPUT_DIR / "evaluation_confusion_matrix.csv"
)


# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

print()
print("=" * 80)
print("20-MISSION AEROTWIN AIML EVALUATION")
print("=" * 80)

print("\nFAULT CLASSIFICATION — ALL ROWS")
print(f"Accuracy          : {accuracy:.4f}")
print(f"Macro Precision   : {precision:.4f}")
print(f"Macro Recall      : {recall:.4f}")
print(f"Macro F1          : {f1:.4f}")

print("\nFAULT CLASSIFICATION — ACTIVE FAULT ROWS")
print(f"Accuracy          : {fault_accuracy:.4f}")
print(f"Macro Precision   : {fault_precision:.4f}")
print(f"Macro Recall      : {fault_recall:.4f}")
print(f"Macro F1          : {fault_f1:.4f}")

print("\nFALSE POSITIVES")
print(f"Normal rows       : {len(normal_rows)}")
print(f"False positives   : {len(false_positive_rows)}")
print(f"FP rate           : {false_positive_rate:.4f}")

print("\nFAULT DETECTION LATENCY")
print(f"Fault missions    : {len(fault_missions)}")
print(f"Detected missions : {len(latency_valid)}")
print(f"Success rate      : {detection_success_rate:.4f}")
print(f"Mean latency      : {mean_latency:.2f} s")
print(f"Median latency    : {median_latency:.2f} s")

print("\nHEALTH")
print(f"MAE               : {health_mae:.4f}")
print(f"RMSE              : {health_rmse:.4f}")

print("\nRUL")
print(f"Active fault rows : {len(rul_eval_all)}")
print(
    f"MAE               : "
    f"{rul_mae:.4f} s"
    if not np.isnan(rul_mae)
    else "MAE               : N/A"
)
print(
    f"RMSE              : "
    f"{rul_rmse:.4f} s"
    if not np.isnan(rul_rmse)
    else "RMSE              : N/A"
)

print("\nPER-FAULT RECALL")

for fault_type, value in per_fault_recall.items():
    print(
        f"{fault_type:28s}: {value:.4f}"
    )

print("\nCONFUSION MATRIX")
print(confusion_df.to_string())

print("\nOUTPUT FILES")
print(
    OUTPUT_DIR
    / "evaluation_predictions_20missions.csv"
)
print(
    OUTPUT_DIR
    / "evaluation_mission_summary.csv"
)
print(
    OUTPUT_DIR
    / "evaluation_confusion_matrix.csv"
)

print("=" * 80)