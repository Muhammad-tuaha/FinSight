"""
FinSight — Ratio Computation Engine
Computes all financial ratios from an extracted FinancialPeriod object.
Every division is guarded — zero denominators return None, never a 500.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


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


def compute_ratios(period) -> ComputedRatios:
    """
    Compute all supported financial ratios for a single FinancialPeriod.
    Returns a ComputedRatios dataclass. Never raises — all errors are logged.
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
        ratios.current_ratio = _div(getattr(bs, 'total_current_assets', None), getattr(bs, 'total_current_liabilities', None))

        # Quick assets = current assets - inventory
        total_curr_assets = getattr(bs, 'total_current_assets', None)
        total_curr_liab = getattr(bs, 'total_current_liabilities', None)
        if total_curr_assets is not None and total_curr_liab is not None:
            inventory = getattr(bs, 'inventory', None) or 0.0
            quick_assets = total_curr_assets - inventory
            ratios.quick_ratio = _div(quick_assets, total_curr_liab)

        ratios.cash_ratio = _div(getattr(bs, 'cash_and_equivalents', None), total_curr_liab)

        # ── Profitability ────────────────────────────────────────────────────
        ratios.gross_margin        = _pct(getattr(inc, 'gross_profit', None),        getattr(inc, 'revenue', None))
        ratios.net_margin          = _pct(getattr(inc, 'profit_after_tax', None),    getattr(inc, 'revenue', None))
        ratios.ebitda_margin       = _pct(getattr(inc, 'ebitda', None),               getattr(inc, 'revenue', None))
        ratios.roa                 = _pct(getattr(inc, 'profit_after_tax', None),    getattr(bs, 'total_assets', None))
        ratios.roe                 = _pct(getattr(inc, 'profit_after_tax', None),    getattr(bs, 'total_equity', None))

        # ── Leverage / Solvency ──────────────────────────────────────────────
        st_borrowings = getattr(bs, 'short_term_borrowings', None) or 0.0
        lt_debt = getattr(bs, 'long_term_debt', None) or 0.0
        curr_portion = getattr(bs, 'current_portion_long_term_debt', None) or 0.0
        
        total_debt = st_borrowings + lt_debt + curr_portion

        ratios.debt_to_equity   = _div(total_debt, getattr(bs, 'total_equity', None))
        ratios.debt_to_assets   = _div(total_debt, getattr(bs, 'total_assets', None))
        finance_costs = getattr(inc, 'finance_costs', None)
        ebit = getattr(inc, 'ebit', None)
        if finance_costs is not None and finance_costs > 0:
            ratios.interest_coverage = _div(ebit, finance_costs)
        elif finance_costs is not None and finance_costs <= 0:
            ratios.interest_coverage = None
        ratios.equity_multiplier = _div(getattr(bs, 'total_assets', None), getattr(bs, 'total_equity', None))

        # ── Efficiency ───────────────────────────────────────────────────────
        ratios.asset_turnover = _div(getattr(inc, 'revenue', None), getattr(bs, 'total_assets', None))
        ratios.inventory_turnover = _div(getattr(inc, 'cost_of_goods_sold', None), getattr(bs, 'inventory', None))
        ratios.receivables_turnover = _div(getattr(inc, 'revenue', None), getattr(bs, 'trade_receivables', None))

        # ── Cash flow ────────────────────────────────────────────────────────
        ratios.cfo_to_net_income = _div(getattr(cf, 'cfo', None), getattr(inc, 'profit_after_tax', None))

        # Free cash flow: use disclosed value first, else compute CFO - capex
        fcf_disclosed = getattr(cf, 'free_cash_flow', None)
        cfo_val = getattr(cf, 'cfo', None)
        capex_val = getattr(cf, 'capex', None)
        
        if fcf_disclosed is not None:
            ratios.free_cash_flow = fcf_disclosed
        elif cfo_val is not None and capex_val is not None:
            ratios.free_cash_flow = round(cfo_val - abs(capex_val), 2)

    except Exception as e:
        logger.error(f"Ratio computation framework execution crash trace: {e}")

    return ratios