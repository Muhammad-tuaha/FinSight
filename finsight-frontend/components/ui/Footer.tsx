// components/ui/Footer.tsx
'use client';

const LinkedInIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="#0A66C2" xmlns="http://www.w3.org/2000/svg" aria-label="LinkedIn">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.446-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
  </svg>
);

const WhatsAppIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="#25D366" xmlns="http://www.w3.org/2000/svg" aria-label="WhatsApp">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
  </svg>
);

const GmailIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-label="Gmail">
    <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 010 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" fill="#EA4335"/>
  </svg>
);

export default function Footer() {
  return (
    <footer style={{
      borderTop: '1px solid var(--border)',
      background: 'var(--surface)',
      padding: '36px 48px 28px',
      display: 'flex',
      flexDirection: 'column',
      gap: 28,
      flexShrink: 0,
      marginTop: 'auto',
    }}>

      {/* Main Row */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 40,
        flexWrap: 'wrap',
      }}>

        {/* Brand */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <img
            src="/finsight-logo.png"
            alt="FinSight"
            style={{ height: 42, width: 'auto', objectFit: 'contain', objectPosition: 'left center', display: 'block' }}
          />
          <div style={{
            fontSize: 12,
            color: 'var(--text3)',
            fontFamily: 'DM Sans, sans-serif',
            marginTop: 2,
            maxWidth: 270,
            lineHeight: 1.65,
          }}>
            AI-powered financial analysis platform for the Pakistan Stock Exchange.
          </div>
        </div>

        {/* Connect */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            fontSize: 9,
            letterSpacing: 2,
            textTransform: 'uppercase',
            color: 'var(--text3)',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
            Connect
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div style={{
              fontSize: 15,
              fontWeight: 600,
              color: 'var(--text1)',
              fontFamily: 'DM Sans, sans-serif',
            }}>
              Taha
            </div>
            <div style={{
              fontSize: 11,
              color: 'var(--text3)',
              fontFamily: 'IBM Plex Mono, monospace',
            }}>
              AI/ML &amp; Software Developer
            </div>
          </div>

          {/* Social Links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

            {/* LinkedIn */}
            <a
              href="https://www.linkedin.com/in/muhammad-taha-cs/"
              target="_blank"
              rel="noopener noreferrer"
              title="LinkedIn — Muhammad Taha"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                textDecoration: 'none',
                color: 'var(--text2)',
                fontFamily: 'DM Sans, sans-serif',
                fontSize: 13,
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = '#0A66C2')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text2)')}
            >
              <span style={{
                width: 32, height: 32,
                borderRadius: 8,
                background: 'rgba(10,102,194,0.1)',
                border: '1px solid rgba(10,102,194,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                transition: 'background 0.15s, border-color 0.15s',
              }}>
                <LinkedInIcon />
              </span>
              Muhammad Taha
            </a>

            {/* WhatsApp */}
            <a
              href="https://wa.me/923105288105"
              target="_blank"
              rel="noopener noreferrer"
              title="WhatsApp — 03105288105"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                textDecoration: 'none',
                color: 'var(--text2)',
                fontFamily: 'DM Sans, sans-serif',
                fontSize: 13,
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = '#25D366')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text2)')}
            >
              <span style={{
                width: 32, height: 32,
                borderRadius: 8,
                background: 'rgba(37,211,102,0.1)',
                border: '1px solid rgba(37,211,102,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <WhatsAppIcon />
              </span>
              03105288105
            </a>

            {/* Gmail */}
            <a
              href="mailto:tahasoomro10@gmail.com"
              title="Email — tahasoomro10@gmail.com"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                textDecoration: 'none',
                color: 'var(--text2)',
                fontFamily: 'DM Sans, sans-serif',
                fontSize: 13,
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = '#EA4335')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text2)')}
            >
              <span style={{
                width: 32, height: 32,
                borderRadius: 8,
                background: 'rgba(234,67,53,0.1)',
                border: '1px solid rgba(234,67,53,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <GmailIcon />
              </span>
              tahasoomro10@gmail.com
            </a>
          </div>
        </div>

        {/* CTA Card */}
        <div style={{
          background: 'rgba(0,229,160,0.05)',
          border: '1px solid rgba(0,229,160,0.18)',
          borderRadius: 14,
          padding: '20px 22px',
          maxWidth: 230,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          <div style={{
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text1)',
            fontFamily: 'DM Sans, sans-serif',
          }}>
            Interested in FinSight?
          </div>
          <div style={{
            fontSize: 12,
            color: 'var(--text3)',
            fontFamily: 'DM Sans, sans-serif',
            lineHeight: 1.65,
          }}>
            Contact Taha for source-code access, collaboration, or job opportunities.
          </div>
          <a
            href="mailto:tahasoomro10@gmail.com"
            style={{
              marginTop: 2,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 11,
              fontFamily: 'IBM Plex Mono, monospace',
              color: 'var(--accent)',
              textDecoration: 'none',
              letterSpacing: 0.5,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.65')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Get in touch →
          </a>
        </div>
      </div>

      {/* Bottom Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 18,
        borderTop: '1px solid var(--border)',
        flexWrap: 'wrap',
        gap: 8,
      }}>
        <div style={{
          fontSize: 10,
          color: 'var(--text3)',
          fontFamily: 'IBM Plex Mono, monospace',
          letterSpacing: 0.5,
        }}>
          © 2026 FinSight. All rights reserved.
        </div>

      </div>
    </footer>
  );
}
