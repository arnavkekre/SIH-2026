import React from 'react';

const STATUS_CONFIG = {
  HEALTHY: {
    dot: 'bg-status-healthy animate-pulse',
    text: 'text-status-healthy',
    label: 'HEALTHY',
  },
  WARNING: {
    dot: 'bg-status-warning',
    text: 'text-status-warning',
    label: 'WARNING',
  },
  DEGRADING: {
    dot: 'bg-status-degrading',
    text: 'text-status-degrading',
    label: 'DEGRADING',
  },
  CRITICAL: {
    dot: 'bg-status-critical animate-pulse',
    text: 'text-status-critical glow-red',
    label: 'CRITICAL',
  },
  ONLINE: {
    dot: 'bg-status-healthy animate-pulse',
    text: 'text-status-healthy',
    label: 'ONLINE',
  },
  OFFLINE: {
    dot: 'bg-status-critical',
    text: 'text-status-critical',
    label: 'OFFLINE',
  },
  CONNECTING: {
    dot: 'bg-text-muted animate-pulse',
    text: 'text-text-muted animate-pulse',
    label: 'CONNECTING',
  },
};

const SIZE_CONFIG = {
  sm: { pill: 'px-1.5 py-0.5 text-xs gap-1',  dot: 'w-1.5 h-1.5' },
  md: { pill: 'px-2   py-1   text-xs gap-1.5', dot: 'w-2   h-2'   },
  lg: { pill: 'px-3   py-1.5 text-sm gap-2',   dot: 'w-2.5 h-2.5' },
};

/**
 * StatusBadge — reusable status pill with colored dot and label.
 * @param {string}        status  HEALTHY|WARNING|DEGRADING|CRITICAL|ONLINE|OFFLINE|CONNECTING
 * @param {'sm'|'md'|'lg'} size
 */
export default function StatusBadge({ status = 'HEALTHY', size = 'md' }) {
  const config = STATUS_CONFIG[status?.toUpperCase()] ?? {
    dot: 'bg-text-muted',
    text: 'text-text-muted',
    label: status ?? 'UNKNOWN',
  };
  const sz = SIZE_CONFIG[size] ?? SIZE_CONFIG.md;

  return (
    <span
      className={`inline-flex items-center font-mono uppercase tracking-wider rounded-full border border-bg-border bg-bg-card ${sz.pill}`}
    >
      <span className={`rounded-full flex-shrink-0 ${sz.dot} ${config.dot}`} />
      <span className={config.text}>{config.label}</span>
    </span>
  );
}
