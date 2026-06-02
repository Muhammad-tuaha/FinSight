# FinSight — PSX Annual Report Analysis System

Automates preliminary financial analysis of Pakistan Stock Exchange (PSX) listed company annual reports.

---

## Architecture

```
PDF Annual Report
       │
       ▼
┌─────────────────────┐
│  1. PDF Parser      │  PyMuPDF + pdfplumber
│  pdf_parser.py      │  Page classification, table extraction
└──────────┬──────────┘
           │ ParsedDocument
           ▼
┌─────────────────────┐
│  2. LLM Extractor   │  Claude API
│  llm_extractor.py   │  Structured JSON extraction via prompt engineering
└──────────┬──────────┘
           │ ExtractedFinancials (Pydantic)
           ▼
┌─────────────────────┐
│  3. Ratio Engine    │  Pure Python
│  ratio_engine.py    │  Liquidity, profitability, leverage, efficiency
└──────────┬──────────┘
           │ RatioSet
           ▼
┌─────────────────────┐
│  4. Red Flag Engine │  Rule-based
│  red_flag_engine.py │  Threshold checks + YoY anomaly detection
└──────────┬──────────┘
           │ RedFlagReport
           ▼
┌─────────────────────┐
│  5. Summary Gen     │  Narrative assembly
│  summary_generator  │  Structured analyst-grade report
└─────────────────────┘
```

---

## File Structure

```
finsight/
├── pipeline.py              ← End-to-end orchestrator + CLI entry point
├── requirements.txt
├── models/
│   └── financial_schema.py  ← Pydantic data contract (shared JSON schema)
├── core/
│   ├── pdf_parser.py        ← PDF ingestion, page classification, table extraction
│   ├── llm_extractor.py     ← Claude API prompting + response validation
│   ├── ratio_engine.py      ← Financial ratio computation
│   ├── red_flag_engine.py   ← Warning signal detection rules
│   └── summary_generator.py ← Analyst narrative generation
└── utils/
    └── validator.py         ← Ground-truth accuracy validation
```

---

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Set API key
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Run analysis
```bash
python -m finsight.pipeline analyse \
    --pdf reports/hub_power_2024.pdf \
    --company "Hub Power Company" \
    --sector "Power Generation" \
    --output results/
```

### Programmatic use
```python
from finsight.pipeline import run_analysis

result = run_analysis(
    pdf_path="reports/hubco_2024.pdf",
    company_name="Hub Power Company",
    sector="Power Generation",
    output_dir="results/",
)

print(result["analyst_summary"])
print(result["red_flags"])
```

### Validate extraction accuracy
```bash
python -m finsight.pipeline validate \
    --ground-truth ground_truth/ \
    --extractions results/ \
    --output-csv accuracy.csv \
    --tolerance 2.0
```

---

## Ground Truth Format

Each file in `ground_truth/` should follow this schema:

```json
{
  "company": "Hub Power Company",
  "period": "FY2024",
  "figures": {
    "current_period.income_statement.revenue": 85234000,
    "current_period.income_statement.gross_profit": 12450000,
    "current_period.balance_sheet.total_assets": 220000000,
    "current_period.cash_flow.cfo": 9800000
  }
}
```

---

## Outputs

| File | Description |
|------|-------------|
| `<company>_<period>_finsight.json` | Full structured output (financials, ratios, flags) |
| `<company>_<period>_finsight_report.txt` | Analyst-grade narrative report |
| `validation_results.csv` | Accuracy spreadsheet (batch validation) |

---

## Key Design Decisions

- **Separation of concerns**: Each layer is independently testable. The Pydantic schema (`financial_schema.py`) is the shared contract between all layers.
- **Defensive extraction**: All ratio computations handle `None` values gracefully — missing data yields `None` rather than exceptions or silent errors.
- **Page classification**: Uses keyword density scoring to identify financial statement pages before sending to the LLM, reducing context window usage and improving extraction accuracy.
- **Confidence scoring**: The LLM is explicitly prompted to report extraction confidence, enabling downstream filtering of low-quality extractions.
- **Tolerance-based validation**: Ground-truth comparison uses a configurable percentage tolerance (default 2%) to account for rounding differences in how PSX reports present figures.
