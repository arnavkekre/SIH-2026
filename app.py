from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


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

PHASE_SCHEDULE = [
    ("TAXI", 0.00, 0.05, 15),
    ("TAKEOFF", 0.05, 0.10, 95),
    ("CLIMB", 0.10, 0.25, 85),
    ("CRUISE", 0.25, 0.70, 60),
    ("LOITER", 0.70, 0.85, 45),
    ("DESCENT", 0.85, 0.95, 30),
    ("LANDING", 0.95, 1.00, 20),
]


def _phase_at(frac: float):
    for name, start, end, throttle in PHASE_SCHEDULE:
        if start <= frac < end:
            return name, throttle
    return PHASE_SCHEDULE[-1][0], PHASE_SCHEDULE[-1][3]


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


def _ramp(frac: float, onset: float, severity_end: float) -> float:
    if frac <= onset:
        return 0.0

    progressed = (frac - onset) / max(1e-6, 1.0 - onset)

    return severity_end * (
        1 / (1 + np.exp(-6 * (progressed - 0.5)))
    )


def generate_mission(cfg: MissionConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)

    n_steps = int(
        (cfg.duration_min * 60) / cfg.sample_interval_s
    )

    rows = []

    alt_boost = 1.0
    ambient_boost = 0

    if cfg.env_condition == "HIGH_ALTITUDE":
        alt_boost = 1.6
    elif cfg.env_condition == "HOT_WEATHER":
        ambient_boost = 15

    rapid_throttle = cfg.env_condition == "RAPID_THROTTLE"

    oil_temp_state = 40.0
    sensor_drift_bias = {}

    drift_target_param = rng.choice(
        ["cht_c", "oil_pressure_kpa", "egt_c"]
    )

    for i in range(n_steps):

        t_min = i * cfg.sample_interval_s / 60.0
        frac = t_min / cfg.duration_min

        phase, base_throttle = _phase_at(frac)

        throttle = base_throttle + rng.normal(0, 3)

        if rapid_throttle and phase in ("CRUISE", "LOITER"):
            throttle += 25 * np.sin(frac * 40)

        throttle = float(np.clip(throttle, 0, 100))

        altitude = (
            (2000 + 4000 * min(1.0, frac / 0.25)) * alt_boost
            if phase != "TAXI"
            else 0
        )

        ambient_c = (
            25
            - altitude * 0.0065
            + ambient_boost
            + rng.normal(0, 0.5)
        )

        # Healthy baseline telemetry
        rpm_base = 800 + throttle * 28

        cht_base = (
            90
            + throttle * 0.9
            + max(0, ambient_c - 20) * 0.6
        )

        egt_base = (
            350
            + throttle * 5.2
            + max(0, ambient_c - 20) * 1.2
        )

        oil_pressure_base = (
            200
            + throttle * 3.0
            - max(0, oil_temp_state - 90) * 1.5
        )

        oil_temp_state += (
            0.02
            + throttle * 0.0006
        ) * (
            1 - (oil_temp_state - 40) / 70
        )

        fuel_flow_base = 4 + throttle * 0.22

        vibration_base = (
            0.15
            + (rpm_base / 4000) * 0.15
            + 0.02 * np.sin(t_min * 3)
        )

        alternator_v_base = 28.0
        battery_v_base = 25.5

        injection_timing_base = 22 + throttle * 0.03

        # Fault deviation
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

        if ft == "MISFIRE":
            if rng.random() < 0.15 * sev:
                d_egt -= rng.uniform(30, 80) * sev
                d_vib += rng.uniform(0.2, 0.6) * sev
                d_rpm -= rng.uniform(50, 150) * sev

        elif ft == "INJECTOR_ABNORMALITY":
            d_fuel += (
                rng.normal(0, 1) * sev * 3
                - 2 * sev
            )

            d_egt += (
                25
                * sev
                * np.sign(rng.normal())
            )

            injection_timing_base += (
                3
                * sev
                * rng.choice([-1, 1])
            )

        elif ft == "COOLING_DEGRADATION":
            d_cht += 35 * sev
            d_egt += 20 * sev

        elif ft == "LUBRICATION_ISSUE":
            d_oilp -= 90 * sev
            d_oilt += 20 * sev

        elif ft == "SENSOR_DRIFT":
            sensor_drift_bias[drift_target_param] = (
                sensor_drift_bias.get(
                    drift_target_param,
                    0,
                )
                + 0.15 * sev
            )

        elif ft == "COMBUSTION_INSTABILITY":
            extra_noise_mult = 1.0 + 4.0 * sev

        elif ft == "OVERHEATING_TREND":
            d_cht += 45 * sev
            d_egt += 35 * sev
            d_oilt += 10 * sev

        elif ft == "ABNORMAL_VIBRATION":
            d_vib += (
                0.5 * sev
                + (
                    0.3 * sev
                    if rng.random() < 0.1
                    else 0
                )
            )

        # Sensor noise
        def noise(std):
            return rng.normal(0, std) * extra_noise_mult

        rpm = rpm_base + d_rpm + noise(15)

        cht = cht_base + d_cht + noise(1.2)

        egt = egt_base + d_egt + noise(4)

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

        # Sensor drift affects actual readings only
        cht_reading = (
            cht
            + sensor_drift_bias.get("cht_c", 0)
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
            + sensor_drift_bias.get("egt_c", 0)
        )

        def maybe_nan(value):
            if rng.random() < 0.002:
                return np.nan
            return value

        row = {
            "timestamp_s": round(
                i * cfg.sample_interval_s,
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

            # Healthy expected values
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

            # Ground truth
            "true_fault_type": ft,

            "true_fault_active": int(
                sev > 0.05
            ),

            "true_severity": round(
                sev,
                3,
            ),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # Residual telemetry
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
        df[f"residual_{parameter}"] = (
            df[parameter]
            - df[f"expected_{parameter}"]
        )

    return df


def generate_dataset(
    n_missions: int = 80,
    seed: int = 42,
    duration_min: float = 1.0,
    sample_interval_s: float = 1.0,
) -> pd.DataFrame:

    rng = np.random.default_rng(seed)

    n_normal = max(
        1,
        round(n_missions * 0.4),
    )

    n_fault_each = max(
        1,
        round((n_missions - n_normal) / 8),
    )

    plan = ["NORMAL"] * n_normal

    for fault_type in FAULT_TYPES[1:]:
        plan += [fault_type] * n_fault_each

    rng.shuffle(plan)

    if len(plan) >= n_missions:
        plan = plan[:n_missions]
    else:
        plan += [
            "NORMAL"
        ] * (
            n_missions - len(plan)
        )

    environments = [
        "STANDARD",
        "HIGH_ALTITUDE",
        "HOT_WEATHER",
        "RAPID_THROTTLE",
    ]

    all_dfs = []

    for idx, fault_type in enumerate(plan):

        jitter = float(
            rng.uniform(0.85, 1.15)
        )

        config = MissionConfig(
            engine_id=f"ENG-{(idx % 3) + 1:03d}",
            mission_id=f"MIS-{idx + 1:04d}",

            duration_min=round(
                duration_min * jitter,
                3,
            ),

            sample_interval_s=sample_interval_s,

            fault_type=fault_type,

            onset_fraction=(
                float(
                    rng.uniform(0.25, 0.55)
                )
                if fault_type != "NORMAL"
                else 1.0
            ),

            severity_at_end=(
                float(
                    rng.uniform(0.6, 0.95)
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
                rng.choice(environments)
            ),
        )

        df = generate_mission(config)
        all_dfs.append(df)

    return pd.concat(
        all_dfs,
        ignore_index=True,
    )


if __name__ == "__main__":
    df = generate_dataset(
        n_missions=20,
        seed=42,
        duration_min=1.0,
        sample_interval_s=1.0,
    )

    df.to_csv(
        "telemetry_dataset.csv",
        index=False,
    )

    print(
        f"Generated {df['mission_id'].nunique()} missions, "
        f"{len(df)} telemetry rows"
    )
