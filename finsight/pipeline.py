"""
FinSight — Main Pipeline Orchestrator
End-to-end runner: PDF → extraction → ratios → red flags → analyst summary.

Usage:
    python -m finsight.pipeline analyse \
        --pdf path/to/report.pdf \
        --company "Hub Power Company" \
        --sector "Power Generation" \
        --output results/

    python -m finsight.pipeline validate \
        --ground-truth ground_truth/ \
        --extractions results/
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from core.pdf_parser import parse_annual_report
from core.llm_extractor import extract_financials
from core.ratio_engine import compute_ratios
from core.red_flag_engine import detect_red_flags
from core.summary_generator import generate_summary
from utils.validator import GroundTruthValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("finsight.pipeline")


def run_analysis(
    pdf_path: str,
    company_name: str,
    sector: Optional[str] = None,
    output_dir: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    Full pipeline: PDF → structured financials → ratios → red flags → summary.
    Returns a result dict containing all outputs.
    Optionally writes JSON + TXT report to output_dir.
    """
    logger.info(f"FinSight pipeline starting — {company_name}")

    # ── Step 1: Parse PDF ────────────────────────────────────────────────
    logger.info("Step 1/4 — PDF parsing")
    document = parse_annual_report(pdf_path)
    logger.info(
        f"Parsed {document.total_pages} pages, "
        f"{len(document.financial_pages)} classified as financial statements"
    )

    # ── Step 2: LLM Extraction ───────────────────────────────────────────
    logger.info("Step 2/4 — LLM extraction")
    financials = extract_financials(
        document,
        company_name=company_name,
        sector=sector,
        api_key=api_key,
    )
    logger.info(
        f"Extraction complete — confidence: {financials.extraction_confidence}"
    )

    # ── Step 3: Ratio Computation ─────────────────────────────────────────
    logger.info("Step 3/4 — Ratio computation")
    current_ratios = compute_ratios(financials.current_period, sector=financials.sector or sector)
    prior_ratios = (
        compute_ratios(financials.prior_period, sector=financials.sector or sector)
        if financials.prior_period else None
    )

    # ── Step 4: Red Flag Detection ────────────────────────────────────────
    logger.info("Step 4/4 — Red flag detection & summary generation")
    red_flags = detect_red_flags(financials)
    summary = generate_summary(financials, current_ratios, prior_ratios, red_flags)

    logger.info(
        f"Complete — {red_flags.high_count} HIGH / "
        f"{red_flags.medium_count} MEDIUM / "
        f"{red_flags.low_count} LOW flags"
    )

    # ── Assemble result dict ──────────────────────────────────────────────
    result = {
        "metadata": {
            "company": financials.company_name,
            "sector": financials.sector,
            "source_file": financials.source_file,
            "extraction_date": financials.extraction_date,
            "extraction_confidence": financials.extraction_confidence,
            "extraction_notes": financials.extraction_notes,
        },
        "financials": financials.model_dump(),
        "ratios": {
            "current": current_ratios.__dict__,
            "prior": prior_ratios.__dict__ if prior_ratios else None,
        },
        "red_flags": {
            "high_count": red_flags.high_count,
            "medium_count": red_flags.medium_count,
            "low_count": red_flags.low_count,
            "flags": [
                {
                    "priority": f.priority,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                }
                for f in red_flags.flags
            ],
        },
        "analyst_summary": summary.full_text,
    }

    # ── Write outputs ─────────────────────────────────────────────────────
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        slug = company_name.lower().replace(" ", "_")
        period = financials.current_period.reporting_period.lower()

        json_path = out / f"{slug}_{period}_finsight.json"
        txt_path = out / f"{slug}_{period}_finsight_report.txt"

        with open(json_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"JSON output: {json_path}")

        with open(txt_path, "w") as f:
            f.write(summary.full_text)
        logger.info(f"Text report: {txt_path}")

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="FinSight — PSX Annual Report Analysis Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── analyse subcommand ────────────────────────────────────────────────
    analyse_cmd = subparsers.add_parser("analyse", help="Run analysis on a PDF report")
    analyse_cmd.add_argument("--pdf", required=True, help="Path to annual report PDF")
    analyse_cmd.add_argument("--company", required=True, help="Company name")
    analyse_cmd.add_argument("--sector", default=None, help="PSX sector (optional)")
    analyse_cmd.add_argument("--output", default="results/", help="Output directory")
    analyse_cmd.add_argument("--api-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY)")

    # ── validate subcommand ───────────────────────────────────────────────
    validate_cmd = subparsers.add_parser("validate", help="Validate extraction accuracy")
    validate_cmd.add_argument("--ground-truth", required=True, help="Ground truth JSON directory")
    validate_cmd.add_argument("--extractions", required=True, help="Directory of extraction JSON files")
    validate_cmd.add_argument("--output-csv", default="validation_results.csv")
    validate_cmd.add_argument("--tolerance", type=float, default=2.0, help="Error tolerance %%")

    args = parser.parse_args()

    if args.command == "analyse":
        result = run_analysis(
            pdf_path=args.pdf,
            company_name=args.company,
            sector=args.sector,
            output_dir=args.output,
            api_key=args.api_key,
        )
        # Print summary to stdout
        print("\n" + result["analyst_summary"])

    elif args.command == "validate":
        validator = GroundTruthValidator(tolerance_pct=args.tolerance)
        # Load all extraction JSONs
        extractions = {}
        for json_file in Path(args.extractions).glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            company = data.get("metadata", {}).get("company", json_file.stem)
            extractions[company] = data.get("financials", data)

        results = validator.batch_validate(
            ground_truth_dir=args.ground_truth,
            extractions=extractions,
            output_csv=args.output_csv,
        )
        for r in results:
            print(r.summary())

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
