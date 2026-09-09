import { create } from 'zustand'

/**
 * AeroTwin global application state.
 * 
 * Single source of truth for all telemetry, inference, replay,
 * and connection data. Components subscribe to slices of this store.
 * 
 * IMPORTANT: No true_* ground-truth fields are ever stored here.
 * All fault/health/anomaly data comes exclusively from backend inference.
 */
const useAeroStore = create((set, get) => ({
  // ──────────────────────────────────────────────
  // Connection
  // ──────────────────────────────────────────────
  connectionStatus: 'CONNECTING', // 'ONLINE' | 'OFFLINE' | 'CONNECTING'
  apiLastPing: null,

  // ──────────────────────────────────────────────
  // Identity
  // ──────────────────────────────────────────────
  engineId: null,
  missionId: null,
  missionPhase: null,
  timestampS: null,

  // ──────────────────────────────────────────────
  // Raw telemetry
  // ──────────────────────────────────────────────
  telemetry: {
    rpm: null,
    cht_c: null,
    egt_c: null,
    oil_pressure_kpa: null,
    oil_temperature_c: null,
    fuel_flow_lph: null,
    vibration_g: null,
    alternator_voltage_v: null,
    battery_voltage_v: null,
    injection_timing_deg: null,
    throttle_pct: null,
    altitude_m: null,
    ambient_temperature_c: null,
  },

  // Digital Twin expected values
  expectedValues: {
    expected_rpm: null,
    expected_cht_c: null,
    expected_egt_c: null,
    expected_oil_pressure_kpa: null,
    expected_oil_temperature_c: null,
    expected_fuel_flow_lph: null,
    expected_vibration_g: null,
    expected_injection_timing_deg: null,
  },

  // Digital Twin residuals (actual - expected)
  residuals: {
    residual_rpm: null,
    residual_cht_c: null,
    residual_egt_c: null,
    residual_oil_pressure_kpa: null,
    residual_oil_temperature_c: null,
    residual_fuel_flow_lph: null,
    residual_vibration_g: null,
    residual_injection_timing_deg: null,
  },

  // ──────────────────────────────────────────────
  // AI/ML inference (from backend ONLY)
  // ──────────────────────────────────────────────
  anomalyScore: null,
  fault: {
    type: null,
    confidence: null,
    severity: null,
    active: false,
  },
  healthScore: null,
  healthStatus: null, // 'HEALTHY' | 'WARNING' | 'DEGRADING' | 'CRITICAL'
  rul: {
    seconds: null,
    minutes: null,
    hours: null,
    status: null,
  },
  trend: null,
  maintenanceRecommendation: null,

  // ──────────────────────────────────────────────
  // Replay state
  // ──────────────────────────────────────────────
  replay: {
    running: false,
    paused: false,
    progress: 0,
    speed: 1.0,
    currentRow: 0,
    totalRows: 0,
  },
  simulationMode: true,

  // ──────────────────────────────────────────────
  // UI freshness
  // ──────────────────────────────────────────────
  dataFreshness: null,
  isStale: false,
  error: null,

  // ──────────────────────────────────────────────
  // History (for charts — last N points)
  // ──────────────────────────────────────────────
  telemetryHistory: [],   // array of telemetry snapshots
  anomalyHistory: [],     // [{ timestampS, anomalyScore }]
  healthHistory: [],      // [{ timestampS, healthScore, healthStatus }]
  faultHistory: [],       // [{ timestampS, type, confidence }]
  HISTORY_MAX: 120,

  // ──────────────────────────────────────────────
  // Actions
  // ──────────────────────────────────────────────

  setConnectionStatus: (status) => set({ connectionStatus: status, apiLastPing: new Date() }),

  setError: (error) => set({ error }),

  /**
   * Update store from a backend /latest response result.
   * Only uses AI/ML inference fields — never true_* ground-truth.
   */
  updateFromResult: (result) => {
    if (!result) return

    const now = new Date()
    const HISTORY_MAX = get().HISTORY_MAX

    // Extract telemetry from the result's embedded data
    // The /latest endpoint returns the processed result which includes
    // the raw telemetry fields at the top level.
    const newTelemetry = {
      rpm: result.rpm ?? get().telemetry.rpm,
      cht_c: result.cht_c ?? get().telemetry.cht_c,
      egt_c: result.egt_c ?? get().telemetry.egt_c,
      oil_pressure_kpa: result.oil_pressure_kpa ?? get().telemetry.oil_pressure_kpa,
      oil_temperature_c: result.oil_temperature_c ?? get().telemetry.oil_temperature_c,
      fuel_flow_lph: result.fuel_flow_lph ?? get().telemetry.fuel_flow_lph,
      vibration_g: result.vibration_g ?? get().telemetry.vibration_g,
      alternator_voltage_v: result.alternator_voltage_v ?? get().telemetry.alternator_voltage_v,
      battery_voltage_v: result.battery_voltage_v ?? get().telemetry.battery_voltage_v,
      injection_timing_deg: result.injection_timing_deg ?? get().telemetry.injection_timing_deg,
      throttle_pct: result.throttle_pct ?? get().telemetry.throttle_pct,
      altitude_m: result.altitude_m ?? get().telemetry.altitude_m,
      ambient_temperature_c: result.ambient_temperature_c ?? get().telemetry.ambient_temperature_c,
    }

    // Build expected values from residuals if raw telemetry is available
    const residuals = result.residuals || {}

    // History updates
    const prevAnomalyHistory = get().anomalyHistory
    const prevHealthHistory = get().healthHistory
    const prevFaultHistory = get().faultHistory
    const prevTelemetryHistory = get().telemetryHistory

    const newAnomalyPoint = {
      timestampS: result.timestamp_s,
      anomalyScore: result.anomaly_score,
    }

    const newHealthPoint = {
      timestampS: result.timestamp_s,
      healthScore: result.health_score,
      healthStatus: result.health_status,
    }

    const newFaultPoint = {
      timestampS: result.timestamp_s,
      type: result.fault?.type,
      confidence: result.fault?.confidence,
      active: result.fault?.active,
    }

    const newTelPoint = {
      timestampS: result.timestamp_s,
      ...newTelemetry,
    }

    set({
      engineId: result.engine_id,
      missionId: result.mission_id,
      missionPhase: result.mission_phase,
      timestampS: result.timestamp_s,

      telemetry: newTelemetry,
      residuals,

      // AI/ML inference only
      anomalyScore: result.anomaly_score,
      fault: {
        type: result.fault?.type ?? null,
        confidence: result.fault?.confidence ?? null,
        severity: result.fault?.severity ?? null,
        active: result.fault?.active ?? false,
      },
      healthScore: result.health_score,
      healthStatus: result.health_status,
      rul: {
        seconds: result.rul_seconds ?? null,
        minutes: result.rul_minutes ?? null,
        hours: result.rul_hours ?? null,
        status: result.rul_status ?? null,
      },
      trend: result.trend,
      maintenanceRecommendation: result.maintenance_recommendation,

      dataFreshness: now,
      isStale: false,
      error: null,

      // Append to history
      anomalyHistory: [...prevAnomalyHistory, newAnomalyPoint].slice(-HISTORY_MAX),
      healthHistory: [...prevHealthHistory, newHealthPoint].slice(-HISTORY_MAX),
      faultHistory: [...prevFaultHistory, newFaultPoint].slice(-HISTORY_MAX),
      telemetryHistory: [...prevTelemetryHistory, newTelPoint].slice(-HISTORY_MAX),
    })
  },

  updateReplay: (replayState) => set({ replay: replayState }),

  setStale: () => set({ isStale: true }),

  reset: () => set({
    engineId: null, missionId: null, missionPhase: null, timestampS: null,
    anomalyScore: null, healthScore: null, healthStatus: null,
    fault: { type: null, confidence: null, severity: null, active: false },
    rul: { seconds: null, minutes: null, hours: null, status: null },
    trend: null, maintenanceRecommendation: null,
    telemetryHistory: [], anomalyHistory: [], healthHistory: [], faultHistory: [],
    isStale: false, error: null,
  }),
}))

export default useAeroStore
