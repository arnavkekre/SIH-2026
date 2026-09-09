import { apiFetch } from './client.js'

/**
 * Get the latest processed telemetry result from the backend.
 * Returns: { status, result } where result contains:
 *   engine_id, mission_id, timestamp_s, mission_phase,
 *   health_score, health_status, anomaly_score,
 *   residuals, ml, fault, rul_seconds, rul_minutes, rul_hours,
 *   rul_status, trend, maintenance_recommendation
 */
export async function getLatest() {
  return apiFetch('/latest')
}
