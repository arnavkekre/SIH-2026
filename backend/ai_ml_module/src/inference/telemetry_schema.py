"""
Backend <-> AI/ML telemetry contract.

The backend sends raw engine telemetry using these fields.
The ML layer converts them into engineered features internally.

Ground-truth fields such as true_fault_type and true_rul_seconds
must NEVER be sent by the real backend.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    timestamp_s: float = Field(..., ge=0)

    engine_id: str
    mission_id: str

    mission_phase: Optional[str] = None

    throttle_pct: float
    altitude_m: float
    ambient_temperature_c: float

    rpm: float
    cht_c: float
    egt_c: float
    oil_pressure_kpa: float
    oil_temperature_c: float
    fuel_flow_lph: float
    vibration_g: float

    alternator_voltage_v: float
    battery_voltage_v: float

    injection_timing_deg: float
    expected_rpm: float | None = None
    expected_cht_c: float | None = None
    expected_egt_c: float | None = None
    expected_oil_pressure_kpa: float | None = None
    expected_oil_temperature_c: float | None = None
    expected_fuel_flow_lph: float | None = None
    expected_vibration_g: float | None = None
    expected_injection_timing_deg: float | None = None

    residual_rpm: float | None = None
    residual_cht_c: float | None = None
    residual_egt_c: float | None = None
    residual_oil_pressure_kpa: float | None = None
    residual_oil_temperature_c: float | None = None
    residual_fuel_flow_lph: float | None = None
    residual_vibration_g: float | None = None
    residual_injection_timing_deg: float | None = None