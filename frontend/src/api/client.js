/**
 * AeroTwin API Client
 * All backend requests go through this module.
 * URL is resolved from VITE_API_BASE_URL environment variable.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export { API_BASE }

/**
 * Perform a fetch to the backend.
 * @param {string} path - Endpoint path (e.g. '/latest')
 * @param {RequestInit} options - Fetch options
 * @param {number} timeoutMs - Request timeout in milliseconds
 */
export async function apiFetch(path, options = {}, timeoutMs = 8000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    clearTimeout(timer)

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error')
      throw new ApiError(response.status, errorText)
    }

    return response.json()
  } catch (err) {
    clearTimeout(timer)
    if (err.name === 'AbortError') {
      throw new ApiError(0, 'Request timed out')
    }
    throw err
  }
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
