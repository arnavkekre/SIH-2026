import { apiFetch } from './client.js'

/**
 * Check backend health.
 * @returns {{ status, service, timestamp, supabase, aiml }}
 */
export async function checkHealth() {
  return apiFetch('/health', {}, 4000)
}
