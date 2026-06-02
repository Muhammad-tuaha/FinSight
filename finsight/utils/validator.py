"""
FinSight — Ground-Truth Validation Utility
Compares system-extracted figures against manually verified values.
Produces an accuracy spreadsheet and highlights deviations above threshold.
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Tolerance: flag if extracted value deviates more than this % from ground truth
DEFAULT_TOLERANCE_PCT = 2.0


@dataclass
class FieldResult:
    field_name: str
    ground_truth: Optional[float]
    extracted: Optional[float]
    abs_error: Optional[float]
    pct_error: Optional[float]
    within_tolerance: bool
    note: str = ""


@dataclass
class ValidationResult:
    company: str
    period: str
    field_results: list[FieldResult] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        return len(self.field_results)

    @property
    def extractable_fields(self) -> int:
        """Fields where ground truth is non-null."""
        return sum(1 for r in self.field_results if r.ground_truth is not None)

    @property
    def fields_within_tolerance(self) -> int:
        return sum(1 for r in self.field_results if r.within_tolerance and r.ground_truth is not None)

    @property
    def accuracy_pct(self) -> Optional[float]:
        if self.extractable_fields == 0:
            return None
        return (self.fields_within_tolerance / self.extractable_fields) * 100

    def summary(self) -> str:
        return (
            f"{self.company} ({self.period}): "
            f"{self.fields_within_tolerance}/{self.extractable_fields} fields "
            f"within tolerance — accuracy {self.accuracy_pct:.1f}%"
            if self.accuracy_pct is not None else "No ground truth available."
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class GroundTruthValidator:
    """
    Loads a ground-truth JSON file and compares against extracted figures.
    
    Ground truth JSON format:
    {
      "company": "Hub Power Company",
      "period": "FY2024",
      "figures": {
        "income_statement.revenue": 85234000,
        "income_statement.gross_profit": 12450000,
        "balance_sheet.total_assets": 220000000,
        ...
      }
    }
    """

    def __init__(self, tolerance_pct: float = DEFAULT_TOLERANCE_PCT):
        self.tolerance_pct = tolerance_pct

    def validate_from_file(
        self,
        ground_truth_path: str,
        extracted_financials_dict: dict,
    ) -> ValidationResult:
        """Load ground truth JSON and validate against extraction dict."""
        with open(ground_truth_path) as f:
            gt = json.load(f)
        return self.validate(gt, extracted_financials_dict)

    def validate(
        self,
        ground_truth: dict,
        extracted: dict,
    ) -> ValidationResult:
        """
        Compare ground truth figures against extracted figures.
        
        ground_truth: parsed ground truth dict with 'company', 'period', 'figures'
        extracted: dict representation of ExtractedFinancials (use .model_dump())
        """
        company = ground_truth.get("company", "Unknown")
        period = ground_truth.get("period", "Unknown")
        gt_figures: dict = ground_truth.get("figures", {})

        result = ValidationResult(company=company, period=period)

        for field_path, gt_value in gt_figures.items():
            extracted_value = self._get_nested(extracted, field_path)
            field_result = self._compare(field_path, gt_value, extracted_value)
            result.field_results.append(field_result)

        logger.info(result.summary())
        return result

    def _get_nested(self, data: dict, path: str) -> Optional[float]:
        """
        Navigate a dot-notation path through nested dicts.
        e.g. "current_period.income_statement.revenue"
        """
        keys = path.split(".")
        node = data
        for k in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(k)
        return node if isinstance(node, (int, float)) else None

    def _compare(
        self,
        field_name: str,
        ground_truth: Optional[float],
        extracted: Optional[float],
    ) -> FieldResult:
        if ground_truth is None:
            return FieldResult(
                field_name=field_name,
                ground_truth=None,
                extracted=extracted,
                abs_error=None,
                pct_error=None,
                within_tolerance=True,
                note="No ground truth — skipped",
            )

        if extracted is None:
            return FieldResult(
                field_name=field_name,
                ground_truth=ground_truth,
                extracted=None,
                abs_error=None,
                pct_error=None,
                within_tolerance=False,
                note="Field not extracted",
            )

        abs_error = abs(extracted - ground_truth)
        pct_error = (abs_error / abs(ground_truth)) * 100 if ground_truth != 0 else None
        within_tol = (pct_error is not None and pct_error <= self.tolerance_pct)

        return FieldResult(
            field_name=field_name,
            ground_truth=ground_truth,
            extracted=extracted,
            abs_error=abs_error,
            pct_error=pct_error,
            within_tolerance=within_tol,
            note=(
                f"ERROR: {pct_error:.2f}% deviation" if not within_tol
                else f"OK ({pct_error:.2f}%)"
            ),
        )

    def export_csv(self, result: ValidationResult, output_path: str) -> None:
        """Write validation results to a CSV for the accuracy spreadsheet."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "company", "period", "field",
                "ground_truth", "extracted",
                "abs_error", "pct_error_%",
                "within_tolerance", "note",
            ])
            writer.writeheader()
            for r in result.field_results:
                writer.writerow({
                    "company": result.company,
                    "period": result.period,
                    "field": r.field_name,
                    "ground_truth": r.ground_truth,
                    "extracted": r.extracted,
                    "abs_error": r.abs_error,
                    "pct_error_%": f"{r.pct_error:.2f}" if r.pct_error is not None else "",
                    "within_tolerance": r.within_tolerance,
                    "note": r.note,
                })
        logger.info(f"Validation CSV written: {output_path}")

    def batch_validate(
        self,
        ground_truth_dir: str,
        extractions: dict[str, dict],   # company_name -> extracted dict
        output_csv: str = "validation_results.csv",
    ) -> list[ValidationResult]:
        """
        Validate multiple reports. Expects ground truth JSON files in ground_truth_dir.
        Each file should be named <company>_<period>.json.
        """
        results = []
        gt_dir = Path(ground_truth_dir)

        for gt_file in sorted(gt_dir.glob("*.json")):
            with open(gt_file) as f:
                gt = json.load(f)
            company_key = gt.get("company", gt_file.stem)

            if company_key not in extractions:
                logger.warning(f"No extraction found for {company_key} — skipping.")
                continue

            result = self.validate(gt, extractions[company_key])
            results.append(result)

        # Aggregate CSV
        if results:
            all_rows = []
            for r in results:
                for fr in r.field_results:
                    all_rows.append({
                        "company": r.company,
                        "period": r.period,
                        "field": fr.field_name,
                        "ground_truth": fr.ground_truth,
                        "extracted": fr.extracted,
                        "abs_error": fr.abs_error,
                        "pct_error_%": f"{fr.pct_error:.2f}" if fr.pct_error is not None else "",
                        "within_tolerance": fr.within_tolerance,
                        "note": fr.note,
                    })

            with open(output_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
                writer.writeheader()
                writer.writerows(all_rows)

            overall_acc = [r.accuracy_pct for r in results if r.accuracy_pct is not None]
            if overall_acc:
                avg = sum(overall_acc) / len(overall_acc)
                logger.info(f"Batch validation complete. Average accuracy: {avg:.1f}%")

        return results
