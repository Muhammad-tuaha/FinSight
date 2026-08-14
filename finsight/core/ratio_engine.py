"""
FinSight — Ratio Computation Engine
Computes all financial ratios from an extracted FinancialPeriod object.
Every division is guarded — zero denominators return None, never a 500.

Bug fixes applied:
  #2 — CR/QR thresholds aligned (done in thresholds.py)
  #3 — revenue is now strictly operating revenue; other_income and
        share_of_profit_associates are excluded from margin / turnover denominators
  #4 — total_debt uses only interest-bearing financial debt (short_term_borrowings +
        long_term_debt + current_portion_long_term_debt). long_term_deposits
        (member/broker security deposits) are NOT included.
  #6 — every ratio now carries a formula footnote in RATIO_FORMULAS for UI display
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sectors where customer deposits are a PRIMARY funding liability
# (should be included in leverage numerator for a complete picture)
# ---------------------------------------------------------------------------
_DEPOSIT_FUNDED_SECTORS = {
    "bank", "banking", "commercial bank", "dfi", "development finance",
    "nbfc", "microfinance", "investment bank",
}


# ---------------------------------------------------------------------------
# Methodology footnotes (Bug #6)
# ---------------------------------------------------------------------------
# Key → human-readable formula + notes shown in the UI tooltip / report footnote.

RATIO_FORMULAS: dict[str, str] = {
    "current_ratio":        "Current Assets ÷ Current Liabilities",
    "quick_ratio":          "(Current Assets − Inventory) ÷ Current Liabilities",
    "cash_ratio":           "Cash & Equivalents ÷ Current Liabilities",
    "gross_margin":         "Gross Profit ÷ Operating Revenue × 100  [Revenue = operating sales/fees only]",
    "net_margin":           "Net Profit After Tax ÷ Operating Revenue × 100  [Revenue excludes Other Income & Associates' share]",
    "ebitda_margin":        "EBITDA ÷ Operating Revenue × 100",
    "roa":                  "Net Profit After Tax ÷ Total Assets × 100",
    "roe":                  "Net Profit After Tax ÷ Total Equity × 100",
    "debt_to_equity":       "Financial Debt ÷ Total Equity  [Financial Debt = borrowings + bonds + lease liabilities only; member/broker deposits excluded]",
    "debt_to_assets":       "Financial Debt ÷ Total Assets  [Financial Debt = interest-bearing obligations only]",
    "interest_coverage":    "EBIT ÷ Finance Costs",
    "equity_multiplier":    "Total Assets ÷ Total Equity",
    "asset_turnover":       "Operating Revenue ÷ Total Assets  [Revenue = operating sales/fees only]",
    "inventory_turnover":   "Cost of Goods Sold ÷ Inventory",
    "receivables_turnover": "Operating Revenue ÷ Trade Receivables",
    "cfo_to_net_income":    "Operating Cash Flow ÷ Net Profit After Tax",
    "free_cash_flow":       "Operating Cash Flow − Capital Expenditure  (PKR value, not a ratio)",
}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ComputedRatios:
    # Liquidity
    current_ratio:        Optional[float] = None
    quick_ratio:          Optional[float] = None
    cash_ratio:           Optional[float] = None

    # Profitability
    gross_margin:         Optional[float] = None   # %
    net_margin:           Optional[float] = None   # %
    ebitda_margin:        Optional[float] = None   # %
    roa:                  Optional[float] = None   # %
    roe:                  Optional[float] = None   # %

    # Leverage / Solvency
    debt_to_equity:       Optional[float] = None
    debt_to_assets:       Optional[float] = None
    interest_coverage:    Optional[float] = None   # x
    equity_multiplier:    Optional[float] = None   # x

    # Efficiency
    asset_turnover:       Optional[float] = None   # x
    inventory_turnover:   Optional[float] = None   # x
    receivables_turnover: Optional[float] = None   # x

    # Cash flow
    cfo_to_net_income:    Optional[float] = None
    free_cash_flow:       Optional[float] = None   # raw PKR value

    def to_dict(self) -> dict:
        """Return only non-None values as a plain dict for JSON serialisation."""
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Safe arithmetic helpers
# ---------------------------------------------------------------------------

def _div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safe division — returns None if either operand is missing or denominator is zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safe percentage — returns None if either operand is missing or denominator is zero."""
    result = _div(numerator, denominator)
    if result is None:
        return None
    return round(result * 100, 4)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def statements_complete(period) -> bool:
    """True when balance sheet, income, and cash flow have minimum fields for ratios."""
    if period is None:
        return False
    bs = getattr(period, "balance_sheet", None)
    inc = getattr(period, "income_statement", None)
    cf = getattr(period, "cash_flow", None)
    if not bs or not inc or not cf:
        return False
    return (
        getattr(bs, "total_assets", None) is not None
        and getattr(bs, "total_current_liabilities", None) is not None
        and getattr(inc, "revenue", None) is not None
        and getattr(cf, "cfo", None) is not None
    )


def compute_ratios(period, sector: str | None = None) -> ComputedRatios:
    """
    Compute all supported financial ratios for a single FinancialPeriod.
    Returns a ComputedRatios dataclass. Never raises — all errors are logged.

    sector (optional): when provided, applies sector-conditional logic:
      - Revenue: always strictly operating revenue (Bug #3)
      - Financial debt: for deposit-funded sectors (banks/DFIs/NBFCs), long_term_deposits
        (customer deposits) are included in the leverage numerator since they are the
        primary funding base. For all other sectors they remain excluded (Bug #4).
    """
    ratios = ComputedRatios()

    if period is None:
        return ratios

    bs = getattr(period, 'balance_sheet', None)
    inc = getattr(period, 'income_statement', None)
    cf = getattr(period, 'cash_flow', None)

    if not bs or not inc or not cf:
        logger.warning("Incomplete statements passed down to ratio calculation matrix.")

    try:
        # ── Liquidity ────────────────────────────────────────────────────────
        ratios.current_ratio = _div(
            getattr(bs, 'total_current_assets', None),
            getattr(bs, 'total_current_liabilities', None),
        )

        total_curr_assets = getattr(bs, 'total_current_assets', None)
        total_curr_liab   = getattr(bs, 'total_current_liabilities', None)
        if total_curr_assets is not None and total_curr_liab is not None:
            inventory = getattr(bs, 'inventory', None) or 0.0
            quick_assets = total_curr_assets - inventory
            ratios.quick_ratio = _div(quick_assets, total_curr_liab)

        ratios.cash_ratio = _div(
            getattr(bs, 'cash_and_equivalents', None),
            total_curr_liab,
        )

        # ── Profitability ────────────────────────────────────────────────────
        # Bug #3: use strictly operating revenue, never blended with other_income
        operating_revenue = getattr(inc, 'revenue', None)

        ratios.gross_margin  = _pct(getattr(inc, 'gross_profit', None),     operating_revenue)
        ratios.net_margin    = _pct(getattr(inc, 'profit_after_tax', None),  operating_revenue)
        ratios.ebitda_margin = _pct(getattr(inc, 'ebitda', None),            operating_revenue)
        ratios.roa           = _pct(getattr(inc, 'profit_after_tax', None),  getattr(bs, 'total_assets', None))
        ratios.roe           = _pct(getattr(inc, 'profit_after_tax', None),  getattr(bs, 'total_equity', None))

        # ── Leverage / Solvency ──────────────────────────────────────────────
        # Bug #4 + sector-conditional: financial debt = interest-bearing obligations only.
        # Exception: for deposit-funded sectors (banks/DFIs/NBFCs), customer deposits
        # ARE the primary funding base and must be included for a meaningful D/E ratio.
        st_borrowings = getattr(bs, 'short_term_borrowings', None) or 0.0
        lt_debt       = getattr(bs, 'long_term_debt', None) or 0.0
        curr_portion  = getattr(bs, 'current_portion_long_term_debt', None) or 0.0
        lt_deposits   = getattr(bs, 'long_term_deposits', None) or 0.0

        sector_norm = (sector or "").strip().lower()
        is_deposit_funded = any(s in sector_norm for s in _DEPOSIT_FUNDED_SECTORS)

        if is_deposit_funded:
            # Banks/DFIs: include customer deposits in funding-liability numerator
            financial_debt = st_borrowings + lt_debt + curr_portion + lt_deposits
            logger.debug(
                f"Deposit-funded sector '{sector}': including long_term_deposits "
                f"({lt_deposits:,.0f}) in leverage numerator."
            )
        else:
            # All other sectors: security/member deposits are operating liabilities, excluded
            financial_debt = st_borrowings + lt_debt + curr_portion

        ratios.debt_to_equity = _div(financial_debt, getattr(bs, 'total_equity', None))
        ratios.debt_to_assets = _div(financial_debt, getattr(bs, 'total_assets', None))

        finance_costs = getattr(inc, 'finance_costs', None)
        ebit = getattr(inc, 'ebit', None)
        if finance_costs is not None and finance_costs > 0:
            ratios.interest_coverage = _div(ebit, finance_costs)
        elif finance_costs is not None and finance_costs <= 0:
            ratios.interest_coverage = None
        ratios.equity_multiplier = _div(
            getattr(bs, 'total_assets', None),
            getattr(bs, 'total_equity', None),
        )

        # ── Efficiency ───────────────────────────────────────────────────────
        # Bug #3: asset_turnover and receivables_turnover use operating revenue only
        ratios.asset_turnover        = _div(operating_revenue, getattr(bs, 'total_assets', None))
        ratios.inventory_turnover    = _div(getattr(inc, 'cost_of_goods_sold', None), getattr(bs, 'inventory', None))
        ratios.receivables_turnover  = _div(operating_revenue, getattr(bs, 'trade_receivables', None))

        # ── Cash flow ────────────────────────────────────────────────────────
        ratios.cfo_to_net_income = _div(
            getattr(cf, 'cfo', None),
            getattr(inc, 'profit_after_tax', None),
        )

        fcf_disclosed = getattr(cf, 'free_cash_flow', None)
        cfo_val   = getattr(cf, 'cfo', None)
        capex_val = getattr(cf, 'capex', None)

        if fcf_disclosed is not None:
            ratios.free_cash_flow = fcf_disclosed
        elif cfo_val is not None and capex_val is not None:
            ratios.free_cash_flow = round(cfo_val - abs(capex_val), 2)

    except Exception as e:
        logger.error(f"Ratio computation framework execution crash trace: {e}")

    return ratios