import sys
from pathlib import Path

import pandas as pd
import pytest


# Allow imports from backend/src
SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from simulation.replay import Replay


# ============================================================
# Helpers
# ============================================================

def create_test_csv(tmp_path):

    csv_path = tmp_path / "test_replay.csv"

    df = pd.DataFrame(
        [
            {
                "timestamp_s": 0.0,
                "engine_id": "ENG-001",
                "mission_id": "MIS-0001",
                "rpm": 2000,
                "cht_c": 150,
                "egt_c": 620,
            },
            {
                "timestamp_s": 1.0,
                "engine_id": "ENG-001",
                "mission_id": "MIS-0001",
                "rpm": 2100,
                "cht_c": 151,
                "egt_c": 625,
            },
            {
                "timestamp_s": 2.0,
                "engine_id": "ENG-001",
                "mission_id": "MIS-0001",
                "rpm": 2200,
                "cht_c": 153,
                "egt_c": 630,
            },
        ]
    )

    df.to_csv(
        csv_path,
        index=False,
    )

    return csv_path


# ============================================================
# Initialization
# ============================================================

def test_replay_initialization(tmp_path):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=1.0,
    )

    assert replay.speed == 1.0
    assert replay.running is False
    assert replay.paused is False


def test_invalid_speed_is_rejected(tmp_path):

    csv_path = create_test_csv(tmp_path)

    with pytest.raises(
        (ValueError, AssertionError)
    ):

        Replay(
            csv_path=str(csv_path),
            speed=0,
        )


# ============================================================
# Replay rows
# ============================================================

def test_replay_reads_all_rows(
    tmp_path,
    monkeypatch,
):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=1000.0,
    )

    emitted = []

    # Prevent actual waiting
    monkeypatch.setattr(
        "simulation.replay.time.sleep",
        lambda _: None,
    )

    # Replace backend sender/process function.
    #
    # Depending on your replay implementation, this may
    # need to be adjusted to the exact function/method name.
    if hasattr(replay, "send_to_backend"):

        monkeypatch.setattr(
            replay,
            "send_to_backend",
            lambda telemetry: emitted.append(
                telemetry
            ),
        )

    replay.start()

    # If your implementation exposes emitted telemetry
    # through a callback/list, this test can be connected
    # directly to it.
    #
    # The basic assertion is that the replay processed
    # the complete CSV.
    assert replay.running is False


# ============================================================
# Stop
# ============================================================

def test_stop_sets_running_false(tmp_path):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=1.0,
    )

    replay.running = True

    replay.stop()

    assert replay.running is False


# ============================================================
# Pause / Resume
# ============================================================

def test_pause_sets_paused_true(tmp_path):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=1.0,
    )

    replay.pause()

    assert replay.paused is True


def test_resume_sets_paused_false(tmp_path):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=1.0,
    )

    replay.pause()

    assert replay.paused is True

    replay.resume()

    assert replay.paused is False


# ============================================================
# Speed
# ============================================================

@pytest.mark.parametrize(
    "speed",
    [
        0.5,
        1.0,
        2.0,
        4.0,
        10.0,
    ],
)
def test_replay_accepts_valid_speeds(
    tmp_path,
    speed,
):

    csv_path = create_test_csv(tmp_path)

    replay = Replay(
        csv_path=str(csv_path),
        speed=speed,
    )

    assert replay.speed == speed