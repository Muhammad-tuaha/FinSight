"""
FinSight — Red Flag Detection Engine
Runs rule-based threshold checks against extracted financials and computed ratios.
Returns a structured RedFlagReport used by the summary generator and API response.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from models.financial_schema import ExtractedFinancials
from core.ratio_engine import ComputedRatios, compute_ratios

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class RedFlagItem:
    priority: str          # 'HIGH' | 'MEDIUM' | 'LOW'
    category: str          # 'Liquidity' | 'Profitability' | 'Leverage' | 'Efficiency' | 'Cash Flow'
    title: str
    description: str

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "category": self.category,
            "title": self.title,
            "description": self.description,
        }


@dataclass
class RedFlagReport:
    flags: list = field(default_factory=list)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.flags if f.priority == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.flags if f.priority == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.flags if f.priority == "LOW")

    def to_list(self) -> list[dict]:
        return [f.to_dict() for f in self.flags]


# ---------------------------------------------------------------------------
# Threshold matrix
# ---------------------------------------------------------------------------
#
# Each entry: (metric_value, condition_fn, priority, category, title, description_template)
# Rules are evaluated in order; multiple rules can fire on the same period.

def _flag(priority, category, title, description) -> RedFlagItem:
    return RedFlagItem(priority=priority, category=category, title=title, description=description)


def _check_liquidity(ratios: ComputedRatios, flags: list) -> None:
    cr = ratios.current_ratio
    qr = ratios.quick_ratio
    cash = ratios.cash_ratio

    if cr is not None:
        if cr < 0.8:
            flags.append(_flag(
                "HIGH", "Liquidity",
                "Critical Liquidity Deficit",
                f"Current ratio of {cr:.2f}x is critically below 1.0. The company may be unable to meet short-term obligations without asset liquidation or refinancing."
            ))
        elif cr < 1.0:
            flags.append(_flag(
                "HIGH", "Liquidity",
                "Current Ratio Below 1.0",
                f"Current ratio of {cr:.2f}x signals that current liabilities exceed current assets — a negative working capital position."
            ))
        elif cr < 1.25:
            flags.append(_flag(
                "MEDIUM", "Liquidity",
                "Thin Liquidity Cushion",
                f"Current ratio of {cr:.2f}x provides a narrow buffer. Any unexpected cash demand could stress working capital."
            ))

    if qr is not None and qr < 0.7:
        flags.append(_flag(
            "MEDIUM", "Liquidity",
            "Low Quick Ratio",
            f"Quick ratio of {qr:.2f}x suggests heavy reliance on inventory liquidation to service current liabilities."
        ))

    if cash is not None and cash < 0.1:
        flags.append(_flag(
            "LOW", "Liquidity",
            "Minimal Cash Buffer",
            f"Cash ratio of {cash:.2f}x indicates very limited immediate liquidity. The company depends on receivable collections and inventory turnover for daily operations."
        ))


def _check_profitability(ratios: ComputedRatios, flags: list) -> None:
    nm = ratios.net_margin
    gm = ratios.gross_margin
    roe = ratios.roe
    roa = ratios.roa

    if nm is not None:
        if nm < 0:
            flags.append(_flag(
                "HIGH", "Profitability",
                "Net Loss Recorded",
                f"Net margin of {nm:.1f}% indicates the company reported a net loss for the period. Sustained losses erode equity and raise going-concern risk."
            ))
        elif nm < 3:
            flags.append(_flag(
                "MEDIUM", "Profitability",
                "Razor-Thin Net Margin",
                f"Net margin of {nm:.1f}% leaves minimal room to absorb cost pressures or revenue shortfalls."
            ))

    if gm is not None and gm < 10:
        flags.append(_flag(
            "MEDIUM", "Profitability",
            "Low Gross Margin",
            f"Gross margin of {gm:.1f}% suggests intense pricing pressure or high direct input costs relative to revenue."
        ))

    if roe is not None:
        if roe < 0:
            flags.append(_flag(
                "HIGH", "Profitability",
                "Negative Return on Equity",
                f"ROE of {roe:.1f}% indicates shareholder equity is being eroded. Sustained negative ROE signals fundamental business model stress."
            ))
        elif roe < 8:
            flags.append(_flag(
                "LOW", "Profitability",
                "Below-Average ROE",
                f"ROE of {roe:.1f}% is below the typical PSX cost-of-equity benchmark of ~12–15%. Capital allocation efficiency warrants review."
            ))

    if roa is not None and roa < 2:
        flags.append(_flag(
            "LOW", "Profitability",
            "Low Asset Productivity",
            f"ROA of {roa:.1f}% indicates the asset base is generating minimal returns. Review capital deployment strategy."
        ))


def _check_leverage(ratios: ComputedRatios, flags: list) -> None:
    dte = ratios.debt_to_equity
    ic = ratios.interest_coverage
    dta = ratios.debt_to_assets

    if dte is not None:
        if dte > 4:
            flags.append(_flag(
                "HIGH", "Leverage",
                "Dangerously High Leverage",
                f"Debt-to-equity of {dte:.2f}x represents extreme financial leverage. The company is highly vulnerable to rising interest rates or a revenue shock."
            ))
        elif dte > 2.5:
            flags.append(_flag(
                "MEDIUM", "Leverage",
                "Elevated Debt-to-Equity",
                f"Debt-to-equity of {dte:.2f}x is above the conservative threshold of 2.0x. Debt service obligations may constrain future investment capacity."
            ))
        elif dte > 1.5:
            flags.append(_flag(
                "LOW", "Leverage",
                "Moderate Leverage Level",
                f"Debt-to-equity of {dte:.2f}x is within manageable range but warrants monitoring as interest rates fluctuate."
            ))

    if ic is not None:
        if ic < 1:
            flags.append(_flag(
                "HIGH", "Leverage",
                "Interest Not Covered by Earnings",
                f"Interest coverage of {ic:.1f}x means operating earnings are insufficient to cover finance costs. Default risk is elevated."
            ))
        elif ic < 1.5:
            flags.append(_flag(
                "HIGH", "Leverage",
                "Dangerously Low Interest Coverage",
                f"Interest coverage of {ic:.1f}x is below the 1.5x danger threshold. Operating earnings provide insufficient cushion for finance charges."
            ))
        elif ic < 3:
            flags.append(_flag(
                "MEDIUM", "Leverage",
                "Thin Interest Coverage",
                f"Interest coverage of {ic:.1f}x is below the 3.0x comfort threshold. Earnings volatility could create debt service stress."
            ))

    if dta is not None and dta > 0.7:
        flags.append(_flag(
            "MEDIUM", "Leverage",
            "High Debt-to-Assets Ratio",
            f"Debt-to-assets of {dta:.2f}x means over 70% of the asset base is debt-financed, limiting financial flexibility."
        ))


# Sectors where low asset turnover is structurally expected and should NOT be flagged
_ASSET_LIGHT_OR_INVESTMENT_HEAVY_SECTORS = {
    "exchange", "stock exchange", "financial services", "investment",
    "insurance", "banking", "holding", "real estate", "reit",
}


def _check_efficiency(ratios: ComputedRatios, flags: list, sector: str | None = None) -> None:
    inv_t = ratios.inventory_turnover
    rec_t = ratios.receivables_turnover
    at    = ratios.asset_turnover

    if inv_t is not None and inv_t < 2:
        flags.append(_flag(
            "MEDIUM", "Efficiency",
            "Slow Inventory Turnover",
            f"Inventory turnover of {inv_t:.1f}x suggests potential overstock, obsolescence risk, or weakening demand."
        ))

    if rec_t is not None and rec_t < 4:
        flags.append(_flag(
            "LOW", "Efficiency",
            "Slow Receivables Collection",
            f"Receivables turnover of {rec_t:.1f}x implies collection cycles exceeding 90 days. Credit risk and working capital pressure may be building."
        ))

    if at is not None and at < 0.3:
        # Bug #5: suppress generic asset-turnover flag for sectors where low AT is by design
        sector_norm = (sector or "").strip().lower()
        is_investment_heavy = any(s in sector_norm for s in _ASSET_LIGHT_OR_INVESTMENT_HEAVY_SECTORS)

        if is_investment_heavy:
            # Informational only — not a concern flag
            flags.append(_flag(
                "LOW", "Efficiency",
                "Asset Turnover: Sector-Normal (Informational)",
                f"Asset turnover of {at:.2f}x is low by manufacturing benchmarks but structurally expected "
                f"for a '{sector}' business model with large long-term investments or balance-sheet-heavy operations. "
                f"Benchmark against sector peers rather than generic thresholds."
            ))
        else:
            flags.append(_flag(
                "LOW", "Efficiency",
                "Low Asset Utilisation",
                f"Asset turnover of {at:.2f}x indicates the company generates limited revenue relative to its asset base. "
                f"Capital-intensive sectors should benchmark against peers."
            ))


def _check_cashflow(ratios: ComputedRatios, flags: list) -> None:
    cfo_ratio = ratios.cfo_to_net_income
    fcf       = ratios.free_cash_flow

    if cfo_ratio is not None and cfo_ratio < 0.5:
        flags.append(_flag(
            "MEDIUM", "Cash Flow",
            "Weak Cash Conversion",
            f"CFO-to-net-income ratio of {cfo_ratio:.2f}x suggests reported profits are not translating into operating cash. Investigate working capital movements and accruals."
        ))

    if fcf is not None and fcf < 0:
        flags.append(_flag(
            "MEDIUM", "Cash Flow",
            "Negative Free Cash Flow",
            f"Negative free cash flow of PKR {fcf:,.0f} thousand indicates capex is exceeding operating cash generation. Assess sustainability of investment programme."
        ))


def _check_yoy(financials: ExtractedFinancials, flags: list) -> None:
    """Year-over-year deterioration checks (requires both periods)."""
    if not financials.prior_period:
        return

    curr = financials.current_period.income_statement
    prev = financials.prior_period.income_statement

    # Revenue decline
    if curr.revenue and prev.revenue and prev.revenue > 0:
        rev_change = (curr.revenue - prev.revenue) / prev.revenue * 100
        if rev_change < -15:
            flags.append(_flag(
                "HIGH", "Profitability",
                "Significant Revenue Decline",
                f"Revenue contracted {abs(rev_change):.1f}% year-over-year. Investigate market share loss, pricing pressure, or demand disruption."
            ))
        elif rev_change < -5:
            flags.append(_flag(
                "MEDIUM", "Profitability",
                "Revenue Contraction",
                f"Revenue declined {abs(rev_change):.1f}% versus prior year. Monitor pipeline and order book for recovery trajectory."
            ))

    # PAT swing to loss
    if curr.profit_after_tax is not None and prev.profit_after_tax is not None:
        if prev.profit_after_tax > 0 and curr.profit_after_tax < 0:
            flags.append(_flag(
                "HIGH", "Profitability",
                "Profit Turned to Loss",
                "The company swung from a profit to a net loss versus the prior year — a significant negative inflection requiring management explanation."
            ))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def detect_red_flags(
    financials: ExtractedFinancials,
    current_ratios: Optional[ComputedRatios] = None,
) -> RedFlagReport:
    """
    Run all rule-based checks. If current_ratios are not pre-computed,
    they are computed internally. Sector is passed through to efficiency
    checks so business-model-aware suppression can apply (Bug #5).
    """
    if current_ratios is None:
        current_ratios = compute_ratios(financials.current_period)

    sector = getattr(financials, "sector", None)
    flags: list[RedFlagItem] = []

    try:
        _check_liquidity(current_ratios, flags)
        _check_profitability(current_ratios, flags)
        _check_leverage(current_ratios, flags)
        _check_efficiency(current_ratios, flags, sector=sector)
        _check_cashflow(current_ratios, flags)
        _check_yoy(financials, flags)
    except Exception as e:
        logger.error(f"Red flag engine error: {e}")

    # Sort: HIGH → MEDIUM → LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    flags.sort(key=lambda f: priority_order.get(f.priority, 3))

    report = RedFlagReport(flags=flags)
    logger.info(
        f"Red flag scan complete: {report.high_count} HIGH, "
        f"{report.medium_count} MEDIUM, {report.low_count} LOW"
    )
    return report