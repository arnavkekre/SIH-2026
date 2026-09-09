import React, { useMemo } from 'react'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea, CartesianGrid
} from 'recharts'
import { Info, AlertTriangle } from 'lucide-react'
import useAeroStore from '../store/useAeroStore.js'
import AnomalyPanel from '../components/diagnostics/AnomalyPanel.jsx'
import FaultPanel from '../components/diagnostics/FaultPanel.jsx'
import MaintenanceAdvisory from '../components/diagnostics/MaintenanceAdvisory.jsx'
import ResidualPanel from '../components/telemetry/ResidualPanel.jsx'
import StatusBadge from '../components/ui/StatusBadge.jsx'

const RESIDUAL_PARAMS = [
  { key: 'residual_rpm',              label: 'RPM',         unit: '',    warnAt: 50,   critAt: 150 },
  { key: 'residual_cht_c',            label: 'CHT',         unit: '°C',  warnAt: 10,   critAt: 25  },
  { key: 'residual_egt_c',            label: 'EGT',         unit: '°C',  warnAt: 20,   critAt: 50  },
  { key: 'residual_oil_pressure_kpa', label: 'Oil Pressure', unit: 'kPa', warnAt: 20,  critAt: 50  },
  { key: 'residual_oil_temperature_c',label: 'Oil Temp',    unit: '°C',  warnAt: 5,    critAt: 15  },
  { key: 'residual_fuel_flow_lph',    label: 'Fuel Flow',   unit: 'L/h', warnAt: 1,    critAt: 3   },
  { key: 'residual_vibration_g',      label: 'Vibration',   unit: 'G',   warnAt: 0.05, critAt: 0.15},
  { key: 'residual_injection_timing_deg', label: 'Inj Timing', unit: '°', warnAt: 1,  critAt: 3   },
]

function residualColor(value, warnAt, critAt) {
  if (value == null) return '#8FA8BC'
  const abs = Math.abs(value)
  if (abs >= critAt) return '#ef4444'
  if (abs >= warnAt) return '#f59e0b'
  return '#22c55e'
}

function fmt(val, d = 1) {
  if (val == null || isNaN(val)) return '--'
  const n = Number(val)
  return (n >= 0 ? '+' : '') + n.toFixed(d)
}

const chartTheme = {
  stroke: '#20384D',
  text: '#8FA8BC',
}

export default function Diagnostics() {
  const {
    connectionStatus, engineId, missionId, healthScore, healthStatus,
    anomalyScore, fault, rul, residuals, healthHistory, anomalyHistory,
  } = useAeroStore()

  const isOffline = connectionStatus === 'OFFLINE'

  const healthChartData = useMemo(() =>
    healthHistory.map((p, i) => ({ i, t: p.timestampS?.toFixed(0), score: p.healthScore })),
    [healthHistory])

  const anomalyChartData = useMemo(() =>
    anomalyHistory.map((p, i) => ({ i, t: p.timestampS?.toFixed(0), score: p.anomalyScore })),
    [anomalyHistory])

  if (isOffline && !engineId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-base p-8">
        <div className="aero-card clip-angle p-8 max-w-lg text-center">
          <AlertTriangle className="w-10 h-10 text-status-warning mx-auto mb-4" />
          <div className="font-mono text-lg text-text-base mb-2">API OFFLINE</div>
          <p className="text-text-muted text-sm mb-4">
            Awaiting backend data. Start the AeroTwin backend and begin a replay session to populate diagnostics.
          </p>
          <code className="block bg-bg-base text-primary text-xs font-mono p-3 text-left">
            cd backend/src && uvicorn backend.server:app --reload<br />
            # Then: POST http://localhost:8000/replay/start
          </code>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-base py-6">
      <div className="max-w-7xl mx-auto px-6">

        {/* ── PAGE HEADER ── */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="aero-label mb-1">Diagnostic Analysis</div>
            <h1 className="font-mono text-2xl font-bold text-text-base">ENGINE DIAGNOSTICS</h1>
            <p className="text-text-muted text-sm mt-1">Why is the engine in this state?</p>
          </div>
          <div className="flex items-center gap-3">
            {healthStatus && <StatusBadge status={healthStatus} />}
            {fault?.type && fault.active && (
              <div className="border border-status-critical text-status-critical font-mono text-xs px-2 py-1 uppercase">
                ⚠ {fault.type.replace(/_/g, ' ')}
              </div>
            )}
          </div>
        </div>

        {/* ── MINI KPI ROW ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Anomaly Score', value: anomalyScore?.toFixed(2) ?? '--', sub: anomalyScore > 0.6 ? 'HIGH' : anomalyScore > 0.3 ? 'ELEVATED' : 'NORMAL',
              color: anomalyScore > 0.6 ? '#ef4444' : anomalyScore > 0.3 ? '#f59e0b' : '#22c55e' },
            { label: 'Top Fault', value: fault?.type?.replace(/_/g, ' ') ?? 'NOMINAL', sub: fault?.confidence != null ? `${(fault.confidence * 100).toFixed(0)}% confidence` : '',
              color: fault?.active ? '#ef4444' : '#22c55e' },
            { label: 'Health Score', value: healthScore?.toFixed(1) ?? '--', sub: healthStatus ?? '--',
              color: healthStatus === 'HEALTHY' ? '#22c55e' : healthStatus === 'WARNING' ? '#f59e0b' : healthStatus === 'DEGRADING' ? '#f97316' : '#ef4444' },
            { label: 'RUL', value: rul.minutes != null ? `${rul.minutes.toFixed(1)} min` : '--', sub: rul.status ?? '--',
              color: rul.status === 'CRITICAL' ? '#ef4444' : rul.status === 'WARNING' ? '#f59e0b' : '#22c55e' },
          ].map(({ label, value, sub, color }) => (
            <div key={label} className="aero-card clip-angle-sm p-4">
              <div className="aero-label mb-1">{label}</div>
              <div className="font-mono text-xl font-bold" style={{ color }}>{value}</div>
              {sub && <div className="font-mono text-xs text-text-muted mt-0.5">{sub}</div>}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">

          {/* ── ANOMALY ANALYSIS ── */}
          <div className="aero-panel p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="aero-title">Anomaly Analysis</div>
              <Info className="w-3.5 h-3.5 text-text-muted" title="Isolation Forest anomaly score — higher = more anomalous" />
            </div>
            <AnomalyPanel expanded />
            <p className="text-text-muted text-xs mt-3 leading-relaxed">
              The anomaly score reflects how different current engine behavior is from the
              learned baseline of normal operation. Score &gt; 0.3 indicates statistical deviation;
              &gt; 0.6 indicates significant anomaly requiring attention.
            </p>
          </div>

          {/* ── FAULT CLASSIFICATION ── */}
          <div className="aero-panel p-4">
            <div className="aero-title mb-3">Fault Evidence</div>
            <FaultPanel />
            <p className="text-text-muted text-xs mt-3 leading-relaxed">
              Multi-label XGBoost classifier identifies the most probable fault type
              based on telemetry patterns and Digital Twin residuals.
            </p>
          </div>
        </div>

        {/* ── RESIDUAL ANALYSIS ── */}
        <div className="aero-panel p-4 mb-4">
          <div className="aero-title mb-1">Digital Twin Residual Analysis</div>
          <p className="text-text-muted text-xs mb-3">
            The following deviations from the Digital Twin expected values are the evidence supporting the current fault classification.
          </p>
          <ResidualPanel />

          {/* Evidence severity list */}
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
            {RESIDUAL_PARAMS.map(({ key, label, unit, warnAt, critAt }) => {
              const val = residuals?.[key]
              if (val == null) return null
              const color = residualColor(val, warnAt, critAt)
              const severity = Math.abs(val) >= critAt ? 'CRITICAL' : Math.abs(val) >= warnAt ? 'WARNING' : 'OK'
              if (severity === 'OK') return null
              return (
                <div key={key} className="bg-bg-card border p-2" style={{ borderColor: color + '44' }}>
                  <div className="font-mono text-[10px] text-text-muted mb-0.5">{label}</div>
                  <div className="font-mono text-sm" style={{ color }}>
                    {fmt(val, key.includes('vibration') ? 3 : 1)}{unit}
                  </div>
                  <div className="font-mono text-[10px]" style={{ color }}>{severity}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── HEALTH TREND ── */}
        <div className="aero-panel p-4 mb-4">
          <div className="aero-title mb-3">Health & Degradation Trend</div>
          {healthChartData.length > 1 ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <LineChart data={healthChartData}>
                  <CartesianGrid stroke={chartTheme.stroke} strokeDasharray="3 3" />
                  <XAxis dataKey="t" tick={{ fill: chartTheme.text, fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: chartTheme.text, fontSize: 10, fontFamily: 'monospace' }} tickLine={false} axisLine={false} width={30} />
                  <Tooltip contentStyle={{ background: '#0D1B2A', border: '1px solid #20384D', fontFamily: 'monospace', fontSize: 11 }} />
                  <ReferenceArea y1={80} y2={100} fill="#22c55e" fillOpacity={0.05} />
                  <ReferenceArea y1={60} y2={80}  fill="#f59e0b" fillOpacity={0.05} />
                  <ReferenceArea y1={35} y2={60}  fill="#f97316" fillOpacity={0.05} />
                  <ReferenceArea y1={0}  y2={35}  fill="#ef4444" fillOpacity={0.05} />
                  <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="4 4" strokeWidth={1} label={{ value: 'HEALTHY', position: 'right', fill: '#22c55e', fontSize: 9, fontFamily: 'monospace' }} />
                  <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} label={{ value: 'WARNING', position: 'right', fill: '#f59e0b', fontSize: 9, fontFamily: 'monospace' }} />
                  <ReferenceLine y={35} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} label={{ value: 'CRITICAL', position: 'right', fill: '#ef4444', fontSize: 9, fontFamily: 'monospace' }} />
                  <Line type="monotone" dataKey="score" stroke="#35C9FF" strokeWidth={2} dot={false} name="Health Score" />
                </LineChart>
              </ResponsiveContainer>
              <div className="flex gap-4 mt-2">
                {[
                  { label: 'HEALTHY', range: '80–100', color: '#22c55e' },
                  { label: 'WARNING', range: '60–80',  color: '#f59e0b' },
                  { label: 'DEGRADING',range: '35–60', color: '#f97316' },
                  { label: 'CRITICAL', range: '0–35',  color: '#ef4444' },
                ].map(({ label, range, color }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-sm" style={{ background: color }} />
                    <span className="font-mono text-[10px] text-text-muted">{label} ({range})</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[150px] flex items-center justify-center text-text-muted font-mono text-xs">
              Awaiting health history data from active replay session
            </div>
          )}
        </div>

        {/* ── MAINTENANCE ADVISORY ── */}
        <div className="aero-panel p-4">
          <MaintenanceAdvisory />
        </div>
      </div>
    </div>
  )
}
