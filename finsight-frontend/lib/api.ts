import { AnalysisResult, FinancialRatios, RedFlag, BackendNarrativeReports } from '@/types'

const FLASK_BASE = process.env.NEXT_PUBLIC_FLASK_URL || 'http://127.0.0.1:5000/api/v1';

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${FLASK_BASE}/health`, { cache: 'no-store' });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}

/** Normalize legacy nested `{ result: { ... } }` responses. */
function normalizeAnalysisPayload(raw: Record<string, unknown>): AnalysisResult {
  const nested = raw.result as Record<string, unknown> | undefined
  if (nested && typeof nested === 'object') {
    return {
      status: (raw.status as string) || 'success',
      metadata: (raw.metadata as AnalysisResult['metadata']) || {
        company_name: '',
        sector: '',
        reporting_period: '',
        extraction_confidence: null,
        extraction_date: '',
        notes: null,
      },
      data_quality: raw.data_quality as AnalysisResult['data_quality'],
      risk_profile: (nested.risk_profile as AnalysisResult['risk_profile']) || {
        high_severity_count: 0,
        medium_severity_count: 0,
        low_severity_count: 0,
        key_concerns: [],
      },
      narrative_reports: (nested.narrative_reports as AnalysisResult['narrative_reports']) || {
        executive_summary: '',
        liquidity_commentary: '',
        profitability_commentary: '',
        leverage_commentary: '',
        cash_flow_commentary: '',
        yoy_commentary: '',
        full_formatted_text: '',
      },
      ratios: (nested.ratios as FinancialRatios) || {},
      ratios_prior: nested.ratios_prior as FinancialRatios | null | undefined,
      red_flags: (nested.red_flags as RedFlag[]) || [],
      summary: nested.summary as string | undefined,
    }
  }
  return raw as unknown as AnalysisResult
}

export async function analyzeDocument(
  file: File,
  companyName: string,
  sector: string
): Promise<AnalysisResult> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('company_name', companyName)
  formData.append('sector', sector)

  const res = await fetch(`${FLASK_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown server error' }))
    throw new Error(err.error || `Server returned ${res.status}`)
  }

  const raw = await res.json()
  return normalizeAnalysisPayload(raw)
}

export async function downloadReport(
  companyName: string,
  sector: string,
  ratios: FinancialRatios,
  redFlags: RedFlag[],
  narrativeReports?: BackendNarrativeReports,
  summary?: string
): Promise<Blob> {
  const res = await fetch(`${FLASK_BASE}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_name: companyName,
      sector,
      ratios,
      red_flags: redFlags,
      narrative_reports: narrativeReports,
      summary,
    }),
  })

  if (!res.ok) {
    throw new Error('Report generation failed — check backend logs')
  }

  return res.blob()
}

export async function validateDocument(file: File): Promise<{ valid: boolean; message?: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${FLASK_BASE}/validate`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) return { valid: false, message: 'Validation failed' }
  return res.json()
}

export function countComputedRatios(ratios?: FinancialRatios): number {
  if (!ratios) return 0
  return Object.values(ratios).filter(v => typeof v === 'number' && !Number.isNaN(v)).length
}

export type RatioStatus = 'good' | 'warn' | 'danger'

export function getRatioStatus(key: string, value: number): RatioStatus {
  const rules: Record<string, (v: number) => RatioStatus> = {
    current_ratio:       v => v >= 2 ? 'good' : v >= 1 ? 'warn' : 'danger',
    quick_ratio:         v => v >= 1 ? 'good' : v >= 0.7 ? 'warn' : 'danger',
    cash_ratio:          v => v >= 0.5 ? 'good' : v >= 0.2 ? 'warn' : 'danger',
    gross_margin:        v => v >= 30 ? 'good' : v >= 15 ? 'warn' : 'danger',
    net_margin:          v => v >= 10 ? 'good' : v >= 4 ? 'warn' : 'danger',
    roa:                 v => v >= 6 ? 'good' : v >= 2 ? 'warn' : 'danger',
    roe:                 v => v >= 15 ? 'good' : v >= 8 ? 'warn' : 'danger',
    debt_to_equity:      v => v <= 1 ? 'good' : v <= 2 ? 'warn' : 'danger',
    interest_coverage:   v => v >= 3 ? 'good' : v >= 1.5 ? 'warn' : 'danger',
    asset_turnover:      v => v >= 1 ? 'good' : v >= 0.5 ? 'warn' : 'danger',
    inventory_turnover:  v => v >= 6 ? 'good' : v >= 3 ? 'warn' : 'danger',
    receivables_turnover:v => v >= 8 ? 'good' : v >= 5 ? 'warn' : 'danger',
  }
  return rules[key]?.(value) ?? 'warn'
}

/** Bar width 0–100 from metric value and status (not arbitrary divisors). */
export function ratioStrengthPct(key: string, value: number): number {
  const status = getRatioStatus(key, value)
  if (status === 'good') return Math.min(100, 70 + Math.min(30, Math.abs(value) * 2))
  if (status === 'warn') return 45
  return 22
}

export const RATIO_META: Record<string, { label: string; category: string; format: (v: number) => string }> = {
  current_ratio:        { label: 'Current Ratio',         category: 'Liquidity',      format: v => `${v.toFixed(2)}x` },
  quick_ratio:          { label: 'Quick Ratio',            category: 'Liquidity',      format: v => `${v.toFixed(2)}x` },
  cash_ratio:           { label: 'Cash Ratio',             category: 'Liquidity',      format: v => `${v.toFixed(2)}x` },
  gross_margin:         { label: 'Gross Margin',           category: 'Profitability',  format: v => `${v.toFixed(1)}%` },
  net_margin:           { label: 'Net Margin',             category: 'Profitability',  format: v => `${v.toFixed(1)}%` },
  roa:                  { label: 'Return on Assets',       category: 'Profitability',  format: v => `${v.toFixed(1)}%` },
  roe:                  { label: 'Return on Equity',       category: 'Profitability',  format: v => `${v.toFixed(1)}%` },
  debt_to_equity:       { label: 'Debt / Equity',          category: 'Leverage',       format: v => `${v.toFixed(2)}x` },
  interest_coverage:    { label: 'Interest Coverage',      category: 'Leverage',       format: v => `${v.toFixed(1)}x` },
  asset_turnover:       { label: 'Asset Turnover',         category: 'Efficiency',     format: v => `${v.toFixed(2)}x` },
  inventory_turnover:   { label: 'Inventory Turnover',     category: 'Efficiency',     format: v => `${v.toFixed(1)}x` },
  receivables_turnover: { label: 'Receivables Turnover',   category: 'Efficiency',     format: v => `${v.toFixed(1)}x` },
}

export const PSX_SECTORS = [
  { value: 'fertilizer',  label: 'Fertilizer' },
  { value: 'cement',      label: 'Cement' },
  { value: 'banking',     label: 'Banking' },
  { value: 'textile',     label: 'Textile' },
  { value: 'oil_gas',     label: 'Oil & Gas' },
  { value: 'power',       label: 'Power Generation' },
  { value: 'pharma',      label: 'Pharmaceuticals' },
  { value: 'steel',       label: 'Steel & Metals' },
  { value: 'chemicals',   label: 'Chemicals' },
  { value: 'fmcg',        label: 'FMCG / Consumer Goods' },
  { value: 'auto',        label: 'Automobile' },
  { value: 'it',          label: 'IT & Technology' },
  { value: 'insurance',   label: 'Insurance' },
  { value: 'other',       label: 'Other' },
]
