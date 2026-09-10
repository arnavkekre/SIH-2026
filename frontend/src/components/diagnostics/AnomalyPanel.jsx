import React, { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, ReferenceLine,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import useAeroStore from '../../store/useAeroStore.js';

function getLevel(score) {
  if (score == null)  return { label: 'UNKNOWN',  color: '#8FA8BC', textClass: 'text-text-muted',       barClass: 'bg-text-muted'       };
  if (score < 0.3)    return { label: 'NORMAL',   color: '#22C55E', textClass: 'text-status-healthy',   barClass: 'bg-status-healthy'   };
  if (score < 0.6)    return { label: 'ELEVATED', color: '#F59E0B', textClass: 'text-status-warning',   barClass: 'bg-status-warning'   };
  if (score < 0.8)    return { label: 'HIGH',     color: '#F97316', textClass: 'text-status-degrading', barClass: 'bg-status-degrading' };
  return               { label: 'CRITICAL', color: '#EF4444', textClass: 'text-status-critical',  barClass: 'bg-status-critical'  };
}

/**
 * AnomalyPanel — anomaly score display + history chart.
 */
export default function AnomalyPanel() {
  const anomalyScore   = useAeroStore((s) => s.anomalyScore);
  const anomalyHistory = useAeroStore((s) => s.anomalyHistory ?? []);

  const level = getLevel(anomalyScore);

  const chartData = useMemo(
    () => anomalyHistory.map((entry, i) => ({
      t: entry.timestampS ?? i,
      v: entry.anomalyScore ?? entry.v ?? 0,
    })),
    [anomalyHistory],
  );

  return (
    <div className="aero-panel flex flex-col gap-3">

      {/* Header */}
      <span className="aero-title tracking-widest">ANOMALY DETECTION</span>

      {anomalyScore == null ? (
        <div className="flex items-center justify-center py-6">
          <span className="font-mono text-sm text-text-muted animate-pulse">Awaiting data...</span>
        </div>
      ) : (
        <>
          {/* Large score */}
          <div className="flex items-baseline gap-2">
            <span className={`font-mono text-4xl font-bold ${level.textClass}`}>
              {anomalyScore.toFixed(2)}
            </span>
            <span className="font-mono text-xs text-text-muted">/ 1.00</span>
          </div>

          {/* Fill bar */}
          <div className="w-full h-2 rounded-full bg-bg-border overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${level.barClass}`}
              style={{ width: `${(anomalyScore * 100).toFixed(1)}%` }}
            />
          </div>

          {/* Status label */}
          <div className="flex items-center gap-2">
            <span className={`font-mono text-sm font-semibold uppercase tracking-wider ${level.textClass}`}>
              {level.label}
            </span>
            <span className="font-mono text-xs text-text-muted">
              ({(anomalyScore * 100).toFixed(1)}%)
            </span>
          </div>
        </>
      )}

      {/* History area chart */}
      {chartData.length > 1 && (
        <div className="w-full" style={{ height: 80 }}>
          <ResponsiveContainer width="100%" height={80}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
              <defs>
                <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={level.color} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={level.color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <XAxis dataKey="t" hide />
              <YAxis
                domain={[0, 1]}
                tickCount={3}
                tick={{ fill: '#8FA8BC', fontSize: 9, fontFamily: 'monospace' }}
              />
              <ReferenceLine y={0.3} stroke="#F59E0B" strokeDasharray="4 3" strokeWidth={1} />
              <Tooltip
                contentStyle={{
                  background: '#0A1320', border: '1px solid #1A2E46',
                  borderRadius: 4, fontFamily: 'monospace', fontSize: 10, color: '#E2F1FF',
                }}
                formatter={(v) => [v != null ? v.toFixed(3) : '--', 'Score']}
                labelFormatter={() => ''}
              />
              <Area
                type="monotone"
                dataKey="v"
                stroke={level.color}
                strokeWidth={1.5}
                fill="url(#anomalyGrad)"
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
