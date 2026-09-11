import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, RefreshCw, Radio, ChevronDown, ChevronUp } from 'lucide-react'
import useAeroStore from '../store/useAeroStore.js'
import KpiRow from '../components/kpi/KpiRow.jsx'
import EngineViewer from '../components/engine3d/EngineViewer.jsx'
import TelemetryCard from '../components/telemetry/TelemetryCard.jsx'
import ResidualPanel from '../components/telemetry/ResidualPanel.jsx'
import AnomalyPanel from '../components/diagnostics/AnomalyPanel.jsx'
import FaultPanel from '../components/diagnostics/FaultPanel.jsx'
import MaintenanceAdvisory from '../components/diagnostics/MaintenanceAdvisory.jsx'
import ReplayControls from '../components/replay/ReplayControls.jsx'
import ConnectionIndicator from '../components/ui/ConnectionIndicator.jsx'

function fmt(val, d = 1) {
  if (val == null || isNaN(val)) return null
  return Number(val)
}

export default function Dashboard() {
  const {
    connectionStatus, engineId, missionId, missionPhase, timestampS,
    telemetry, residuals, healthScore, healthStatus, fault,
    anomalyScore, rul, replay, telemetryHistory, anomalyHistory,
  } = useAeroStore()

  const isOffline = connectionStatus === 'OFFLINE'
  const hasData   = engineId != null
  const [showResiduals, setShowResiduals] = useState(false)

  // Sparkline data helpers — extract raw numeric values for the chart
  const rpmHistory  = useMemo(() => telemetryHistory.map(p => p.rpm), [telemetryHistory])
  const chtHistory  = useMemo(() => telemetryHistory.map(p => p.cht_c), [telemetryHistory])
  const egtHistory  = useMemo(() => telemetryHistory.map(p => p.egt_c), [telemetryHistory])
  const oilPHistory = useMemo(() => telemetryHistory.map(p => p.oil_pressure_kpa), [telemetryHistory])
  const oilTHistory = useMemo(() => telemetryHistory.map(p => p.oil_temperature_c), [telemetryHistory])
  const fuelHistory = useMemo(() => telemetryHistory.map(p => p.fuel_flow_lph), [telemetryHistory])
  const vibHistory  = useMemo(() => telemetryHistory.map(p => p.vibration_g), [telemetryHistory])

  const now = timestampS != null ? `T+${Number(timestampS).toFixed(1)}s` : '--'

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-bg-base overflow-hidden">

      {/* ── HEADER BAR ── */}
      <div className="flex items-center justify-between px-4 h-9 bg-bg-panel border-b border-bg-border flex-shrink-0">
        <div className="flex items-center gap-4 font-mono text-xs text-text-muted">
          <span>ENGINE: <span className="text-text-base">{engineId || '--'}</span></span>
          <span className="text-bg-border">|</span>
          <span>MISSION: <span className="text-text-base">{missionId || '--'}</span></span>
          {missionPhase && (
            <>
              <span className="text-bg-border">|</span>
              <span className="border border-primary/30 text-primary px-1.5 py-0.5 text-[10px] uppercase tracking-wider">{missionPhase}</span>
            </>
          )}
        </div>
        <span className="font-mono text-[11px] text-primary tracking-widest hidden md:block">AEROTWIN COMMAND CONSOLE</span>
        <div className="flex items-center gap-3">
          <ConnectionIndicator />
          <span className="font-mono text-xs text-text-muted">{now}</span>
        </div>
      </div>

      {/* ── KPI ROW ── */}
      <div className="px-2 py-2 flex-shrink-0">
        <KpiRow />
      </div>

      {/* ── SIMULATION BANNER ── */}
      {replay.running && (
        <div className="flex items-center gap-2 px-4 py-1 bg-primary/10 border-b border-primary/30 flex-shrink-0">
          <Radio className="w-3 h-3 text-primary animate-pulse" />
          <span className="font-mono text-[11px] text-primary uppercase tracking-wider">
            Simulation Active — Replay {replay.paused ? 'PAUSED' : 'RUNNING'} at {replay.speed}× speed
            ({Math.round((replay.progress || 0) * 100)}%)
          </span>
        </div>
      )}

      {/* ── MAIN 3-COLUMN GRID ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* LEFT PANEL — Replay + Primary Telemetry */}
        <div className="w-56 flex-shrink-0 border-r border-bg-border flex flex-col gap-2 p-2 overflow-y-auto">
          <ReplayControls />

          <div className="aero-title text-[10px] mt-1">PRIMARY TELEMETRY</div>
          <TelemetryCard label="RPM"     value={fmt(telemetry.rpm, 0)}  unit="rpm"  historyData={rpmHistory}
            expected={fmt(useAeroStore.getState().expectedValues?.expected_rpm, 0)}
            residual={residuals?.residual_rpm}
            thresholds={{ warn: 50, crit: 150 }} precision={0} />
          <TelemetryCard label="CHT"     value={fmt(telemetry.cht_c)}   unit="°C"  historyData={chtHistory}
            expected={fmt(useAeroStore.getState().expectedValues?.expected_cht_c)}
            residual={residuals?.residual_cht_c}
            thresholds={{ warn: 10, crit: 25 }} />
          <TelemetryCard label="EGT"     value={fmt(telemetry.egt_c, 0)} unit="°C" historyData={egtHistory}
            expected={fmt(useAeroStore.getState().expectedValues?.expected_egt_c, 0)}
            residual={residuals?.residual_egt_c}
            thresholds={{ warn: 20, crit: 50 }} precision={0} />
        </div>

        {/* CENTER — 3D Engine + Residuals */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Engine viewer */}
          <div className="flex-1 relative min-h-0">
            <EngineViewer
              rpm={telemetry.rpm}
              vibration={telemetry.vibration_g}
              healthStatus={healthStatus}
              faultType={fault?.type}
              className="absolute inset-0"
            />
          </div>

          {/* Residual panel below engine - collapsible */}
          <div className="flex-shrink-0 border-t border-bg-border bg-bg-panel/90">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-bg-border/60">
              <span className="aero-title text-[10px]">DIGITAL TWIN — EXPECTED vs ACTUAL</span>
              <button
                onClick={() => setShowResiduals((prev) => !prev)}
                className="flex items-center gap-1 font-mono text-[10px] text-text-muted hover:text-primary transition-colors px-1.5 py-0.5 rounded border border-bg-border"
              >
                {showResiduals ? (
                  <>
                    <span>COLLAPSE</span>
                    <ChevronDown size={12} />
                  </>
                ) : (
                  <>
                    <span>EXPAND TABLE</span>
                    <ChevronUp size={12} />
                  </>
                )}
              </button>
            </div>
            {showResiduals && (
              <div className="max-h-36 overflow-y-auto px-3 py-2">
                <ResidualPanel hideHeader={true} />
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL — Diagnostics */}
        <div className="w-64 flex-shrink-0 border-l border-bg-border flex flex-col gap-0 overflow-y-auto divide-y divide-bg-border">
          <div className="p-3">
            <AnomalyPanel />
          </div>
          <div className="p-3">
            <FaultPanel />
          </div>
          <div className="p-3">
            <MaintenanceAdvisory />
          </div>

          {/* Secondary telemetry in right panel */}
          <div className="p-3 flex flex-col gap-2">
            <div className="aero-title text-[10px]">SECONDARY TELEMETRY</div>
            <div className="grid grid-cols-2 gap-2">
              <TelemetryCard label="OIL PRESS" value={fmt(telemetry.oil_pressure_kpa, 0)} unit="kPa" historyData={oilPHistory}
                residual={residuals?.residual_oil_pressure_kpa} thresholds={{ warn: 20, crit: 50 }} precision={0} />
              <TelemetryCard label="OIL TEMP"  value={fmt(telemetry.oil_temperature_c)}  unit="°C"  historyData={oilTHistory}
                residual={residuals?.residual_oil_temperature_c} thresholds={{ warn: 5, crit: 15 }} />
              <TelemetryCard label="FUEL FLOW" value={fmt(telemetry.fuel_flow_lph)}       unit="L/h" historyData={fuelHistory}
                residual={residuals?.residual_fuel_flow_lph} thresholds={{ warn: 1, crit: 3 }} />
              <TelemetryCard label="VIBRATION" value={fmt(telemetry.vibration_g, 3)}      unit="G"   historyData={vibHistory}
                residual={residuals?.residual_vibration_g} thresholds={{ warn: 0.05, crit: 0.15 }} precision={3} />
            </div>
            <TelemetryCard label="ALTERNATOR" value={fmt(telemetry.alternator_voltage_v)} unit="V"  historyData={[]} thresholds={{ warn: 1, crit: 3 }} />
            <TelemetryCard label="BATTERY"    value={fmt(telemetry.battery_voltage_v)}   unit="V"   historyData={[]} thresholds={{ warn: 0.5, crit: 2 }} />
            <TelemetryCard label="INJ TIMING" value={fmt(telemetry.injection_timing_deg)} unit="°" historyData={[]}
              residual={residuals?.residual_injection_timing_deg} thresholds={{ warn: 1, crit: 3 }} />
          </div>
        </div>
      </div>

      {/* ── OFFLINE OVERLAY ── */}
      {isOffline && !hasData && (
        <div className="absolute inset-0 top-14 z-30 flex items-center justify-center bg-bg-base/95 backdrop-blur-sm">
          <div className="aero-card clip-angle p-8 text-center max-w-sm">
            <AlertTriangle className="w-10 h-10 text-status-warning mx-auto mb-4" />
            <div className="font-mono text-lg text-text-base mb-2 uppercase tracking-wider">API OFFLINE</div>
            <p className="text-text-muted text-sm mb-4">
              Cannot reach the AeroTwin backend. Start the FastAPI server and begin a replay session.
            </p>
            <code className="block bg-bg-base text-primary text-xs font-mono p-2 mb-4 text-left">
              cd backend/src<br />
              uvicorn backend.server:app --reload
            </code>
            <p className="text-text-muted text-xs mb-4">Then start replay:</p>
            <code className="block bg-bg-base text-primary text-xs font-mono p-2 mb-4 text-left">
              POST http://localhost:8000/replay/start
            </code>
            <button onClick={() => window.location.reload()}
              className="aero-btn flex items-center gap-2 mx-auto">
              <RefreshCw className="w-3 h-3" /> Retry Connection
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
