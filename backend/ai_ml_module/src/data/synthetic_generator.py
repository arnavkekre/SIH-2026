"""
Synthetic telemetry generator for PS54.

Purpose
-------
Generate realistic, deterministic-enough synthetic telemetry for the
AI/ML module of SIH PS54.

Core design
-----------
For every timestep, a healthy operating baseline is calculated from:

    throttle
    altitude
    ambient temperature
    mission phase
    engine warm-up state

That baseline represents the "Digital Twin expected value".

Then:

    actual_reading = expected_value + fault_deviation + sensor_noise

Therefore:

    residual = actual_reading - expected_value

The residual is meaningful because it represents deviation from expected
healthy engine behavior under the same operating conditions.

This is important for PS54 because a developing fault may remain below
a traditional static threshold while still deviating significantly from
Digital Twin expectations.

Mission
-------
Each mission follows:

    TAXI
      -> TAKEOFF
      -> CLIMB
      -> CRUISE
      -> LOITER
      -> DESCENT
      -> LANDING

Faults begin partway through a mission and progressively increase.

RUL design
----------
The simulation is intentionally short (roughly 1–2 minutes), therefore
RUL is expressed in SIMULATION SECONDS rather than hours.

For fault missions:

    true_rul_seconds =
        max(0, eol_timestamp_s - timestamp_s)

EOL is defined using the simulated severity threshold.

Ground-truth fields:
    true_fault_type
    true_fault_active
    true_severity
    true_effective_severity
    true_degradation_health
    eol_timestamp_s
    true_rul_seconds

These are training/evaluation labels only and are NOT available from
a real telemetry stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ============================================================================
# FAULT TAXONOMY
# ============================================================================

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


# ============================================================================
# MISSION PHASES
# ============================================================================
#
# Each tuple:
#   phase_name
#   start_fraction
#   end_fraction
#   nominal_throttle
#
# Fractions refer to the total mission duration.
# ============================================================================

PHASE_SCHEDULE = [
    ("TAXI",     0.00, 0.05, 15),
    ("TAKEOFF",  0.05, 0.10, 95),
    ("CLIMB",    0.10, 0.25, 85),
    ("CRUISE",   0.25, 0.70, 60),
    ("LOITER",   0.70, 0.85, 45),
    ("DESCENT",  0.85, 0.95, 30),
    ("LANDING",  0.95, 1.00, 20),
]


# ============================================================================
# HELPERS
# ============================================================================

def _phase_at(frac: float) -> tuple[str, float]:
    """
    Return mission phase and nominal throttle for a normalized mission time.

    Parameters
    ----------
    frac:
        Mission progress in [0, 1].

    Returns
    -------
    (phase_name, nominal_throttle)
    """

    frac = float(np.clip(frac, 0.0, 1.0))

    for name, start, end, throttle in PHASE_SCHEDULE:

        # Include the final endpoint in LANDING.
        if start <= frac < end:
            return name, float(throttle)

    # Explicit endpoint fallback.
    return "LANDING", float(PHASE_SCHEDULE[-1][3])


def _ramp(
    frac: float,
    onset: float,
    severity_end: float,
) -> float:
    """
    Monotonic smooth fault-severity ramp.

    Before onset:
        severity = 0

    After onset:
        severity smoothly increases toward severity_end.

    At mission end:
        severity == severity_end

    A cubic smoothstep is used so that:
        - there is no abrupt fault activation
        - the progression is monotonic
        - the endpoint is exactly controlled
    """

    if frac <= onset:
        return 0.0

    if onset >= 1.0:
        return 0.0

    progressed = (
        (frac - onset)
        / max(1e-6, 1.0 - onset)
    )

    progressed = float(
        np.clip(progressed, 0.0, 1.0)
    )

    smooth = (
        progressed
        * progressed
        * (3.0 - 2.0 * progressed)
    )

    return float(
        np.clip(severity_end, 0.0, 1.0)
        * smooth
    )


# ============================================================================
# MISSION CONFIGURATION
# ============================================================================

@dataclass
class MissionConfig:
    engine_id: str
    mission_id: str

    # Fast simulation for hackathon demo.
    duration_min: float = 1.0

    # 1 Hz telemetry.
    sample_interval_s: float = 1.0

    # Fault configuration.
    fault_type: str = "NORMAL"
    onset_fraction: float = 0.4
    severity_at_end: float = 0.8

    # Reproducibility.
    seed: Optional[int] = None

    # Environment.
    # STANDARD
    # HIGH_ALTITUDE
    # HOT_WEATHER
    # RAPID_THROTTLE
    env_condition: str = "STANDARD"


# ============================================================================
# MISSION GENERATION
# ============================================================================

def generate_mission(cfg: MissionConfig) -> pd.DataFrame:
    """
    Generate one complete synthetic mission.

    Returns
    -------
    pandas.DataFrame
        Timestamped engine telemetry, Digital Twin expectations,
        residuals and ground-truth labels.
    """

    if cfg.duration_min <= 0:
        raise ValueError("duration_min must be > 0.")

    if cfg.sample_interval_s <= 0:
        raise ValueError("sample_interval_s must be > 0.")

    if cfg.fault_type not in FAULT_TYPES:
        raise ValueError(
            f"Unknown fault_type={cfg.fault_type!r}. "
            f"Expected one of: {FAULT_TYPES}"
        )

    rng = np.random.default_rng(cfg.seed)

    # Use floor rather than int(float) ambiguity.
    n_steps = max(
        2,
        int(
            np.floor(
                (cfg.duration_min * 60.0)
                / cfg.sample_interval_s
            )
        ),
    )

    rows: list[dict] = []

    # ------------------------------------------------------------------------
    # Environment modifiers
    # ------------------------------------------------------------------------

    altitude_multiplier = 1.0
    ambient_temperature_offset = 0.0

    if cfg.env_condition == "HIGH_ALTITUDE":
        altitude_multiplier = 1.6

    elif cfg.env_condition == "HOT_WEATHER":
        ambient_temperature_offset = 15.0

    elif cfg.env_condition == "RAPID_THROTTLE":
        pass

    elif cfg.env_condition != "STANDARD":
        raise ValueError(
            f"Unknown env_condition={cfg.env_condition!r}."
        )

    rapid_throttle = (
        cfg.env_condition == "RAPID_THROTTLE"
    )

    # ------------------------------------------------------------------------
    # Stateful engine variables
    # ------------------------------------------------------------------------

    # Oil warms throughout the mission.
    oil_temp_state = 40.0

    # Persistent sensor bias for SENSOR_DRIFT.
    sensor_drift_bias: dict[str, float] = {}

    # Which physical parameter will experience the sensor drift.
    drift_target_param = str(
        rng.choice(
            [
                "cht_c",
                "oil_pressure_kpa",
                "egt_c",
            ]
        )
    )

    # Misfire creates a short-lived post-event signature.
    misfire_state = {
        "egt": 0.0,
        "vib": 0.0,
        "rpm": 0.0,
    }

    # ------------------------------------------------------------------------
    # Main mission loop
    # ------------------------------------------------------------------------

    for i in range(n_steps):

        timestamp_s = (
            i * cfg.sample_interval_s
        )

        t_min = (
            timestamp_s / 60.0
        )

        frac = (
            timestamp_s
            / max(
                cfg.duration_min * 60.0,
                1e-9,
            )
        )

        frac = float(
            np.clip(frac, 0.0, 1.0)
        )

        phase, base_throttle = _phase_at(frac)

        # ====================================================================
        # OPERATING CONDITIONS
        # ====================================================================

        throttle = (
            base_throttle
            + rng.normal(0.0, 3.0)
        )

        # Rapid throttle scenario.
        if rapid_throttle and phase in (
            "CRUISE",
            "LOITER",
        ):
            throttle += (
                25.0
                * np.sin(frac * 40.0)
            )

        throttle = float(
            np.clip(throttle, 0.0, 100.0)
        )

        # Altitude profile.
        if phase == "TAXI":
            altitude = 0.0
        else:
            altitude = (
                (
                    2000.0
                    + 4000.0
                    * min(
                        1.0,
                        frac / 0.25,
                    )
                )
                * altitude_multiplier
            )

        # Ambient temperature decreases with altitude.
        ambient_c = (
            25.0
            - altitude * 0.0065
            + ambient_temperature_offset
            + rng.normal(0.0, 0.5)
        )

        # ====================================================================
        # HEALTHY BASELINE / DIGITAL TWIN
        # ====================================================================
        #
        # This is the healthy expected engine behavior.
        #
        # Important:
        # The actual project currently uses this baseline as the simulated
        # Digital Twin expected output. P2 can later replace it with a more
        # sophisticated physics model without changing the ML interface.
        # ====================================================================

        rpm_base = (
            800.0
            + throttle * 28.0
        )

        cht_base = (
            90.0
            + throttle * 0.9
            + max(
                0.0,
                ambient_c - 20.0,
            ) * 0.6
        )

        egt_base = (
            350.0
            + throttle * 5.2
            + max(
                0.0,
                ambient_c - 20.0,
            ) * 1.2
        )

        oil_pressure_base = (
            200.0
            + throttle * 3.0
            - max(
                0.0,
                oil_temp_state - 90.0,
            ) * 1.5
        )

        # Stateful oil temperature.
        oil_temp_state += (
            0.02
            + throttle * 0.0006
        ) * (
            1.0
            - (
                oil_temp_state - 40.0
            ) / 70.0
        )

        # Keep physical value within sensible prototype range.
        oil_temp_state = float(
            np.clip(
                oil_temp_state,
                40.0,
                110.0,
            )
        )

        fuel_flow_base = (
            4.0
            + throttle * 0.22
        )

        vibration_base = (
            0.15
            + (rpm_base / 4000.0) * 0.15
            + 0.02 * np.sin(t_min * 3.0)
        )

        alternator_voltage_base = 28.0

        battery_voltage_base = 25.5

        injection_timing_base = (
            22.0
            + throttle * 0.03
        )

        # ====================================================================
        # FAULT DEVIATION
        # ====================================================================

        severity = _ramp(
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

        # Injection timing offset must be initialized for EVERY fault type.
        # It is only modified for INJECTOR_ABNORMALITY below.
        injection_timing_fault_offset = 0.0

        extra_noise_mult = 1.0

        fault_type = cfg.fault_type

        event_fired = False

        # ====================================================================
        # MISFIRE
        # ====================================================================

        if fault_type == "MISFIRE":

            if rng.random() < (
                0.15 * severity
            ):

                misfire_state["egt"] = (
                    rng.uniform(30.0, 80.0)
                    * max(severity, 0.1)
                )

                misfire_state["vib"] = (
                    rng.uniform(0.2, 0.6)
                    * max(severity, 0.1)
                )

                misfire_state["rpm"] = (
                    rng.uniform(50.0, 150.0)
                    * max(severity, 0.1)
                )

                event_fired = True

            else:

                misfire_state = {
                    key: value * 0.55
                    for key, value
                    in misfire_state.items()
                }

            d_egt -= misfire_state["egt"]
            d_vib += misfire_state["vib"]
            d_rpm -= misfire_state["rpm"]

        # ====================================================================
        # INJECTOR ABNORMALITY
        # ====================================================================

        elif fault_type == "INJECTOR_ABNORMALITY":

            d_fuel += (
                rng.normal(0.0, 1.0)
                * severity
                * 3.0
                - 2.0 * severity
            )

            d_egt += (
                25.0
                * severity
                * np.sign(
                    rng.normal()
                )
            )

            # Timing deviation is applied through a separate value below.
            injection_timing_fault_offset = (
                3.0
                * severity
                * rng.choice(
                    [-1.0, 1.0]
                )
            )

        else:

            injection_timing_fault_offset = 0.0

        # ====================================================================
        # COOLING DEGRADATION
        # ====================================================================

        if fault_type == "COOLING_DEGRADATION":

            d_cht += 35.0 * severity
            d_egt += 20.0 * severity

        # ====================================================================
        # LUBRICATION ISSUE
        # ====================================================================

        elif fault_type == "LUBRICATION_ISSUE":

            d_oilp -= 90.0 * severity
            d_oilt += 20.0 * severity

        # ====================================================================
        # SENSOR DRIFT
        # ====================================================================

        elif fault_type == "SENSOR_DRIFT":

            sensor_drift_bias[
                drift_target_param
            ] = (
                sensor_drift_bias.get(
                    drift_target_param,
                    0.0,
                )
                + 0.15 * severity
            )

        # ====================================================================
        # COMBUSTION INSTABILITY
        # ====================================================================

        elif fault_type == "COMBUSTION_INSTABILITY":

            extra_noise_mult = (
                1.0
                + 4.0 * severity
            )

        # ====================================================================
        # OVERHEATING TREND
        # ====================================================================

        elif fault_type == "OVERHEATING_TREND":

            d_cht += 45.0 * severity
            d_egt += 35.0 * severity
            d_oilt += 10.0 * severity

        # ====================================================================
        # ABNORMAL VIBRATION
        # ====================================================================

        elif fault_type == "ABNORMAL_VIBRATION":

            d_vib += (
                0.5 * severity
                + (
                    0.3 * severity
                    if rng.random() < 0.1
                    else 0.0
                )
            )

        # ====================================================================
        # EFFECTIVE / DETECTABLE SEVERITY
        # ====================================================================
        #
        # This label is specifically intended for fault classification.
        # Underlying true_severity remains the smooth degradation trajectory.
        #
        # MISFIRE:
        #   Positive classification signal exists only while the event/tail
        #   actually carries measurable signal.
        #
        # SENSOR_DRIFT:
        #   Classification signal follows actual accumulated bias.
        # ====================================================================

        if fault_type == "MISFIRE":

            tail_active = (
                max(
                    misfire_state.values()
                )
                > 5.0
            )

            effective_severity = (
                severity
                if (
                    event_fired
                    or tail_active
                )
                else 0.0
            )

        elif fault_type == "SENSOR_DRIFT":

            current_bias_mag = abs(
                sensor_drift_bias.get(
                    drift_target_param,
                    0.0,
                )
            )

            effective_severity = min(
                1.0,
                current_bias_mag / 1.5,
            )

        else:

            effective_severity = severity

        # ====================================================================
        # SENSOR NOISE
        # ====================================================================

        def noise(std: float) -> float:
            return float(
                rng.normal(0.0, std)
                * extra_noise_mult
            )

        rpm = (
            rpm_base
            + d_rpm
            + noise(15.0)
        )

        cht = (
            cht_base
            + d_cht
            + noise(1.2)
        )

        egt = (
            egt_base
            + d_egt
            + noise(4.0)
        )

        oil_pressure = (
            oil_pressure_base
            + d_oilp
            + noise(4.0)
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
            0.0,
            vibration_base
            + d_vib
            + noise(0.02),
        )

        alternator_v = (
            alternator_voltage_base
            + noise(0.15)
        )

        battery_v = (
            battery_voltage_base
            + noise(0.15)
        )

        injection_timing = (
            injection_timing_base
            + injection_timing_fault_offset
            + noise(0.2)
        )

        # ====================================================================
        # APPLY SENSOR DRIFT TO ACTUAL READING ONLY
        # ====================================================================
        #
        # The Digital Twin expected value stays clean.
        # This is necessary so SENSOR_DRIFT creates a genuine residual.
        # ====================================================================

        cht_reading = (
            cht
            + sensor_drift_bias.get(
                "cht_c",
                0.0,
            )
        )

        oilp_reading = (
            oil_pressure
            + sensor_drift_bias.get(
                "oil_pressure_kpa",
                0.0,
            )
        )

        egt_reading = (
            egt
            + sensor_drift_bias.get(
                "egt_c",
                0.0,
            )
        )

        # ====================================================================
        # OCCASIONAL SENSOR DROPOUT
        # ====================================================================

        def maybe_nan(value: float) -> float:
            if rng.random() < 0.002:
                return float("nan")
            return value

        # ====================================================================
        # ROW ASSEMBLY
        # ====================================================================

        row = {
            # ---------------------------------------------------------------
            # Metadata / operating context
            # ---------------------------------------------------------------

            "timestamp_s": round(
                timestamp_s,
                1,
            ),

            "engine_id": cfg.engine_id,

            "mission_id": cfg.mission_id,

            "mission_phase": phase,

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

            # ---------------------------------------------------------------
            # Actual sensor telemetry
            # ---------------------------------------------------------------

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

            # ---------------------------------------------------------------
            # Digital Twin expected values
            # ---------------------------------------------------------------
            #
            # These are the healthy baseline values.
            # ---------------------------------------------------------------

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

            # ---------------------------------------------------------------
            # Ground-truth labels
            # ---------------------------------------------------------------

            "true_fault_type": fault_type,

            "true_fault_active": int(
                severity > 0.05
            ),

            "true_severity": round(
                severity,
                3,
            ),

            "true_effective_severity": round(
                effective_severity,
                3,
            ),
        }

        rows.append(row)

    # =========================================================================
    # BUILD DATAFRAME
    # =========================================================================

    df = pd.DataFrame(rows)

    # =========================================================================
    # DIGITAL TWIN RESIDUALS
    # =========================================================================

    residual_parameters = [
        "rpm",
        "cht_c",
        "egt_c",
        "oil_pressure_kpa",
        "oil_temperature_c",
        "fuel_flow_lph",
        "vibration_g",
        "injection_timing_deg",
    ]

    for parameter in residual_parameters:

        df[f"residual_{parameter}"] = (
            df[parameter]
            - df[f"expected_{parameter}"]
        )

    # =========================================================================
    # GROUND-TRUTH DEGRADATION
    # =========================================================================

    # Severity at which this simulated engine is considered EOL.
    eol_threshold = 0.90

    df["true_degradation_health"] = (
        100.0
        * (
            1.0
            - (
                df["true_severity"]
                / eol_threshold
            )
        )
    ).clip(
        lower=0.0,
        upper=100.0,
    )

    # =========================================================================
    # GROUND-TRUTH RUL
    # =========================================================================
    #
    # RUL is in SIMULATION SECONDS.
    #
    # Fault mission:
    #
    #     current time → EOL time
    #
    # Normal mission:
    #
    #     no simulated EOL => NaN
    #
    # For fault missions, use a projected EOL timestamp. If the sampled
    # mission itself reaches the EOL threshold, use the first such timestep.
    # Otherwise estimate the EOL time based on the severity progression.
    # =========================================================================

    df["eol_timestamp_s"] = np.nan

    df["true_rul_seconds"] = np.nan

    if fault_type != "NORMAL":

        time_values = (
            df["timestamp_s"]
            .to_numpy(dtype=float)
        )

        severity_values = (
            df["true_severity"]
            .to_numpy(dtype=float)
        )

        # ---------------------------------------------------------------------
        # Case 1:
        # Sampled mission actually reaches EOL.
        # ---------------------------------------------------------------------

        eol_candidates = np.where(
            severity_values >= eol_threshold
        )[0]

        if len(eol_candidates) > 0:

            eol_index = int(
                eol_candidates[0]
            )

            eol_time = float(
                time_values[eol_index]
            )

        # ---------------------------------------------------------------------
        # Case 2:
        # Mission ends below EOL threshold.
        #
        # Project the EOL point using the configured end severity.
        # ---------------------------------------------------------------------

        else:

            severity_end = float(
                max(
                    cfg.severity_at_end,
                    1e-6,
                )
            )

            mission_end_time = float(
                time_values[-1]
            )

            onset_time = float(
                cfg.onset_fraction
                * cfg.duration_min
                * 60.0
            )

            progression_duration = max(
                mission_end_time
                - onset_time,
                cfg.sample_interval_s,
            )

            # Approximate additional progression required to reach EOL.
            projected_extra_time = (
                progression_duration
                * (
                    eol_threshold
                    / severity_end
                    - 1.0
                )
            )

            eol_time = (
                mission_end_time
                + max(
                    0.0,
                    projected_extra_time,
                )
            )

        # Every row in a mission shares the same simulated EOL timestamp.
        df["eol_timestamp_s"] = eol_time

        # Remaining simulated operating time until EOL.
        df["true_rul_seconds"] = (
            df["eol_timestamp_s"]
            - df["timestamp_s"]
        ).clip(
            lower=0.0
        )

    else:

        # NORMAL missions have no simulated EOL event.
        #
        # NaN is intentional. It means:
        # "No foreseeable failure within this simulation."
        df["eol_timestamp_s"] = np.nan

        df["true_rul_seconds"] = np.nan

    # =========================================================================
    # FINAL COLUMN ORDER
    # =========================================================================
    #
    # This provides a stable canonical schema for downstream ML code.
    # =========================================================================

    canonical_columns = [
        # Metadata
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_phase",

        # Operating/environment context
        "throttle_pct",
        "altitude_m",
        "ambient_temperature_c",

        # Actual telemetry
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

        # Digital Twin expected values
        "expected_rpm",
        "expected_cht_c",
        "expected_egt_c",
        "expected_oil_pressure_kpa",
        "expected_oil_temperature_c",
        "expected_fuel_flow_lph",
        "expected_vibration_g",
        "expected_injection_timing_deg",

        # Residuals
        "residual_rpm",
        "residual_cht_c",
        "residual_egt_c",
        "residual_oil_pressure_kpa",
        "residual_oil_temperature_c",
        "residual_fuel_flow_lph",
        "residual_vibration_g",
        "residual_injection_timing_deg",

        # Ground truth
        "true_fault_type",
        "true_fault_active",
        "true_severity",
        "true_effective_severity",
        "true_degradation_health",
        "eol_timestamp_s",
        "true_rul_seconds",
    ]

    df = df[canonical_columns]

    return df


# ============================================================================
# DATASET GENERATION
# ============================================================================

def generate_dataset(
    n_missions: int = 80,
    seed: int = 42,
    out_dir: str = "data/synthetic",
    duration_min: float = 1.0,
    sample_interval_s: float = 1.0,
) -> pd.DataFrame:
    """
    Generate a balanced multi-mission synthetic dataset.

    Approximately:
        40% NORMAL
        60% spread over eight fault types.

    Missions are randomized across environmental conditions and small
    duration variations so the model cannot simply memorize a fixed pattern.
    """

    import os

    os.makedirs(
        out_dir,
        exist_ok=True,
    )

    if n_missions < 1:
        raise ValueError(
            "n_missions must be >= 1."
        )

    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------------
    # Fault distribution
    # ------------------------------------------------------------------------

    n_normal = max(
        1,
        round(
            n_missions * 0.40
        ),
    )

    remaining_missions = max(
        0,
        n_missions - n_normal,
    )

    n_fault_each = max(
        1,
        round(
            remaining_missions / 8
        ),
    )

    plan = (
        ["NORMAL"] * n_normal
    )

    for fault_type in FAULT_TYPES[1:]:
        plan += (
            [fault_type]
            * n_fault_each
        )

    rng.shuffle(plan)

    if len(plan) >= n_missions:

        plan = plan[:n_missions]

    else:

        plan += (
            ["NORMAL"]
            * (
                n_missions
                - len(plan)
            )
        )

    # ------------------------------------------------------------------------
    # Environments
    # ------------------------------------------------------------------------

    environments = [
        "STANDARD",
        "HIGH_ALTITUDE",
        "HOT_WEATHER",
        "RAPID_THROTTLE",
    ]

    all_dfs: list[pd.DataFrame] = []

    # ------------------------------------------------------------------------
    # Generate missions
    # ------------------------------------------------------------------------

    for idx, fault_type in enumerate(plan):

        # Small mission-duration variation prevents models from learning
        # an identical fixed mission timeline.
        duration_jitter = float(
            rng.uniform(
                0.85,
                1.15,
            )
        )

        mission_duration = round(
            duration_min
            * duration_jitter,
            3,
        )

        if fault_type != "NORMAL":

            onset_fraction = float(
                rng.uniform(
                    0.25,
                    0.55,
                )
            )

            # Ensure fault missions reach the EOL threshold.
            severity_at_end = float(
                rng.uniform(
                    0.92,
                    1.00,
                )
            )

        else:

            onset_fraction = 1.0
            severity_at_end = 0.0

        cfg = MissionConfig(

            engine_id=(
                f"ENG-{(idx % 3) + 1:03d}"
            ),

            mission_id=(
                f"MIS-{idx + 1:04d}"
            ),

            duration_min=mission_duration,

            sample_interval_s=sample_interval_s,

            fault_type=fault_type,

            onset_fraction=onset_fraction,

            severity_at_end=severity_at_end,

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

        mission_df = generate_mission(
            cfg
        )

        mission_path = os.path.join(
            out_dir,
            f"{cfg.mission_id}_{fault_type}.csv",
        )

        mission_df.to_csv(
            mission_path,
            index=False,
        )

        all_dfs.append(
            mission_df
        )

    # ------------------------------------------------------------------------
    # Combined dataset
    # ------------------------------------------------------------------------

    combined = pd.concat(
        all_dfs,
        ignore_index=True,
    )

    combined_path = os.path.join(
        out_dir,
        "combined_dataset.csv",
    )

    combined.to_csv(
        combined_path,
        index=False,
    )

    return combined


# ============================================================================
# COMMAND-LINE ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    df = generate_dataset(
        n_missions=20,
    )

    print(
        f"Generated "
        f"{df['mission_id'].nunique()} missions, "
        f"{len(df)} total rows"
    )

    print(
        "\nFault distribution:"
    )

    print(
        df["true_fault_type"]
        .value_counts()
    )

    print(
        "\nRUL summary:"
    )

    print(
        df["true_rul_seconds"]
        .describe()
        .round(3)
    )