import React from 'react';
import { Wrench, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import useAeroStore from '../../store/useAeroStore.js';

const RESIDUAL_THRESHOLDS = {
  rpm:         { warn: 50,   crit: 150  },
  cht:         { warn: 10,   crit: 25   },
  egt:         { warn: 20,   crit: 50   },
  oilPressure: { warn: 20,   crit: 50   },
  oilTemp:     { warn: 5,    crit: 15   },
  fuelFlow:    { warn: 1,    crit: 3    },
  vibration:   { warn: 0.05, crit: 0.15 },
  injTiming:   { warn: 1,    crit: 3    },
};

const PARAM_LABELS = {
  rpm:         'RPM',
  cht:         'CHT',
  egt:         'EGT',
  oilPressure: 'Oil Pressure',
  oilTemp:     'Oil Temp',
  fuelFlow:    'Fuel Flow',
  vibration:   'Vibration',
  injTiming:   'Inj. Timing',
};

function formatFaultType(type) {
  if (!type || type === 'NORMAL') return null;
  return type.toLowerCase().split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function deriveAdvisory({ healthStatus, fault, anomalyScore, residuals }) {
  const evidence = [];

  if (residuals) {
    for (const [key, thr] of Object.entries(RESIDUAL_THRESHOLDS)) {
      const val = residuals[key];
      if (val == null) continue;
      const abs = Math.abs(val);
      const sign = val > 0 ? '+' : '';
      if (abs >= thr.crit)
        evidence.push(`${PARAM_LABELS[key]} residual critically deviated (${sign}${val.toFixed(2)})`);
      else if (abs >= thr.warn)
        evidence.push(`${PARAM_LABELS[key]} residual elevated (${sign}${val.toFixed(2)})`);
    }
  }

  const faultLabel = formatFaultType(fault?.type);
  if (fault?.active && faultLabel) {
    evidence.push(
      `Active fault: ${faultLabel} (conf ${fault?.confidence != null ? (fault.confidence * 100).toFixed(0) : '--'}%)`
    );
  }

  if (anomalyScore != null && anomalyScore >= 0.6)
    evidence.push(`Anomaly score elevated: ${anomalyScore.toFixed(3)}`);

  const isCritical =
    healthStatus === 'CRITICAL' ||
    (fault?.active && (fault?.severity ?? 0) > 0.7);

  const isWarning =
    healthStatus === 'WARNING' ||
    healthStatus === 'DEGRADING' ||
    (anomalyScore != null && anomalyScore >= 0.3) ||
    (fault?.active && !isCritical);

  if (isCritical) {
    return {
      severity: 'CRITICAL',
      action: 'IMMEDIATE INSPECTION REQUIRED',
      evidence: evidence.length ? evidence : ['Health status critical \u2014 multiple subsystems affected.'],
    };
  }
  if (isWarning) {
    return {
      severity: 'WARNING',
      action: 'MONITOR CLOSELY',
      evidence: evidence.length ? evidence : ['Parameters approaching alert thresholds.'],
    };
  }
  return {
    severity: 'NOMINAL',
    action: 'NOMINAL \u2014 No action required',
    evidence: evidence.length ? evidence : ['All parameters within expected bounds.'],
  };
}

const SEVERITY_STYLES = {
  CRITICAL: {
    badge: 'text-status-critical border-status-critical/40 bg-status-critical/10',
    icon:  <AlertTriangle size={14} className="text-status-critical" />,
    text:  'text-status-critical',
    dot:   'bg-status-critical',
  },
  WARNING: {
    badge: 'text-status-warning border-status-warning/40 bg-status-warning/10',
    icon:  <AlertTriangle size={14} className="text-status-warning" />,
    text:  'text-status-warning',
    dot:   'bg-status-warning',
  },
  NOMINAL: {
    badge: 'text-status-healthy border-status-healthy/40 bg-status-healthy/10',
    icon:  <CheckCircle2 size={14} className="text-status-healthy" />,
    text:  'text-status-healthy',
    dot:   'bg-status-healthy',
  },
};

/**
 * MaintenanceAdvisory — frontend-inferred maintenance guidance card.
 */
export default function MaintenanceAdvisory() {
  const healthStatus = useAeroStore((s) => s.healthStatus);
  const fault        = useAeroStore((s) => s.fault);
  const anomalyScore = useAeroStore((s) => s.anomalyScore);
  const residuals    = useAeroStore((s) => s.residuals);
  const backendRec   = useAeroStore((s) => s.maintenanceRecommendation);

  const derived  = deriveAdvisory({ healthStatus, fault, anomalyScore, residuals });
  const advisory = backendRec
    ? { ...derived, action: backendRec }
    : derived;

  const styles = SEVERITY_STYLES[advisory.severity] ?? SEVERITY_STYLES.NOMINAL;

  return (
    <div className="aero-panel flex flex-col gap-3">

      {/* Header */}
      <div className="flex items-center gap-2">
        <Wrench size={13} className="text-text-muted" strokeWidth={1.8} />
        <span className="aero-title tracking-widest">MAINTENANCE ADVISORY</span>
      </div>

      {/* Severity badge */}
      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${styles.badge}`}>
        {styles.icon}
        <span className={`font-mono text-sm font-bold uppercase tracking-wider ${styles.text}`}>
          {advisory.severity}
        </span>
      </div>

      {/* Recommended action */}
      <div className="font-mono text-sm text-text-base font-semibold leading-snug">
        {advisory.action}
      </div>

      {/* Evidence list */}
      {advisory.evidence.length > 0 && (
        <ul className="flex flex-col gap-1 list-none p-0 m-0">
          {advisory.evidence.map((item, i) => (
            <li key={i} className="flex items-start gap-1.5">
              <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${styles.dot}`} />
              <span className="font-mono text-xs text-text-muted">{item}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Disclaimer */}
      <div className="flex items-start gap-1.5 mt-1 pt-2 border-t border-bg-border">
        <Info size={10} className="text-text-muted flex-shrink-0 mt-0.5" />
        <p className="font-mono text-[10px] text-text-muted leading-relaxed m-0">
          Decision support only. Not autonomous control.
        </p>
      </div>
    </div>
  );
}
