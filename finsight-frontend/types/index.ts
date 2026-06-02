// types/index.ts

export type FlagPriority = 'HIGH' | 'MEDIUM' | 'LOW';

export interface BackendMetadata {
  company_name: string;
  sector: string;
  reporting_period: string;
  extraction_confidence: number | null;
  extraction_date: string;
  notes: string | null;
}

export interface DataQuality {
  financial_pages: number;
  total_pages: number;
  context_chars: number;
  statements_complete: boolean;
  ratios_computed_count: number;
  has_prior_period: boolean;
  insufficient_data: boolean;
  extracted_fields_count?: number;
  extraction_mode?: 'text' | 'vision';
  vision_pages?: number;
}

export interface BackendRiskProfile {
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  key_concerns: string[];
}

export interface BackendNarrativeReports {
  executive_summary: string;
  liquidity_commentary: string;
  profitability_commentary: string;
  leverage_commentary: string;
  cash_flow_commentary: string;
  yoy_commentary: string;
  full_formatted_text: string;
}

export interface AnalysisResult {
  status: string;
  metadata: BackendMetadata;
  data_quality?: DataQuality;
  risk_profile: BackendRiskProfile;
  narrative_reports: BackendNarrativeReports;
  ratios: FinancialRatios;
  ratios_prior?: FinancialRatios | null;
  red_flags: RedFlag[];
  summary?: string;
}

export interface UploadFormState {
  file: File | null;
  companyName: string;
  sector: string;
}

export interface AnalysisContext {
  result: AnalysisResult | null;
  meta: { company: string; sector: string } | null;
  isLoading: boolean;
  error: string | null;
}

export interface FinancialRatios {
  current_ratio?: number;
  quick_ratio?: number;
  cash_ratio?: number;
  gross_margin?: number;
  net_margin?: number;
  roa?: number;
  roe?: number;
  debt_to_equity?: number;
  interest_coverage?: number;
  asset_turnover?: number;
  inventory_turnover?: number;
  receivables_turnover?: number;
  ebitda_margin?: number;
  debt_to_assets?: number;
  equity_multiplier?: number;
  cfo_to_net_income?: number;
  free_cash_flow?: number;
}

export interface RedFlag {
  priority: FlagPriority;
  title: string;
  description: string;
  category?: string;
}
