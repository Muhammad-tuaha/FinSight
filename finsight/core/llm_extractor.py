"""
FinSight — Gemini Extraction Pipeline
Sends parsed document text to Gemini and extracts structured financial figures
using Gemini's native Structured Outputs and Pydantic validation.

Upgraded with an automated exponential retry shield to absorb Free-Tier 503/429 constraints.
"""

import json
import logging
import os
import re
import time
from datetime import date
from typing import Any, Optional

# Import the modern Google GenAI SDK
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:

    class ResourceExhausted(Exception):
        """Fallback when google.api_core is not installed."""

from models.financial_schema import ExtractedFinancials
from core.pdf_parser import ParsedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

# 'gemini-2.5-flash' is the standard, lightning-fast model with free-tier access
MODEL = "gemini-2.5-flash"

# Maximum characters of document text to send.
# Gemini features an ultra-large 1-million token context window, so we can comfortably
# expand this limit compared to other models if you need to pull more pages.
MAX_CONTEXT_CHARS = 150_000


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior financial analyst specialising in Pakistani listed companies (PSX).
Your task is to extract specific financial figures from annual report text with precision.

Rules you must follow:
1. Extract ONLY figures that are explicitly stated in the provided text. Do not estimate or interpolate.
2. All monetary figures should be in the unit stated in the report (typically PKR thousands or millions).
   Do NOT convert units — extract the numeric magnitude only.
3. CRITICAL — Missing fields: If any line item, sub-statement, or single schema key is absent from the
   document, you MUST set that JSON field to null. Never omit keys, never use empty strings for numbers,
   and never skip an entire statement block because one field is missing. Other fields must still populate.
4. CRITICAL — Numeric format: Output all monetary values as JSON numbers (float), not strings.
   Thousands separators have been stripped in the source text (e.g. 25420000 not "25,420,000").
   Parentheses indicate negatives. Use null when a value is not disclosed.
5. PSX reports often present two years side-by-side (current year and prior year).
   Extract both. The more recent year is "current_period"; the earlier year is "prior_period".
6. Report your confidence as a float 0.0–1.0 in "extraction_confidence".
   Use 0.9+ only if figures were clearly stated in tabular format with labels matching the schema.
7. If figures appear inconsistent (e.g. gross_profit != revenue - COGS), note it in "extraction_notes".
8. Always populate current_period.company_name and current_period.reporting_period when inferable
   from the document header or column labels (e.g. "FY2024").
"""

EXTRACTION_PROMPT_TEMPLATE = """Extract financial data from the following annual report text.

Company name: {company_name}
Reporting sector (if known): {sector}

Populate the requested JSON structure accurately based on the text below.

--- ANNUAL REPORT TEXT START ---
{document_text}
--- ANNUAL REPORT TEXT END ---
"""

VISION_EXTRACTION_PROMPT = """Extract financial data from the attached scanned annual report page images.

Company name: {company_name}
Reporting sector (if known): {sector}

The PDF had little or no machine-readable text; these PNG renders are the authoritative source.
Read every table cell carefully. PSX reports often show current year and prior year side-by-side —
map the more recent column to current_period and the earlier column to prior_period.

For each image, use the page label in order (Page 1, Page 2, …) to locate balance sheet,
income statement, and cash flow figures. Output JSON numbers only (no formatted strings).
Use null for any line item not visible on the provided pages.
"""


# ---------------------------------------------------------------------------
# Post-parse numeric coercion (string "25,420,000" -> 25420000.0)
# ---------------------------------------------------------------------------

_NUMERIC_FIELD_RE = re.compile(
    r"^(revenue|cost_of_goods_sold|gross_profit|ebitda|ebit|finance_costs|"
    r"profit_|taxation|eps|cfo|cfi|cff|capex|free_cash_flow|net_change|"
    r"cash_|trade_|inventory|total_|short_term_|long_term_|property_|"
    r"intangible_|deferred_|reserves_|share_capital|operating_|depreciation)",
    re.I,
)


def _try_parse_numeric(value: Any) -> Any:
    if value is None or isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s.lower() in ("", "-", "—", "n/a", "na", "nil", "none", "-"):
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    s = s.replace(",", "").replace(" ", "")
    if s.endswith("%"):
        s = s[:-1]
    try:
        num = float(s)
        return -num if negative else num
    except ValueError:
        return value


def _coerce_numeric_tree(obj: Any, parent_key: str = "") -> Any:
    if isinstance(obj, dict):
        return {k: _coerce_numeric_tree(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_numeric_tree(item, parent_key) for item in obj]
    if isinstance(obj, str) and _NUMERIC_FIELD_RE.match(parent_key):
        return _try_parse_numeric(obj)
    return obj


# ---------------------------------------------------------------------------
# Extraction engine
# ---------------------------------------------------------------------------

def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, ResourceExhausted):
        return True
    if isinstance(exc, (ServerError, ClientError)):
        code = getattr(exc, "code", None)
        if code in (429, 503):
            return True
    msg = str(exc).lower()
    return "429" in msg or "resource exhausted" in msg or "quota" in msg


class LLMExtractor:
    """
    Wraps the Gemini API call and returns validated Pydantic ExtractedFinancials objects.
    Utilizes structural response schemas to guarantee valid JSON serialization.
    Features an automated retry shield to protect against free-tier rush-hour blocks.
    """

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. "
                "Set GEMINI_API_KEY environment variable or pass api_key."
            )
        # Initialize the modern standard client
        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _enrich_metadata(
        financials: ExtractedFinancials,
        document: ParsedDocument,
        company_name: str,
        sector: Optional[str],
    ) -> ExtractedFinancials:
        """Fill server-side metadata when the model omits optional fields."""
        from pathlib import Path

        updates = {}
        if not financials.source_file:
            updates["source_file"] = Path(document.source_path).name
        if not financials.extraction_date:
            updates["extraction_date"] = date.today().isoformat()
        if not financials.company_name:
            updates["company_name"] = company_name
        if not financials.sector and sector:
            updates["sector"] = sector

        cp = financials.current_period
        cp_updates = {}
        if not cp.company_name:
            cp_updates["company_name"] = company_name
        if not cp.reporting_period:
            cp_updates["reporting_period"] = "Unknown Period"
        if cp_updates:
            updates["current_period"] = cp.model_copy(update=cp_updates)

        if updates:
            return financials.model_copy(update=updates)
        return financials

    def _parse_gemini_response(
        self,
        response,
        document: ParsedDocument,
        company_name: str,
        sector: Optional[str],
    ) -> ExtractedFinancials:
        raw_json = response.text
        logger.debug(f"Raw Gemini response (first 500 chars): {raw_json[:500]}")
        payload = json.loads(raw_json)
        payload = _coerce_numeric_tree(payload)
        parsed = ExtractedFinancials.model_validate(payload)
        return self._enrich_metadata(
            parsed,
            document=document,
            company_name=company_name,
            sector=sector,
        )

    def _generate_with_retry(self, contents, *, mode_label: str) -> ExtractedFinancials:
        """Shared exponential backoff for text and vision Gemini calls."""
        max_attempts = 4
        base_delay = 3
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ExtractedFinancials,
            temperature=0.0,
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as e:
                last_error = e
                if not _is_rate_limit_error(e) or attempt == max_attempts:
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[{mode_label}] Rate limit (attempt {attempt}/{max_attempts}). "
                    f"Retrying in {delay}s…"
                )
                time.sleep(delay)

        raise last_error  # pragma: no cover

    def _extract_text(
        self,
        document: ParsedDocument,
        company_name: str,
        sector: Optional[str],
    ) -> ExtractedFinancials:
        doc_text = document.full_text[:MAX_CONTEXT_CHARS]
        if len(document.full_text) > MAX_CONTEXT_CHARS:
            logger.warning(
                f"Document text truncated from {len(document.full_text):,} "
                f"to {MAX_CONTEXT_CHARS:,} chars."
            )

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            company_name=company_name,
            sector=sector or "Not specified",
            document_text=doc_text,
        )
        response = self._generate_with_retry(prompt, mode_label="text")
        return self._parse_gemini_response(response, document, company_name, sector)

    def _extract_vision(
        self,
        document: ParsedDocument,
        company_name: str,
        sector: Optional[str],
    ) -> ExtractedFinancials:
        prompt_text = VISION_EXTRACTION_PROMPT.format(
            company_name=company_name,
            sector=sector or "Not specified",
        )

        parts: list[types.Part] = [types.Part.from_text(text=prompt_text)]
        for vp in document.visual_pages:
            label = f"Page {vp.page_number}"
            if vp.statement_type:
                label += f" [{vp.statement_type}]"
            parts.append(types.Part.from_text(text=f"--- {label} ---"))
            parts.append(types.Part.from_bytes(data=vp.png_bytes, mime_type="image/png"))

        logger.info(
            f"Vision extraction: {len(document.visual_pages)} image(s), "
            f"{sum(len(v.png_bytes) for v in document.visual_pages) / 1024:.0f} KB total"
        )

        contents = [types.Content(role="user", parts=parts)]
        response = self._generate_with_retry(contents, mode_label="vision")
        financials = self._parse_gemini_response(response, document, company_name, sector)

        note = (
            f"Extracted via Gemini vision fallback ({len(document.visual_pages)} scanned pages)."
        )
        if financials.extraction_notes:
            financials = financials.model_copy(
                update={"extraction_notes": f"{financials.extraction_notes} {note}"}
            )
        else:
            financials = financials.model_copy(update={"extraction_notes": note})
        return financials

    def extract(
        self,
        document: ParsedDocument,
        company_name: str = "Unknown Company",
        sector: Optional[str] = None,
    ) -> ExtractedFinancials:
        """
        Text pathway by default; multimodal vision when parser set visual_pages.
        """
        mode = getattr(document, "extraction_mode", "text") or "text"
        if document.visual_pages:
            logger.info(f"Extracting financials for: {company_name} via Gemini vision ({mode})")
            return self._extract_vision(document, company_name, sector)

        logger.info(f"Extracting financials for: {company_name} via Gemini text")
        return self._extract_text(document, company_name, sector)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def extract_financials(
    document: ParsedDocument,
    company_name: str = "Unknown Company",  
    sector: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ExtractedFinancials:
    """Top-level extraction entry point."""
    extractor = LLMExtractor(api_key=api_key)
    return extractor.extract(document, company_name=company_name, sector=sector)