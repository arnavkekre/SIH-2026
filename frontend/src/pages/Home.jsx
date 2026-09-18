import React from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, ShieldCheck, Activity, Cpu, Layers,
  Compass, AlertTriangle, Clock, CheckCircle2, ChevronDown,
  Plane, Wrench, BarChart2, Sparkles, Sliders, Database
} from 'lucide-react'

const METRICS_SUMMARY = [
  { label: 'Intelligence Pipeline', value: '5-Stage', desc: 'Telemetry to Predictive Advisory' },
  { label: 'Monitored Faults',     value: '8 Classes', desc: 'Misfire to Cooling Degradation' },
  { label: 'Inference Latency',    value: '< 1.0s',    desc: 'Real-time Edge / GCS Evaluation' },
  { label: 'Target Platform',      value: 'MALE UAV',  desc: 'Rotax 912-Class Aero Piston Engines' },
]

const INTELLIGENCE_CYCLE = [
  {
    step: '01',
    zone: 'Zone 1: Sensor & Mission Ingestion',
    title: 'Multi-Sensor Data Acquisition',
    desc: 'Continuous ingestion of 8 primary telemetry streams (RPM, CHT, EGT, Oil Press/Temp, Fuel Flow, Vibration, Timing) combined with mission parameters (Altitude, Throttle %, Ambient Temp, Flight Phase).',
    icon: Database,
  },
  {
    step: '02',
    zone: 'Zone 2: Digital Twin State Layer',
    title: 'Physics-Based Expected State & Residuals',
    desc: 'The Digital Twin models nominal engine thermodynamic behavior under current atmospheric and throttle conditions, computing residuals (Residual = Actual − Expected) that isolate subtle mechanical stress.',
    icon: Cpu,
  },
  {
    step: '03',
    zone: 'Zone 3 & 4: AI/ML Inference Brain',
    title: 'Anomaly Detection & Fault Classification',
    desc: 'Unsupervised Isolation Forest algorithm scores multivariate statistical deviations (0–1), while a multi-label XGBoost classifier pinpoints fault signatures and outputs probability & severity rankings.',
    icon: Activity,
  },
  {
    step: '04',
    zone: 'Zone 4: Health & Prognostics',
    title: 'Engine Health Index & RUL Estimation',
    desc: 'Synthesizes residual severity and anomaly confidence into a dynamic 0–100 Health Score with categorical status (Healthy, Warning, Degrading, Critical) and computes formula-based Remaining Useful Life (RUL).',
    icon: Clock,
  },
  {
    step: '05',
    zone: 'Zone 5: Decision Support',
    title: 'Predictive Ground Control Decision Support',
    desc: 'Translates raw predictions into actionable maintenance advisories and mission-readiness alerts displayed on the Operator Dashboard and simulated across diverse flight profiles.',
    icon: ShieldCheck,
  },
]

const INNOVATION_PILLARS = [
  {
    title: 'Physics + AI Twin Fusion',
    subtitle: 'HYBRID INTELLIGENCE',
    desc: 'Rather than treating machine learning as a pure black box, AeroTwin grounds model inference in thermodynamic engine physics. Sensor residuals filter out operational variations so AI learns genuine mechanical faults.',
    icon: Sparkles,
  },
  {
    title: 'Real-Time Health Intelligence',
    subtitle: 'CONTINUOUS METRICS',
    desc: 'Converts multi-sensor telemetry into a live 0–100 Engine Health Score, categorical status bands, and fault probabilities instead of relying on rudimentary static threshold alarms that trigger too late.',
    icon: Activity,
  },
  {
    title: 'Predictive Mission Reliability',
    subtitle: 'RUL PROGNOSTICS',
    desc: 'Tracks micro-degradation trends over time to project Remaining Useful Life (RUL) before critical components fail, enabling condition-based maintenance and averting costly in-flight mission abortions.',
    icon: Compass,
  },
  {
    title: 'Mission-Aware Context',
    subtitle: 'FLIGHT PROFILE SENSITIVE',
    desc: 'Dynamically accounts for altitude-induced barometric drop, ambient temperatures, and flight phases (Taxi, Takeoff, Climb, Cruise, Loiter, Descent, Landing) to ensure zero false positives during throttle transients.',
    icon: Sliders,
  },
]

const STAKEHOLDERS = [
  {
    role: 'UAV Operators & Mission Planners',
    benefit: 'Real-time visibility into engine health and flight endurance to make confident go/no-go operational decisions during high-stakes reconnaissance.',
    icon: Plane,
  },
  {
    role: 'Maintenance & Ground Crews',
    benefit: 'Pinpointed diagnostic evidence, fault confidence scores, and prescriptive maintenance recommendations before catastrophic failure occurs on the tarmac.',
    icon: Wrench,
  },
  {
    role: 'Defence & UAV Organizations',
    benefit: 'Enhanced asset survivability, higher fleet availability, and reduced lifecycle maintenance costs by shifting from fixed-hour overhauls to condition-based care.',
    icon: ShieldCheck,
  },
  {
    role: 'Propulsion Researchers & Engineers',
    benefit: 'Rich synthetic and recorded multi-mission datasets to analyze thermal degradation curves and refine engine reliability designs.',
    icon: BarChart2,
  },
]

const SYSTEM_MODULES = [
  {
    title: 'Interactive 3D Engine Twin',
    to: '/model',
    desc: 'Full 3D Rotax-912 engine viewer with real-time cylinder 4-stroke cycle animation and live HUD telemetry gauges.',
    badge: '3D VISUALIZER',
  },
  {
    title: 'Mission Control Dashboard',
    to: '/dashboard',
    desc: 'Command console featuring real-time sparklines, KPI telemetry cards, and the collapsible Expected vs Actual table.',
    badge: 'LIVE TELEMETRY',
  },
  {
    title: 'Diagnostic Studio',
    to: '/diagnostics',
    desc: 'Detailed breakdown of Isolation Forest anomaly scoring, XGBoost fault probability, and diagnostic evidence severity.',
    badge: 'AI INFERENCE',
  },
  {
    title: 'Flight Simulation & Replay',
    to: '/missions',
    desc: 'Interactive trajectory playback engine supporting 0.5× to 10× replay speeds across diverse mission phases.',
    badge: 'SIMULATION',
  },
  {
    title: 'Engineering Analytics',
    to: '/analytics',
    desc: 'Session degradation trends, peak anomaly metrics, active fault counts, and multi-sensor performance graphs.',
    badge: 'ANALYTICS',
  },
  {
    title: 'Project Foundations & Research',
    to: '/about',
    desc: 'Overview of the SIH26054 challenge, technical architecture documentation, and academic references.',
    badge: 'DOCUMENTATION',
  },
]

export default function Home() {
  return (
    <div className="bg-bg-base text-text-base">

      {/* ═══════════════════════════════════════════
          1. HERO & INTRODUCTION
      ═══════════════════════════════════════════ */}
      <section className="relative min-h-[85vh] bg-tech-grid flex items-center border-b border-bg-border overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(0, 240, 255, 0.05) 0%, transparent 70%)' }}
          />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6 py-20 w-full flex flex-col items-center text-center">

          {/* Hackathon & Team Header Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-6">
            <span className="border border-primary/40 bg-primary/10 text-primary font-mono text-[11px] px-3 py-1 uppercase tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              Smart India Hackathon 2026
            </span>
            <span className="border border-bg-border bg-bg-card font-mono text-[11px] text-text-muted px-3 py-1 uppercase tracking-wider">
              Problem Statement ID: <strong className="text-text-base">SIH26054</strong>
            </span>
            <span className="border border-bg-border bg-bg-card font-mono text-[11px] text-text-muted px-3 py-1 uppercase tracking-wider">
              Team: <strong className="text-text-base">TechVanguard</strong>
            </span>
          </div>

          {/* Main Title */}
          <h1 className="font-mono font-bold tracking-tight text-4xl sm:text-6xl lg:text-7xl leading-none mb-4">
            <span className="text-text-base">AERO</span><span className="text-primary">TWIN</span>
          </h1>

          <div className="font-mono text-xs sm:text-sm md:text-base text-primary uppercase tracking-[0.3em] mb-6">
            AI-Enabled Real-Time Digital Twin System
          </div>

          {/* Executive Summary */}
          <p className="max-w-3xl text-sm sm:text-base text-text-muted leading-relaxed mb-8">
            Engineered for <strong className="text-text-base">Medium-Altitude Long-Endurance (MALE) UAVs</strong>, AeroTwin fuses physics-informed engine modeling with advanced machine learning to deliver continuous health monitoring, micro-fault prediction, and Remaining Useful Life (RUL) estimation for aero piston engines.
          </p>

          {/* Primary Actions */}
          <div className="flex flex-wrap items-center justify-center gap-4 mb-14">
            <Link to="/dashboard" className="aero-btn-filled flex items-center gap-2 text-xs sm:text-sm">
              LAUNCH MISSION DASHBOARD <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/model" className="aero-btn flex items-center gap-2 text-xs sm:text-sm">
              <Layers className="w-4 h-4" /> EXPLORE 3D ENGINE TWIN
            </Link>
            <a href="#intelligence-cycle" className="px-4 py-2 border border-bg-border font-mono text-xs uppercase tracking-wider text-text-muted hover:text-text-base hover:border-text-muted transition-colors">
              SYSTEM ARCHITECTURE ↓
            </a>
          </div>

          {/* Key Metrics Strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 w-full max-w-5xl">
            {METRICS_SUMMARY.map(({ label, value, desc }) => (
              <div key={label} className="aero-card clip-angle-sm p-4 text-left border-t-2 border-t-primary/70">
                <div className="aero-label text-[10px] mb-1">{label}</div>
                <div className="font-mono text-xl font-bold text-text-base mb-0.5">{value}</div>
                <div className="font-mono text-[10px] text-text-muted">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          2. PROBLEM & STRATEGIC SIGNIFICANCE
      ═══════════════════════════════════════════ */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">

          <div className="lg:col-span-5 flex flex-col gap-4">
            <div className="aero-label flex items-center gap-2">
              <span className="w-2 h-2 rounded-sm bg-status-warning" />
              Strategic Significance
            </div>
            <h2 className="font-mono text-2xl sm:text-3xl font-bold leading-tight text-text-base">
              THE CHALLENGE OF MALE UAV PROPULSION RELIABILITY
            </h2>
            <p className="text-text-muted text-sm leading-relaxed">
              MALE UAVs conduct persistent surveillance missions spanning 24+ hours at varying altitudes and atmospheric densities. Aero-piston powerplants (such as Rotax-912 class engines) operate under demanding thermal and vibrational cycles where undetected mechanical degradation can trigger sudden catastrophic in-flight engine failure.
            </p>
            <div className="border-l-2 border-primary pl-4 py-1 mt-2">
              <p className="font-mono text-xs text-text-base italic">
                "In unmanned defence aviation, engine stoppage means mission failure and asset loss. Fixed-hour overhauls and basic threshold alerts are no longer sufficient."
              </p>
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="aero-card p-5 border-l-2 border-l-status-critical">
              <div className="flex items-center gap-2 mb-2 font-mono text-xs uppercase tracking-wider text-status-critical">
                <AlertTriangle className="w-4 h-4" /> The Risk of Late Detection
              </div>
              <p className="text-text-muted text-xs leading-relaxed">
                Conventional sensors trigger threshold warnings only after temperatures, pressure, or vibrations surpass emergency limits—giving ground operators mere seconds to respond before mechanical seizure.
              </p>
            </div>

            <div className="aero-card p-5 border-l-2 border-l-status-warning">
              <div className="flex items-center gap-2 mb-2 font-mono text-xs uppercase tracking-wider text-status-warning">
                <Clock className="w-4 h-4" /> Costly Scheduled Overhauls
              </div>
              <p className="text-text-muted text-xs leading-relaxed">
                Traditional time-based inspections ground operational aircraft prematurely, driving up maintenance downtime and life-cycle costs while remaining blind to sudden anomalies between service intervals.
              </p>
            </div>

            <div className="aero-card p-5 border-l-2 border-l-primary sm:col-span-2">
              <div className="flex items-center gap-2 mb-2 font-mono text-xs uppercase tracking-wider text-primary">
                <CheckCircle2 className="w-4 h-4" /> The AeroTwin Paradigm Shift
              </div>
              <p className="text-text-muted text-xs leading-relaxed">
                AeroTwin combines a physics-based digital twin that models healthy expected engine behavior in real time with machine learning residual analysis. By isolating deviations as subtle as a 0.5% fuel-flow variance or subtle cylinder head temperature drifts, anomalies are caught hours before irreversible damage occurs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          3. THE 5-STAGE INTELLIGENCE CYCLE
      ═══════════════════════════════════════════ */}
      <section id="intelligence-cycle" className="py-20 bg-bg-panel border-y border-bg-border scroll-mt-14">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <div className="aero-label mb-2 flex items-center justify-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-primary" />
              End-to-End Technical Approach
            </div>
            <h2 className="font-mono text-2xl sm:text-3xl font-bold text-text-base uppercase tracking-tight">
              THE AERO TWIN INTELLIGENCE CYCLE
            </h2>
            <p className="text-text-muted text-xs sm:text-sm mt-2">
              From raw sensor telemetry ingestion to real-time predictive decision support across 5 architectural zones.
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {INTELLIGENCE_CYCLE.map(({ step, zone, title, desc, icon: Icon }) => (
              <div
                key={step}
                className="aero-card p-5 flex flex-col md:flex-row items-start md:items-center gap-6 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-center gap-4 flex-shrink-0">
                  <div className="font-mono text-2xl font-bold text-primary/40 border border-primary/20 w-12 h-12 flex items-center justify-center clip-angle-sm">
                    {step}
                  </div>
                  <div className="p-2.5 rounded-sm bg-primary/10 text-primary border border-primary/30">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="font-mono text-[10px] text-primary uppercase tracking-widest mb-1">{zone}</div>
                  <h3 className="font-mono text-base font-semibold text-text-base mb-1">{title}</h3>
                  <p className="text-text-muted text-xs leading-relaxed">{desc}</p>
                </div>

                <div className="hidden lg:block flex-shrink-0">
                  <span className="font-mono text-[10px] text-text-muted/60 uppercase tracking-widest border border-bg-border px-2 py-1">
                    AUTONOMOUS
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          4. FOUR CORE INNOVATION PILLARS
      ═══════════════════════════════════════════ */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="aero-label mb-2 flex items-center justify-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            Key Innovations
          </div>
          <h2 className="font-mono text-2xl sm:text-3xl font-bold text-text-base uppercase tracking-tight">
            INNOVATION & UNIQUENESS
          </h2>
          <p className="text-text-muted text-xs sm:text-sm mt-2">
            What distinguishes AeroTwin from traditional fault detection systems.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {INNOVATION_PILLARS.map(({ title, subtitle, desc, icon: Icon }) => (
            <div key={title} className="aero-card clip-angle p-6 flex flex-col justify-between hover:border-primary/40 transition-colors group">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="aero-label text-[10px]">{subtitle}</div>
                  <Icon className="w-5 h-5 text-primary group-hover:scale-110 transition-transform" />
                </div>
                <h3 className="font-mono text-lg font-bold text-text-base mb-2 uppercase tracking-wide">{title}</h3>
                <p className="text-text-muted text-xs sm:text-sm leading-relaxed">{desc}</p>
              </div>
              <div className="mt-6 pt-3 border-t border-bg-border/60 flex items-center justify-between font-mono text-[10px] text-text-muted">
                <span>VALIDATED PROTOCOL</span>
                <span className="text-primary">SIH26054</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          5. TARGET AUDIENCE & MISSION OUTCOME
      ═══════════════════════════════════════════ */}
      <section className="py-20 bg-bg-panel border-y border-bg-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-12">
            <div className="aero-label mb-2">Operational Impact</div>
            <h2 className="font-mono text-2xl sm:text-3xl font-bold text-text-base uppercase tracking-tight">
              STAKEHOLDER BENEFITS & MISSION OUTCOMES
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            {STAKEHOLDERS.map(({ role, benefit, icon: Icon }) => (
              <div key={role} className="aero-card p-5 flex flex-col justify-between">
                <div>
                  <div className="w-8 h-8 rounded-sm bg-primary/10 border border-primary/30 text-primary flex items-center justify-center mb-3">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="font-mono text-xs font-semibold text-text-base mb-2 uppercase tracking-wide">{role}</div>
                  <p className="text-text-muted text-xs leading-relaxed">{benefit}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Mission Outcome Funnel */}
          <div className="bg-bg-card border border-bg-border p-6 clip-angle-sm">
            <div className="aero-label text-[10px] mb-3 text-center">AeroTwin Mission Outcome Value Chain</div>
            <div className="flex flex-wrap items-center justify-center gap-3 md:gap-6 font-mono text-xs uppercase tracking-wider">
              <span className="px-3 py-1.5 border border-primary/40 text-primary bg-primary/10">1. Early Warning</span>
              <span className="text-text-muted">→</span>
              <span className="px-3 py-1.5 border border-primary/40 text-primary bg-primary/10">2. Condition-Based Maintenance</span>
              <span className="text-text-muted">→</span>
              <span className="px-3 py-1.5 border border-status-healthy/40 text-status-healthy bg-status-healthy/10">3. Engine Availability</span>
              <span className="text-text-muted">→</span>
              <span className="px-3 py-1.5 border border-status-healthy/40 text-status-healthy bg-status-healthy/10">4. Mission Readiness</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          6. SYSTEM MODULES DIRECTORY
      ═══════════════════════════════════════════ */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="aero-label mb-2 flex items-center justify-center gap-2">
            <Layers className="w-3.5 h-3.5 text-primary" />
            Application Console
          </div>
          <h2 className="font-mono text-2xl sm:text-3xl font-bold text-text-base uppercase tracking-tight">
            EXPLORE THE SYSTEM MODULES
          </h2>
          <p className="text-text-muted text-xs sm:text-sm mt-2">
            Access live telemetry, interactive 3D visualizations, model diagnostics, and mission simulators.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SYSTEM_MODULES.map(({ title, to, desc, badge }) => (
            <Link
              key={to}
              to={to}
              className="aero-card p-5 flex flex-col justify-between hover:border-primary transition-all duration-200 group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-[9px] px-2 py-0.5 rounded border border-primary/30 text-primary uppercase tracking-widest bg-primary/5">
                    {badge}
                  </span>
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-primary group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="font-mono text-sm font-semibold text-text-base mb-2 group-hover:text-primary transition-colors">
                  {title}
                </h3>
                <p className="text-text-muted text-xs leading-relaxed">{desc}</p>
              </div>
              <div className="mt-4 pt-3 border-t border-bg-border font-mono text-[10px] text-text-muted group-hover:text-primary">
                OPEN MODULE →
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          7. PROTOTYPE NOTICE
      ═══════════════════════════════════════════ */}
      <section className="py-8 max-w-7xl mx-auto px-6">
        <div className="border border-status-warning/30 bg-status-warning/5 p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-status-warning flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-mono text-xs text-status-warning uppercase tracking-wider mb-1">
              Smart India Hackathon 2026 Prototype Notice
            </div>
            <p className="text-text-muted text-xs leading-relaxed">
              This system uses representative synthetic and simulated telemetry calibrated to the Rotax 912 aero piston engine specifications. All health indices, fault classifications, and RUL estimates are demonstrative decision-support indicators and do not directly actuate aircraft flight controls.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          8. FOOTER
      ═══════════════════════════════════════════ */}
      <footer className="bg-bg-panel border-t border-bg-border py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-mono text-sm font-bold text-text-base">
            <span className="text-text-base">AERO</span><span className="text-primary">TWIN</span>
            <span className="text-text-muted text-xs font-normal ml-2">| SIH 2026 Team TechVanguard</span>
          </div>

          <div className="flex flex-wrap gap-5">
            {[
              { to: '/', label: 'Home' },
              { to: '/model', label: 'Engine 3D' },
              { to: '/dashboard', label: 'Dashboard' },
              { to: '/diagnostics', label: 'Diagnostics' },
              { to: '/missions', label: 'Missions' },
              { to: '/analytics', label: 'Analytics' },
              { to: '/about', label: 'About' },
            ].map(({ to, label }) => (
              <Link key={to} to={to} className="font-mono text-xs text-text-muted hover:text-primary transition-colors uppercase">
                {label}
              </Link>
            ))}
          </div>

          <div className="font-mono text-xs text-text-muted">Problem Statement: SIH26054</div>
        </div>
      </footer>
    </div>
  )
}
