'use client'

import { useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { analyzeDocument, validateDocument, PSX_SECTORS, ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

const LOADING_STEPS = [
  ['Parsing PDF...', 'PyMuPDF + pdfplumber → financial pages & tables'],
  ['Extracting figures...', 'Gemini 2.5 → current & prior period schema'],
  ['Computing ratios...', 'Liquidity, profitability, leverage, efficiency'],
  ['Scanning risks...', 'Threshold rules + YoY checks'],
  ['Building narrative...', 'Summary generator → analyst commentary'],
]

export default function UploadPage() {
  const router = useRouter()
  const { setAnalysis } = useStore()
  const { user, token, signInWithGoogle } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [sector, setSector] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [slowWarning, setSlowWarning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validateMsg, setValidateMsg] = useState<string | null>(null)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [showSignInModal, setShowSignInModal] = useState(false)
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [isSuccess, setIsSuccess] = useState(false)
  const [wasSlowRefState, setWasSlowRefState] = useState(false)


  // ── Drag & Drop ──────────────────────────────────────────────────────────────
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setIsDragging(false), [])

  const runValidation = useCallback(async (f: File) => {
    setValidateMsg('Checking PDF structure…')
    try {
      const v = await validateDocument(f)
      if (v.valid) {
        const pages = (v as { financial_pages?: number }).financial_pages
        setValidateMsg(
          v.message || (pages != null ? `OK — ${pages} financial page(s) detected` : 'PDF structure looks valid'),
        )
      } else {
        setValidateMsg(v.message || 'PDF may not contain readable financial statements')
      }
    } catch {
      // Backend unreachable — don't block the user, just clear the validation hint
      setValidateMsg('Server unavailable — validation skipped, you can still proceed')
    }
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped?.type === 'application/pdf') {
      setFile(dropped)
      setError(null)
      runValidation(dropped)
    } else {
      setError('Only PDF files are accepted.')
    }
  }, [runValidation])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setError(null)
      runValidation(f)
    }
  }

  // ── Submit ───────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!user) {
      setShowSignInModal(true)
      return
    }
    if (!file) return setError('Please select a PDF file.')
    if (!companyName.trim()) return setError('Please enter the company name.')
    if (!sector) return setError('Please select a PSX sector.')

    setError(null)
    setIsLoading(true)
    setLoadingStep(0)
    setSlowWarning(false)
    setIsSuccess(false)
    setWasSlowRefState(false)

    // After 10s of total loading time, enable slow warning text
    if (slowTimerRef.current) clearTimeout(slowTimerRef.current)
    slowTimerRef.current = setTimeout(() => {
      setSlowWarning(true)
      setWasSlowRefState(true)
    }, 10000)

    const stepInterval = setInterval(() => {
      setLoadingStep(prev => Math.min(prev + 1, LOADING_STEPS.length - 1))
    }, 3500)

    try {
      const result = await analyzeDocument(file, companyName.trim(), sector, token)
      if (slowTimerRef.current) clearTimeout(slowTimerRef.current)
      clearInterval(stepInterval)
      setLoadingStep(LOADING_STEPS.length - 1)
      setIsSuccess(true)

      // Short delay to show the "Thanks for your patience!" message on screen
      setTimeout(() => {
        setAnalysis(result, companyName.trim(), sector, wasSlowRefState || slowWarning)
        router.push('/results')
      }, 1400)
    } catch (err: unknown) {
      if (slowTimerRef.current) clearTimeout(slowTimerRef.current)
      clearInterval(stepInterval)
      setIsLoading(false)
      setSlowWarning(false)
      setIsSuccess(false)

      if (err instanceof ApiError && (err.status === 403 || err.code === 'LIMIT_REACHED')) {
        setShowUpgradeModal(true)
        setError(null)
      } else {
        const msg = err instanceof Error ? err.message : 'Analysis failed'
        setError(msg)
      }
    }
  }

  // ── Loading screen ───────────────────────────────────────────────────────────
  if (isLoading) {
    const currentStepTitle = isSuccess
      ? 'Analysis Complete!'
      : (slowWarning && loadingStep === LOADING_STEPS.length - 1)
        ? 'Building Narrative (High Traffic Mode)...'
        : LOADING_STEPS[loadingStep][0]

    const currentStepSub = isSuccess
      ? '🎉 Thanks for your patience! Generating final report view...'
      : (slowWarning && loadingStep === LOADING_STEPS.length - 1)
        ? 'Processing complex pages with AI. Our free model might take 3–4 minutes under heavy load — feel free to switch tabs!'
        : LOADING_STEPS[loadingStep][1]

    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20 }} className="centered-screen">
        <div style={{
          width: 56, height: 56,
          border: '2px solid var(--border2)',
          borderTopColor: isSuccess ? 'var(--accent)' : slowWarning ? '#f5a623' : 'var(--accent)',
          borderRadius: '50%',
        }} className="animate-spin-slow" />
        <div style={{ textAlign: 'center', maxWidth: 440, padding: '0 16px' }}>
          <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 14, color: isSuccess ? 'var(--accent)' : 'var(--text1)', fontWeight: 600 }}>
            {currentStepTitle}
          </div>
          <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: 'var(--text2)', marginTop: 8, lineHeight: 1.6 }}>
            {currentStepSub}
          </div>
          <div style={{ marginTop: 24, display: 'flex', gap: 6, justifyContent: 'center' }}>
            {LOADING_STEPS.map((_, i) => (
              <div key={i} style={{
                width: i <= loadingStep ? 20 : 6,
                height: 4,
                borderRadius: 2,
                background: isSuccess ? 'var(--accent)' : i <= loadingStep ? (slowWarning ? '#f5a623' : 'var(--accent)') : 'var(--surface3)',
                transition: 'all 0.3s',
              }} />
            ))}
          </div>

          {/* Success banner */}
          {isSuccess && (
            <div style={{
              marginTop: 20,
              background: 'rgba(0,229,160,0.1)',
              border: '1px solid rgba(0,229,160,0.3)',
              borderRadius: 10,
              padding: '12px 16px',
              fontSize: 12,
              color: 'var(--accent)',
              fontFamily: 'IBM Plex Mono, monospace',
              lineHeight: 1.6,
              textAlign: 'center',
            }}>
              🎉 Thanks for your patience! All statements processed cleanly without any error.
            </div>
          )}

          {/* Slow-warning — appears after 10s */}
          {slowWarning && !isSuccess && (
            <div style={{
              marginTop: 20,
              background: 'rgba(245,166,35,0.08)',
              border: '1px solid rgba(245,166,35,0.25)',
              borderRadius: 10,
              padding: '12px 16px',
              fontSize: 12,
              color: '#f5a623',
              fontFamily: 'IBM Plex Mono, monospace',
              lineHeight: 1.6,
              textAlign: 'center',
            }}>
              ⏳ Please wait, too many requests right now! Our free LLM model might take some time (3–4 minutes), so chill — you can switch tabs while waiting!
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Upload form ──────────────────────────────────────────────────────────────
  return (
    <div style={{ flex: 1, padding: 24 }} className="page-pad">
      <div style={{ maxWidth: 680, margin: '0 auto' }}>

        {/* Guest Sign-In Banner */}
        {!user && (
          <div style={{
            background: 'rgba(77,159,255,0.08)',
            border: '1px solid rgba(77,159,255,0.25)',
            borderRadius: 14,
            padding: '14px 20px',
            marginBottom: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}>
            <div style={{ fontSize: 13, color: 'var(--text1)', fontFamily: 'DM Sans, sans-serif' }}>
              🎁 <strong>Free Trial:</strong> Sign in to get<strong> 2 free document analyses</strong>.
            </div>
            <button
              onClick={() => signInWithGoogle().catch(() => { })}
              style={{
                background: 'rgba(77,159,255,0.1)',
                border: '1px solid rgba(77,159,255,0.3)',
                borderRadius: 10,
                padding: '8px 14px',
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--blue)',
                cursor: 'pointer',
                fontFamily: 'DM Sans, sans-serif',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              Sign in with Google
            </button>
          </div>
        )}

        {/* Page header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontSize: 26, fontWeight: 700, letterSpacing: '-0.5px', margin: 0 }}>
            New Analysis
          </h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontSize: 13 }}>
            Upload a PSX annual report PDF. The pipeline extracts, analyses, and scores it automatically.
          </p>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => !file && fileInputRef.current?.click()}
          style={{
            border: `1.5px dashed ${isDragging ? 'var(--accent)' : 'var(--border2)'}`,
            borderRadius: 16,
            padding: '48px 32px',
            textAlign: 'center',
            cursor: file ? 'default' : 'pointer',
            background: isDragging ? 'rgba(0,229,160,0.04)' : 'var(--surface)',
            transition: 'all 0.2s',
          }}
        >
          {file ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, textAlign: 'left', maxWidth: 400, margin: '0 auto' }}>
              <div style={{ fontSize: 32, color: 'var(--accent)' }}>⬛</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: 14 }}>{file.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', marginTop: 2 }}>
                  {(file.size / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); setFile(null) }}
                style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 18, padding: 4 }}
              >
                ✕
              </button>
            </div>
          ) : (
            <>
              <div style={{ fontSize: 38, color: 'var(--text3)', marginBottom: 14 }}>↑</div>
              <div style={{ fontFamily: 'Syne, sans-serif', fontSize: 17, fontWeight: 600, marginBottom: 6 }}>
                Drop your annual report here
              </div>
              <div style={{ color: 'var(--text2)', fontSize: 13 }}>
                Drag & drop a PDF, or{' '}
                <span style={{ color: 'var(--accent)', textDecoration: 'underline', textUnderlineOffset: 3, cursor: 'pointer' }}>
                  browse files
                </span>
              </div>
            </>
          )}
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={onFileChange} style={{ display: 'none' }} />
        </div>

        {/* Form fields */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 20 }} className="form-grid">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace' }}>
              Company Name
            </label>
            <input
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              placeholder="e.g. Engro Corporation"
              style={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '10px 14px',
                color: 'var(--text1)',
                fontFamily: 'DM Sans, sans-serif',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace' }}>
              PSX Sector
            </label>
            <select
              value={sector}
              onChange={e => setSector(e.target.value)}
              style={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '10px 14px',
                color: sector ? 'var(--text1)' : 'var(--text3)',
                fontFamily: 'DM Sans, sans-serif',
                fontSize: 13,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="">— Select sector —</option>
              {PSX_SECTORS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        {validateMsg && !error && (
          <div style={{
            marginTop: 16,
            background: 'rgba(0,229,160,0.06)',
            border: '1px solid rgba(0,229,160,0.2)',
            borderRadius: 10,
            padding: '10px 14px',
            fontSize: 12,
            color: 'var(--accent)',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
            ✓ {validateMsg}
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            marginTop: 16,
            background: 'rgba(255,77,77,0.08)',
            border: '1px solid rgba(255,77,77,0.2)',
            borderRadius: 10,
            padding: '10px 14px',
            fontSize: 12,
            color: 'var(--danger)',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
            ✕ {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!file || !companyName || !sector}
          style={{
            marginTop: 24,
            width: '100%',
            background: (!file || !companyName || !sector) ? 'var(--surface3)' : 'var(--accent)',
            color: (!file || !companyName || !sector) ? 'var(--text3)' : '#0a0d12',
            border: 'none',
            borderRadius: 10,
            padding: 14,
            fontFamily: 'Syne, sans-serif',
            fontSize: 15,
            fontWeight: 700,
            cursor: (!file || !companyName || !sector) ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            transition: 'all 0.2s',
          }}
        >
          ⚡ Run Financial Analysis
        </button>
      </div>

      {/* Upgrade / Waitlist Modal on 403 Limit Reached */}
      {showUpgradeModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 100,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
        }}>
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 20,
            padding: 32,
            maxWidth: 480,
            width: '100%',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>⚡</div>
            <h2 style={{ fontFamily: 'Syne, sans-serif', fontSize: 22, fontWeight: 700, margin: '0 0 8px 0', color: 'var(--text1)' }}>
              Free Tier Limit Reached
            </h2>
            <p style={{ color: 'var(--text2)', fontSize: 13, lineHeight: 1.6, margin: '0 0 20px 0', fontFamily: 'DM Sans, sans-serif' }}>
              You have completed your <strong>2 free institutional document analyses</strong>. To process additional PSX disclosures, join the Pro waitlist or request expanded quota.
            </p>

            <div style={{
              background: 'rgba(245,166,35,0.08)',
              border: '1px solid rgba(245,166,35,0.25)',
              borderRadius: 12,
              padding: '10px 16px',
              fontSize: 12,
              color: 'var(--amber)',
              fontFamily: 'IBM Plex Mono, monospace',
              marginBottom: 24,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span>PLAN: FREE</span> · <span>2 / 2 REPORTS USED</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                onClick={() => {
                  alert('🎉 You have been registered on the FinSight Pro waitlist! We will notify you when additional quotas open.')
                  setShowUpgradeModal(false)
                }}
                style={{
                  background: 'var(--accent)',
                  color: '#0a0d12',
                  border: 'none',
                  borderRadius: 10,
                  padding: 14,
                  fontFamily: 'Syne, sans-serif',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Join Pro Waitlist / Request Quota
              </button>

              <button
                onClick={() => setShowUpgradeModal(false)}
                style={{
                  background: 'transparent',
                  color: 'var(--text3)',
                  border: 'none',
                  padding: 10,
                  fontSize: 13,
                  cursor: 'pointer',
                  fontFamily: 'DM Sans, sans-serif',
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Guest Sign-In Modal Prompt */}
      {showSignInModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 100,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 15,
        }}>
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 20,
            padding: 32,
            maxWidth: 460,
            width: '100%',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 40, marginBottom: 19 }}>🎁</div>
            <h2 style={{ fontFamily: 'dm sans, sans-serif', fontSize: 22, fontWeight: 700, margin: '0 0 8px 0', color: 'var(--text1)' }}>
              Sign In to Start Free Trial
            </h2>
            <p style={{ color: 'var(--text2)', fontSize: 13, lineHeight: 1.6, margin: '0 0 20px 0', fontFamily: 'DM Sans, sans-serif' }}>
              Please sign in to get <strong>2 free document analyses</strong>
            </p>

            <button
              onClick={async () => {
                try {
                  await signInWithGoogle()
                  setShowSignInModal(false)
                } catch {
                  // Sign-in cancelled or failed
                }
              }}
              style={{
                width: '100%',
                background: 'var(--accent)',
                color: '#0a0d12',
                border: 'none',
                borderRadius: 10,
                padding: 14,
                fontFamily: 'dm sans, sans-serif',
                fontSize: 15,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                transition: 'all 0.2s',
              }}
            >
              Sign In with Google
            </button>

            <button
              onClick={() => setShowSignInModal(false)}
              style={{
                background: 'transparent',
                color: 'var(--text3)',
                border: 'none',
                padding: 10,
                marginTop: 10,
                fontSize: 13,
                cursor: 'pointer',
                fontFamily: 'DM Sans, sans-serif',
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
