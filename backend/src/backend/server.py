from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from digital_twin.generator import generate_dataset
from simulation.replay import Replay

from backend.pipeline import (
    clear_all_mission_buffers,
    clear_mission_buffer,
    process_telemetry,
    _mission_buffers,
)

from backend.supabase_client import (
    get_engine_uuid,
    get_mission_uuid,
    insert_telemetry,
    supabase_available,
)


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

GENERATED_DIR = (
    BACKEND_DIR
    / "data"
    / "generated"
)


# ============================================================
# APPLICATION CONFIG
# ============================================================

AUTOSTART_REPLAY = (
    os.getenv(
        "AEROTWIN_AUTOSTART_REPLAY",
        "false",
    ).strip().lower()
    == "true"
)

DEFAULT_REPLAY_SPEED = float(
    os.getenv(
        "AEROTWIN_REPLAY_SPEED",
        "1.0",
    )
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="AeroTwin Backend",
    description=(
        "Backend API for AeroTwin engine telemetry, "
        "Digital Twin processing, AI/ML fault detection, "
        "health monitoring and formula-based RUL estimation."
    ),
    version="1.0.0",
)


# ============================================================
# REPLAY STATE
# ============================================================

replay: Optional[Replay] = None

replay_thread: Optional[
    threading.Thread
] = None

replay_lock = threading.Lock()

latest_result: Optional[
    dict[str, Any]
] = None

latest_result_lock = threading.Lock()


# ============================================================
# TELEMETRY SCHEMA
# ============================================================

class Telemetry(BaseModel):
    """
    One telemetry record.

    Ground-truth fields are optional because they are useful
    for simulation/evaluation but are never passed into AIML
    inference.
    """

    timestamp_s: float

    engine_id: str
    mission_id: str

    mission_phase: Optional[str] = None

    throttle_pct: Optional[float] = None
    altitude_m: Optional[float] = None
    ambient_temperature_c: Optional[float] = None

    rpm: Optional[float] = None
    cht_c: Optional[float] = None
    egt_c: Optional[float] = None

    oil_pressure_kpa: Optional[float] = None
    oil_temperature_c: Optional[float] = None

    fuel_flow_lph: Optional[float] = None
    vibration_g: Optional[float] = None

    alternator_voltage_v: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    injection_timing_deg: Optional[float] = None

    # Digital-Twin expected values
    expected_rpm: Optional[float] = None
    expected_cht_c: Optional[float] = None
    expected_egt_c: Optional[float] = None
    expected_oil_pressure_kpa: Optional[float] = None
    expected_oil_temperature_c: Optional[float] = None
    expected_fuel_flow_lph: Optional[float] = None
    expected_vibration_g: Optional[float] = None
    expected_injection_timing_deg: Optional[float] = None

    # Digital-Twin residuals
    residual_rpm: Optional[float] = None
    residual_cht_c: Optional[float] = None
    residual_egt_c: Optional[float] = None
    residual_oil_pressure_kpa: Optional[float] = None
    residual_oil_temperature_c: Optional[float] = None
    residual_fuel_flow_lph: Optional[float] = None
    residual_vibration_g: Optional[float] = None
    residual_injection_timing_deg: Optional[float] = None

    # Evaluation-only ground truth
    true_fault_type: Optional[str] = None
    true_fault_active: Optional[int] = None
    true_severity: Optional[float] = None
    true_degradation_health: Optional[float] = None
    true_rul_hours: Optional[float] = None


# ============================================================
# REPLAY CONTROL SCHEMA
# ============================================================

class ReplayStartRequest(BaseModel):
    speed: float = Field(
        default=DEFAULT_REPLAY_SPEED,
        gt=0.0,
    )


class ReplaySpeedRequest(BaseModel):
    speed: float = Field(
        ...,
        gt=0.0,
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "AeroTwin Backend",
        "version": "1.0.0",
        "status": "running",
        "supabase": supabase_available(),
        "rul": "formula-based",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "aerotwin-backend",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "supabase": supabase_available(),
        "aiml": "anomaly + fault + health + formula_rul",
    }


# ============================================================
# PROCESS ONE TELEMETRY POINT
# ============================================================

def process_one_telemetry(
    telemetry_dict: dict[str, Any],
) -> dict[str, Any]:

    global latest_result

    # --------------------------------------------------------
    # Validate identifiers
    # --------------------------------------------------------

    engine_id = str(
        telemetry_dict.get(
            "engine_id",
            "",
        )
    ).strip()

    mission_id = str(
        telemetry_dict.get(
            "mission_id",
            "",
        )
    ).strip()

    if not engine_id:
        raise ValueError(
            "Missing engine_id."
        )

    if not mission_id:
        raise ValueError(
            "Missing mission_id."
        )

    if telemetry_dict.get(
        "timestamp_s"
    ) is None:
        raise ValueError(
            "Missing timestamp_s."
        )

    telemetry_dict[
        "engine_id"
    ] = engine_id

    telemetry_dict[
        "mission_id"
    ] = mission_id

    # --------------------------------------------------------
    # Persist telemetry when Supabase is configured.
    #
    # Ground truth may be stored for evaluation, but is
    # removed before AIML inference below.
    # --------------------------------------------------------

    if supabase_available():

        engine_uuid = get_engine_uuid(
            engine_id
        )

        mission_uuid = get_mission_uuid(
            mission_id,
            engine_uuid,
        )

        db_telemetry = dict(
            telemetry_dict
        )

        db_telemetry[
            "engine_id"
        ] = engine_uuid

        db_telemetry[
            "mission_id"
        ] = mission_uuid

        insert_telemetry(
            db_telemetry
        )

    # --------------------------------------------------------
    # Never expose ground truth to AIML.
    # --------------------------------------------------------

    inference_telemetry = dict(
        telemetry_dict
    )

    for field in (
        "true_fault_type",
        "true_fault_active",
        "true_severity",
        "true_degradation_health",
        "true_rul_hours",
    ):
        inference_telemetry.pop(
            field,
            None,
        )

    # --------------------------------------------------------
    # Run canonical backend pipeline.
    # --------------------------------------------------------

    result = process_telemetry(
        inference_telemetry
    )

    # --------------------------------------------------------
    # Store latest prediction.
    # --------------------------------------------------------

    with latest_result_lock:

        latest_result = result

    return result


# ============================================================
# REPLAY CALLBACK
# ============================================================

def replay_callback(
    telemetry: dict[str, Any],
) -> None:

    mission_id = telemetry.get(
        "mission_id",
        "UNKNOWN",
    )

    timestamp_s = telemetry.get(
        "timestamp_s",
        "UNKNOWN",
    )

    print(
        "[SERVER] Replay telemetry:"
        f" mission={mission_id}"
        f" timestamp={timestamp_s}s"
    )

    try:

        result = process_one_telemetry(
            telemetry
        )

        fault = (
            result
            .get("fault", {})
            .get("type")
        )

        print(
            "[SERVER] Processed:"
            f" health={result.get('health_score')}"
            f" status={result.get('health_status')}"
            f" fault={fault}"
            f" rul={result.get('rul_seconds')}"
        )

    except Exception as exc:

        print(
            "[SERVER] Telemetry processing failed:"
            f" {exc}"
        )


# ============================================================
# DATA GENERATION
# ============================================================

def generate_fresh_dataset() -> Path:

    GENERATED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "[SERVER] Generating fresh telemetry dataset..."
    )

    df = generate_dataset(
        n_missions=20,
        seed=None,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    csv_path = (
        GENERATED_DIR
        / f"telemetry_{timestamp}.csv"
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    print(
        "[SERVER] Generated:"
        f" missions={df['mission_id'].nunique()}"
        f" rows={len(df)}"
    )

    return csv_path


# ============================================================
# START REPLAY
# ============================================================

def start_replay(
    speed: float = DEFAULT_REPLAY_SPEED,
) -> dict[str, Any]:

    global replay
    global replay_thread

    with replay_lock:

        if replay is not None and replay.is_running:

            return {
                "started": False,
                "message": "Replay is already running.",
            }

        csv_path = (
            generate_fresh_dataset()
        )

        replay = Replay(
            csv_path=csv_path,
            speed=speed,
            emit_callback=replay_callback,
        )

        clear_all_mission_buffers()

        def run() -> None:

            print(
                "[SERVER] Starting telemetry replay..."
            )

            try:
                replay.start()
            except Exception as exc:
                print(
                    "[SERVER] Replay failed:"
                    f" {exc}"
                )

            print(
                "[SERVER] Replay thread finished."
            )

        replay_thread = threading.Thread(
            target=run,
            daemon=True,
            name="aerotwin-replay",
        )

        replay_thread.start()

        return {
            "started": True,
            "speed": speed,
            "csv_path": str(csv_path),
        }


# ============================================================
# SHUTDOWN REPLAY
# ============================================================

def stop_replay_internal() -> None:

    global replay

    with replay_lock:

        if replay is not None:

            replay.stop()

        clear_all_mission_buffers()


# ============================================================
# STARTUP / SHUTDOWN
# ============================================================

@app.on_event("startup")
def startup_event() -> None:

    print(
        "[SERVER] AeroTwin backend starting."
    )

    print(
        "[SERVER] Supabase:"
        f" {'enabled' if supabase_available() else 'disabled'}"
    )

    print(
        "[SERVER] RUL:"
        " formula-based"
    )

    if AUTOSTART_REPLAY:

        print(
            "[SERVER] AUTOSTART_REPLAY=true"
        )

        start_replay(
            DEFAULT_REPLAY_SPEED
        )

    else:

        print(
            "[SERVER] Replay autostart disabled."
        )

        print(
            "[SERVER] Use POST /replay/start"
        )


@app.on_event("shutdown")
def shutdown_event() -> None:

    print(
        "[SERVER] Shutting down..."
    )

    stop_replay_internal()


# ============================================================
# MANUAL TELEMETRY ENDPOINT
# ============================================================

@app.post("/telemetry")
def receive_telemetry(
    telemetry: Telemetry,
) -> dict[str, Any]:

    if not telemetry.engine_id.strip():

        raise HTTPException(
            status_code=400,
            detail="engine_id cannot be empty.",
        )

    if not telemetry.mission_id.strip():

        raise HTTPException(
            status_code=400,
            detail="mission_id cannot be empty.",
        )

    try:

        result = process_one_telemetry(
            telemetry.model_dump()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Telemetry processing failed: {exc}"
            ),
        ) from exc

    return {
        "status": "processed",
        "processed": True,
        "engine_id": telemetry.engine_id,
        "mission_id": telemetry.mission_id,
        "timestamp_s": telemetry.timestamp_s,
        "result": result,
    }


# ============================================================
# LATEST RESULT
# ============================================================

@app.get("/latest")
def latest() -> dict[str, Any]:

    with latest_result_lock:

        result = latest_result

    if result is None:

        return {
            "status": "ok",
            "message": (
                "No telemetry has been processed yet."
            ),
            "result": None,
        }

    return {
        "status": "ok",
        "result": result,
    }


# ============================================================
# MISSION HISTORY
# ============================================================

@app.get(
    "/missions/{mission_id}/history"
)
def mission_history(
    mission_id: str,
) -> dict[str, Any]:

    mission_id = mission_id.strip()

    if not mission_id:

        raise HTTPException(
            status_code=400,
            detail="mission_id cannot be empty.",
        )

    with _mission_buffers_lock:

        history = list(
            _mission_buffers.get(
                mission_id,
                [],
            )
        )

    return {
        "status": "ok",
        "mission_id": mission_id,
        "points": len(history),
        "history": history,
    }


# ============================================================
# REPLAY STATUS
# ============================================================

@app.get("/replay/status")
def replay_status() -> dict[str, Any]:

    with replay_lock:

        current = replay

        if current is None:

            return {
                "running": False,
                "paused": False,
                "progress": 0.0,
                "speed": None,
                "current_row": 0,
                "total_rows": 0,
            }

        return {
            "running": current.is_running,
            "paused": current.is_paused,
            "progress": current.progress,
            "speed": current.speed,
            "current_row": current.current_row,
            "total_rows": current.total_rows,
        }


# ============================================================
# START REPLAY
# ============================================================

@app.post("/replay/start")
def replay_start(
    request: ReplayStartRequest,
) -> dict[str, Any]:

    try:

        return start_replay(
            request.speed
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to start replay: {exc}"
            ),
        ) from exc


# ============================================================
# SPEED
# ============================================================

@app.post("/replay/speed")
def replay_speed(
    request: ReplaySpeedRequest,
) -> dict[str, Any]:

    with replay_lock:

        if replay is None:

            raise HTTPException(
                status_code=400,
                detail="Replay has not started.",
            )

        replay.set_speed(
            request.speed
        )

        return {
            "status": "ok",
            "speed": replay.speed,
        }


# ============================================================
# PAUSE
# ============================================================

@app.post("/replay/pause")
def pause_replay() -> dict[str, Any]:

    with replay_lock:

        if replay is None:

            raise HTTPException(
                status_code=400,
                detail="Replay has not started.",
            )

        replay.pause()

    return {
        "status": "ok",
        "message": "Replay paused.",
    }


# ============================================================
# RESUME
# ============================================================

@app.post("/replay/resume")
def resume_replay() -> dict[str, Any]:

    with replay_lock:

        if replay is None:

            raise HTTPException(
                status_code=400,
                detail="Replay has not started.",
            )

        replay.resume()

    return {
        "status": "ok",
        "message": "Replay resumed.",
    }


# ============================================================
# STOP
# ============================================================

@app.post("/replay/stop")
def stop_replay() -> dict[str, Any]:

    stop_replay_internal()

    return {
        "status": "ok",
        "message": "Replay stopped.",
    }


# ============================================================
# CLEAR MISSION
# ============================================================

@app.delete(
    "/missions/{mission_id}/history"
)
def clear_mission_history(
    mission_id: str,
) -> dict[str, Any]:

    mission_id = mission_id.strip()

    if not mission_id:

        raise HTTPException(
            status_code=400,
            detail="mission_id cannot be empty.",
        )

    clear_mission_buffer(
        mission_id
    )

    return {
        "status": "ok",
        "mission_id": mission_id,
        "message": "Mission history cleared.",
    }