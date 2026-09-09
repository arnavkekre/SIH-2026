import React, { createContext, useContext, useEffect, useRef, useCallback } from 'react'
import useAeroStore from '../store/useAeroStore.js'
import { getLatest } from '../api/telemetry.js'
import { checkHealth } from '../api/health.js'
import { getReplayStatus } from '../api/replay.js'

/**
 * TelemetryProvider — Data source abstraction layer.
 * 
 * Currently implemented as REST polling (GET /latest every POLL_INTERVAL_MS).
 * 
 * To switch to WebSocket or SSE in the future:
 * Replace the polling implementation inside this component without
 * changing any consuming component — they all subscribe to Zustand store.
 * 
 * Telemetry source interface (conceptual):
 *   connect()                    — start receiving data
 *   disconnect()                 — stop receiving data  
 *   getLatest()                  — returns cached latest result
 *   subscribe(callback)          — callback on new data
 *   getMissionHistory(missionId) — fetch mission history
 */

const TelemetryContext = createContext(null)

const POLL_INTERVAL = parseInt(import.meta.env.VITE_POLL_INTERVAL_MS || '1000', 10)
const HEALTH_POLL_INTERVAL = 5000  // Check API health every 5s
const STALE_THRESHOLD_MS = 5000    // Mark data stale after 5s without update
const REPLAY_POLL_INTERVAL = 2000  // Poll replay status every 2s

export function TelemetryProvider({ children }) {
  const {
    setConnectionStatus,
    updateFromResult,
    updateReplay,
    setStale,
    setError,
    connectionStatus,
    dataFreshness,
  } = useAeroStore()

  const telemetryTimerRef = useRef(null)
  const healthTimerRef = useRef(null)
  const replayTimerRef = useRef(null)
  const staleTimerRef = useRef(null)
  const isMountedRef = useRef(true)

  // ──────────────────────────────────────────────
  // Poll /latest for telemetry
  // ──────────────────────────────────────────────
  const pollTelemetry = useCallback(async () => {
    if (!isMountedRef.current) return
    try {
      const data = await getLatest()
      if (!isMountedRef.current) return

      if (data?.result) {
        updateFromResult(data.result)
        setConnectionStatus('ONLINE')
      }
    } catch (err) {
      if (!isMountedRef.current) return
      // Only set offline if we were previously online/connecting
      setConnectionStatus('OFFLINE')
      setError(err.message)
    }
  }, [updateFromResult, setConnectionStatus, setError])

  // ──────────────────────────────────────────────
  // Poll /health for API connectivity
  // ──────────────────────────────────────────────
  const pollHealth = useCallback(async () => {
    if (!isMountedRef.current) return
    try {
      await checkHealth()
      if (!isMountedRef.current) return
      // Health OK — already marked online by telemetry poll if data exists
      if (useAeroStore.getState().connectionStatus !== 'ONLINE') {
        setConnectionStatus('ONLINE')
      }
    } catch (err) {
      if (!isMountedRef.current) return
      setConnectionStatus('OFFLINE')
    }
  }, [setConnectionStatus])

  // ──────────────────────────────────────────────
  // Poll /replay/status
  // ──────────────────────────────────────────────
  const pollReplay = useCallback(async () => {
    if (!isMountedRef.current) return
    try {
      const status = await getReplayStatus()
      if (!isMountedRef.current) return
      updateReplay({
        running: status.running,
        paused: status.paused,
        progress: status.progress,
        speed: status.speed,
        currentRow: status.current_row,
        totalRows: status.total_rows,
      })
    } catch (_) {
      // Replay status failure is non-critical
    }
  }, [updateReplay])

  // ──────────────────────────────────────────────
  // Start polling on mount
  // ──────────────────────────────────────────────
  useEffect(() => {
    isMountedRef.current = true

    // Initial polls
    pollHealth()
    pollTelemetry()
    pollReplay()

    // Set up intervals
    telemetryTimerRef.current = setInterval(pollTelemetry, POLL_INTERVAL)
    healthTimerRef.current = setInterval(pollHealth, HEALTH_POLL_INTERVAL)
    replayTimerRef.current = setInterval(pollReplay, REPLAY_POLL_INTERVAL)

    return () => {
      isMountedRef.current = false
      clearInterval(telemetryTimerRef.current)
      clearInterval(healthTimerRef.current)
      clearInterval(replayTimerRef.current)
      clearTimeout(staleTimerRef.current)
    }
  }, [])

  // ──────────────────────────────────────────────
  // Stale data detection
  // ──────────────────────────────────────────────
  useEffect(() => {
    clearTimeout(staleTimerRef.current)
    if (dataFreshness) {
      staleTimerRef.current = setTimeout(() => {
        if (isMountedRef.current) setStale()
      }, STALE_THRESHOLD_MS)
    }
  }, [dataFreshness, setStale])

  return (
    <TelemetryContext.Provider value={{ pollTelemetry, pollReplay }}>
      {children}
    </TelemetryContext.Provider>
  )
}

export function useTelemetryContext() {
  return useContext(TelemetryContext)
}

export default TelemetryProvider
