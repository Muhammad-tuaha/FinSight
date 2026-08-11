// components/ui/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { checkBackendHealth } from '@/lib/api';

export default function Sidebar() {
  const pathname = usePathname();
  const { result } = useStore();
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    // Initial health ping check configuration
    checkBackendHealth().then(ok => setBackendStatus(ok ? 'online' : 'offline'));

    // Interval sweep tracking pipeline health state transformations every 30 seconds
    const interval = setInterval(async () => {
      const ok = await checkBackendHealth();
      setBackendStatus(ok ? 'online' : 'offline');
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const statusColor = backendStatus === 'online' ? '#00e5a0' : backendStatus === 'offline' ? '#ff4d4d' : '#f5a623';
  const statusLabel = backendStatus === 'online' ? 'Server Running' : backendStatus === 'offline' ? 'Server offline' : 'checking...';

  return (
    <aside style={{
      width: isCollapsed ? 52 : 220,
      minWidth: isCollapsed ? 52 : 220,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1), min-width 0.25s cubic-bezier(0.4,0,0.2,1)',
      overflow: 'hidden',
      flexShrink: 0,
    }}>

      {/* Header */}
      <div style={{
        padding: isCollapsed ? '16px 0' : '20px 20px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: isCollapsed ? 'center' : 'space-between',
        gap: 8,
        minHeight: 64,
        flexShrink: 0,
      }}>
        {/* Brand logo — hidden when collapsed */}
        {!isCollapsed && (
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <img
              src="/finsight-logo.png"
              alt="FinSight"
              style={{ height: 36, width: 'auto', display: 'block', objectFit: 'contain' }}
            />
          </div>
        )}

        {/* Small logo icon shown when collapsed */}
        {isCollapsed && (
          <img
            src="/finsight-logo.png"
            alt="FinSight"
            title="FinSight"
            style={{ width: 34, height: 34, objectFit: 'contain', objectPosition: 'left center' }}
          />
        )}

        {/* Toggle button */}
        <button
          onClick={() => setIsCollapsed(prev => !prev)}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            width: 28,
            height: 28,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: 'var(--text3)',
            flexShrink: 0,
            transition: 'background 0.15s, color 0.15s, border-color 0.15s',
            marginTop: isCollapsed ? 28 : 0,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(0,229,160,0.12)';
            e.currentTarget.style.color = 'var(--accent)';
            e.currentTarget.style.borderColor = 'rgba(0,229,160,0.3)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
            e.currentTarget.style.color = 'var(--text3)';
            e.currentTarget.style.borderColor = 'var(--border)';
          }}
        >
          {/* Chevron SVG — flips direction */}
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            style={{ transition: 'transform 0.25s', transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)' }}
          >
            <path d="M4.5 2L8.5 6L4.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Navigation — expanded */}
      {!isCollapsed && (
        <nav style={{ padding: '12px 10px', flex: 1 }}>
          <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '8px 10px 4px' }}>
            Workspace
          </div>

          <NavItem href="/upload" active={pathname === '/upload'} icon="▲">
            New Analysis
          </NavItem>

          {/* Disabled logic binds cleanly to the metadata object footprint verification state */}
          <NavItem
            href="/results"
            active={pathname === '/results'}
            icon="◈"
            disabled={!result || !result.metadata}
          >
            Results
          </NavItem>

          <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '16px 10px 4px' }}>
            System
          </div>

          <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 6, height: 6,
              borderRadius: '50%',
              background: statusColor,
              flexShrink: 0,
            }} className={backendStatus === 'checking' ? 'animate-pulse-dot' : ''} />
            {statusLabel}
          </div>
        </nav>
      )}

      {/* Navigation — collapsed (icon-only) */}
      {isCollapsed && (
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0', gap: 6 }}>
          <Link
            href="/upload"
            title="New Analysis"
            style={{
              width: 34, height: 34,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 9,
              color: pathname === '/upload' ? 'var(--accent)' : 'var(--text3)',
              background: pathname === '/upload' ? 'rgba(0,229,160,0.1)' : 'transparent',
              textDecoration: 'none',
              fontSize: 13,
              transition: 'all 0.15s',
            }}
          >
            ▲
          </Link>

          <div
            title={!result || !result.metadata ? 'Results (no data yet)' : 'Results'}
            style={{
              width: 34, height: 34,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 9,
              color: pathname === '/results' ? 'var(--accent)' : 'var(--text3)',
              background: pathname === '/results' ? 'rgba(0,229,160,0.1)' : 'transparent',
              fontSize: 13,
              opacity: !result || !result.metadata ? 0.35 : 1,
              cursor: !result || !result.metadata ? 'not-allowed' : 'default',
            }}
          >
            ◈
          </div>

          {/* Status indicator */}
          <div
            title={statusLabel}
            style={{
              width: 7, height: 7,
              borderRadius: '50%',
              background: statusColor,
              marginTop: 8,
            }}
            className={backendStatus === 'checking' ? 'animate-pulse-dot' : ''}
          />
        </nav>
      )}

      {/* Footer Benchmark Tracker Indicator Status Space */}
      <div style={{ padding: isCollapsed ? '10px 0' : '12px 10px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: isCollapsed ? 'center' : 'flex-start' }}>
        {!isCollapsed ? (
          <div style={{
            background: 'rgba(0,229,160,0.08)',
            border: '1px solid rgba(0,229,160,0.2)',
            borderRadius: 10,
            padding: '8px 12px',
            fontSize: 11,
            color: 'var(--accent)',
            fontFamily: 'IBM Plex Mono, monospace',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            width: '100%',
          }}>
            <div style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%' }} className="animate-pulse-dot" />
            PSX Market Data
          </div>
        ) : (
          <div
            title="PSX Market Data"
            style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%' }}
            className="animate-pulse-dot"
          />
        )}
      </div>
    </aside>
  );
}

function NavItem({
  href,
  active,
  icon,
  disabled,
  children,
}: {
  href: string;
  active: boolean;
  icon: string;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  const style: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '8px 10px',
    borderRadius: 10,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: active ? 'var(--accent)' : disabled ? 'var(--text3)' : 'var(--text2)',
    background: active ? 'rgba(0,229,160,0.1)' : 'transparent',
    fontSize: 13,
    marginBottom: 2,
    textDecoration: 'none',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.15s',
    fontFamily: 'DM Sans, sans-serif',
  };

  if (disabled) return (
    <div style={style}>
      <span style={{ fontSize: 12 }}>{icon}</span>
      {children}
    </div>
  );

  return (
    <Link href={href} style={style}>
      <span style={{ fontSize: 12 }}>{icon}</span>
      {children}
    </Link>
  );
}