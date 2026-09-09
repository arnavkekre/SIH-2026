import { apiFetch } from './client.js'

/**
 * Get the buffered telemetry history for a mission.
 * @param {string} missionId
 * @returns {{ status, mission_id, points, history }}
 */
export async function getMissionHistory(missionId) {
  return apiFetch(`/missions/${encodeURIComponent(missionId)}/history`)
}

/**
 * Clear buffered history for a mission.
 * @param {string} missionId
 */
export async function clearMissionHistory(missionId) {
  return apiFetch(`/missions/${encodeURIComponent(missionId)}/history`, {
    method: 'DELETE',
  })
}
