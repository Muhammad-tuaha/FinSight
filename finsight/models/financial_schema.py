"""
FinSight — Financial Data Schema
Pydantic models representing the JSON data contract shared across all pipeline layers.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class IncomeStatement(BaseModel):
    """Extracted income statement figures (PKR thousands unless noted)."""
    revenue: Optional[float] = Field(None, description="Net revenue / turnover — operating sales revenue ONLY. Exclude other income and associates' profit.")
    cost_of_goods_sold: Optional[float] = Field(None, description="Cost of sales / COGS")
    gross_profit: Optional[float] = Field(None, description="Gross profit")
    other_income: Optional[float] = Field(None, description="Other income / non-operating income — separate from revenue")
    share_of_profit_associates: Optional[float] = Field(None, description="Share of profit from associates / equity-method income — separate from revenue")
    operating_expenses: Optional[float] = Field(None, description="Total operating / distribution + admin expenses")
    ebitda: Optional[float] = Field(None, description="EBITDA if disclosed, else computed")
    depreciation_amortization: Optional[float] = Field(None, description="D&A charges")
    ebit: Optional[float] = Field(None, description="Earnings before interest and tax")
    finance_costs: Optional[float] = Field(None, description="Interest / finance costs")
    profit_before_tax: Optional[float] = Field(None, description="PBT")
    taxation: Optional[float] = Field(None, description="Tax expense")
    profit_after_tax: Optional[float] = Field(None, description="PAT / net profit")
    eps: Optional[float] = Field(None, description="Earnings per share (PKR)")


class BalanceSheet(BaseModel):
    """Extracted balance sheet figures."""
    # Assets
    cash_and_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    trade_receivables: Optional[float] = None
    inventory: Optional[float] = None
    other_current_assets: Optional[float] = None
    total_current_assets: Optional[float] = None
    property_plant_equipment: Optional[float] = None
    intangible_assets: Optional[float] = None
    long_term_investments: Optional[float] = None
    total_non_current_assets: Optional[float] = None
    total_assets: Optional[float] = None

    # Liabilities — financial debt separated from operating liabilities
    short_term_borrowings: Optional[float] = Field(None, description="Bank borrowings, short-term loans — interest-bearing ONLY")
    trade_payables: Optional[float] = None
    other_current_liabilities: Optional[float] = None
    current_portion_long_term_debt: Optional[float] = Field(None, description="Current portion of long-term FINANCIAL debt — loans/bonds only, NOT deposits or trade payables")
    total_current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = Field(None, description="Long-term FINANCIAL debt only — bank loans, bonds, lease liabilities. Member/broker security deposits are NOT financial debt.")
    long_term_deposits: Optional[float] = Field(None, description="Security deposits from members/brokers — operating liability, NOT financial debt")
    deferred_liabilities: Optional[float] = None
    total_non_current_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None

    # Equity
    share_capital: Optional[float] = None
    reserves_surplus: Optional[float] = None
    total_equity: Optional[float] = None


class CashFlowStatement(BaseModel):
    """Extracted cash flow statement figures."""
    cfo: Optional[float] = Field(None, description="Cash from operating activities")
    cfi: Optional[float] = Field(None, description="Cash from investing activities")
    cff: Optional[float] = Field(None, description="Cash from financing activities")
    capex: Optional[float] = Field(None, description="Capital expenditure (usually inside CFI)")
    net_change_in_cash: Optional[float] = None
    free_cash_flow: Optional[float] = Field(None, description="CFO - Capex, computed if not disclosed")


class FinancialPeriod(BaseModel):
    """All financial statements for one reporting period."""
    company_name: str = ""
    reporting_period: str = ""           # e.g. "FY2023", "FY2024"
    period_end_date: Optional[str] = None  # ISO date string
    currency: str = "PKR"
    unit: str = "thousands"         # thousands / millions — as disclosed
    income_statement: IncomeStatement = IncomeStatement()
    balance_sheet: BalanceSheet = BalanceSheet()
    cash_flow: CashFlowStatement = CashFlowStatement()


class ExtractedFinancials(BaseModel):
    """Top-level extraction result: current year + prior year for YoY comparison."""
    company_name: str
    sector: Optional[str] = None
    source_file: str = ""
    extraction_date: str = ""
    current_period: FinancialPeriod
    prior_period: Optional[FinancialPeriod] = None
    extraction_confidence: Optional[float] = Field(
        None, ge=0, le=1,
        description="LLM confidence in numeric figure extraction 0–1"
    )
    entity_confidence: Optional[float] = Field(
        None, ge=0, le=1,
        description="LLM confidence in company name identification 0–1 (separate from numeric confidence)"
    )
    sector_confidence: Optional[float] = Field(
        None, ge=0, le=1,
        description="LLM confidence in sector classification 0–1 (separate from numeric confidence)"
    )
    extraction_notes: Optional[str] = Field(
        None, description="Warnings or caveats from extraction"
    )
