import { apiFetch } from './client.js'

/**
 * Get current replay status.
 * @returns {{ running, paused, progress, speed, current_row, total_rows }}
 */
export async function getReplayStatus() {
  return apiFetch('/replay/status')
}

/**
 * Start the replay.
 * @param {number} speed - Playback speed multiplier (default 1.0)
 */
export async function startReplay(speed = 1.0) {
  return apiFetch('/replay/start', {
    method: 'POST',
    body: JSON.stringify({ speed }),
  })
}

/**
 * Set replay speed.
 * @param {number} speed
 */
export async function setReplaySpeed(speed) {
  return apiFetch('/replay/speed', {
    method: 'POST',
    body: JSON.stringify({ speed }),
  })
}

/**
 * Pause the replay.
 */
export async function pauseReplay() {
  return apiFetch('/replay/pause', { method: 'POST' })
}

/**
 * Resume a paused replay.
 */
export async function resumeReplay() {
  return apiFetch('/replay/resume', { method: 'POST' })
}

/**
 * Stop and clear the current replay.
 */
export async function stopReplay() {
  return apiFetch('/replay/stop', { method: 'POST' })
}
