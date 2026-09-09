import React, { useState } from 'react'
import { Info } from 'lucide-react'
import useAeroStore from '../../store/useAeroStore.js'

/**
 * Parameter definitions — keys match exactly:
 *   telemetry.*        → store.telemetry (e.g. telemetry.rpm)
 *   expectedKey        → store.expectedValues (e.g. expectedValues.expected_rpm)
 *   residualKey        → store.residuals (e.g. residuals.residual_rpm)
 */
const PARAMS = [
  { label: 'RPM',          unit: 'rpm',  telKey: 'rpm',                 expKey: 'expected_rpm',                  resKey: 'residual_rpm',                  warn: 50,   crit: 150,  prec: 0 },
  { label: 'CHT',          unit: '°C',   telKey: 'cht_c',               expKey: 'expected_cht_c',                resKey: 'residual_cht_c',                warn: 10,   crit: 25,   prec: 1 },
  { label: 'EGT',          unit: '°C',   telKey: 'egt_c',               expKey: 'expected_egt_c',                resKey: 'residual_egt_c',                warn: 20,   crit: 50,   prec: 1 },
  { label: 'Oil Pressure', unit: 'kPa',  telKey: 'oil_pressure_kpa',    expKey: 'expected_oil_pressure_kpa',     resKey: 'residual_oil_pressure_kpa',     warn: 20,   crit: 50,   prec: 1 },
  { label: 'Oil Temp',     unit: '°C',   telKey: 'oil_temperature_c',   expKey: 'expected_oil_temperature_c',    resKey: 'residual_oil_temperature_c',    warn: 5,    crit: 15,   prec: 1 },
  { label: 'Fuel Flow',    unit: 'L/h',  telKey: 'fuel_flow_lph',       expKey: 'expected_fuel_flow_lph',        resKey: 'residual_fuel_flow_lph',        warn: 1,    crit: 3,    prec: 2 },
  { label: 'Vibration',    unit: 'G',    telKey: 'vibration_g',         expKey: 'expected_vibration_g',          resKey: 'residual_vibration_g',          warn: 0.05, crit: 0.15, prec: 3 },
  { label: 'Inj. Timing',  unit: '°',    telKey: 'injection_timing_deg',expKey: 'expected_injection_timing_deg', resKey: 'residual_injection_timing_deg', warn: 1,    crit: 3,    prec: 2 },
]

function residualClass(residual, warn, crit) {
  if (residual == null) return 'text-text-muted'
  const abs = Math.abs(residual)
  if (abs >= crit) return 'text-status-critical'
  if (abs >= warn) return 'text-status-warning'
  return 'text-status-healthy'
}

function fmt(val, prec) {
  if (val == null || isNaN(val)) return '--'
  return Number(val).toFixed(prec)
}

export default function ResidualPanel() {
  const telemetry      = useAeroStore((s) => s.telemetry)
  const expectedValues = useAeroStore((s) => s.expectedValues)
  const residuals      = useAeroStore((s) => s.residuals)
  const [tip, setTip]  = useState(false)

  return (
    <div className="flex flex-col gap-2">

      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="aero-title">
          DIGITAL TWIN — EXPECTED vs ACTUAL
        </span>
        <div className="relative">
          <button
            className="text-text-muted hover:text-text-base transition-colors"
            onMouseEnter={() => setTip(true)}
            onMouseLeave={() => setTip(false)}
            aria-label="Residual info"
          >
            <Info size={13} strokeWidth={1.8} />
          </button>
          {tip && (
            <div className="absolute right-0 top-5 z-20 w-60 p-2 bg-bg-card border border-bg-border font-mono text-[10px] text-text-muted shadow-lg">
              Residual = Actual - Expected. Computed by the Digital Twin.
            </div>
          )}
        </div>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-4 gap-2 pb-1 border-b border-bg-border">
        {['PARAMETER', 'EXPECTED', 'ACTUAL', 'RESIDUAL'].map((h) => (
          <span key={h} className="font-mono text-[10px] text-text-muted uppercase tracking-widest">{h}</span>
        ))}
      </div>

      {/* Data rows */}
      <div className="flex flex-col divide-y divide-bg-border">
        {PARAMS.map(({ label, unit, telKey, expKey, resKey, warn, crit, prec }, idx) => {
          const actual   = telemetry?.[telKey]      ?? null
          const expected = expectedValues?.[expKey] ?? null
          const residual = residuals?.[resKey]      ?? null
          const resClass = residualClass(residual, warn, crit)
          const resSign  = residual != null && residual >= 0 ? '+' : ''

          return (
            <div
              key={resKey}
              className={`grid grid-cols-4 gap-2 py-1.5 ${idx % 2 === 0 ? 'bg-bg-card/30' : ''}`}
            >
              <div className="flex items-center gap-1">
                <span className="font-mono text-xs text-text-base">{label}</span>
                <span className="font-mono text-[10px] text-text-muted">{unit}</span>
              </div>
              <span className="font-mono text-xs text-text-muted">{fmt(expected, prec)}</span>
              <span className={`font-mono text-xs ${actual != null ? 'text-text-base' : 'text-text-muted'}`}>
                {fmt(actual, prec)}
              </span>
              <span className={`font-mono text-xs font-semibold ${resClass}`}>
                {residual != null ? `${resSign}${fmt(residual, prec)}` : '--'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
