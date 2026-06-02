'use client'

import { DataQuality } from '@/types'

interface Props {
  company: string
  dataQuality?: DataQuality
  extractionNotes?: string | null
  onOpenNarrative: () => void
  onNewAnalysis: () => void
}

export default function ExtractionTriage({
  company,
  dataQuality,
  extractionNotes,
  onOpenNarrative,
  onNewAnalysis,
}: Props) {
  const pages = dataQuality?.financial_pages ?? 0
  const total = dataQuality?.total_pages ?? 0
  const chars = dataQuality?.context_chars ?? 0
  const extractedFields = dataQuality?.extracted_fields_count ?? 0
  const usedVision = dataQuality?.extraction_mode === 'vision'
  const visionPages = dataQuality?.vision_pages ?? 0
  const likelyScanned = pages > 0 && chars < 800 && !usedVision
  const emptyExtraction = extractedFields === 0

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 20,
      padding: '40px 36px',
      maxWidth: 640,
      margin: '0 auto',
      boxShadow: '0 8px 32px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        width: 52,
        height: 52,
        borderRadius: 14,
        background: 'rgba(245,166,35,0.12)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        marginBottom: 20,
      }}>
        ◇
      </div>

      <h2 style={{
        fontFamily: 'Syne, sans-serif',
        fontSize: 22,
        fontWeight: 700,
        margin: '0 0 10px',
        color: 'var(--text1)',
        letterSpacing: '-0.3px',
      }}>
        Structured metrics could not be verified
      </h2>

      <p style={{
        fontSize: 14,
        lineHeight: 1.7,
        color: 'var(--text2)',
        margin: '0 0 20px',
        fontFamily: 'DM Sans, sans-serif',
      }}>
        FinSight isolated <strong>{pages}</strong> financial page{pages !== 1 ? 's' : ''} from{' '}
        <strong>{total || '?'}</strong> total in <strong>{company}</strong>, but no accounting ratios
        could be computed. This usually means figures were not mapped into the extraction schema
        (formatted numbers, missing line items, or a scanned image PDF without a text layer).
      </p>

      <ul style={{
        margin: '0 0 24px',
        paddingLeft: 20,
        fontSize: 13,
        lineHeight: 1.8,
        color: 'var(--text2)',
        fontFamily: 'DM Sans, sans-serif',
      }}>
        {usedVision && (
          <li>
            <strong>Vision mode ran</strong> ({visionPages} page image(s) sent to Gemini) but ratios still could
            not be computed. Try a higher-quality scan or a digital PDF export.
          </li>
        )}
        {likelyScanned && (
          <li>
            <strong>Likely scanned PDF:</strong> only {chars.toLocaleString()} characters of machine-readable
            text were found. Re-upload a digital PDF with selectable text, or rely on vision mode (restart backend).
          </li>
        )}
        {likelyScanned && !emptyExtraction && (
          <li>Some text was recovered, but layout may be poor for table extraction.</li>
        )}
        {!likelyScanned && emptyExtraction && (
          <li>
            Text was extracted ({chars.toLocaleString()} chars) but no numeric fields were mapped into the
            schema. Re-run analysis after restarting the backend (number normalization is now applied).
          </li>
        )}
        {!likelyScanned && !emptyExtraction && (
          <li>
            Gemini returned {extractedFields} line item(s), but not enough to compute ratios (missing
            revenue, assets, or liabilities). Check column labels match the current reporting year.
          </li>
        )}
        <li>Confirm the file includes consolidated balance sheet, income statement, and cash flow tables.</li>
        <li>Open <strong>Strategic Narrative</strong> for any text-based commentary that was still generated.</li>
      </ul>

      {extractionNotes && (
        <div style={{
          marginBottom: 24,
          padding: '14px 16px',
          borderRadius: 12,
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          fontSize: 12,
          lineHeight: 1.6,
          color: 'var(--text2)',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>
          <div style={{ color: 'var(--text3)', marginBottom: 6, fontSize: 10, letterSpacing: 0.5, textTransform: 'uppercase' }}>
            Extraction notes
          </div>
          {extractionNotes}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <button
          type="button"
          onClick={onOpenNarrative}
          style={{
            background: 'var(--accent)',
            color: '#0a0d12',
            border: 'none',
            borderRadius: 10,
            padding: '12px 20px',
            fontFamily: 'Syne, sans-serif',
            fontSize: 14,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Open Strategic Narrative →
        </button>
        <button
          type="button"
          onClick={onNewAnalysis}
          style={{
            background: 'transparent',
            color: 'var(--text2)',
            border: '1px solid var(--border2)',
            borderRadius: 10,
            padding: '12px 20px',
            fontFamily: 'DM Sans, sans-serif',
            fontSize: 13,
            cursor: 'pointer',
          }}
        >
          ← Upload different PDF
        </button>
      </div>
    </div>
  )
}
