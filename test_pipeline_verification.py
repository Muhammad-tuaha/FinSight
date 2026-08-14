import os
import sys
import json
import logging

# Ensure finsight directory is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "finsight"))

from models.financial_schema import ExtractedFinancials, FinancialPeriod, IncomeStatement, BalanceSheet, CashFlowStatement
from core.ratio_engine import compute_ratios, RATIO_FORMULAS
from core.red_flag_engine import detect_red_flags
from utils.thresholds import ratio_status_label, ratio_status_class

logging.basicConfig(level=logging.INFO)

def test_psx_exchange_scenario():
    print("\n--- 1. Testing PSX Exchange Scenario (No Inventory, High Deposits, Investment Heavy, Non-operating income) ---")
    
    # Synthetic period mimicking Pakistan Stock Exchange Limited 2025 report
    period = FinancialPeriod(
        company_name="Pakistan Stock Exchange Limited",
        reporting_period="FY2025",
        income_statement=IncomeStatement(
            revenue=1_500_000, # Operating revenue
            cost_of_goods_sold=None, # Exchange operator - no direct COGS
            gross_profit=1_500_000,
            other_income=500_000, # Non-operating income
            share_of_profit_associates=300_000, # Equity method profit from associates
            profit_after_tax=1_000_000,
            ebit=1_200_000,
            finance_costs=20_000,
        ),
        balance_sheet=BalanceSheet(
            total_current_assets=5_000_000,
            inventory=None, # 0 inventory
            total_current_liabilities=3_000_000, # CR = 5M / 3M = 1.67x, QR = 1.67x
            cash_and_equivalents=2_000_000,
            short_term_borrowings=0,
            long_term_debt=100_000, # Actual financial debt (IFRS 16 lease liability)
            long_term_deposits=3_000_000, # Broker security deposits (Operating liability)
            current_portion_long_term_debt=80_000,
            total_assets=20_000_000, # Large asset base including associates investments
            total_equity=15_000_000,
        ),
        cash_flow=CashFlowStatement(cfo=1_100_000, capex=200_000)
    )

    financials = ExtractedFinancials(
        company_name="Pakistan Stock Exchange Limited",
        sector="Financial Exchange",
        current_period=period,
        entity_confidence=0.95,
        sector_confidence=0.90,
        extraction_confidence=0.95
    )

    ratios = compute_ratios(period, sector=financials.sector)
    red_flags = detect_red_flags(financials, current_ratios=ratios)

    print(f"Company: {financials.company_name} | Sector: {financials.sector}")
    print(f"Current Ratio: {ratios.current_ratio}x -> Status: {ratio_status_label('current_ratio', ratios.current_ratio)}")
    print(f"Quick Ratio:   {ratios.quick_ratio}x -> Status: {ratio_status_label('quick_ratio', ratios.quick_ratio)}")
    print(f"Net Margin:    {ratios.net_margin}%  (NPAT / Operating Revenue, excluding other income/associates)")
    print(f"Debt to Equity:{ratios.debt_to_equity}x (Financial debt only: (100k+80k)/15M = 0.012x; deposits excluded)")
    print(f"Asset Turnover:{ratios.asset_turnover}x")
    print("\nRed Flags Fired:")
    for f in red_flags.flags:
        print(f"  [{f.priority}] [{f.category}] {f.title}: {f.description}")

    # Assertions
    assert abs(ratios.current_ratio - 1.6667) < 0.001
    assert abs(ratios.quick_ratio - 1.6667) < 0.001
    assert ratio_status_label('current_ratio', ratios.current_ratio) == ratio_status_label('quick_ratio', ratios.quick_ratio) == "Healthy"
    assert abs(ratios.net_margin - 66.67) < 0.01 # 1,000,000 / 1,500,000 * 100 (66.67%)
    assert abs(ratios.debt_to_equity - 0.012) < 0.001 # 180,000 / 15,000,000
    assert not any(f.title == "Low Asset Utilisation" for f in red_flags.flags)
    print("SUCCESS: PSX Exchange scenario passed all assertions!")

def test_inventory_sector_scenario():
    print("\n--- 2. Testing Manufacturing Sector Scenario (With Real Inventory) ---")
    
    period = FinancialPeriod(
        company_name="Lucky Cement Limited",
        reporting_period="FY2024",
        income_statement=IncomeStatement(
            revenue=10_000_000,
            cost_of_goods_sold=7_000_000,
            gross_profit=3_000_000,
            profit_after_tax=1_200_000,
        ),
        balance_sheet=BalanceSheet(
            total_current_assets=4_000_000,
            inventory=1_500_000, # Substantial inventory
            total_current_liabilities=3_000_000, # CR = 4M / 3M = 1.33x, QR = (4M - 1.5M)/3M = 0.83x
            total_assets=15_000_000,
            total_equity=8_000_000,
        ),
        cash_flow=CashFlowStatement(cfo=1_500_000, capex=500_000)
    )

    financials = ExtractedFinancials(
        company_name="Lucky Cement Limited",
        sector="Cement / Manufacturing",
        current_period=period,
        entity_confidence=0.98,
        sector_confidence=0.95,
        extraction_confidence=0.95
    )

    ratios = compute_ratios(period, sector=financials.sector)
    
    print(f"Current Ratio: {ratios.current_ratio}x -> Status: {ratio_status_label('current_ratio', ratios.current_ratio)}")
    print(f"Quick Ratio:   {ratios.quick_ratio}x -> Status: {ratio_status_label('quick_ratio', ratios.quick_ratio)}")

    assert abs(ratios.current_ratio - 1.3333) < 0.001 # Marginal (>=1.0, <1.5)
    assert abs(ratios.quick_ratio - 0.8333) < 0.001   # Marginal (>=0.7, <1.0 for QR? wait, QR >=1.5 is good, >=1.0 is warn, <1.0 is danger! Wait, let's verify)
    assert ratio_status_label('current_ratio', ratios.current_ratio) == "Marginal"
    print("SUCCESS: Manufacturing sector inventory scenario passed!")

def test_banking_sector_scenario():
    print("\n--- 3. Testing Banking Sector Scenario (Sector-Conditional Deposits) ---")
    
    period = FinancialPeriod(
        company_name="Meezan Bank Limited",
        reporting_period="FY2024",
        income_statement=IncomeStatement(
            revenue=100_000_000, # Interest / Return earned
            profit_after_tax=30_000_000,
        ),
        balance_sheet=BalanceSheet(
            total_current_assets=500_000_000,
            total_current_liabilities=450_000_000,
            short_term_borrowings=20_000_000,
            long_term_debt=10_000_000,
            long_term_deposits=400_000_000, # Customer deposits in Bank
            total_assets=600_000_000,
            total_equity=50_000_000,
        ),
        cash_flow=CashFlowStatement(cfo=35_000_000)
    )

    financials = ExtractedFinancials(
        company_name="Meezan Bank Limited",
        sector="Commercial Bank",
        current_period=period,
        entity_confidence=0.99,
        sector_confidence=0.98,
        extraction_confidence=0.96
    )

    ratios = compute_ratios(period, sector=financials.sector)
    print(f"Bank Debt-to-Equity (including customer deposits): {ratios.debt_to_equity}x")
    # Total funding liabilities = 20M + 10M + 400M = 430M / 50M = 8.6x
    assert ratios.debt_to_equity == 8.6
    print("SUCCESS: Banking sector conditional deposit inclusion passed!")

if __name__ == "__main__":
    test_psx_exchange_scenario()
    test_inventory_sector_scenario()
    test_banking_sector_scenario()
