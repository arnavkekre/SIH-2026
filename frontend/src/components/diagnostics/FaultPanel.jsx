import React from 'react';
import {
  Zap, Thermometer, Droplets, Flame, Activity,
  Waves, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import useAeroStore from '../../store/useAeroStore.js';

const FAULT_ICONS = {
  MISFIRE:                Zap,
  COOLING_DEGRADATION:    Thermometer,
  LUBRICATION_ISSUE:      Droplets,
  INJECTOR_ABNORMALITY:   Flame,
  SENSOR_DRIFT:           Activity,
  COMBUSTION_INSTABILITY: Flame,
  OVERHEATING_TREND:      Thermometer,
  ABNORMAL_VIBRATION:     Waves,
  NORMAL:                 CheckCircle2,
};

function getFaultIcon(type) {
  return FAULT_ICONS[type?.toUpperCase()] ?? CheckCircle2;
}

function formatFaultType(type) {
  if (!type || type === 'NORMAL') return 'NOMINAL';
  return type.toLowerCase().split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function getSeverityLabel(sev) {
  if (sev == null)  return 'UNKNOWN';
  if (sev < 0.25)   return 'LOW';
  if (sev < 0.5)    return 'MODERATE';
  if (sev < 0.75)   return 'HIGH';
  return 'CRITICAL';
}

function getSeverityTextClass(sev) {
  if (sev == null)  return 'text-text-muted';
  if (sev < 0.25)   return 'text-status-healthy';
  if (sev < 0.5)    return 'text-status-warning';
  if (sev < 0.75)   return 'text-status-degrading';
  return 'text-status-critical';
}

function getSeverityBgClass(sev) {
  if (sev == null)  return 'bg-text-muted';
  if (sev < 0.25)   return 'bg-status-healthy';
  if (sev < 0.5)    return 'bg-status-warning';
  if (sev < 0.75)   return 'bg-status-degrading';
  return 'bg-status-critical';
}

function getConfBarClass(conf) {
  if (conf == null) return 'bg-text-muted';
  if (conf < 0.5)   return 'bg-status-healthy';
  if (conf < 0.75)  return 'bg-status-warning';
  return 'bg-status-critical';
}

/**
 * FaultPanel — fault classification with icon, confidence bar, and severity indicator.
 */
export default function FaultPanel() {
  const fault = useAeroStore((s) => s.fault);

  const type      = fault?.type      ?? 'NORMAL';
  const active    = fault?.active    ?? false;
  const confidence= fault?.confidence ?? null;
  const severity  = fault?.severity  ?? null;
  const isNominal = !active || type === 'NORMAL' || !type;

  const FaultIcon    = getFaultIcon(type);
  const typeLabel    = formatFaultType(type);
  const sevLabel     = getSeverityLabel(severity);
  const sevTextClass = getSeverityTextClass(severity);
  const sevBgClass   = getSeverityBgClass(severity);
  const confPct      = confidence != null ? (confidence * 100).toFixed(0) : '--';
  const confBarClass = getConfBarClass(confidence);

  // Severity segment bars (4 levels)
  const SEV_LEVELS = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
  const sevThresholds = [0, 0.25, 0.5, 0.75];

  return (
    <div className="aero-panel flex flex-col gap-3">

      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="aero-title tracking-widest">FAULT CLASSIFICATION</span>
        <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
          active
            ? 'text-status-critical border-status-critical/40 bg-status-critical/10'
            : 'text-status-healthy border-status-healthy/40 bg-status-healthy/10'
        }`}>
          {active ? 'ACTIVE' : 'INACTIVE'}
        </span>
      </div>

      {/* Fault type block */}
      <div className={`flex items-center gap-2 p-3 rounded-lg border ${
        active && !isNominal
          ? 'border-status-critical/40 bg-status-critical/5'
          : 'border-status-healthy/30 bg-status-healthy/5'
      }`}>
        <FaultIcon
          size={22}
          className={active && !isNominal ? 'text-status-critical' : 'text-status-healthy'}
          strokeWidth={1.8}
        />
        <div className="flex flex-col">
          <span className={`font-mono text-lg font-bold leading-tight ${
            active && !isNominal ? 'text-status-critical' : 'text-status-healthy'
          }`}>
            {typeLabel}
          </span>
          {active && !isNominal && (
            <div className="flex items-center gap-1 mt-0.5">
              <AlertTriangle size={10} className="text-status-warning" />
              <span className="font-mono text-[10px] text-status-warning uppercase tracking-wider">
                Fault Detected
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Confidence bar */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Confidence</span>
          <span className="font-mono text-xs text-text-base">{confPct}%</span>
        </div>
        <div className="w-full h-2 rounded-full bg-bg-border overflow-hidden">
          {confidence != null && (
            <div
              className={`h-full rounded-full transition-all duration-500 ${confBarClass}`}
              style={{ width: `${(confidence * 100).toFixed(1)}%` }}
            />
          )}
        </div>
      </div>

      {/* Severity indicator */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Severity</span>
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {SEV_LEVELS.map((lvl, i) => {
              const filled = severity != null && severity >= sevThresholds[i];
              return (
                <div
                  key={lvl}
                  className={`w-4 h-1.5 rounded-sm ${filled ? sevBgClass : 'bg-bg-border'}`}
                />
              );
            })}
          </div>
          <span className={`font-mono text-xs font-semibold ${sevTextClass}`}>{sevLabel}</span>
        </div>
      </div>
    </div>
  );
}
