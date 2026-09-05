"""
Canonical data contracts for the PS54 AI/ML Engine Health module.

These mirror configs/features.yaml exactly. If you change a field name here,
update the YAML too - they must stay in sync since the YAML is the
human-readable spec other sub-teams (P1, P2, P4) read.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal, Dict, List
from pydantic import BaseModel, Field

MissionPhase = Literal[
    "TAXI", "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING"
]

FAULT_CODES = [
    "MISFIRE",
    "INJECTOR_ABNORMALITY",
    "COOLING_DEGRADATION",
    "LUBRICATION_ISSUE",
    "SENSOR_DRIFT",
    "COMBUSTION_INSTABILITY",
    "OVERHEATING_TREND",
    "ABNORMAL_VIBRATION",
]


class Telemetry(BaseModel):
    """P1 -> P3 contract: raw sensor telemetry for a single timestep."""
    timestamp: datetime
    engine_id: str
    mission_id: str

    rpm: float = Field(ge=0)
    cht_c: float
    egt_c: float
    oil_pressure_kpa: float = Field(ge=0)
    oil_temperature_c: float
    fuel_flow_lph: float = Field(ge=0)
    vibration_g: float = Field(ge=0)
    alternator_voltage_v: float
    battery_voltage_v: float
    injection_timing_deg: float

    altitude_m: float
    ambient_temperature_c: float
    throttle_pct: float = Field(ge=0, le=100)
    mission_phase: MissionPhase


class DigitalTwinExpected(BaseModel):
    """The 'expected' block from P2's digital twin core."""
    rpm: float
    cht_c: float
    egt_c: float
    oil_pressure_kpa: float
    oil_temperature_c: float
    fuel_flow_lph: float
    vibration_g: float
    alternator_voltage_v: float
    injection_timing_deg: float


class DigitalTwinFrame(BaseModel):
    """P2 -> P3 contract."""
    timestamp: datetime
    engine_id: str
    expected: DigitalTwinExpected
    residuals: Dict[str, float]
    dt_model_version: str


class Evidence(BaseModel):
    parameter: str
    observation: str
    reason_code: str


class FaultPrediction(BaseModel):
    fault: str
    probability: float = Field(ge=0, le=1)
    severity: Literal["LOW", "MEDIUM", "HIGH"]


class RULEstimate(BaseModel):
    value: float
    unit: Literal["hours"] = "hours"
    confidence: float = Field(ge=0, le=1)


class HealthBlock(BaseModel):
    score: float = Field(ge=0, le=100)
    status: Literal["HEALTHY", "WARNING", "DEGRADING", "CRITICAL"]


class AnomalyBlock(BaseModel):
    detected: bool
    score: float = Field(ge=0, le=1)


class MLOutput(BaseModel):
    """P3 -> P4 contract. This is the exact JSON returned by POST /predict."""
    engine_id: str
    timestamp: datetime

    health: HealthBlock
    anomaly: AnomalyBlock
    fault_predictions: List[FaultPrediction]
    rul: RULEstimate
    evidence: List[Evidence]
    model_version: str
