from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import pandas as pd


class Replay:
    """
    Replays prerecorded engine telemetry from a CSV file.

    Responsibilities:
    - Load telemetry CSV
    - Emit telemetry rows in order
    - Control replay speed
    - Pause / resume / stop
    - Track replay progress

    This class does NOT:
    - Run the Digital Twin
    - Run ML inference
    - Talk directly to Supabase
    - Contain API/business logic

    The `emit_callback` is used to send each telemetry
    record to another component, such as the backend API.
    """

    def __init__(
        self,
        csv_path: str | Path,
        speed: float = 1.0,
        emit_callback: Optional[
            Callable[[dict], None]
        ] = None,
    ):
        self.csv_path = Path(csv_path)

        if speed <= 0:
            raise ValueError("Replay speed must be greater than 0.")

        self.speed = speed

        self.emit_callback = emit_callback

        self.running = False
        self.paused = False

        self.current_row = 0
        self.total_rows = 0

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    @property
    def progress(self) -> float:
        """
        Return replay progress as a percentage.
        """

        if self.total_rows == 0:
            return 0.0

        return (
            self.current_row
            / self.total_rows
        ) * 100

    @property
    def is_running(self) -> bool:
        return self.running

    @property
    def is_paused(self) -> bool:
        return self.paused

    # ---------------------------------------------------------
    # Speed control
    # ---------------------------------------------------------

    def set_speed(self, speed: float) -> None:
        """
        Change replay speed.

        Examples:
            1.0  -> 1x
            2.0  -> 2x
            4.0  -> 4x
            10.0 -> 10x
        """

        if speed <= 0:
            raise ValueError(
                "Replay speed must be greater than 0."
            )

        self.speed = speed

    # ---------------------------------------------------------
    # Start replay
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Start replay from the beginning of the CSV.
        """

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {self.csv_path}"
            )

        if self.running:
            print("Replay is already running.")
            return

        df = pd.read_csv(self.csv_path)

        self.total_rows = len(df)
        self.current_row = 0

        if self.total_rows == 0:
            print("CSV contains no telemetry records.")
            return

        self.running = True
        self.paused = False

        print()
        print("========================================")
        print("          AEROTWIN TELEMETRY REPLAY")
        print("========================================")
        print(f"CSV:   {self.csv_path.name}")
        print(f"Rows:  {self.total_rows}")
        print(f"Speed: {self.speed}x")
        print("========================================")
        print()

        try:
            for _, row in df.iterrows():

                # Stop requested
                if not self.running:
                    break

                # Pause requested
                while self.paused and self.running:
                    time.sleep(0.1)

                # Stop may have been requested while paused
                if not self.running:
                    break

                telemetry = row.to_dict()

                # -------------------------------------------------
                # Emit telemetry
                # -------------------------------------------------

                process_start = time.monotonic()

                self.emit(telemetry)

                elapsed = (
                    time.monotonic()
                    - process_start
                )

                # -------------------------------------------------
                # Replay timing
                #
                # Original CSV interval is assumed to be
                # approximately 1 second.
                #
                # 1x  -> 1.00 sec
                # 2x  -> 0.50 sec
                # 4x  -> 0.25 sec
                # 10x -> 0.10 sec
                # -------------------------------------------------

                target_interval = 1.0 / self.speed

                remaining_delay = (
                    target_interval
                    - elapsed
                )

                if remaining_delay > 0:
                    time.sleep(remaining_delay)

                self.current_row += 1

                self.print_progress(telemetry)

        finally:
            self.running = False
            self.paused = False

        if self.current_row >= self.total_rows:
            print()
            print("Replay completed.")
            print()

        else:
            print()
            print("Replay stopped.")
            print(
                f"Progress: {self.progress:.1f}%"
            )
            print()

    # ---------------------------------------------------------
    # Emit telemetry
    # ---------------------------------------------------------

    def emit(self, telemetry: dict) -> None:
        """
        Send one telemetry record to the configured destination.

        For now, if no callback is provided, the telemetry
        record is simply printed.

        Later this can be connected to:
            POST /telemetry
        """

        if self.emit_callback is not None:
            self.emit_callback(telemetry)

        else:
            print(
                f"[TELEMETRY] "
                f"mission={telemetry.get('mission_id')} "
                f"rpm={telemetry.get('rpm')} "
                f"cht={telemetry.get('cht_c')} "
                f"egt={telemetry.get('egt_c')}"
            )

    # ---------------------------------------------------------
    # Pause
    # ---------------------------------------------------------

    def pause(self) -> None:
        """
        Pause the replay.
        """

        if not self.running:
            print("Replay is not running.")
            return

        self.paused = True

        print()
        print("Replay paused.")

    # ---------------------------------------------------------
    # Resume
    # ---------------------------------------------------------

    def resume(self) -> None:
        """
        Resume a paused replay.
        """

        if not self.running:
            print("Replay is not running.")
            return

        if not self.paused:
            print("Replay is already running.")
            return

        self.paused = False

        print()
        print("Replay resumed.")

    # ---------------------------------------------------------
    # Stop
    # ---------------------------------------------------------

    def stop(self) -> None:
        """
        Stop the replay.
        """

        if not self.running:
            print("Replay is not running.")
            return

        self.running = False
        self.paused = False

        print()
        print("Stopping replay...")

    # ---------------------------------------------------------
    # Progress display
    # ---------------------------------------------------------

    def print_progress(
        self,
        telemetry: dict,
    ) -> None:
        """
        Print basic replay progress information.
        """

        progress = self.progress

        mission_id = telemetry.get(
            "mission_id",
            "UNKNOWN",
        )

        timestamp = telemetry.get(
            "timestamp_s",
            "UNKNOWN",
        )

        print(
            f"[REPLAY] "
            f"{progress:6.2f}% | "
            f"mission={mission_id} | "
            f"sim_time={timestamp}s | "
            f"speed={self.speed}x"
        )


# =============================================================
# Example usage
# =============================================================

def main() -> None:
    """
    Simple local test.

    This does NOT require the backend to be running.
    """

    # ---------------------------------------------------------
    # Find the backend directory based on this file location.
    #
    # backend/
    # └── src/
    #     └── simulation/
    #         └── replay.py
    #
    # Therefore parents[2] = backend/
    # ---------------------------------------------------------

    current_file = Path(__file__).resolve()

    backend_dir = current_file.parents[2]

    generated_dir = (
        backend_dir
        / "data"
        / "generated"
    )

    # ---------------------------------------------------------
    # Automatically select the newest generated CSV.
    # ---------------------------------------------------------

    csv_files = sorted(
        generated_dir.glob("*.csv"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    if not csv_files:
        print(
            "No CSV files found in:"
        )

        print(generated_dir)

        print()
        print(
            "Run generator.py first."
        )

        return

    csv_path = csv_files[0]

    print(
        f"Using latest dataset: "
        f"{csv_path.name}"
    )

    # ---------------------------------------------------------
    # Create replay.
    #
    # Change speed here:
    #
    # 1.0  = 1x
    # 2.0  = 2x
    # 4.0  = 4x
    # 10.0 = 10x
    # ---------------------------------------------------------

    replay = Replay(
        csv_path=csv_path,
        speed=1.0,
    )

    # ---------------------------------------------------------
    # Start replay.
    # ---------------------------------------------------------

    replay.start()


if __name__ == "__main__":
    main()