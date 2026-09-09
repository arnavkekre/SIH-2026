import React from 'react';

const STATUS_COLOR = {
  HEALTHY:  { stroke: '#22C55E', text: '#22C55E', glow: '0 0 12px #22C55E88' },
  WARNING:  { stroke: '#F59E0B', text: '#F59E0B', glow: '0 0 12px #F59E0B88' },
  DEGRADING:{ stroke: '#F97316', text: '#F97316', glow: '0 0 12px #F9731688' },
  CRITICAL: { stroke: '#EF4444', text: '#EF4444', glow: '0 0 12px #EF444488' },
};
const DEFAULT_COLOR = { stroke: '#8FA8BC', text: '#8FA8BC', glow: 'none' };

/** Convert polar angle (0 = top, clockwise) to SVG cartesian. */
function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Build SVG arc path for given angular range. */
function arcPath(cx, cy, r, startAngle, endAngle) {
  const s = polarToCartesian(cx, cy, r, startAngle);
  const e = polarToCartesian(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} 1 ${e.x} ${e.y}`;
}

/**
 * HealthGauge — 240° SVG arc gauge.
 * @param {number|null} score   0–100
 * @param {string}      status  HEALTHY|WARNING|DEGRADING|CRITICAL
 * @param {number}      size    px, default 120
 */
export default function HealthGauge({ score = null, status = 'HEALTHY', size = 120 }) {
  const START = 150;   // degrees from top
  const SWEEP = 240;   // total arc degrees

  const cx = size / 2;
  const cy = size / 2;
  const r  = size * 0.38;
  const sw = size * 0.075;

  const colorCfg = STATUS_COLOR[status?.toUpperCase()] ?? DEFAULT_COLOR;

  const clampedScore = score != null ? Math.max(0, Math.min(100, score)) : 0;
  const fgEnd        = START + (clampedScore / 100) * SWEEP;
  const tipCoords    = score != null ? polarToCartesian(cx, cy, r, fgEnd) : null;

  const bgPath = arcPath(cx, cy, r, START, START + SWEEP);
  const fgPath = score != null ? arcPath(cx, cy, r, START, fgEnd) : null;

  return (
    <div className="flex flex-col items-center" style={{ width: size, height: size + 16 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <path d={bgPath} fill="none" stroke="#20384D" strokeWidth={sw} strokeLinecap="round" />

        {/* Foreground arc */}
        {fgPath && (
          <path
            d={fgPath}
            fill="none"
            stroke={colorCfg.stroke}
            strokeWidth={sw}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(${colorCfg.glow})` }}
          />
        )}

        {/* Arc tip glow dot */}
        {tipCoords && score != null && (
          <circle
            cx={tipCoords.x}
            cy={tipCoords.y}
            r={sw * 0.6}
            fill={colorCfg.stroke}
            style={{ filter: `drop-shadow(${colorCfg.glow})` }}
          />
        )}

        {/* Center score number */}
        <text
          x={cx} y={cy - size * 0.04}
          textAnchor="middle" dominantBaseline="middle"
          fill={score != null ? colorCfg.text : '#8FA8BC'}
          fontSize={size * 0.24} fontFamily="monospace" fontWeight="bold"
        >
          {score != null ? Math.round(score) : '--'}
        </text>

        {/* Status label */}
        <text
          x={cx} y={cy + size * 0.22}
          textAnchor="middle" dominantBaseline="middle"
          fill={score != null ? colorCfg.text : '#8FA8BC'}
          fontSize={size * 0.09} fontFamily="monospace" letterSpacing="0.08em"
        >
          {score != null ? (status ?? 'UNKNOWN') : 'NO DATA'}
        </text>
      </svg>
    </div>
  );
}
