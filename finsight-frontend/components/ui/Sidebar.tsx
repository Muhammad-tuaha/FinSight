// components/ui/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { checkBackendHealth } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

// ── Hamburger icon ────────────────────────────────────────────────────────────
const HamburgerIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </svg>
);

// ── Close icon ────────────────────────────────────────────────────────────────
const CloseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M2 2l12 12M14 2L2 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
  </svg>
);

// ── Chevron icon ──────────────────────────────────────────────────────────────
const ChevronRight = ({ flipped = false }: { flipped?: boolean }) => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
    style={{ transition: 'transform 0.25s', transform: flipped ? 'rotate(180deg)' : 'rotate(0deg)' }}
  >
    <path d="M4.5 2L8.5 6L4.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export default function Sidebar() {
  const pathname = usePathname();
  const { result } = useStore();
  const { user, signInWithGoogle, logout } = useAuth();
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [isCollapsed, setIsCollapsed] = useState(false); // desktop only
  const [isMobile, setIsMobile] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Detect mobile breakpoint
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) setIsDrawerOpen(false);
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Close drawer on route change
  useEffect(() => { setIsDrawerOpen(false); }, [pathname]);

  // Health check
  useEffect(() => {
    checkBackendHealth().then(ok => setBackendStatus(ok ? 'online' : 'offline'));
    const interval = setInterval(async () => {
      const ok = await checkBackendHealth();
      setBackendStatus(ok ? 'online' : 'offline');
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const statusColor  = backendStatus === 'online' ? '#00e5a0' : backendStatus === 'offline' ? '#ff4d4d' : '#f5a623';
  const statusLabel  = backendStatus === 'online' ? 'Server Running' : backendStatus === 'offline' ? 'Server offline' : 'checking...';

  // ── Shared nav content (used in both mobile drawer and desktop sidebar) ─────
  const navContent = (
    <nav style={{ padding: '12px 10px', flex: 1 }}>
      <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '8px 10px 4px' }}>
        Workspace
      </div>

      <NavItem href="/upload" active={pathname === '/upload'} icon="▲">
        New Analysis
      </NavItem>

      <NavItem href="/results" active={pathname === '/results'} icon="◈" disabled={!result || !result.metadata}>
        Results
      </NavItem>

      <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '16px 10px 4px' }}>
        System
      </div>

      <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusColor, flexShrink: 0 }}
          className={backendStatus === 'checking' ? 'animate-pulse-dot' : ''} />
        {statusLabel}
      </div>
    </nav>
  );

  // ── User profile & auth block ────────────────────────────────────────────────
  const userProfileBlock = (
    <div style={{ padding: '12px 10px', borderTop: '1px solid var(--border)' }}>
      {user ? (
        <div style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 12, padding: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            {user.photoURL ? (
              <img src={user.photoURL} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
            ) : (
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12 }}>
                {user.email?.[0].toUpperCase() || 'U'}
              </div>
            )}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.displayName || user.email?.split('@')[0] || 'User'}
              </div>
              <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace' }}>
                Free Trial · 2 Reports
              </div>
            </div>
          </div>
          <button
            onClick={() => logout()}
            style={{
              width: '100%', background: 'transparent', border: '1px solid var(--border)',
              borderRadius: 8, padding: '5px 8px', fontSize: 11, color: 'var(--text2)',
              cursor: 'pointer', fontFamily: 'DM Sans, sans-serif'
            }}
          >
            Sign Out
          </button>
        </div>
      ) : (
        <button
          onClick={() => signInWithGoogle().catch(() => {})}
          style={{
            width: '100%', background: 'rgba(77,159,255,0.1)', border: '1px solid rgba(77,159,255,0.3)',
            borderRadius: 10, padding: '9px 12px', fontSize: 12, fontWeight: 600,
            color: 'var(--blue)', cursor: 'pointer', display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: 8, fontFamily: 'DM Sans, sans-serif'
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          Sign in with Google
        </button>
      )}
    </div>
  );

  // ── Footer badge ─────────────────────────────────────────────────────────────
  const footerBadge = (
    <div style={{ padding: '12px 10px', borderTop: '1px solid var(--border)' }}>
      <div style={{
        background: 'rgba(0,229,160,0.08)', border: '1px solid rgba(0,229,160,0.2)',
        borderRadius: 10, padding: '8px 12px', fontSize: 11, color: 'var(--accent)',
        fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%' }} className="animate-pulse-dot" />
        PSX Market Data
      </div>
    </div>
  );

  // ────────────────────────────────────────────────────────────────────────────
  // MOBILE LAYOUT — top navbar + slide-in drawer
  // ────────────────────────────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <>
        {/* Fixed top navbar */}
        <nav style={{
          position: 'fixed', top: 0, left: 0, right: 0,
          height: 'var(--mobile-nav-h)',
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
          zIndex: 30,
        }}>
          <img src="/finsight-logo.png" alt="FinSight" style={{ height: 32, objectFit: 'contain' }} />

          {/* Inline nav links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Link href="/upload" style={{
              padding: '7px 12px', borderRadius: 8, fontSize: 13,
              color: pathname === '/upload' ? 'var(--accent)' : 'var(--text2)',
              background: pathname === '/upload' ? 'rgba(0,229,160,0.1)' : 'transparent',
              textDecoration: 'none', fontFamily: 'DM Sans, sans-serif',
            }}>Upload</Link>
            <Link href="/results" style={{
              padding: '7px 12px', borderRadius: 8, fontSize: 13,
              color: pathname === '/results' ? 'var(--accent)' : (!result || !result.metadata ? 'var(--text3)' : 'var(--text2)'),
              background: pathname === '/results' ? 'rgba(0,229,160,0.1)' : 'transparent',
              textDecoration: 'none', fontFamily: 'DM Sans, sans-serif',
              opacity: !result || !result.metadata ? 0.4 : 1,
              pointerEvents: !result || !result.metadata ? 'none' : 'auto',
            }}>Results</Link>
          </div>

          {/* Hamburger / Close toggle */}
          <button
            onClick={() => setIsDrawerOpen(prev => !prev)}
            aria-label={isDrawerOpen ? 'Close menu' : 'Open menu'}
            style={{
              background: isDrawerOpen ? 'rgba(0,229,160,0.1)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${isDrawerOpen ? 'rgba(0,229,160,0.3)' : 'var(--border)'}`,
              borderRadius: 9, width: 38, height: 38,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
              color: isDrawerOpen ? 'var(--accent)' : 'var(--text2)',
              transition: 'all 0.15s',
            }}
          >
            {isDrawerOpen ? <CloseIcon /> : <HamburgerIcon />}
          </button>
        </nav>

        {/* Backdrop — dim the page content when dropdown is open */}
        <div
          onClick={() => setIsDrawerOpen(false)}
          style={{
            position: 'fixed', inset: 0,
            top: 'var(--mobile-nav-h)',
            background: 'rgba(0,0,0,0.45)',
            zIndex: 28,
            backdropFilter: 'blur(2px)',
            opacity: isDrawerOpen ? 1 : 0,
            pointerEvents: isDrawerOpen ? 'auto' : 'none',
            transition: 'opacity 0.2s',
          }}
        />

        {/* Dropdown panel — slides down from below the navbar */}
        <div style={{
          position: 'fixed',
          top: 'var(--mobile-nav-h)',
          left: 0, right: 0,
          zIndex: 29,
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
          maxHeight: isDrawerOpen ? '420px' : '0px',
          overflow: 'hidden',
          transition: 'max-height 0.3s cubic-bezier(0.4,0,0.2,1)',
        }}>
          <div style={{ padding: '12px 10px' }}>

            {/* Section label */}
            <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '4px 10px 8px' }}>
              Workspace
            </div>

            <NavItem href="/upload" active={pathname === '/upload'} icon="▲">
              New Analysis
            </NavItem>
            <NavItem href="/results" active={pathname === '/results'} icon="◈" disabled={!result || !result.metadata}>
              Results
            </NavItem>

            {/* Divider */}
            <div style={{ height: 1, background: 'var(--border)', margin: '10px 10px' }} />

            {/* System / Status */}
            <div style={{ fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', padding: '0 10px 6px' }}>
              System
            </div>
            <div style={{ padding: '6px 10px', fontSize: 12, color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusColor, flexShrink: 0 }}
                className={backendStatus === 'checking' ? 'animate-pulse-dot' : ''} />
              {statusLabel}
            </div>

            {/* PSX badge */}
            <div style={{ margin: '10px 10px 12px' }}>
              <div style={{
                background: 'rgba(0,229,160,0.08)', border: '1px solid rgba(0,229,160,0.2)',
                borderRadius: 10, padding: '8px 12px', fontSize: 11, color: 'var(--accent)',
                fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <div style={{ width: 6, height: 6, background: 'var(--accent)', borderRadius: '50%' }} className="animate-pulse-dot" />
                PSX Market Data
              </div>
            </div>

          </div>
        </div>
      </>
    );
  }

  // ────────────────────────────────────────────────────────────────────────────
  // DESKTOP LAYOUT — collapsible sidebar
  // ────────────────────────────────────────────────────────────────────────────
  return (
    <>
      <aside style={{
        width: isCollapsed ? 0 : 220,
        minWidth: isCollapsed ? 0 : 220,
        background: 'var(--surface)',
        borderRight: isCollapsed ? 'none' : '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1), min-width 0.25s cubic-bezier(0.4,0,0.2,1)',
        overflow: 'hidden', flexShrink: 0,
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 20px 16px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          gap: 8, minHeight: 64, flexShrink: 0,
        }}>
          <div style={{ overflow: 'hidden', flex: 1 }}>
            <img src="/finsight-logo.png" alt="FinSight" style={{ height: 36, width: 'auto', display: 'block', objectFit: 'contain' }} />
          </div>

          {/* Collapse button */}
          <button
            onClick={() => setIsCollapsed(true)}
            title="Collapse sidebar"
            style={{
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)',
              borderRadius: 8, width: 28, height: 28,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: 'var(--text3)', flexShrink: 0,
              transition: 'background 0.15s, color 0.15s, border-color 0.15s',
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
            <ChevronRight flipped />
          </button>
        </div>

        {navContent}
        {userProfileBlock}
        {footerBadge}
      </aside>

      {/* Floating expand button when collapsed */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed(false)}
          title="Expand sidebar"
          style={{
            position: 'fixed', top: 20, left: 12, zIndex: 50,
            width: 36, height: 36, borderRadius: '50%',
            background: 'var(--surface)', border: '1px solid var(--border)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: 'var(--text3)',
            transition: 'background 0.15s, color 0.15s, box-shadow 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(0,229,160,0.15)';
            e.currentTarget.style.color = 'var(--accent)';
            e.currentTarget.style.borderColor = 'rgba(0,229,160,0.4)';
            e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,229,160,0.2)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'var(--surface)';
            e.currentTarget.style.color = 'var(--text3)';
            e.currentTarget.style.borderColor = 'var(--border)';
            e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.4)';
          }}
        >
          <ChevronRight />
        </button>
      )}
    </>
  );
}

// ── NavItem ───────────────────────────────────────────────────────────────────
function NavItem({ href, active, icon, disabled, children }: {
  href: string; active: boolean; icon: string; disabled?: boolean; children: React.ReactNode;
}) {
  const style: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '8px 10px', borderRadius: 10,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: active ? 'var(--accent)' : disabled ? 'var(--text3)' : 'var(--text2)',
    background: active ? 'rgba(0,229,160,0.1)' : 'transparent',
    fontSize: 13, marginBottom: 2, textDecoration: 'none',
    opacity: disabled ? 0.5 : 1, transition: 'all 0.15s',
    fontFamily: 'DM Sans, sans-serif',
  };
  if (disabled) return <div style={style}><span style={{ fontSize: 12 }}>{icon}</span>{children}</div>;
  return <Link href={href} style={style}><span style={{ fontSize: 12 }}>{icon}</span>{children}</Link>;
}