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
  const statusLabel = backendStatus === 'online' ? 'backend online' : backendStatus === 'offline' ? 'backend offline' : 'checking...';

  return (
    <aside style={{
      width: 220,
      minWidth: 220,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Brand Space Header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          fontFamily: 'Syne, sans-serif',
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: '-0.5px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <div style={{
            width: 8, height: 8,
            background: 'var(--accent)',
            borderRadius: '50%',
            boxShadow: '0 0 10px var(--accent)',
          }} className="animate-pulse-dot" />
          FinSight
        </div>
        <div style={{
          fontSize: 10,
          color: 'var(--text3)',
          fontFamily: 'IBM Plex Mono, monospace',
          marginTop: 2,
          letterSpacing: 1,
          textTransform: 'uppercase',
        }}>
          PSX Financial Intelligence
        </div>
      </div>

      {/* Internal Core Navigation Links */}
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

      {/* Footer Benchmark Tracker Indicator Status Space */}
      <div style={{ padding: '12px 10px', borderTop: '1px solid var(--border)' }}>
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
        }}>
          <div style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%' }} className="animate-pulse-dot" />
          PSX Market Data
        </div>
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