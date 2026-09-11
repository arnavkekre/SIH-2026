import React from 'react';
import useAeroStore from '../../store/useAeroStore.js';
import StatusBadge from '../ui/StatusBadge.jsx';

/** COOLING_DEGRADATION → Cooling Degradation */
function formatFaultType(type) {
  if (!type || type === 'NORMAL') return 'NOMINAL';
  return type
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function KpiCard({ label, children, className = '' }) {
  return (
    <div className={`aero-card clip-angle flex-1 min-w-0 p-3 flex flex-col gap-1 ${className}`}>
      <span className="aero-title text-[10px]">{label}</span>
      {children}
    </div>
  );
}

/**
 * KpiRow — horizontal strip of 5 key performance indicator cards.
 */
export default function KpiRow() {
  const healthScore    = useAeroStore((s) => s.healthScore);
  const healthStatus   = useAeroStore((s) => s.healthStatus);
  const anomalyScore   = useAeroStore((s) => s.anomalyScore);
  const fault          = useAeroStore((s) => s.fault);
  const rul            = useAeroStore((s) => s.rul);
  const missionId      = useAeroStore((s) => s.missionId);
  const missionPhase   = useAeroStore((s) => s.missionPhase);
  const replayRunning  = useAeroStore((s) => s.replayRunning);
  const replayProgress = useAeroStore((s) => s.replayProgress);
  const replayRow      = useAeroStore((s) => s.replayCurrentRow);
  const replayTotal    = useAeroStore((s) => s.replayTotalRows);

  // Anomaly
  const anomalyPct = anomalyScore != null ? Math.round(anomalyScore * 100) : null;
  const anomalyBarColor =
    anomalyScore == null          ? 'bg-text-muted'        :
    anomalyScore < 0.3            ? 'bg-status-healthy'    :
    anomalyScore < 0.6            ? 'bg-status-warning'    :
    anomalyScore < 0.8            ? 'bg-status-degrading'  : 'bg-status-critical';

  // Fault
  const faultActive    = fault?.active ?? false;
  const faultTypeLabel = formatFaultType(fault?.type);
  const faultConf      = fault?.confidence != null ? (fault.confidence * 100).toFixed(0) : '--';

  // RUL
  const rulMinutes = rul?.minutes != null ? rul.minutes.toFixed(1) : '--';
  const rulStatus  = rul?.status ?? null;

  // Mission
  const missionDisplay = missionId ?? '--';
  const phaseDisplay   = missionPhase ?? '--';

  // Replay progress
  const replayPct =
    replayProgress != null ? Math.round(replayProgress * 100) :
    replayRow != null && replayTotal ? Math.round((replayRow / replayTotal) * 100) : null;

  return (
    <div className="flex flex-row gap-2 w-full px-2">

      {/* 1 — ENGINE HEALTH */}
      <KpiCard label="ENGINE HEALTH">
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-2xl font-bold text-text-base">
            {healthScore != null ? healthScore.toFixed(1) : '--'}
          </span>
          <span className="font-mono text-xs text-text-muted">/100</span>
        </div>
        {healthStatus
          ? <StatusBadge status={healthStatus} size="sm" />
          : <span className="text-text-muted font-mono text-xs">--</span>}
      </KpiCard>

      {/* 2 — ANOMALY SCORE */}
      <KpiCard label="ANOMALY SCORE">
        <span className="font-mono text-2xl font-bold text-text-base">
          {anomalyScore != null ? anomalyScore.toFixed(2) : '--'}
        </span>
        <div className="w-full h-1.5 rounded-full bg-bg-border overflow-hidden mt-1">
          {anomalyPct != null && (
            <div
              className={`h-full rounded-full transition-all duration-500 ${anomalyBarColor}`}
              style={{ width: `${anomalyPct}%` }}
            />
          )}
        </div>
        <span className="font-mono text-[10px] text-text-muted">
          {anomalyPct != null ? `${anomalyPct}%` : '-- %'}
        </span>
      </KpiCard>

      {/* 3 — FAULT */}
      <KpiCard label="FAULT">
        <span className={`font-mono text-sm font-semibold leading-tight ${
          faultActive ? 'text-status-critical' : 'text-status-healthy'
        }`}>
          {faultTypeLabel}
        </span>
        <div className="flex items-center gap-1 mt-0.5">
          <span className="font-mono text-xs text-text-muted">CONF:</span>
          <span className={`font-mono text-xs ${faultActive ? 'text-status-critical' : 'text-text-muted'}`}>
            {faultConf}%
          </span>
        </div>
      </KpiCard>

      {/* 4 — RUL */}
      <KpiCard label="RUL">
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-2xl font-bold text-text-base">{rulMinutes}</span>
          <span className="font-mono text-xs text-text-muted">min</span>
        </div>
        {rulStatus
          ? <StatusBadge status={rulStatus} size="sm" />
          : <span className="text-text-muted font-mono text-xs">--</span>}
      </KpiCard>

      {/* 5 — MISSION */}
      <KpiCard label="MISSION">
        <span className="font-mono text-sm font-bold text-primary truncate">{missionDisplay}</span>
        <span className="font-mono text-xs text-text-muted truncate">{phaseDisplay}</span>
        {replayRunning && replayPct != null && (
          <div className="mt-1">
            <div className="w-full h-1 rounded-full bg-bg-border overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${replayPct}%` }}
              />
            </div>
            <span className="font-mono text-[10px] text-text-muted">{replayPct}% replay</span>
          </div>
        )}
      </KpiCard>

    </div>
  );
}
