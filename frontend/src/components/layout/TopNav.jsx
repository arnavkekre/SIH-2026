import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Triangle, Radio } from 'lucide-react';
import useAeroStore from '../../store/useAeroStore.js';
import ConnectionIndicator from '../ui/ConnectionIndicator.jsx';

const NAV_LINKS = [
  { to: '/',            label: 'HOME'        },
  { to: '/dashboard',   label: 'DASHBOARD'   },
  { to: '/diagnostics', label: 'DIAGNOSTICS' },
  { to: '/missions',    label: 'MISSIONS'    },
  { to: '/analytics',   label: 'ANALYTICS'  },
  { to: '/about',       label: 'ABOUT'       },
];

/**
 * TopNav — fixed top navigation bar for AeroTwin.
 * Height: h-14, z-50, bg-bg-panel / border-bg-border.
 */
export default function TopNav() {
  const navigate = useNavigate();
  const engineId = useAeroStore((s) => s.engineId);

  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const timeStr = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
  const dateStr = now
    .toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
    .toUpperCase();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center justify-between px-4 bg-bg-panel border-b border-bg-border">

      {/* ── LEFT: Logo ── */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Triangle size={20} className="text-primary fill-primary/20" strokeWidth={1.5} />
        <span className="font-mono font-bold text-base tracking-widest select-none">
          <span className="text-text-base">AERO</span>
          <span className="text-primary">TWIN</span>
        </span>
      </div>

      {/* ── CENTER: Nav links ── */}
      <ul className="hidden md:flex items-center gap-0.5 list-none m-0 p-0">
        {NAV_LINKS.map(({ to, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                [
                  'px-3 py-1 font-mono text-xs uppercase tracking-wider transition-colors duration-150 inline-block',
                  isActive
                    ? 'text-primary border-b border-primary'
                    : 'text-text-muted hover:text-text-base',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* ── RIGHT: Status cluster ── */}
      <div className="flex items-center gap-3 flex-shrink-0">

        {/* Connection indicator */}
        <ConnectionIndicator />

        {/* Simulation badge */}
        <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded border border-primary/40 text-primary font-mono text-xs uppercase tracking-wider">
          <Radio size={11} strokeWidth={2} />
          <span>Simulation</span>
        </div>

        {/* Engine ID */}
        <div className="hidden lg:flex items-center gap-1 font-mono text-xs">
          <span className="text-text-muted uppercase tracking-wider">ENG:</span>
          <span className="text-text-base">{engineId ?? '--'}</span>
        </div>

        {/* Live clock */}
        <div className="hidden lg:flex flex-col items-end font-mono leading-none">
          <span className="text-text-base text-xs">{timeStr}</span>
          <span className="text-text-muted text-[10px] tracking-wide mt-0.5">{dateStr}</span>
        </div>

        {/* Launch CTA */}
        <button
          onClick={() => navigate('/dashboard')}
          className="aero-btn-filled text-xs px-3 py-1.5 hidden sm:block"
        >
          LAUNCH DASHBOARD
        </button>
      </div>
    </nav>
  );
}
