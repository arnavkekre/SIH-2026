import React, { useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Cpu, Activity, AlertTriangle, Heart, ArrowRight,
  Zap, Droplets, Thermometer, Waves, Radio, Wind, Flame, BarChart3
} from 'lucide-react'
import useAeroStore from '../store/useAeroStore.js'
import EngineViewer from '../components/engine3d/EngineViewer.jsx'

const FAULT_TYPES = [
  { name: 'Misfire',               icon: Zap },
  { name: 'Injector Abnormality',  icon: Flame },
  { name: 'Cooling Degradation',   icon: Thermometer },
  { name: 'Lubrication Issue',     icon: Droplets },
  { name: 'Sensor Drift',          icon: Activity },
  { name: 'Combustion Instability',icon: Waves },
  { name: 'Overheating Trend',     icon: Thermometer },
  { name: 'Abnormal Vibration',    icon: Radio },
]

const CAPABILITIES = [
  {
    icon: Cpu,
    title: 'Digital Twin',
    desc: 'Compares observed telemetry against a physics-informed engine model in real-time, computing residuals that reveal subtle deviations before they become faults.',
  },
  {
    icon: Activity,
    title: 'Anomaly Detection',
    desc: 'Isolation Forest-based unsupervised anomaly scoring continuously monitors all telemetry channels for statistical deviations from normal operation.',
  },
  {
    icon: AlertTriangle,
    title: 'Fault Diagnosis',
    desc: 'Multi-label XGBoost classifier identifies and ranks 8 distinct fault types — from misfire to cooling degradation — with confidence scoring.',
  },
  {
    icon: Heart,
    title: 'Health + RUL',
    desc: 'Degradation-informed composite health index (0–100) with formula-based Remaining Useful Life estimation and maintenance advisory generation.',
  },
]

const PIPELINE_STAGES = [
  { label: 'TELEMETRY',     desc: 'Raw sensor data' },
  { label: 'DIGITAL TWIN', desc: 'Expected state model' },
  { label: 'RESIDUALS',    desc: 'Actual vs expected' },
  { label: 'AI / ML',      desc: 'Anomaly + fault inference' },
  { label: 'HEALTH',       desc: 'Score + status band' },
  { label: 'RUL',          desc: 'Formula-based estimate' },
  { label: 'DASHBOARD',    desc: 'Decision support' },
]

function fmt(val, decimals = 1) {
  if (val == null || isNaN(val)) return '--'
  return Number(val).toFixed(decimals)
}

export default function Home() {
  const exploreRef = useRef(null)
  const { telemetry, healthScore, healthStatus, connectionStatus } = useAeroStore()

  const healthColor =
    healthStatus === 'HEALTHY'   ? '#22c55e' :
    healthStatus === 'WARNING'   ? '#f59e0b' :
    healthStatus === 'DEGRADING' ? '#f97316' :
    healthStatus === 'CRITICAL'  ? '#ef4444' : '#8FA8BC'

  return (
    <div className="bg-bg-base text-text-base">

      {/* ═══════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════ */}
      <section className="min-h-[calc(100vh-3.5rem)] relative bg-tech-grid flex items-center overflow-hidden">

        {/* Radial glow background */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(53,201,255,0.04) 0%, transparent 70%)' }} />
        </div>

        <div className="relative z-10 w-full max-w-7xl mx-auto px-6 py-16 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

          {/* LEFT — Text content */}
          <div className="flex flex-col gap-6">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 border border-primary/40 px-3 py-1 w-fit">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="font-mono text-xs text-primary uppercase tracking-widest">AI-Enabled Digital Twin</span>
            </div>

            {/* Title */}
            <div>
              <h1 className="font-mono font-bold leading-none" style={{ fontSize: 'clamp(3rem, 8vw, 5.5rem)' }}>
                <span className="text-text-base">AERO</span><span className="text-primary">TWIN</span>
              </h1>
              <p className="font-mono text-lg md:text-2xl text-text-muted tracking-[0.25em] mt-2">
                PREDICT. MONITOR. PREVENT.
              </p>
            </div>

            {/* Description */}
            <p className="text-text-muted leading-relaxed max-w-lg">
              AI-enabled real-time digital twin system for health monitoring, fault prediction
              and mission reliability enhancement of aero piston engines in MALE UAVs.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap gap-3 mt-2">
              <Link to="/dashboard" className="aero-btn-filled flex items-center gap-2">
                LAUNCH DASHBOARD <ArrowRight className="w-4 h-4" />
              </Link>
              <button
                onClick={() => exploreRef.current?.scrollIntoView({ behavior: 'smooth' })}
                className="aero-btn flex items-center gap-2"
              >
                EXPLORE SYSTEM
              </button>
            </div>

            {/* Live telemetry mini-grid */}
            <div className="mt-4">
              <div className="aero-label mb-2 flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'ONLINE' ? 'bg-status-healthy animate-pulse-slow' : 'bg-text-muted'}`} />
                Live Telemetry {connectionStatus !== 'ONLINE' && '— Awaiting backend'}
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'RPM',      value: fmt(telemetry.rpm, 0),       unit: '' },
                  { label: 'CHT',      value: fmt(telemetry.cht_c),        unit: '°C' },
                  { label: 'EGT',      value: fmt(telemetry.egt_c, 0),     unit: '°C' },
                  { label: 'OIL PRES',  value: fmt(telemetry.oil_pressure_kpa, 0), unit: 'kPa' },
                  { label: 'VIBRATION',value: fmt(telemetry.vibration_g, 3), unit: 'G' },
                  { label: 'HEALTH',   value: fmt(healthScore),             unit: '' },
                ].map(({ label, value, unit }) => (
                  <div key={label} className="aero-card px-2 py-1.5 clip-angle-sm">
                    <div className="aero-label text-[9px]">{label}</div>
                    <div className={`font-mono text-sm ${label === 'HEALTH' ? '' : 'text-text-base'}`}
                      style={label === 'HEALTH' ? { color: healthColor } : {}}>
                      {value}{unit}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT — Engine Digital Twin visual */}
          <div className="relative flex items-center justify-center">
            <div className="relative w-full aspect-square max-w-lg">
              {/* Outer rings */}
              <div className="absolute inset-0 rounded-full border border-primary/10 animate-spin-slow" />
              <div className="absolute inset-4 rounded-full border border-primary/15" style={{ animation: 'spin 8s linear infinite reverse' }} />
              <div className="absolute inset-8 rounded-full border border-primary/20 animate-spin-slow" style={{ animationDuration: '12s' }} />

              {/* Center — actual 3D engine viewer */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-64 h-64">
                  <EngineViewer
                    rpm={telemetry.rpm}
                    vibration={telemetry.vibration_g}
                    healthStatus={healthStatus}
                    faultType={null}
                    className="w-full h-full"
                  />
                  <div className="absolute bottom-0 left-0 right-0 text-center pb-1 pointer-events-none">
                    <span className="font-mono text-[9px] text-primary uppercase tracking-widest">ROTAX 912-STYLE</span>
                  </div>
                </div>
              </div>

              {/* Floating HUD labels */}
              <div className="absolute top-8 left-4 bg-bg-panel/90 border border-bg-border px-2 py-1 backdrop-blur-sm">
                <div className="aero-label text-[9px]">RPM</div>
                <div className="font-mono text-xs text-primary">{fmt(telemetry.rpm, 0)}</div>
              </div>
              <div className="absolute top-8 right-4 bg-bg-panel/90 border border-bg-border px-2 py-1 backdrop-blur-sm">
                <div className="aero-label text-[9px]">CHT</div>
                <div className="font-mono text-xs text-primary">{fmt(telemetry.cht_c)} °C</div>
              </div>
              <div className="absolute bottom-16 left-4 bg-bg-panel/90 border border-bg-border px-2 py-1 backdrop-blur-sm">
                <div className="aero-label text-[9px]">OIL PRES</div>
                <div className="font-mono text-xs text-primary">{fmt(telemetry.oil_pressure_kpa, 0)} kPa</div>
              </div>
              <div className="absolute bottom-16 right-4 bg-bg-panel/90 border border-bg-border px-2 py-1 backdrop-blur-sm">
                <div className="aero-label text-[9px]">VIBRATION</div>
                <div className="font-mono text-xs text-primary">{fmt(telemetry.vibration_g, 3)} G</div>
              </div>
              <div className="absolute top-1/2 right-0 -translate-y-1/2 bg-bg-panel/90 border border-bg-border px-2 py-1 backdrop-blur-sm">
                <div className="aero-label text-[9px]">HEALTH</div>
                <div className="font-mono text-xs" style={{ color: healthColor }}>
                  {fmt(healthScore)}{healthStatus ? ` · ${healthStatus}` : ''}
                </div>
              </div>

              {/* Engine label */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center">
                <div className="font-mono text-[10px] text-primary uppercase tracking-widest">ENGINE DIGITAL TWIN</div>
                <Link to="/dashboard" className="font-mono text-[9px] text-text-muted hover:text-primary transition-colors">
                  → View Full 3D Dashboard
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          TELEMETRY PREVIEW STRIP
      ═══════════════════════════════════════════ */}
      <section ref={exploreRef} className="bg-bg-panel border-y border-bg-border py-6">
        <div className="max-w-7xl mx-auto px-6">
          <div className="aero-label mb-4 flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'ONLINE' ? 'bg-status-healthy animate-pulse-slow' : 'bg-text-muted'}`} />
            Live Telemetry Preview
          </div>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { label: 'RPM',          value: fmt(telemetry.rpm, 0),               unit: 'RPM' },
              { label: 'CHT',          value: fmt(telemetry.cht_c),                unit: '°C' },
              { label: 'EGT',          value: fmt(telemetry.egt_c, 0),             unit: '°C' },
              { label: 'OIL PRESSURE', value: fmt(telemetry.oil_pressure_kpa, 0), unit: 'kPa' },
              { label: 'VIBRATION',    value: fmt(telemetry.vibration_g, 3),       unit: 'G' },
              { label: 'HEALTH',       value: fmt(healthScore),                    unit: '' },
            ].map(({ label, value, unit }) => (
              <div key={label} className="aero-card p-3 text-center">
                <div className="aero-label text-[10px] mb-1">{label}</div>
                <div className="font-mono text-lg text-text-base">{value}</div>
                {unit && <div className="font-mono text-[10px] text-text-muted">{unit}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          CORE CAPABILITIES
      ═══════════════════════════════════════════ */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="mb-10 text-center">
          <div className="aero-label mb-2">System Capabilities</div>
          <h2 className="font-mono text-3xl font-bold text-text-base">CORE TECHNOLOGY</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {CAPABILITIES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="aero-card clip-angle p-5 hover:border-primary/40 transition-colors group">
              <Icon className="w-6 h-6 text-primary mb-3 group-hover:scale-110 transition-transform" />
              <div className="font-mono text-sm font-semibold text-text-base mb-2 uppercase tracking-wider">{title}</div>
              <p className="text-text-muted text-xs leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          SYSTEM FLOW PIPELINE
      ═══════════════════════════════════════════ */}
      <section className="py-16 bg-bg-panel border-y border-bg-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-8 text-center">
            <div className="aero-label mb-2">End-to-End Data Flow</div>
            <h2 className="font-mono text-2xl font-bold text-text-base">PIPELINE ARCHITECTURE</h2>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {PIPELINE_STAGES.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <div className="flex flex-col items-center gap-1">
                  <div className="bg-bg-card border border-bg-border px-3 py-2 clip-angle-sm min-w-[90px] text-center hover:border-primary/50 transition-colors">
                    <div className="font-mono text-[10px] text-primary uppercase tracking-wider">{stage.label}</div>
                  </div>
                  <div className="font-mono text-[9px] text-text-muted text-center max-w-[90px]">{stage.desc}</div>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-primary/50 flex-shrink-0 mb-4" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          FAULT COVERAGE
      ═══════════════════════════════════════════ */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="mb-10">
          <div className="aero-label mb-2">Detection Coverage</div>
          <h2 className="font-mono text-2xl font-bold text-text-base">MONITORED FAULT CONDITIONS</h2>
          <p className="text-text-muted text-sm mt-2">8 distinct fault types classified by multi-label XGBoost inference</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {FAULT_TYPES.map(({ name, icon: Icon }) => (
            <div key={name} className="aero-card flex items-center gap-3 px-3 py-2.5 hover:border-primary/40 transition-colors">
              <Icon className="w-4 h-4 text-primary flex-shrink-0" />
              <span className="font-mono text-xs text-text-base uppercase tracking-wide">{name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          PROTOTYPE NOTICE
      ═══════════════════════════════════════════ */}
      <section className="py-10 max-w-7xl mx-auto px-6">
        <div className="border border-status-warning/30 bg-status-warning/5 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-status-warning flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-mono text-sm text-status-warning uppercase tracking-wider mb-2">
                ⚠ Prototype / Simulation Data Notice
              </div>
              <p className="text-text-muted text-xs leading-relaxed">
                This demonstrator uses <strong className="text-text-base">representative synthetic telemetry</strong> and
                public aero-piston engine data to illustrate the architecture.
                Real UAV / DRDO engine telemetry is <strong className="text-text-base">not publicly available</strong> for prototype development.
                This system is <strong className="text-text-base">NOT validated for operational defence use</strong>.
                All inference results (health scores, fault classifications, RUL estimates) are demonstrative only
                and must not be used for actual engine control or flight-safety decisions.
                There is <strong className="text-text-base">no autonomous engine-control pathway</strong> in this system.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          FINAL CTA
      ═══════════════════════════════════════════ */}
      <section className="py-24 bg-bg-panel border-t border-bg-border text-center">
        <div className="max-w-3xl mx-auto px-6">
          <div className="font-mono text-3xl md:text-5xl font-bold text-text-base mb-4 tracking-tight">
            MONITOR. <span className="text-primary">PREDICT.</span> PREVENT.
          </div>
          <p className="text-text-muted mb-8">
            Experience real-time AI-driven engine health monitoring with the AeroTwin dashboard.
          </p>
          <Link to="/dashboard" className="aero-btn-filled inline-flex items-center gap-2 text-sm">
            LAUNCH DASHBOARD <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          FOOTER
      ═══════════════════════════════════════════ */}
      <footer className="bg-bg-panel border-t border-bg-border py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-mono text-sm font-bold text-text-base">
            <span className="text-text-base">AERO</span><span className="text-primary">TWIN</span>
          </div>
          <div className="flex gap-6">
            {['/', '/dashboard', '/diagnostics', '/missions', '/analytics', '/about'].map((href, i) => (
              <Link key={href} to={href} className="font-mono text-xs text-text-muted hover:text-primary transition-colors uppercase">
                {['Home', 'Dashboard', 'Diagnostics', 'Missions', 'Analytics', 'About'][i]}
              </Link>
            ))}
          </div>
          <div className="font-mono text-xs text-text-muted">SIH 2026 | Problem ID: SIH26054</div>
        </div>
      </footer>
    </div>
  )
}
