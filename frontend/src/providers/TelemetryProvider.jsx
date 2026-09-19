import React, { createContext, useContext, useEffect, useRef, useCallback } from 'react'
import useAeroStore from '../store/useAeroStore.js'
import { getLatest } from '../api/telemetry.js'
import { checkHealth } from '../api/health.js'
import { getReplayStatus } from '../api/replay.js'
const TelemetryContext = createContext(null)

const POLL_INTERVAL = parseInt(import.meta.env.VITE_POLL_INTERVAL_MS || '1000', 10)
const HEALTH_POLL_INTERVAL = 5000
const STALE_THRESHOLD_MS = 5000
const REPLAY_POLL_INTERVAL = 2000

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
      setConnectionStatus('OFFLINE')
      setError(err.message)
    }
  }, [updateFromResult, setConnectionStatus, setError])
  const pollHealth = useCallback(async () => {
    if (!isMountedRef.current) return
    try {
      await checkHealth()
      if (!isMountedRef.current) return
      if (useAeroStore.getState().connectionStatus !== 'ONLINE') {
        setConnectionStatus('ONLINE')
      }
    } catch (err) {
      if (!isMountedRef.current) return
      setConnectionStatus('OFFLINE')
    }
  }, [setConnectionStatus])
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
    }
  }, [updateReplay])
  useEffect(() => {
    isMountedRef.current = true
    pollHealth()
    pollTelemetry()
    pollReplay()
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
