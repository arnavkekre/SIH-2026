from __future__ import annotations

import numpy as np
import pandas as pd

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime


# ============================================================
# Fault types
# ============================================================

FAULT_TYPES = [
    "NORMAL",
    "MISFIRE",
    "INJECTOR_ABNORMALITY",
    "COOLING_DEGRADATION",
    "LUBRICATION_ISSUE",
    "SENSOR_DRIFT",
    "COMBUSTION_INSTABILITY",
    "OVERHEATING_TREND",
    "ABNORMAL_VIBRATION",
]


# ============================================================
# Mission phases
# ============================================================

PHASE_SCHEDULE = [
    ("TAXI", 0.00, 0.05, 15),
    ("TAKEOFF", 0.05, 0.10, 95),
    ("CLIMB", 0.10, 0.25, 85),
    ("CRUISE", 0.25, 0.70, 60),
    ("LOITER", 0.70, 0.85, 45),
    ("DESCENT", 0.85, 0.95, 30),
    ("LANDING", 0.95, 1.00, 20),
]


# ============================================================
# Determine mission phase
# ============================================================

def _phase_at(frac: float):

    for name, start, end, throttle in PHASE_SCHEDULE:

        if start <= frac < end:
            return name, throttle

    return (
        PHASE_SCHEDULE[-1][0],
        PHASE_SCHEDULE[-1][3],
    )


# ============================================================
# Mission configuration
# ============================================================

@dataclass
class MissionConfig:

    engine_id: str
    mission_id: str

    duration_min: float = 1.0
    sample_interval_s: float = 1.0

    fault_type: str = "NORMAL"

    onset_fraction: float = 0.4
    severity_at_end: float = 0.8

    seed: Optional[int] = None

    env_condition: str = "STANDARD"


# ============================================================
# Fault severity ramp
# ============================================================

def _ramp(
    frac: float,
    onset: float,
    severity_end: float,
) -> float:

    if frac <= onset:
        return 0.0

    progressed = (
        (frac - onset)
        / max(1e-6, 1.0 - onset)
    )

    return severity_end * (
        1
        / (
            1
            + np.exp(
                -6 * (progressed - 0.5)
            )
        )
    )


# ============================================================
# Generate one mission
# ============================================================

def generate_mission(
    cfg: MissionConfig,
) -> pd.DataFrame:

    rng = np.random.default_rng(cfg.seed)

    # Number of telemetry samples
    n_steps = int(
        (cfg.duration_min * 60)
        / cfg.sample_interval_s
    )

    rows = []

    # --------------------------------------------------------
    # Environment modifiers
    # --------------------------------------------------------

    alt_boost = 1.0
    ambient_boost = 0

    if cfg.env_condition == "HIGH_ALTITUDE":

        alt_boost = 1.6

    elif cfg.env_condition == "HOT_WEATHER":

        ambient_boost = 15

    rapid_throttle = (
        cfg.env_condition == "RAPID_THROTTLE"
    )

    # --------------------------------------------------------
    # Stateful variables
    # --------------------------------------------------------

    oil_temp_state = 40.0

    sensor_drift_bias = {}

    drift_target_param = rng.choice(
        [
            "cht_c",
            "oil_pressure_kpa",
            "egt_c",
        ]
    )

    # ========================================================
    # Generate telemetry row by row
    # ========================================================

    for i in range(n_steps):

        # ----------------------------------------------------
        # Time
        # ----------------------------------------------------

        t_min = (
            i
            * cfg.sample_interval_s
            / 60.0
        )

        frac = (
            t_min
            / cfg.duration_min
        )

        # ----------------------------------------------------
        # Mission phase
        # ----------------------------------------------------

        phase, base_throttle = _phase_at(
            frac
        )

        # ----------------------------------------------------
        # Throttle
        # ----------------------------------------------------

        throttle = (
            base_throttle
            + rng.normal(0, 3)
        )

        if (
            rapid_throttle
            and phase in ("CRUISE", "LOITER")
        ):

            throttle += (
                25
                * np.sin(frac * 40)
            )

        throttle = float(
            np.clip(
                throttle,
                0,
                100,
            )
        )

        # ----------------------------------------------------
        # Altitude
        # ----------------------------------------------------

        if phase != "TAXI":

            altitude = (
                (
                    2000
                    + 4000
                    * min(
                        1.0,
                        frac / 0.25,
                    )
                )
                * alt_boost
            )

        else:

            altitude = 0

        # ----------------------------------------------------
        # Ambient temperature
        # ----------------------------------------------------

        ambient_c = (
            25
            - altitude * 0.0065
            + ambient_boost
            + rng.normal(0, 0.5)
        )

        # ====================================================
        # HEALTHY DIGITAL TWIN BASELINE
        # ====================================================

        rpm_base = (
            800
            + throttle * 28
        )

        cht_base = (
            90
            + throttle * 0.9
            + max(
                0,
                ambient_c - 20,
            ) * 0.6
        )

        egt_base = (
            350
            + throttle * 5.2
            + max(
                0,
                ambient_c - 20,
            ) * 1.2
        )

        oil_pressure_base = (
            200
            + throttle * 3.0
            - max(
                0,
                oil_temp_state - 90,
            ) * 1.5
        )

        oil_temp_state += (
            0.02
            + throttle * 0.0006
        ) * (
            1
            - (
                oil_temp_state - 40
            ) / 70
        )

        fuel_flow_base = (
            4
            + throttle * 0.22
        )

        vibration_base = (
            0.15
            + (
                rpm_base / 4000
            ) * 0.15
            + 0.02
            * np.sin(t_min * 3)
        )

        alternator_v_base = 28.0

        battery_v_base = 25.5

        injection_timing_base = (
            22
            + throttle * 0.03
        )

        # ====================================================
        # FAULT
        # ====================================================

        sev = _ramp(
            frac,
            cfg.onset_fraction,
            cfg.severity_at_end,
        )

        d_rpm = 0.0
        d_cht = 0.0
        d_egt = 0.0
        d_oilp = 0.0
        d_oilt = 0.0
        d_fuel = 0.0
        d_vib = 0.0

        extra_noise_mult = 1.0

        ft = cfg.fault_type

        # ----------------------------------------------------
        # Misfire
        # ----------------------------------------------------

        if ft == "MISFIRE":

            if rng.random() < 0.15 * sev:

                d_egt -= (
                    rng.uniform(30, 80)
                    * sev
                )

                d_vib += (
                    rng.uniform(0.2, 0.6)
                    * sev
                )

                d_rpm -= (
                    rng.uniform(50, 150)
                    * sev
                )

        # ----------------------------------------------------
        # Injector abnormality
        # ----------------------------------------------------

        elif ft == "INJECTOR_ABNORMALITY":

            d_fuel += (
                rng.normal(0, 1)
                * sev
                * 3
                - 2 * sev
            )

            d_egt += (
                25
                * sev
                * np.sign(
                    rng.normal()
                )
            )

            injection_timing_base += (
                3
                * sev
                * rng.choice(
                    [-1, 1]
                )
            )

        # ----------------------------------------------------
        # Cooling degradation
        # ----------------------------------------------------

        elif ft == "COOLING_DEGRADATION":

            d_cht += 35 * sev
            d_egt += 20 * sev

        # ----------------------------------------------------
        # Lubrication issue
        # ----------------------------------------------------

        elif ft == "LUBRICATION_ISSUE":

            d_oilp -= 90 * sev
            d_oilt += 20 * sev

        # ----------------------------------------------------
        # Sensor drift
        # ----------------------------------------------------

        elif ft == "SENSOR_DRIFT":

            sensor_drift_bias[
                drift_target_param
            ] = (
                sensor_drift_bias.get(
                    drift_target_param,
                    0,
                )
                + 0.15 * sev
            )

        # ----------------------------------------------------
        # Combustion instability
        # ----------------------------------------------------

        elif ft == "COMBUSTION_INSTABILITY":

            extra_noise_mult = (
                1.0
                + 4.0 * sev
            )

        # ----------------------------------------------------
        # Overheating trend
        # ----------------------------------------------------

        elif ft == "OVERHEATING_TREND":

            d_cht += 45 * sev
            d_egt += 35 * sev
            d_oilt += 10 * sev

        # ----------------------------------------------------
        # Abnormal vibration
        # ----------------------------------------------------

        elif ft == "ABNORMAL_VIBRATION":

            d_vib += (
                0.5 * sev
                + (
                    0.3 * sev
                    if rng.random() < 0.1
                    else 0
                )
            )

        # ====================================================
        # SENSOR NOISE
        # ====================================================

        def noise(std):

            return (
                rng.normal(0, std)
                * extra_noise_mult
            )

        rpm = (
            rpm_base
            + d_rpm
            + noise(15)
        )

        cht = (
            cht_base
            + d_cht
            + noise(1.2)
        )

        egt = (
            egt_base
            + d_egt
            + noise(4)
        )

        oil_pressure = (
            oil_pressure_base
            + d_oilp
            + noise(4)
        )

        oil_temperature = (
            oil_temp_state
            + d_oilt
            + noise(0.8)
        )

        fuel_flow = (
            fuel_flow_base
            + d_fuel
            + noise(0.3)
        )

        vibration = max(
            0,
            vibration_base
            + d_vib
            + noise(0.02),
        )

        alternator_v = (
            alternator_v_base
            + noise(0.15)
        )

        battery_v = (
            battery_v_base
            + noise(0.15)
        )

        injection_timing = (
            injection_timing_base
            + noise(0.2)
        )

        # ====================================================
        # SENSOR DRIFT
        # ====================================================

        cht_reading = (
            cht
            + sensor_drift_bias.get(
                "cht_c",
                0,
            )
        )

        oilp_reading = (
            oil_pressure
            + sensor_drift_bias.get(
                "oil_pressure_kpa",
                0,
            )
        )

        egt_reading = (
            egt
            + sensor_drift_bias.get(
                "egt_c",
                0,
            )
        )

        # ====================================================
        # Missing sensor values
        # ====================================================

        def maybe_nan(value):

            if rng.random() < 0.002:
                return np.nan

            return value

        # ====================================================
        # Ground-truth labels
        # ====================================================

        true_fault_type = ft

        true_fault_active = int(
            sev > 0.05
        )

        true_severity = round(
            sev,
            3,
        )

        # ====================================================
        # Build telemetry row
        # ====================================================

        row = {

            # ------------------------------------------------
            # 1-4: Identity / mission
            # ------------------------------------------------

            "timestamp_s": round(
                i * cfg.sample_interval_s,
                1,
            ),

            "engine_id": cfg.engine_id,

            "mission_id": cfg.mission_id,

            "mission_phase": phase,

            # ------------------------------------------------
            # 5-7: Operating conditions
            # ------------------------------------------------

            "throttle_pct": round(
                throttle,
                2,
            ),

            "altitude_m": round(
                altitude,
                1,
            ),

            "ambient_temperature_c": round(
                ambient_c,
                2,
            ),

            # ------------------------------------------------
            # 8-17: Actual sensor readings
            # ------------------------------------------------

            "rpm": round(
                maybe_nan(rpm),
                1,
            ),

            "cht_c": round(
                maybe_nan(cht_reading),
                2,
            ),

            "egt_c": round(
                maybe_nan(egt_reading),
                2,
            ),

            "oil_pressure_kpa": round(
                maybe_nan(oilp_reading),
                2,
            ),

            "oil_temperature_c": round(
                maybe_nan(oil_temperature),
                2,
            ),

            "fuel_flow_lph": round(
                maybe_nan(fuel_flow),
                2,
            ),

            "vibration_g": round(
                maybe_nan(vibration),
                3,
            ),

            "alternator_voltage_v": round(
                alternator_v,
                2,
            ),

            "battery_voltage_v": round(
                battery_v,
                2,
            ),

            "injection_timing_deg": round(
                injection_timing,
                2,
            ),

            # ------------------------------------------------
            # 18-25: Digital Twin expected values
            # ------------------------------------------------

            "expected_rpm": round(
                rpm_base,
                1,
            ),

            "expected_cht_c": round(
                cht_base,
                2,
            ),

            "expected_egt_c": round(
                egt_base,
                2,
            ),

            "expected_oil_pressure_kpa": round(
                oil_pressure_base,
                2,
            ),

            "expected_oil_temperature_c": round(
                oil_temp_state,
                2,
            ),

            "expected_fuel_flow_lph": round(
                fuel_flow_base,
                2,
            ),

            "expected_vibration_g": round(
                vibration_base,
                3,
            ),

            "expected_injection_timing_deg": round(
                injection_timing_base,
                2,
            ),

            # ------------------------------------------------
            # 26-28: Ground truth fault labels
            # ------------------------------------------------

            "true_fault_type": true_fault_type,

            "true_fault_active": true_fault_active,

            "true_severity": true_severity,
        }

        rows.append(row)

    # ========================================================
    # Convert rows to dataframe
    # ========================================================

    df = pd.DataFrame(rows)

    # ========================================================
    # Residuals
    #
    # actual - expected
    # ========================================================

    parameters = [
        "rpm",
        "cht_c",
        "egt_c",
        "oil_pressure_kpa",
        "oil_temperature_c",
        "fuel_flow_lph",
        "vibration_g",
        "injection_timing_deg",
    ]

    for parameter in parameters:

        df[
            f"residual_{parameter}"
        ] = (
            df[parameter]
            - df[
                f"expected_{parameter}"
            ]
        )

    # ========================================================
    # TRUE DEGRADATION HEALTH
    #
    # 100 = healthy
    # 0   = end of life
    #
    # severity 0.0 -> health 100
    # severity 0.9 -> health 0
    # ========================================================

    eol_threshold = 0.9

    df["true_degradation_health"] = (
        100
        * (
            1
            - (
                df["true_severity"]
                / eol_threshold
            )
        )
    ).clip(
        lower=0,
        upper=100,
    )

    # ========================================================
    # TRUE RUL
    #
    # Ground-truth remaining useful life.
    #
    # This is only a synthetic reference value.
    # A real aircraft would NOT provide this value.
    # ========================================================

    df["true_rul_hours"] = np.nan

    total_steps = len(df)

    if cfg.fault_type != "NORMAL":

        onset_step = int(
            cfg.onset_fraction
            * total_steps
        )

        end_step = (
            total_steps - 1
        )

        # ----------------------------------------------------
        # Before fault onset
        # ----------------------------------------------------

        pre_fault_rul = (
            (
                end_step
                - onset_step
            )
            * cfg.sample_interval_s
            / 3600
            * (
                eol_threshold
                / max(
                    cfg.severity_at_end,
                    1e-6,
                )
            )
        )

        for i in range(total_steps):

            if i < onset_step:

                df.loc[
                    i,
                    "true_rul_hours",
                ] = pre_fault_rul

            else:

                remaining_steps = max(
                    0,
                    end_step - i,
                )

                df.loc[
                    i,
                    "true_rul_hours",
                ] = (
                    remaining_steps
                    * cfg.sample_interval_s
                    / 3600
                )

    else:

        # NORMAL mission:
        # effectively no foreseeable failure.
        df["true_rul_hours"] = 999.0

    # ========================================================
    # Reorder columns explicitly
    #
    # This guarantees the CSV always has exactly 38 columns
    # in the intended order.
    # ========================================================

    column_order = [

        # 1-4
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_phase",

        # 5-7
        "throttle_pct",
        "altitude_m",
        "ambient_temperature_c",

        # 8-17
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

        # 18-25
        "expected_rpm",
        "expected_cht_c",
        "expected_egt_c",
        "expected_oil_pressure_kpa",
        "expected_oil_temperature_c",
        "expected_fuel_flow_lph",
        "expected_vibration_g",
        "expected_injection_timing_deg",

        # 26-28
        "true_fault_type",
        "true_fault_active",
        "true_severity",

        # 29-36
        "residual_rpm",
        "residual_cht_c",
        "residual_egt_c",
        "residual_oil_pressure_kpa",
        "residual_oil_temperature_c",
        "residual_fuel_flow_lph",
        "residual_vibration_g",
        "residual_injection_timing_deg",

        # 37-38
        "true_degradation_health",
        "true_rul_hours",
    ]

    df = df[column_order]

    # ========================================================
    # Safety check
    # ========================================================

    assert len(df.columns) == 38, (
        f"Expected 38 columns, "
        f"got {len(df.columns)}"
    )

    return df


# ============================================================
# Generate complete dataset
# ============================================================

def generate_dataset(
    n_missions: int = 80,
    seed: Optional[int] = 42,
    duration_min: float = 1.0,
    sample_interval_s: float = 1.0,
) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    # --------------------------------------------------------
    # Roughly 40% normal missions
    # Remaining missions distributed across 8 faults
    # --------------------------------------------------------

    n_normal = max(
        1,
        round(
            n_missions * 0.4
        ),
    )

    n_fault_each = max(
        1,
        round(
            (n_missions - n_normal)
            / 8
        ),
    )

    plan = [
        "NORMAL"
    ] * n_normal

    for fault_type in FAULT_TYPES[1:]:

        plan += [
            fault_type
        ] * n_fault_each

    rng.shuffle(plan)

    if len(plan) >= n_missions:

        plan = plan[:n_missions]

    else:

        plan += (
            [
                "NORMAL"
            ]
            * (
                n_missions
                - len(plan)
            )
        )

    # --------------------------------------------------------
    # Environmental conditions
    # --------------------------------------------------------

    environments = [
        "STANDARD",
        "HIGH_ALTITUDE",
        "HOT_WEATHER",
        "RAPID_THROTTLE",
    ]

    all_dfs = []

    # ========================================================
    # Generate each mission
    # ========================================================

    for idx, fault_type in enumerate(plan):

        jitter = float(
            rng.uniform(
                0.85,
                1.15,
            )
        )

        config = MissionConfig(

            engine_id=(
                f"ENG-{(idx % 3) + 1:03d}"
            ),

            mission_id=(
                f"MIS-{idx + 1:04d}"
            ),

            duration_min=round(
                duration_min * jitter,
                3,
            ),

            sample_interval_s=(
                sample_interval_s
            ),

            fault_type=fault_type,

            onset_fraction=(
                float(
                    rng.uniform(
                        0.25,
                        0.55,
                    )
                )
                if fault_type != "NORMAL"
                else 1.0
            ),

            severity_at_end=(
                float(
                    rng.uniform(
                        0.6,
                        0.95,
                    )
                )
                if fault_type != "NORMAL"
                else 0.0
            ),

            seed=int(
                rng.integers(
                    0,
                    1_000_000,
                )
            ),

            env_condition=str(
                rng.choice(
                    environments
                )
            ),
        )

        df = generate_mission(
            config
        )

        all_dfs.append(df)

    # ========================================================
    # Combine all missions
    # ========================================================

    combined = pd.concat(
        all_dfs,
        ignore_index=True,
    )

    # ========================================================
    # Final safety check
    # ========================================================

    assert len(combined.columns) == 38, (
        f"Expected 38 columns, "
        f"got {len(combined.columns)}"
    )

    return combined


# ============================================================
# Script entry point
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Generate a fresh dataset every time.
    # --------------------------------------------------------

    df = generate_dataset(
        n_missions=20,
        seed=None,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    # --------------------------------------------------------
    # Locate backend directory
    #
    # generator.py:
    #
    # PS54/
    #   backend/
    #     src/
    #       digital_twin/
    #         generator.py
    #
    # parents[0] = digital_twin
    # parents[1] = src
    # parents[2] = backend
    # --------------------------------------------------------

    current_file = Path(
        __file__
    ).resolve()

    backend_dir = (
        current_file.parents[2]
    )

    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    output_dir = (
        backend_dir
        / "data"
        / "generated"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Unique filename
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    output_file = (
        output_dir
        / f"telemetry_{timestamp}.csv"
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    df.to_csv(
        output_file,
        index=False,
    )

    # --------------------------------------------------------
    # Print information
    # --------------------------------------------------------

    print(
        f"Generated "
        f"{df['mission_id'].nunique()} missions, "
        f"{len(df)} telemetry rows"
    )

    print(
        f"Generated "
        f"{len(df.columns)} columns"
    )

    print(
        f"Saved dataset to: "
        f"{output_file}"
    )

    print()
    print("Columns:")

    for index, column in enumerate(
        df.columns,
        start=1,
    ):

        print(
            f"{index:2}. {column}"
        )
