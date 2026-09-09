import React, { useState, useEffect } from 'react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

/** Returns Tailwind color class for a value based on threshold proximity. */
function getValueColor(value, expected, thresholds) {
  if (value == null || !thresholds) return 'text-text-base';
  const dev = Math.abs(value - (expected ?? value));
  if (dev >= thresholds.crit) return 'text-status-critical';
  if (dev >= thresholds.warn) return 'text-status-warning';
  return 'text-text-base';
}

/** Returns Tailwind classes for residual badge. */
function getResidualClasses(residual, thresholds) {
  if (residual == null || !thresholds) return 'text-text-muted border-bg-border';
  const abs = Math.abs(residual);
  if (abs >= thresholds.crit)
    return 'text-status-critical bg-status-critical/10 border-status-critical/30';
  if (abs >= thresholds.warn)
    return 'text-status-warning bg-status-warning/10 border-status-warning/30';
  return 'text-status-healthy bg-status-healthy/10 border-status-healthy/30';
}

/**
 * TelemetryCard — parameter card with mini sparkline.
 *
 * @param {string}                label
 * @param {number|null}           value
 * @param {string}                unit
 * @param {number|null}           expected
 * @param {number|null}           residual
 * @param {number[]}              historyData   array of raw values
 * @param {{ warn: number, crit: number }} thresholds
 * @param {number}                precision     decimal places, default 1
 * @param {React.ComponentType}   icon          lucide-react icon
 */
export default function TelemetryCard({
  label,
  value,
  unit,
  expected,
  residual,
  historyData = [],
  thresholds,
  precision = 1,
  icon: Icon,
}) {
  const [updatedAt, setUpdatedAt]   = useState(Date.now());
  const [secondsAgo, setSecondsAgo] = useState(0);

  // Reset freshness timer when value changes
  useEffect(() => {
    if (value != null) {
      setUpdatedAt(Date.now());
      setSecondsAgo(0);
    }
  }, [value]);

  useEffect(() => {
    const id = setInterval(
      () => setSecondsAgo(Math.floor((Date.now() - updatedAt) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, [updatedAt]);

  const valueColor    = getValueColor(value, expected, thresholds);
  const residualClass = getResidualClasses(residual, thresholds);

  const residualSign  = residual != null ? (residual >= 0 ? '+' : '') : '';
  const residualLabel = residual != null ? `${residualSign}${residual.toFixed(precision)}` : null;

  const chartData = historyData.map((v, i) => ({ i, v }));

  return (
    <div className="aero-card flex flex-col gap-2 p-3">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {Icon && <Icon size={13} className="text-text-muted flex-shrink-0" strokeWidth={1.8} />}
          <span className="aero-title text-[10px]">{label}</span>
        </div>
        {residualLabel && (
          <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${residualClass}`}>
            {residualLabel}
          </span>
        )}
      </div>

      {/* Main value */}
      <div className="flex items-baseline gap-1.5">
        <span className={`font-mono text-2xl font-bold ${valueColor}`}>
          {value != null ? value.toFixed(precision) : '--'}
        </span>
        {unit && <span className="font-mono text-xs text-text-muted">{unit}</span>}
      </div>

      {/* Expected annotation */}
      {expected != null && (
        <span className="font-mono text-[10px] text-text-muted">
          EXP: {expected.toFixed(precision)}{unit ? ` ${unit}` : ''}
        </span>
      )}

      {/* Sparkline */}
      {chartData.length > 1 && (
        <div className="w-full" style={{ height: 60 }}>
          <ResponsiveContainer width="100%" height={60}>
            <LineChart data={chartData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke="#35C9FF"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Tooltip
                contentStyle={{
                  background: '#0D1B2A',
                  border: '1px solid #20384D',
                  borderRadius: 4,
                  fontSize: 10,
                  fontFamily: 'monospace',
                  color: '#EAF4FF',
                }}
                formatter={(v) => [v != null ? v.toFixed(precision) : '--', label]}
                labelFormatter={() => ''}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Freshness */}
      <div className="font-mono text-[10px] text-text-muted/60">
        {value != null
          ? secondsAgo === 0 ? 'Updated just now' : `Updated ${secondsAgo}s ago`
          : 'No data'}
      </div>
    </div>
  );
}
