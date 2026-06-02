"""
FinSight — Narrative Summary Generator
Builds structured analyst commentary from computed ratios, red flags,
and extracted financials. No LLM call — pure deterministic text generation
so the pipeline never stalls on a second API round-trip.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from models.financial_schema import ExtractedFinancials
from core.ratio_engine import ComputedRatios
from core.red_flag_engine import RedFlagReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class NarrativeReport:
    period: str
    executive_summary: str
    liquidity_commentary: str
    profitability_commentary: str
    leverage_commentary: str
    cash_flow_commentary: str
    yoy_commentary: str
    full_text: str
    key_concerns: list   # list[str] — top flag titles for risk_profile


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _fmt(val: Optional[float], decimals: int = 2, suffix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"


def _build_liquidity(ratios: ComputedRatios) -> str:
    cr = ratios.current_ratio
    qr = ratios.quick_ratio
    cash = ratios.cash_ratio

    if cr is None:
        return "Liquidity data was not available in the extracted financial statements."

    if cr >= 2.0:
        posture = "strong liquidity posture"
        outlook = "The company is well-positioned to absorb unexpected short-term cash demands."
    elif cr >= 1.5:
        posture = "adequate liquidity"
        outlook = "Working capital appears healthy, though management should monitor seasonal cash cycles."
    elif cr >= 1.0:
        posture = "tight but positive working capital"
        outlook = "The company can meet current obligations but has limited headroom. Active working capital management is advisable."
    else:
        posture = "a working capital deficit"
        outlook = "Current liabilities exceed current assets. Immediate attention to cash management and short-term financing is recommended."

    parts = [
        f"The company reported {posture} with a current ratio of {_fmt(cr)}x.",
        f"The quick ratio stood at {_fmt(qr)}x, " + (
            "indicating reliance on inventory liquidation to meet obligations."
            if qr is not None and qr < 0.8
            else "reflecting a reasonable near-liquid asset buffer."
        ) if qr is not None else "",
        f"The cash ratio of {_fmt(cash)}x suggests " + (
            "minimal immediate cash reserves."
            if cash is not None and cash < 0.2
            else "an adequate immediate liquidity floor."
        ) if cash is not None else "",
        outlook,
    ]
    return " ".join(p for p in parts if p)


def _build_profitability(ratios: ComputedRatios) -> str:
    nm   = ratios.net_margin
    gm   = ratios.gross_margin
    roe  = ratios.roe
    roa  = ratios.roa

    if nm is None and roe is None:
        return "Profitability data was not available in the extracted financial statements."

    lines = []

    if gm is not None:
        gm_comment = (
            "a strong gross margin"   if gm > 30 else
            "a healthy gross margin"  if gm > 15 else
            "a thin gross margin"     if gm > 5  else
            "a critically compressed gross margin"
        )
        lines.append(f"Gross margin of {_fmt(gm, 1)}% represents {gm_comment}, reflecting the underlying pricing and cost structure.")

    if nm is not None:
        if nm < 0:
            lines.append(f"The company recorded a net loss margin of {_fmt(nm, 1)}%, indicating expenses exceeded revenues for the period.")
        elif nm < 5:
            lines.append(f"Net margin of {_fmt(nm, 1)}% is narrow, leaving limited earnings buffer against cost inflation or revenue pressure.")
        elif nm < 15:
            lines.append(f"Net margin of {_fmt(nm, 1)}% is moderate, consistent with competitive sectors with high operating leverage.")
        else:
            lines.append(f"Net margin of {_fmt(nm, 1)}% is robust, demonstrating strong bottom-line conversion from revenue.")

    if roe is not None:
        if roe < 0:
            lines.append(f"ROE of {_fmt(roe, 1)}% is negative, signalling active equity erosion and potential investor concern.")
        elif roe < 10:
            lines.append(f"ROE of {_fmt(roe, 1)}% trails the typical PSX cost-of-equity hurdle rate, suggesting sub-optimal capital allocation.")
        elif roe < 20:
            lines.append(f"ROE of {_fmt(roe, 1)}% reflects reasonable shareholder value creation.")
        else:
            lines.append(f"ROE of {_fmt(roe, 1)}% is strong, reflecting efficient use of equity capital to generate earnings.")

    if roa is not None:
        lines.append(f"Asset productivity (ROA) of {_fmt(roa, 1)}% indicates the asset base is " + (
            "generating satisfactory returns." if roa >= 5 else "underperforming relative to deployed capital."
        ))

    return " ".join(lines) if lines else "Profitability figures are partially available; interpretation may be incomplete."


def _build_leverage(ratios: ComputedRatios) -> str:
    dte = ratios.debt_to_equity
    ic  = ratios.interest_coverage
    dta = ratios.debt_to_assets

    if dte is None and ic is None:
        return "Leverage data was not available in the extracted financial statements."

    lines = []

    if dte is not None:
        if dte > 3:
            lines.append(f"The capital structure is heavily debt-dependent, with a debt-to-equity ratio of {_fmt(dte)}x — a level that amplifies financial risk significantly.")
        elif dte > 1.5:
            lines.append(f"Debt-to-equity of {_fmt(dte)}x reflects an elevated leverage profile. Refinancing risk and rising interest rates warrant close monitoring.")
        elif dte > 0.5:
            lines.append(f"Debt-to-equity of {_fmt(dte)}x represents a balanced capital structure with moderate financial risk.")
        else:
            lines.append(f"Debt-to-equity of {_fmt(dte)}x indicates a conservative, equity-heavy balance sheet with low insolvency risk.")

    if ic is not None:
        if ic < 1.5:
            lines.append(f"Interest coverage of {_fmt(ic, 1)}x is critically low — operating earnings barely cover debt servicing costs.")
        elif ic < 3:
            lines.append(f"Interest coverage of {_fmt(ic, 1)}x provides a thin margin of safety for debt obligations.")
        elif ic < 6:
            lines.append(f"Interest coverage of {_fmt(ic, 1)}x is comfortable, indicating earnings can comfortably absorb finance costs.")
        else:
            lines.append(f"Interest coverage of {_fmt(ic, 1)}x is strong, reflecting minimal debt servicing pressure on operating earnings.")

    if dta is not None:
        lines.append(f"Debt finances {_fmt(dta * 100, 1)}% of total assets, " + (
            "indicating significant creditor claims on the asset base."
            if dta > 0.6 else "reflecting moderate asset encumbrance."
        ))

    return " ".join(lines) if lines else "Leverage figures are partially available."


def _build_cashflow(ratios: ComputedRatios, period) -> str:
    cf = period.cash_flow
    cfo_ratio = ratios.cfo_to_net_income
    fcf = ratios.free_cash_flow

    if cf.cfo is None:
        return "Cash flow data was not available in the extracted financial statements."

    lines = []

    if cf.cfo is not None:
        cfo_sign = "positive" if cf.cfo > 0 else "negative"
        lines.append(f"Operating cash flow (CFO) was PKR {cf.cfo:,.0f} thousand — a {cfo_sign} result.")

    if cfo_ratio is not None:
        if cfo_ratio >= 1.0:
            lines.append(f"The CFO-to-net-income ratio of {_fmt(cfo_ratio)}x confirms high earnings quality; reported profits are backed by real cash generation.")
        elif cfo_ratio >= 0.5:
            lines.append(f"CFO conversion ratio of {_fmt(cfo_ratio)}x is acceptable, though some divergence between accrual earnings and cash exists.")
        else:
            lines.append(f"CFO conversion of {_fmt(cfo_ratio)}x is weak — a material gap between reported earnings and actual cash collected warrants investigation of working capital movements.")

    if fcf is not None:
        fcf_sign = "positive" if fcf >= 0 else "negative"
        lines.append(f"Free cash flow was {fcf_sign} at PKR {fcf:,.0f} thousand after capital expenditure, " + (
            "providing capacity for debt repayment, dividends, or reinvestment."
            if fcf >= 0 else
            "indicating that current investment outlays exceed internally generated cash — external financing may be required."
        ))

    return " ".join(lines)


def _build_yoy(financials: ExtractedFinancials,
               current_ratios: ComputedRatios,
               prior_ratios: Optional[ComputedRatios]) -> str:

    if not financials.prior_period or prior_ratios is None:
        return "Prior period data was not available; year-over-year comparison cannot be performed."

    curr_inc  = financials.current_period.income_statement
    prior_inc = financials.prior_period.income_statement
    curr_per  = financials.current_period.reporting_period
    prior_per = financials.prior_period.reporting_period

    lines = [f"Comparing {curr_per} against {prior_per}:"]

    # Revenue
    if curr_inc.revenue and prior_inc.revenue and prior_inc.revenue != 0:
        rev_chg = (curr_inc.revenue - prior_inc.revenue) / prior_inc.revenue * 100
        direction = "grew" if rev_chg >= 0 else "declined"
        lines.append(f"Revenue {direction} {abs(rev_chg):.1f}% year-over-year.")

    # PAT
    if curr_inc.profit_after_tax is not None and prior_inc.profit_after_tax:
        if prior_inc.profit_after_tax != 0:
            pat_chg = (curr_inc.profit_after_tax - prior_inc.profit_after_tax) / abs(prior_inc.profit_after_tax) * 100
            direction = "improved" if pat_chg >= 0 else "contracted"
            lines.append(f"Net profit {direction} {abs(pat_chg):.1f}% versus the prior year.")

    # Margin shift
    if current_ratios.net_margin is not None and prior_ratios.net_margin is not None:
        delta = current_ratios.net_margin - prior_ratios.net_margin
        if abs(delta) > 0.5:
            direction = "expanded" if delta > 0 else "compressed"
            lines.append(f"Net margin {direction} by {abs(delta):.1f} percentage points.")

    # ROE shift
    if current_ratios.roe is not None and prior_ratios.roe is not None:
        delta = current_ratios.roe - prior_ratios.roe
        if abs(delta) > 1:
            direction = "improved" if delta > 0 else "declined"
            lines.append(f"Return on equity {direction} {abs(delta):.1f} pp year-on-year.")

    if len(lines) == 1:
        return "Insufficient comparable data for meaningful year-over-year analysis."

    return " ".join(lines)


def _build_executive_summary(
    financials: ExtractedFinancials,
    ratios: ComputedRatios,
    flags: RedFlagReport,
) -> str:
    company  = financials.company_name
    period   = financials.current_period.reporting_period
    sector   = financials.sector or "general market"
    conf     = financials.extraction_confidence

    high = flags.high_count
    total = len(flags.flags)

    # Overall health verdict
    if high >= 3:
        verdict = "significant financial stress across multiple dimensions"
        action  = "Immediate management attention and investor scrutiny is warranted."
    elif high >= 1:
        verdict = "mixed financial health with notable areas of concern"
        action  = "Key risk areas should be monitored closely."
    elif total == 0:
        verdict = "a broadly healthy financial position"
        action  = "No material red flags were identified in this analysis cycle."
    else:
        verdict = "generally stable financials with minor areas requiring attention"
        action  = "Low-severity observations are noted for completeness."

    conf_note = (
        f" Extraction confidence was rated at {conf:.0%}."
        if conf is not None else ""
    )

    return (
        f"FinSight analysis of {company} ({sector.upper()} sector) for {period} "
        f"indicates {verdict}. "
        f"The analysis identified {total} risk indicator{'s' if total != 1 else ''}, "
        f"of which {high} {'are' if high != 1 else 'is'} classified HIGH priority. "
        f"{action}{conf_note}"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_summary(
    financials: ExtractedFinancials,
    current_ratios: ComputedRatios,
    prior_ratios: Optional[ComputedRatios],
    flags: RedFlagReport,
) -> NarrativeReport:
    """
    Build a complete NarrativeReport from pre-computed ratios and flags.
    Never raises — all errors are caught and noted in the output.
    """
    try:
        period_label = financials.current_period.reporting_period

        executive   = _build_executive_summary(financials, current_ratios, flags)
        liquidity   = _build_liquidity(current_ratios)
        profit      = _build_profitability(current_ratios)
        leverage    = _build_leverage(current_ratios)
        cashflow    = _build_cashflow(current_ratios, financials.current_period)
        yoy         = _build_yoy(financials, current_ratios, prior_ratios)

        full_text = "\n\n".join([
            f"=== EXECUTIVE SUMMARY ===\n{executive}",
            f"=== LIQUIDITY ANALYSIS ===\n{liquidity}",
            f"=== PROFITABILITY ASSESSMENT ===\n{profit}",
            f"=== LEVERAGE & SOLVENCY ===\n{leverage}",
            f"=== CASH FLOW DYNAMICS ===\n{cashflow}",
            f"=== YEAR-OVER-YEAR TRAJECTORY ===\n{yoy}",
        ])

        # key_concerns: top 5 flag titles for the risk_profile block
        key_concerns = [
            f"[{f.priority}] {f.title}: {f.description}"
            for f in flags.flags[:5]
        ]

        logger.info(f"Narrative report generated for {financials.company_name}")

        return NarrativeReport(
            period=period_label,
            executive_summary=executive,
            liquidity_commentary=liquidity,
            profitability_commentary=profit,
            leverage_commentary=leverage,
            cash_flow_commentary=cashflow,
            yoy_commentary=yoy,
            full_text=full_text,
            key_concerns=key_concerns,
        )

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        # Return a minimal valid report so the API never crashes
        return NarrativeReport(
            period=getattr(financials.current_period, "reporting_period", "Unknown"),
            executive_summary="Summary generation encountered an error.",
            liquidity_commentary="",
            profitability_commentary="",
            leverage_commentary="",
            cash_flow_commentary="",
            yoy_commentary="",
            full_text="",
            key_concerns=[],
        )