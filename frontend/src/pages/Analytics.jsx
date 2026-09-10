import React, { useMemo } from 'react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  ReferenceLine, ReferenceArea, Cell, PieChart, Pie, Legend,
} from 'recharts'
import { BarChart3, AlertTriangle } from 'lucide-react'
import useAeroStore from '../store/useAeroStore.js'

const chartTheme = { stroke: '#1A2E46', text: '#6F8EA9' }

const FAULT_COLORS = {
  NORMAL:                  '#22c55e',
  MISFIRE:                 '#ef4444',
  INJECTOR_ABNORMALITY:    '#f97316',
  COOLING_DEGRADATION:     '#f59e0b',
  LUBRICATION_ISSUE:       '#eab308',
  SENSOR_DRIFT:            '#7C5CFF',
  COMBUSTION_INSTABILITY:  '#ec4899',
  OVERHEATING_TREND:       '#dc2626',
  ABNORMAL_VIBRATION:      '#8b5cf6',
}

function fmt(val, d = 1) {
  if (val == null || isNaN(val)) return '--'
  return Number(val).toFixed(d)
}

function PlaceholderPanel({ title, message }) {
  return (
    <div className="aero-panel p-4 flex flex-col">
      <div className="aero-title mb-2">{title}</div>
      <div className="flex-1 flex items-center justify-center min-h-[100px]">
        <div className="text-center">
          <BarChart3 className="w-6 h-6 text-text-muted mx-auto mb-2" />
          <p className="font-mono text-xs text-text-muted">{message}</p>
        </div>
      </div>
    </div>
  )
}

export default function Analytics() {
  const {
    telemetryHistory, anomalyHistory, healthHistory, faultHistory,
  } = useAeroStore()

  // ── Session summary
  const totalPoints   = telemetryHistory.length
  const peakAnomaly   = useMemo(() => Math.max(0, ...anomalyHistory.map(p => p.anomalyScore ?? 0)), [anomalyHistory])
  const lowestHealth  = useMemo(() => Math.min(100, ...healthHistory.map(p => p.healthScore ?? 100)), [healthHistory])
  const activeFaults  = useMemo(() => faultHistory.filter(p => p.active).length, [faultHistory])

  // ── Chart data
  const healthData    = useMemo(() => healthHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), score: p.healthScore })), [healthHistory])
  const anomalyData   = useMemo(() => anomalyHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), score: p.anomalyScore })), [anomalyHistory])
  const rpmData       = useMemo(() => telemetryHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), v: p.rpm })), [telemetryHistory])
  const vibData       = useMemo(() => telemetryHistory.map((p, i) => ({ i, t: fmt(p.timestampS, 0), v: p.vibration_g })), [telemetryHistory])

  const faultDist = useMemo(() => {
    const counts = {}
    faultHistory.forEach(p => {
      if (p.type) counts[p.type] = (counts[p.type] || 0) + 1
    })
    return Object.entries(counts).map(([name, count]) => ({ name: name.replace(/_/g, ' '), count, raw: name }))
  }, [faultHistory])

  const noData = totalPoints === 0

  return (
    <div className="min-h-screen bg-bg-base py-6">
      <div className="max-w-7xl mx-auto px-6">

        {/* ── HEADER ── */}
        <div className="mb-6">
          <div className="aero-label mb-1">Engineering Analysis</div>
          <h1 className="font-mono text-2xl font-bold text-text-base">ANALYTICS</h1>
          <p className="text-text-muted text-xs mt-1">
            Based on current session data.
            Multi-mission historical analytics requires extended backend integration.
          </p>
        </div>

        {/* ── SESSION SUMMARY ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Data Points',     value: totalPoints.toString(),      color: '#00F0FF', sub: 'this session' },
            { label: 'Peak Anomaly',    value: peakAnomaly.toFixed(2),      color: peakAnomaly > 0.6 ? '#ef4444' : peakAnomaly > 0.3 ? '#f59e0b' : '#00E5A3', sub: 'max score' },
            { label: 'Lowest Health',   value: lowestHealth === 100 ? '--' : lowestHealth.toFixed(1), color: lowestHealth < 35 ? '#ef4444' : lowestHealth < 60 ? '#f97316' : lowestHealth < 80 ? '#f59e0b' : '#00E5A3', sub: 'min score' },
            { label: 'Active Faults',   value: activeFaults.toString(),     color: activeFaults > 0 ? '#ef4444' : '#00E5A3', sub: 'events logged' },
          ].map(({ label, value, color, sub }) => (
            <div key={label} className="aero-card clip-angle-sm p-4">
              <div className="aero-label text-[10px] mb-1">{label}</div>
              <div className="font-mono text-2xl font-bold" style={{ color }}>{value}</div>
              <div className="font-mono text-[10px] text-text-muted">{sub}</div>
            </div>
          ))}
        </div>

        {/* ── HEALTH TREND ── */}
        <div className="aero-panel p-4 mb-4">
          <div className="aero-title mb-3">Health Score Trend</div>
          {healthData.length > 1 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={healthData}>
                  <CartesianGrid stroke={chartTheme.stroke} strokeDasharray="3 3" />
                  <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0,100]} tick={{ fill: chartTheme.text, fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={30} />
                  <Tooltip contentStyle={{ background:'#0A1320', border:'1px solid #1A2E46', fontFamily:'monospace', fontSize:11, color:'#E2F1FF' }} />
                  <ReferenceArea y1={80} y2={100} fill="#00E5A3" fillOpacity={0.05} />
                  <ReferenceArea y1={60} y2={80}  fill="#f59e0b" fillOpacity={0.05} />
                  <ReferenceArea y1={35} y2={60}  fill="#f97316" fillOpacity={0.05} />
                  <ReferenceArea y1={0}  y2={35}  fill="#ef4444" fillOpacity={0.05} />
                  <ReferenceLine y={80} stroke="#00E5A3" strokeDasharray="4 4" strokeWidth={1} />
                  <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />
                  <ReferenceLine y={35} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} />
                  <Line type="monotone" dataKey="score" stroke="#00F0FF" strokeWidth={2} dot={false} name="Health Score" />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2">
                {[['HEALTHY','80–100','#00E5A3'],['WARNING','60–80','#f59e0b'],['DEGRADING','35–60','#f97316'],['CRITICAL','0–35','#ef4444']].map(([l,r,c])=>(
                  <div key={l} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-sm" style={{ background: c }} />
                    <span className="font-mono text-[10px] text-text-muted">{l} ({r})</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-text-muted font-mono text-xs">
              {noData ? 'Start a replay session to collect data' : 'Collecting data...'}
            </div>
          )}
        </div>

        {/* ── ANOMALY + FAULT DIST ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">

          <div className="aero-panel p-4">
            <div className="aero-title mb-3">Anomaly Score Trend</div>
            {anomalyData.length > 1 ? (
              <ResponsiveContainer width="100%" height={150}>
                <AreaChart data={anomalyData}>
                  <CartesianGrid stroke={chartTheme.stroke} strokeDasharray="3 3" />
                  <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0,1]} tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={25} />
                  <Tooltip contentStyle={{ background:'#0A1320', border:'1px solid #1A2E46', fontFamily:'monospace', fontSize:10, color:'#E2F1FF' }} />
                  <ReferenceLine y={0.3} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} label={{ value:'WARN', fill:'#f59e0b', fontSize:9, fontFamily:'monospace' }} />
                  <ReferenceLine y={0.6} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} label={{ value:'HIGH', fill:'#ef4444', fontSize:9, fontFamily:'monospace' }} />
                  <defs>
                    <linearGradient id="aGrad3" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00F0FF" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#00F0FF" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="score" stroke="#00F0FF" strokeWidth={2} fill="url(#aGrad3)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[150px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
            )}
          </div>

          <div className="aero-panel p-4">
            <div className="aero-title mb-3">Fault Distribution</div>
            {faultDist.length > 0 ? (
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={faultDist} layout="vertical">
                  <XAxis type="number" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={120} />
                  <Tooltip contentStyle={{ background:'#0A1320', border:'1px solid #1A2E46', fontFamily:'monospace', fontSize:10, color:'#E2F1FF' }} />
                  <Bar dataKey="count" radius={[0,2,2,0]}>
                    {faultDist.map((entry) => (
                      <Cell key={entry.raw} fill={FAULT_COLORS[entry.raw] || '#00F0FF'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[150px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting fault data</div>
            )}
          </div>
        </div>

        {/* ── PARAMETER TRENDS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="aero-panel p-4">
            <div className="aero-title mb-3">RPM Trend</div>
            {rpmData.length > 1 ? (
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={rpmData}>
                  <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip contentStyle={{ background:'#111111', border:'1px solid #2A2A2A', fontFamily:'monospace', fontSize:10 }} />
                  <Line type="monotone" dataKey="v" stroke="#7C5CFF" strokeWidth={1.5} dot={false} name="RPM" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[120px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
            )}
          </div>

          <div className="aero-panel p-4">
            <div className="aero-title mb-3">Vibration Trend (G)</div>
            {vibData.length > 1 ? (
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={vibData}>
                  <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: chartTheme.text, fontSize: 9, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={40} />
                  <Tooltip contentStyle={{ background:'#111111', border:'1px solid #2A2A2A', fontFamily:'monospace', fontSize:10 }} />
                  <Line type="monotone" dataKey="v" stroke="#f97316" strokeWidth={1.5} dot={false} name="Vibration G" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[120px] flex items-center justify-center text-text-muted font-mono text-xs">Awaiting data</div>
            )}
          </div>
        </div>

        {/* ── PLACEHOLDER PANELS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PlaceholderPanel
            title="MULTI-MISSION HEALTH COMPARISON"
            message={`Requires multi-mission database.\nAwaiting backend endpoint: GET /analytics/missions`}
          />
          <PlaceholderPanel
            title="DEGRADATION RATE ANALYSIS"
            message={`Requires extended time-series data\nacross multiple completed missions.`}
          />
        </div>
      </div>
    </div>
  )
}
