from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ============================================================
# AeroTwin imports
# ============================================================
import sys

SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# ============================================================
# Now AeroTwin imports work
# ============================================================

from digital_twin.generator import generate_dataset
from simulation.replay import Replay
from backend.pipeline import process_telemetry
from backend.supabase_client import (
    get_engine_uuid,
    get_mission_uuid,
    insert_telemetry,
)


# ============================================================
# Paths
# ============================================================

# server.py
#
# backend/
# ├── src/
# │   └── backend/
# │       └── server.py
# └── data/
#     └── generated/
#
# parents[0] = backend/src/backend
# parents[1] = backend/src
# parents[2] = backend

BACKEND_DIR = Path(__file__).resolve().parents[2]

GENERATED_DIR = (
    BACKEND_DIR
    / "data"
    / "generated"
)


# ============================================================
# FastAPI application
# ============================================================
import sys

print("Python import search paths:")
for path in sys.path:
    print("  ", path)

app = FastAPI(
    title="AeroTwin Backend",
    description=(
        "Backend API for AeroTwin engine telemetry, "
        "Digital Twin processing and ML fault detection."
    ),
    version="0.2.0",
)


# ============================================================
# Replay state
# ============================================================

replay: Optional[Replay] = None

replay_thread: Optional[threading.Thread] = None

latest_result: Optional[dict[str, Any]] = None


# ============================================================
# Telemetry request model
# ============================================================

class Telemetry(BaseModel):
    """
    One telemetry record.

    This matches the output produced by generator.py.
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

    expected_rpm: Optional[float] = None
    expected_cht_c: Optional[float] = None
    expected_egt_c: Optional[float] = None

    expected_oil_pressure_kpa: Optional[float] = None
    expected_oil_temperature_c: Optional[float] = None

    expected_fuel_flow_lph: Optional[float] = None
    expected_vibration_g: Optional[float] = None

    expected_injection_timing_deg: Optional[float] = None

    residual_rpm: Optional[float] = None
    residual_cht_c: Optional[float] = None
    residual_egt_c: Optional[float] = None

    residual_oil_pressure_kpa: Optional[float] = None
    residual_oil_temperature_c: Optional[float] = None

    residual_fuel_flow_lph: Optional[float] = None
    residual_vibration_g: Optional[float] = None

    residual_injection_timing_deg: Optional[float] = None

    # ========================================================
    # Ground truth / simulation labels
    # ========================================================

    true_fault_type: Optional[str] = None
    true_fault_active: Optional[int] = None
    true_severity: Optional[float] = None
    true_degradation_health: Optional[float] = None
    true_rul_hours: Optional[float] = None


# ============================================================
# Root endpoint
# ============================================================

@app.get("/")
def root() -> dict[str, Any]:

    return {
        "service": "AeroTwin Backend",
        "status": "running",
        "version": "0.2.0",
    }


# ============================================================
# Health check
# ============================================================

@app.get("/health")
def health_check() -> dict[str, Any]:

    return {
        "status": "ok",
        "service": "aerotwin-backend",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ============================================================
# Telemetry processing
# ============================================================

def process_one_telemetry(
    telemetry_dict: dict[str, Any],
) -> dict[str, Any]:

    global latest_result

    # --------------------------------------------------------
    # Get database UUIDs
    # --------------------------------------------------------

    engine_uuid = get_engine_uuid(
    telemetry_dict["engine_id"]
)

    mission_uuid = get_mission_uuid(
        telemetry_dict["mission_id"],
        engine_uuid,
    )


    # --------------------------------------------------------
    # Prepare telemetry for Supabase
    # --------------------------------------------------------

    db_telemetry = telemetry_dict.copy()

    db_telemetry["engine_id"] = engine_uuid
    db_telemetry["mission_id"] = mission_uuid

    # --------------------------------------------------------
    # Insert telemetry into Supabase
    # --------------------------------------------------------

    insert_telemetry(
        db_telemetry
    )

    print(
        "[SERVER] Telemetry stored in Supabase."
    )

    # --------------------------------------------------------
    # Process telemetry
    #
    # Ground-truth values are stored in Supabase but must
    # NOT be passed into the ML / Digital Twin pipeline.
    # --------------------------------------------------------

    inference_telemetry = telemetry_dict.copy()

    for field in [
        "true_fault_type",
        "true_fault_active",
        "true_severity",
        "true_degradation_health",
        "true_rul_hours",
    ]:
        inference_telemetry.pop(
            field,
            None,
        )

    result = process_telemetry(
        inference_telemetry
    )

    latest_result = result

    return result



# ============================================================
# Replay callback
# ============================================================

def replay_callback(
    telemetry: dict[str, Any],
) -> None:
    """
    Called by Replay once for every CSV row.

    Flow:

        CSV row
           |
           v
        Replay
           |
           v
        replay_callback()
           |
           v
        process_telemetry()
           |
           v
        ML / health / residuals
    """

    print()
    print(
        "[SERVER] Received replay telemetry:"
        f" mission={telemetry.get('mission_id')}"
        f" timestamp={telemetry.get('timestamp_s')}s"
    )

    try:

        result = process_one_telemetry(
            telemetry
        )

        print(
            "[SERVER] Processing complete:"
            f" health={result.get('health_score')}"
            f" severity={result.get('severity')}"
            f" fault={result.get('fault', {}).get('type')}"
        )

    except Exception as exc:

        print(
            "[SERVER] Telemetry processing failed:"
            f" {exc}"
        )


# ============================================================
# Generate fresh dataset
# ============================================================

def generate_fresh_dataset() -> Path:
    """
    Generate a brand-new telemetry dataset.

    This runs when the server starts.

    Example:

        server starts
             |
             v
        generator.py
             |
             v
        fresh CSV
    """

    print()
    print("========================================")
    print("       AEROTWIN DATA GENERATION")
    print("========================================")

    GENERATED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Generating fresh dataset in:"
        f"\n{GENERATED_DIR}"
    )

    # --------------------------------------------------------
    # Generate fresh dataset.
    #
    # seed=None means every server start produces
    # different telemetry.
    # --------------------------------------------------------

    df = generate_dataset(
        n_missions=20,
        seed=None,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

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
        f"Generated missions:"
        f" {df['mission_id'].nunique()}"
    )

    print(
        f"Generated rows:"
        f" {len(df)}"
    )

    print(
        f"Fresh CSV:"
        f" {csv_path}"
    )

    print("========================================")
    print()

    return csv_path


# ============================================================
# Start replay
# ============================================================

def start_replay() -> None:
    """
    Generate a fresh CSV and start replaying it.

    Replay runs in a background thread so that FastAPI
    remains responsive.
    """

    global replay
    global replay_thread

    # --------------------------------------------------------
    # Generate fresh CSV
    # --------------------------------------------------------

    csv_path = generate_fresh_dataset()

    # --------------------------------------------------------
    # Create Replay object
    # --------------------------------------------------------

    replay = Replay(
        csv_path=csv_path,

        # 1.0 = one record per second
        #
        # Change this to:
        #
        # 2.0 -> approximately 2 records/sec
        # 4.0 -> approximately 4 records/sec
        # 10.0 -> approximately 10 records/sec
        speed=1.0,

        emit_callback=replay_callback,
    )

    # --------------------------------------------------------
    # Replay.start() is blocking.
    #
    # Therefore run it in a background thread.
    # --------------------------------------------------------

    def run_replay():

        print()
        print(
            "[SERVER] Starting telemetry replay..."
        )

        replay.start()

        print(
            "[SERVER] Replay thread finished."
        )

    replay_thread = threading.Thread(
        target=run_replay,
        daemon=True,
    )

    replay_thread.start()


# ============================================================
# Startup
# ============================================================

@app.on_event("startup")
def startup_event() -> None:
    """
    Runs automatically when FastAPI starts.

    Presentation flow:

        uvicorn
           |
           v
        server.py
           |
           v
        generator.py
           |
           v
        fresh CSV
           |
           v
        replay.py
           |
           v
        pipeline.py
    """

    print()
    print("========================================")
    print("          AEROTWIN BACKEND")
    print("========================================")
    print("Server starting...")
    print()

    start_replay()


# ============================================================
# Shutdown
# ============================================================

@app.on_event("shutdown")
def shutdown_event() -> None:
    """
    Stop replay when the server shuts down.
    """

    global replay

    if replay is not None:

        print()
        print(
            "[SERVER] Stopping telemetry replay..."
        )

        replay.stop()

        print(
            "[SERVER] Replay stopped."
        )


# ============================================================
# Manual telemetry endpoint
# ============================================================

@app.post("/telemetry")
def receive_telemetry(
    telemetry: Telemetry,
) -> dict[str, Any]:
    """
    Receive one telemetry record manually.

    Replay normally feeds telemetry into the same pipeline
    through replay_callback().

    This endpoint is useful if:
    - frontend sends telemetry
    - another simulator sends telemetry
    - you want to test the API manually
    """

    telemetry_dict = telemetry.model_dump()

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Process
    # --------------------------------------------------------

    try:

        result = process_one_telemetry(
            telemetry_dict
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
# Latest result
# ============================================================

@app.get("/latest")
def latest() -> dict[str, Any]:
    """
    Return the most recently processed telemetry result.
    """

    if latest_result is None:

        return {
            "status": "ok",
            "message": (
                "No telemetry has been processed yet."
            ),
            "result": None,
        }

    return {
        "status": "ok",
        "result": latest_result,
    }


# ============================================================
# Replay status
# ============================================================

@app.get("/replay/status")
def replay_status() -> dict[str, Any]:
    """
    Return current replay state.

    Useful for a future frontend.
    """

    if replay is None:

        return {
            "running": False,
            "paused": False,
            "progress": 0.0,
            "speed": None,
        }

    return {
        "running": replay.is_running,
        "paused": replay.is_paused,
        "progress": replay.progress,
        "speed": replay.speed,
        "current_row": replay.current_row,
        "total_rows": replay.total_rows,
    }


# ============================================================
# Pause replay
# ============================================================

@app.post("/replay/pause")
def pause_replay() -> dict[str, Any]:

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
# Resume replay
# ============================================================

@app.post("/replay/resume")
def resume_replay() -> dict[str, Any]:

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
# Stop replay
# ============================================================

@app.post("/replay/stop")
def stop_replay() -> dict[str, Any]:

    if replay is None:

        raise HTTPException(
            status_code=400,
            detail="Replay has not started.",
        )

    replay.stop()

    return {
        "status": "ok",
        "message": "Replay stopped.",
    }


# ============================================================
# Change replay speed
# ============================================================

@app.post("/replay/speed/{speed}")
def change_replay_speed(
    speed: float,
) -> dict[str, Any]:

    if replay is None:

        raise HTTPException(
            status_code=400,
            detail="Replay has not started.",
        )

    try:

        replay.set_speed(speed)

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "status": "ok",
        "speed": replay.speed,
    }


# ============================================================
# Local entry point
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend.server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
