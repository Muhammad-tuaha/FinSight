"""
Shared ratio status thresholds — keep PDF, API helpers, and frontend rules aligned.
Interest coverage: danger below 1.5x (matches red-flag HIGH boundary band).
"""

from typing import Optional


def ratio_status_label(key: str, value: Optional[float]) -> str:
    """Return Healthy | Marginal | Concern | N/A for report tables."""
    if value is None:
        return "N/A"

    status = ratio_status_class(key, value)
    if status == "good":
        return "Healthy"
    if status == "warn":
        return "Marginal"
    return "Concern"


def ratio_status_class(key: str, value: float) -> str:
    """Return good | warn | danger.

    Thresholds are intentionally aligned so identical CR/QR values (common when
    inventory=0) produce the same status label.  Previous version used >= 2.0 for
    CR 'good' but >= 1.0 for QR 'good', giving inconsistent labels for equal values.
    """
    rules = {
        # Liquidity: aligned thresholds — same cut-offs for CR and QR
        "current_ratio": lambda v: "good" if v >= 1.5 else "warn" if v >= 1.0 else "danger",
        "quick_ratio":   lambda v: "good" if v >= 1.5 else "warn" if v >= 1.0 else "danger",
        "cash_ratio":    lambda v: "good" if v >= 0.5 else "warn" if v >= 0.2 else "danger",
        # Profitability
        "gross_margin":  lambda v: "good" if v >= 30 else "warn" if v >= 15 else "danger",
        "net_margin":    lambda v: "good" if v >= 10 else "warn" if v >= 4  else "danger",
        "roa":           lambda v: "good" if v >= 6  else "warn" if v >= 2  else "danger",
        "roe":           lambda v: "good" if v >= 15 else "warn" if v >= 8  else "danger",
        # Leverage
        "debt_to_equity":     lambda v: "good" if v <= 1   else "warn" if v <= 2   else "danger",
        "interest_coverage":  lambda v: "good" if v >= 3   else "warn" if v >= 1.5 else "danger",
        # Efficiency
        "asset_turnover":        lambda v: "good" if v >= 1 else "warn" if v >= 0.5 else "danger",
        "inventory_turnover":    lambda v: "good" if v >= 6 else "warn" if v >= 3   else "danger",
        "receivables_turnover":  lambda v: "good" if v >= 8 else "warn" if v >= 5   else "danger",
    }
    fn = rules.get(key)
    return fn(value) if fn else "warn"


def ratio_status_color(status: str) -> str:
    return {
        "good": "#10b981",
        "warn": "#b45309",
        "danger": "#b91c1c",
        "N/A": "#64748b",
    }.get(status, "#64748b")
