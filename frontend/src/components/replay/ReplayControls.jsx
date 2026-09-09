import React, { useState, useCallback } from 'react'
import { Play, Pause, Square, Radio } from 'lucide-react'
import useAeroStore from '../../store/useAeroStore.js'
import {
  startReplay,
  pauseReplay,
  resumeReplay,
  stopReplay,
  setReplaySpeed,
} from '../../api/replay.js'

const SPEED_OPTIONS = [0.5, 1, 2, 5, 10]

export default function ReplayControls() {
  // Correctly read from the nested replay object in the store
  const replay = useAeroStore((s) => s.replay)

  const running  = replay?.running  ?? false
  const paused   = replay?.paused   ?? false
  const speed    = replay?.speed    ?? 1
  const row      = replay?.currentRow ?? null
  const total    = replay?.totalRows  ?? null
  const progress = replay?.progress   ?? 0

  const [loading, setLoading] = useState(null)
  const [error,   setError  ] = useState(null)

  const progressPct = Math.min(100, (progress ?? 0) * 100)
  const rowDisplay  = row != null && total ? `${row} / ${total}` : '-- / --'

  const statusLabel = running ? (paused ? 'PAUSED' : 'RUNNING') : 'STOPPED'
  const statusClass = running
    ? paused
      ? 'text-status-warning border-status-warning/40 bg-status-warning/10'
      : 'text-status-healthy border-status-healthy/40 bg-status-healthy/10'
    : 'text-text-muted border-bg-border bg-bg-card'

  const callApi = useCallback(async (key, fn) => {
    setLoading(key)
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err?.message ?? 'API error')
    } finally {
      setLoading(null)
    }
  }, [])

  return (
    <div className="aero-panel flex flex-col gap-3 p-3">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio size={12} className="text-primary" strokeWidth={1.8} />
          <span className="aero-title">REPLAY</span>
        </div>
        <span className={`font-mono text-[10px] px-1.5 py-0.5 border ${statusClass}`}>
          {statusLabel}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="font-mono text-[10px] text-status-critical bg-status-critical/10 border border-status-critical/30 px-2 py-1">
          {error}
        </div>
      )}

      {/* Control buttons */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          className="aero-btn flex items-center gap-1 text-[10px] px-2 py-1"
          disabled={running || loading != null}
          onClick={() => callApi('start', startReplay)}
        >
          <Play size={10} strokeWidth={2} />
          {loading === 'start' ? '...' : 'START'}
        </button>

        <button
          className="aero-btn flex items-center gap-1 text-[10px] px-2 py-1"
          disabled={!running || paused || loading != null}
          onClick={() => callApi('pause', pauseReplay)}
        >
          <Pause size={10} strokeWidth={2} />
          {loading === 'pause' ? '...' : 'PAUSE'}
        </button>

        <button
          className="aero-btn flex items-center gap-1 text-[10px] px-2 py-1"
          disabled={!running || !paused || loading != null}
          onClick={() => callApi('resume', resumeReplay)}
        >
          <Play size={10} strokeWidth={2} />
          {loading === 'resume' ? '...' : 'RESUME'}
        </button>

        <button
          className="aero-btn flex items-center gap-1 text-[10px] px-2 py-1 text-status-critical"
          disabled={!running || loading != null}
          onClick={() => callApi('stop', stopReplay)}
        >
          <Square size={10} strokeWidth={2} />
          {loading === 'stop' ? '...' : 'STOP'}
        </button>
      </div>

      {/* Speed selector */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="font-mono text-[10px] text-text-muted">SPD:</span>
        {SPEED_OPTIONS.map((sp) => {
          const isActive = Math.abs(speed - sp) < 0.01
          return (
            <button
              key={sp}
              className={`font-mono text-[10px] px-1.5 py-0.5 border transition-colors ${
                isActive
                  ? 'text-primary border-primary bg-primary/10'
                  : 'text-text-muted border-bg-border hover:text-primary hover:border-primary/50'
              }`}
              onClick={() => callApi(`spd-${sp}`, () => setReplaySpeed(sp))}
              disabled={loading != null}
            >
              {sp}x
            </button>
          )
        })}
      </div>

      {/* Progress */}
      <div className="flex flex-col gap-1">
        <div className="w-full h-1 bg-bg-border overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${progressPct.toFixed(1)}%` }}
          />
        </div>
        <div className="flex justify-between">
          <span className="font-mono text-[10px] text-text-muted">Row {rowDisplay}</span>
          <span className="font-mono text-[10px] text-text-base">{progressPct.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  )
}
