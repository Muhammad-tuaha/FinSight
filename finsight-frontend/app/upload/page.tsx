'use client'

import { useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { analyzeDocument, validateDocument, PSX_SECTORS } from '@/lib/api'

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
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [sector, setSector] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [validateMsg, setValidateMsg] = useState<string | null>(null)

  // ── Drag & Drop ──────────────────────────────────────────────────────────────
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setIsDragging(false), [])

  const runValidation = useCallback(async (f: File) => {
    setValidateMsg('Checking PDF structure…')
    const v = await validateDocument(f)
    if (v.valid) {
      const pages = (v as { financial_pages?: number }).financial_pages
      setValidateMsg(
        v.message || (pages != null ? `OK — ${pages} financial page(s) detected` : 'PDF structure looks valid'),
      )
    } else {
      setValidateMsg(v.message || 'PDF may not contain readable financial statements')
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
    if (!file) return setError('Please select a PDF file.')
    if (!companyName.trim()) return setError('Please enter the company name.')
    if (!sector) return setError('Please select a PSX sector.')

    setError(null)
    setIsLoading(true)
    setLoadingStep(0)

    const stepInterval = setInterval(() => {
      setLoadingStep(prev => Math.min(prev + 1, LOADING_STEPS.length - 1))
    }, 3500)

    try {
      setLoadingStep(0)
      const result = await analyzeDocument(file, companyName.trim(), sector)
      setLoadingStep(LOADING_STEPS.length - 1)
      clearInterval(stepInterval)
      setAnalysis(result, companyName.trim(), sector)
      router.push('/results')
    } catch (err: unknown) {
      clearInterval(stepInterval)
      const msg = err instanceof Error ? err.message : 'Analysis failed'
      setError(msg)
      setIsLoading(false)
    }
  }

  // ── Loading screen ───────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20 }}>
        <div style={{
          width: 56, height: 56,
          border: '2px solid var(--border2)',
          borderTopColor: 'var(--accent)',
          borderRadius: '50%',
        }} className="animate-spin-slow" />
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 14, color: 'var(--text2)' }}>
            {LOADING_STEPS[loadingStep][0]}
          </div>
          <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, color: 'var(--text3)', marginTop: 6 }}>
            {LOADING_STEPS[loadingStep][1]}
          </div>
          <div style={{ marginTop: 24, display: 'flex', gap: 6, justifyContent: 'center' }}>
            {LOADING_STEPS.map((_, i) => (
              <div key={i} style={{
                width: i <= loadingStep ? 20 : 6,
                height: 4,
                borderRadius: 2,
                background: i <= loadingStep ? 'var(--accent)' : 'var(--surface3)',
                transition: 'all 0.3s',
              }} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Upload form ──────────────────────────────────────────────────────────────
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
      <div style={{ maxWidth: 680, margin: '0 auto' }}>

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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 20 }}>
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
    </div>
  )
}
