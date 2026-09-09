import React from 'react'
import { Link } from 'react-router-dom'
import { Cpu, Activity, AlertTriangle, Heart, ArrowRight, Shield, Info } from 'lucide-react'

const STACK = [
  { cat: 'Frontend',  items: 'React 18, Vite, Tailwind CSS, React Router v6' },
  { cat: 'State',     items: 'Zustand (global store), TelemetryProvider (REST polling)' },
  { cat: '3D Engine', items: 'Three.js WebGL, GLTF/GLB, OrbitControls, RoomEnvironment' },
  { cat: 'Charts',    items: 'Recharts (LineChart, AreaChart, BarChart)' },
  { cat: 'Backend',   items: 'FastAPI (Python), Uvicorn, Pydantic' },
  { cat: 'AI/ML',     items: 'scikit-learn (Isolation Forest), XGBoost, joblib' },
  { cat: 'Data Gen',  items: 'NumPy, Pandas (synthetic telemetry generator)' },
  { cat: 'Database',  items: 'Supabase (optional PostgreSQL persistence)' },
]

const FAULT_TYPES = [
  'MISFIRE', 'INJECTOR ABNORMALITY', 'COOLING DEGRADATION', 'LUBRICATION ISSUE',
  'SENSOR DRIFT', 'COMBUSTION INSTABILITY', 'OVERHEATING TREND', 'ABNORMAL VIBRATION',
]

export default function About() {
  return (
    <div className="min-h-screen bg-bg-base py-10">
      <div className="max-w-4xl mx-auto px-6">

        {/* ── HERO ── */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 border border-primary/30 px-3 py-1 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span className="font-mono text-xs text-primary uppercase tracking-widest">Smart India Hackathon 2026</span>
          </div>
          <h1 className="font-mono font-bold mb-2" style={{ fontSize: 'clamp(2.5rem,6vw,4rem)' }}>
            <span className="text-text-base">AERO</span><span className="text-primary">TWIN</span>
          </h1>
          <p className="text-text-muted text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
            AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction
            and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs.
          </p>
          <div className="mt-4 inline-block border border-bg-border px-4 py-1.5">
            <span className="font-mono text-xs text-text-muted">Problem Statement ID: </span>
            <span className="font-mono text-xs text-primary">SIH26054</span>
          </div>
        </div>

        {/* ── PROJECT OVERVIEW ── */}
        <section className="aero-panel p-6 mb-6">
          <div className="aero-title mb-3 flex items-center gap-2">
            <Info className="w-3.5 h-3.5" /> Project Overview
          </div>
          <p className="text-text-muted text-sm leading-relaxed mb-3">
            Medium Altitude Long Endurance (MALE) UAVs rely on aero piston engines — such as the Rotax 912
            family — for propulsion during extended missions. Real-time health monitoring, early fault detection,
            and mission reliability enhancement are critical operational requirements.
          </p>
          <p className="text-text-muted text-sm leading-relaxed">
            AeroTwin addresses this challenge by combining a physics-informed Digital Twin with an integrated
            AI/ML inference pipeline, delivering continuous anomaly scoring, multi-label fault classification,
            composite health scoring, and formula-based Remaining Useful Life estimation — all on the
            actual telemetry stream.
          </p>
        </section>

        {/* ── DIGITAL TWIN ── */}
        <section className="aero-panel p-6 mb-6">
          <div className="aero-title mb-3 flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5" /> Digital Twin Architecture
          </div>
          <p className="text-text-muted text-sm leading-relaxed mb-4">
            The Digital Twin continuously models the expected engine state based on throttle, altitude,
            ambient conditions and mission phase. Comparing this expected state against the actual observed
            telemetry produces <strong className="text-text-base">residuals</strong> — the signal-level
            fingerprints that reveal developing faults before they manifest as hard failures.
          </p>
          {/* Pipeline */}
          <div className="flex flex-wrap items-center gap-2">
            {['TELEMETRY', 'DIGITAL TWIN MODEL', 'RESIDUALS', 'AI/ML INFERENCE', 'HEALTH + RUL', 'DASHBOARD'].map((s, i, arr) => (
              <React.Fragment key={s}>
                <div className="bg-bg-card border border-bg-border px-3 py-1.5 clip-angle-sm">
                  <span className="font-mono text-[10px] text-primary uppercase tracking-wider">{s}</span>
                </div>
                {i < arr.length - 1 && <ArrowRight className="w-3 h-3 text-primary/50 flex-shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </section>

        {/* ── AI/ML PIPELINE ── */}
        <section className="aero-panel p-6 mb-6">
          <div className="aero-title mb-4 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" /> AI / ML Pipeline
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {[
              { title: 'Anomaly Detection', desc: 'Isolation Forest-based unsupervised anomaly scoring on the telemetry and residual feature vector. Score 0–1; higher = more anomalous.' },
              { title: 'Fault Classification', desc: 'Multi-label XGBoost classifier identifying the most probable fault type from 8 categories, with per-class confidence scores.' },
              { title: 'Health Scoring', desc: 'Degradation-informed composite health index (0–100) with four bands: HEALTHY (80–100), WARNING (60–80), DEGRADING (35–60), CRITICAL (0–35).' },
              { title: 'RUL Estimation', desc: 'Formula-based Remaining Useful Life derived from health degradation rate. No separate ML regression model — computed analytically by the backend.' },
            ].map(({ title, desc }) => (
              <div key={title} className="aero-card p-4">
                <div className="font-mono text-xs font-semibold text-text-base mb-2 uppercase tracking-wider">{title}</div>
                <p className="text-text-muted text-xs leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-2">
            <div className="aero-label mb-2">8 Monitored Fault Types</div>
            <div className="flex flex-wrap gap-2">
              {FAULT_TYPES.map((f) => (
                <span key={f} className="font-mono text-[10px] border border-bg-border text-text-muted px-2 py-1 uppercase tracking-wider hover:border-primary/40 hover:text-primary transition-colors">
                  {f}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ── TECHNOLOGY STACK ── */}
        <section className="aero-panel p-6 mb-6">
          <div className="aero-title mb-4">Technology Stack</div>
          <div className="divide-y divide-bg-border">
            {STACK.map(({ cat, items }) => (
              <div key={cat} className="flex gap-4 py-2.5">
                <div className="font-mono text-xs text-text-muted w-28 flex-shrink-0 uppercase tracking-wider pt-0.5">{cat}</div>
                <div className="font-mono text-xs text-text-base">{items}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── DISCLAIMER ── */}
        <section className="border border-status-warning/30 bg-status-warning/5 p-6 mb-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-status-warning flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-mono text-sm text-status-warning uppercase tracking-wider mb-3">
                Important Disclaimers
              </div>
              <ul className="text-text-muted text-xs space-y-2 list-none">
                {[
                  'This system uses representative SYNTHETIC telemetry — NOT real DRDO classified engine data. Real UAV/DRDO telemetry is not publicly available for prototype development.',
                  'This is a SOFTWARE DEMONSTRATOR built for SIH 2026. All inference results are illustrative only.',
                  'Inference accuracy is NOT defence-grade validated. No formal accuracy certification exists.',
                  'There is NO autonomous engine-control pathway. The system is decision-support and visualization only.',
                  'Do NOT use this system for actual engine control, flight-safety decisions, or operational deployment.',
                ].map((point, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-status-warning flex-shrink-0 mt-0.5">›</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── TEAM ── */}
        <section className="aero-panel p-6 mb-8 text-center">
          <Shield className="w-8 h-8 text-primary mx-auto mb-3" />
          <div className="font-mono text-sm text-text-base mb-1">Built for Smart India Hackathon 2026</div>
          <div className="font-mono text-xs text-text-muted">Problem Statement: SIH26054</div>
          <div className="font-mono text-xs text-text-muted mt-1">AI-Enabled Digital Twin · Aero Piston Engines · MALE UAVs</div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <Link to="/dashboard" className="aero-btn-filled inline-flex items-center gap-2">
            LAUNCH DASHBOARD <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  )
}
