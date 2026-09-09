import React, { useMemo, useState, useEffect } from 'react'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { Clock, Radio, Activity, AlertTriangle } from 'lucide-react'
import useAeroStore from '../store/useAeroStore.js'
import ReplayControls from '../components/replay/ReplayControls.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'

const chartTheme = { stroke: '#20384D', text: '#8FA8BC' }

function fmt(val, d = 1) {
  if (val == null || isNaN(val)) return '--'
  return Number(val).toFixed(d)
}

export default function Missions() {
  const {
    connectionStatus, engineId, missionId, missionPhase, timestampS,
    healthScore, healthStatus, fault, anomalyScore, rul, replay,
    healthHistory, anomalyHistory, faultHistory, telemetryHistory,
  } = useAeroStore()

  const [sessionStart] = useState(() => new Date())
  const hasData = engineId != null

  const healthData  = useMemo(() => healthHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), score: p.healthScore })), [healthHistory])
  const anomalyData = useMemo(() => anomalyHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), score: p.anomalyScore })), [anomalyHistory])
  const rpmData     = useMemo(() => telemetryHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), v: p.rpm })), [telemetryHistory])
  const vibData     = useMemo(() => telemetryHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), v: p.vibration_g })), [telemetryHistory])

  const activeFaultEvents = useMemo(() =>
    faultHistory.filter(p => p.active && p.type && p.type !== 'NORMAL'),
    [faultHistory])

  const sessionElapsed = Math.round((Date.now() - sessionStart) / 1000)

  const healthColor =
    healthStatus === 'HEALTHY'   ? '#22c55e' :
    healthStatus === 'WARNING'   ? '#f59e0b' :
    healthStatus === 'DEGRADING' ? '#f97316' :
    healthStatus === 'CRITICAL'  ? '#ef4444' : '#8FA8BC'

  return (
    <div className="min-h-screen bg-bg-base py-6">
      <div className="max-w-7xl mx-auto px-6">

        {/* ── HEADER ── */}
        <div className="mb-6">
          <div className="aero-label mb-1">Mission Control</div>
          <h1 className="font-mono text-2xl font-bold text-text-base">SIMULATION REPLAY MANAGER</h1>
        </div>

        <div className="flex flex-col lg:flex-row gap-4">

          {/* ── LEFT — CONTROLS ── */}
          <div className="lg:w-72 flex-shrink-0 flex flex-col gap-4">

            {/* Active session */}
            <div className="aero-panel p-4">
              <div className="aero-title mb-3 flex items-center gap-2">
                <Radio className="w-3 h-3 text-primary" />
                Active Session
              </div>

              <div className="flex flex-col gap-2 font-mono text-xs">
                <div className="flex justify-between">
                  <span className="text-text-muted">Engine:</span>
                  <span className="text-text-base">{engineId || '--'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Mission:</span>
                  <span className="text-text-base">{missionId || '--'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Phase:</span>
                  <span className="text-primary">{missionPhase || '--'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">T+:</span>
                  <span className="text-text-base">{timestampS != null ? `${fmt(timestampS, 1)}s` : '--'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Session up:</span>
                  <span className="text-text-base">{sessionElapsed}s</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text-muted">Replay:</span>
                  <StatusBadge status={
                    replay.running && !replay.paused ? 'ONLINE' :
                    replay.paused ? 'CONNECTING' : 'OFFLINE'
                  } size="sm" />
                </div>
              </div>

              {/* Progress bar */}
              {replay.running && (
                <div className="mt-3">
                  <div className="flex justify-between font-mono text-[10px] text-text-muted mb-1">
                    <span>Row {replay.currentRow} / {replay.totalRows}</span>
                    <span>{Math.round((replay.progress || 0) * 100)}%</span>
                  </div>
                  <div className="h-1 bg-bg-border rounded-full overflow-hidden">
                    <div className="h-full bg-primary transition-all duration-500"
                      style={{ width: `${(replay.progress || 0) * 100}%` }} />
                  </div>
                </div>
              )}
            </div>

            {/* Replay controls */}
            <ReplayControls />

            <div className="aero-card p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-text-muted flex-shrink-0 mt-0.5" />
                <p className="text-text-muted text-[11px] leading-relaxed">
                  Session missions are tracked during active replay.
                  Historical multi-mission archive requires database integration (Supabase).
                </p>
              </div>
            </div>
          </div>

          {/* ── RIGHT — MISSION DETAIL ── */}
          <div className="flex-1 min-w-0">
            {hasData ? (
              <>
                {/* Mission header */}
                <div className="aero-panel p-4 mb-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="font-mono text-lg font-bold text-text-base">{missionId}</div>
                    <div className="font-mono text-xs text-text-muted border border-bg-border px-2 py-0.5">{engineId}</div>
                    {missionPhase && (
                      <div className="font-mono text-xs text-primary border border-primary/30 px-2 py-0.5 uppercase">{missionPhase}</div>
                    )}
                  </div>

                  {/* 4 KPI cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                    {[
                      { label: 'Health', value: fmt(healthScore), color: healthColor, sub: healthStatus },
                      { label: 'Fault',  value: fault?.type?.replace(/_/g,' ') ?? 'NOMINAL',
                        color: fault?.active ? '#ef4444' : '#22c55e',
                        sub: fault?.confidence != null ? `${(fault.confidence*100).toFixed(0)}%` : '' },
                      { label: 'RUL',    value: rul.minutes != null ? `${fmt(rul.minutes)} min` : '--',
                        color: rul.status === 'CRITICAL' ? '#ef4444' : rul.status === 'WARNING' ? '#f59e0b' : '#22c55e',
                        sub: rul.status },
                      { label: 'Anomaly', value: fmt(anomalyScore, 2),
                        color: anomalyScore > 0.6 ? '#ef4444' : anomalyScore > 0.3 ? '#f59e0b' : '#22c55e',
                        sub: anomalyScore > 0.6 ? 'HIGH' : anomalyScore > 0.3 ? 'ELEVATED' : 'NORMAL' },
                    ].map(({ label, value, color, sub }) => (
                      <div key={label} className="aero-card clip-angle-sm p-3">
                        <div className="aero-label text-[10px] mb-1">{label}</div>
                        <div className="font-mono text-lg font-bold" style={{ color }}>{value}</div>
                        {sub && <div className="font-mono text-[10px] text-text-muted">{sub}</div>}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Charts grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">

                  {/* Health timeline */}
                  <div className="aero-panel p-4">
                    <div className="aero-title mb-3">Health Score Timeline</div>
                    {healthData.length > 1 ? (
                      <ResponsiveContainer width="100%" height={120}>
                        <LineChart data={healthData}>
                          <CartesianGrid stroke={chartTheme.stroke} strokeDasharray="3 3" />
                          <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                          <YAxis domain={[0,100]} tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={25} />
                          <Tooltip contentStyle={{ background:'#0D1B2A', border:'1px solid #20384D', fontFamily:'monospace', fontSize:10 }} />
                          <Line type="monotone" dataKey="score" stroke="#35C9FF" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[120px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
                    )}
                  </div>

                  {/* Anomaly timeline */}
                  <div className="aero-panel p-4">
                    <div className="aero-title mb-3">Anomaly Score Timeline</div>
                    {anomalyData.length > 1 ? (
                      <ResponsiveContainer width="100%" height={120}>
                        <AreaChart data={anomalyData}>
                          <CartesianGrid stroke={chartTheme.stroke} strokeDasharray="3 3" />
                          <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                          <YAxis domain={[0,1]} tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={25} />
                          <Tooltip contentStyle={{ background:'#0D1B2A', border:'1px solid #20384D', fontFamily:'monospace', fontSize:10 }} />
                          <defs>
                            <linearGradient id="aGrad2" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#35C9FF" stopOpacity={0.3} />
                              <stop offset="100%" stopColor="#35C9FF" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <Area type="monotone" dataKey="score" stroke="#35C9FF" strokeWidth={2} fill="url(#aGrad2)" dot={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[120px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
                    )}
                  </div>

                  {/* RPM */}
                  <div className="aero-panel p-4">
                    <div className="aero-title mb-3">RPM Timeline</div>
                    {rpmData.length > 1 ? (
                      <ResponsiveContainer width="100%" height={100}>
                        <LineChart data={rpmData}>
                          <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                          <YAxis tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={35} />
                          <Tooltip contentStyle={{ background:'#0D1B2A', border:'1px solid #20384D', fontFamily:'monospace', fontSize:10 }} />
                          <Line type="monotone" dataKey="v" stroke="#7C5CFF" strokeWidth={1.5} dot={false} name="RPM" />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[100px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
                    )}
                  </div>

                  {/* Vibration */}
                  <div className="aero-panel p-4">
                    <div className="aero-title mb-3">Vibration Timeline (G)</div>
                    {vibData.length > 1 ? (
                      <ResponsiveContainer width="100%" height={100}>
                        <LineChart data={vibData}>
                          <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                          <YAxis tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={35} />
                          <Tooltip contentStyle={{ background:'#0D1B2A', border:'1px solid #20384D', fontFamily:'monospace', fontSize:10 }} />
                          <Line type="monotone" dataKey="v" stroke="#f97316" strokeWidth={1.5} dot={false} name="Vibration G" />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[100px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
                    )}
                  </div>
                </div>

                {/* Fault events */}
                <div className="aero-panel p-4">
                  <div className="aero-title mb-3 flex items-center gap-2">
                    <Activity className="w-3 h-3" />
                    Fault Events ({activeFaultEvents.length})
                  </div>
                  {activeFaultEvents.length > 0 ? (
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {activeFaultEvents.slice().reverse().map((evt, i) => (
                        <div key={i} className="flex items-center gap-3 bg-bg-card px-2 py-1.5 border border-bg-border">
                          <div className="w-1.5 h-1.5 rounded-full bg-status-critical" />
                          <span className="font-mono text-xs text-text-muted w-16">T+{fmt(evt.timestampS, 1)}s</span>
                          <span className="font-mono text-xs text-text-base uppercase">{evt.type?.replace(/_/g,' ')}</span>
                          {evt.confidence != null && (
                            <span className="font-mono text-xs text-text-muted ml-auto">{(evt.confidence*100).toFixed(0)}%</span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="font-mono text-xs text-text-muted">No active fault events recorded in this session.</div>
                  )}
                </div>
              </>
            ) : (
              <div className="aero-panel p-10 text-center">
                <Radio className="w-10 h-10 text-text-muted mx-auto mb-4" />
                <div className="font-mono text-lg text-text-base mb-2">No Active Mission</div>
                <p className="text-text-muted text-sm mb-4">
                  Start a replay session to begin monitoring mission telemetry.
                </p>
                <div className="bg-bg-base border border-bg-border p-3 text-left max-w-sm mx-auto">
                  <div className="font-mono text-xs text-primary mb-1">1. Start backend:</div>
                  <code className="block text-text-muted font-mono text-xs mb-2">
                    cd backend/src<br/>
                    uvicorn backend.server:app --reload
                  </code>
                  <div className="font-mono text-xs text-primary mb-1">2. Start replay:</div>
                  <code className="block text-text-muted font-mono text-xs">
                    POST /replay/start {'{"speed": 2.0}'}
                  </code>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
