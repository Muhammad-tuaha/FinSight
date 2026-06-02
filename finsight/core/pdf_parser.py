"""
FinSight — PDF Ingestion & Parsing Layer
Handles raw PDF reading, page classification, and structured text/table extraction.
Uses PyMuPDF (fitz) for fast text extraction and pdfplumber for table detection.
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Vision fallback — rasterize only financial (or heuristic) pages, not full document
THIN_TEXT_THRESHOLD = 100          # document-level signal for scanned PDFs
VISION_DPI = 200
MAX_VISION_PAGES = 20

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try importing PDF libraries; fail gracefully if not installed
# ---------------------------------------------------------------------------
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed. Install with: pip install pymupdf")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed. Install with: pip install pdfplumber")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageContent:
    page_number: int
    raw_text: str
    tables: list[list[list[str]]] = field(default_factory=list)  # list of tables; each table = list of rows
    is_financial_statement: bool = False
    statement_type: Optional[str] = None   # "income_statement" | "balance_sheet" | "cash_flow"


@dataclass
class VisualPage:
    """Rasterized financial statement page for Gemini vision extraction."""
    page_number: int                      # 1-based
    statement_type: Optional[str] = None
    png_bytes: bytes = b""


@dataclass
class ParsedDocument:
    source_path: str
    total_pages: int
    pages: list[PageContent]
    financial_pages: list[PageContent]   # subset — only pages classified as financial statements
    full_text: str                        # concatenated text of financial pages for LLM context
    visual_pages: list[VisualPage] = field(default_factory=list)
    extraction_mode: str = "text"         # "text" | "vision"


# ---------------------------------------------------------------------------
# Keywords used to classify pages
# ---------------------------------------------------------------------------

# Pages matching these are excluded even if financial keywords appear (notes, CSR, governance).
NEGATIVE_KEYWORDS = [
    "corporate social responsibility", "sustainability report", "board of directors",
    "pattern of shareholding", "corporate governance", "gratuity fund", "employee benefit",
    "independent auditor", "auditor's report", "statement of compliance",
    "code of conduct", "whistle blowing", "human resources", "health and safety",
    "environmental policy", "notice of annual general meeting", "proxy form",
    "form of proxy", "glossary of terms", "definitions and interpretations",
]

MIN_FINANCIAL_CONTEXT_CHARS = 400

STATEMENT_KEYWORDS = {
    "income_statement": [
        "profit and loss", "profit & loss", "income statement",
        "statement of comprehensive income", "statement of profit or loss",
        "revenue", "turnover", "cost of sales", "gross profit",
        "operating profit", "finance cost", "profit before tax",
        "profit after tax", "earnings per share",
    ],
    "balance_sheet": [
        "balance sheet", "statement of financial position",
        "total assets", "total liabilities", "shareholders equity",
        "share capital", "trade receivables", "trade payables",
        "property plant and equipment", "non-current assets", "current assets",
    ],
    "cash_flow": [
        "cash flow", "statement of cash flows",
        "cash from operations", "cash used in investing",
        "cash from financing", "operating activities",
        "investing activities", "financing activities",
        "net increase in cash", "net decrease in cash",
    ],
}


def _negative_page_score(text: str) -> int:
    text_lower = text.lower()
    return sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)


def _classify_page(text: str) -> tuple[bool, Optional[str]]:
    """
    Returns (is_financial, statement_type | None).
    Checks keyword density to reduce false positives from notes sections.
    """
    text_lower = text.lower()

    if _negative_page_score(text) >= 2:
        return False, None

    best_type = None
    best_score = 0

    for stmt_type, keywords in STATEMENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_type = stmt_type

    # Require at least 3 keyword hits to qualify as a financial statement page
    is_financial = best_score >= 3
    return is_financial, best_type if is_financial else None


def _collapse_comma_thousands(text: str) -> str:
    """25,420,000 -> 25420000"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", text)
    return text


def _collapse_space_thousands(text: str) -> str:
    """25 420 000 -> 25420000 (PSX / European grouping in PDF text)."""
    return re.sub(
        r"\b(\d{1,3}(?: \d{3})+)\b",
        lambda m: m.group(1).replace(" ", ""),
        text,
    )


def _sanitize_financial_numbers(text: str) -> str:
    """
    Normalize formatted integers before LLM extraction.
    Handles comma- and space-separated thousands; preserves decimals (e.g. 12.5%).
    """
    if not text:
        return text

    # Parenthetical negatives: (14 000 000) -> (-14000000) for model readability
    def _paren_repl(m: re.Match) -> str:
        inner = _collapse_space_thousands(_collapse_comma_thousands(m.group(1)))
        inner = inner.replace(" ", "")
        return f"(-{inner})"

    text = re.sub(r"\(\s*([\d, ]+)\s*\)", _paren_repl, text)
    text = _collapse_comma_thousands(text)
    text = _collapse_space_thousands(text)
    return text


def _sanitize_cell(cell: str) -> str:
    return _sanitize_financial_numbers(cell.strip()) if cell else ""


def _clean_text(text: str) -> str:
    """Normalise whitespace, PDF artefacts, and PSX number formatting."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    return _sanitize_financial_numbers(text)


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

class PDFParser:
    """
    Ingests a PSX annual report PDF and returns a ParsedDocument containing:
    - Raw text per page
    - Tables extracted via pdfplumber
    - Financial-statement pages classified and isolated
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = str(pdf_path)
        if not Path(self.pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse(self) -> ParsedDocument:
        logger.info(f"Parsing: {self.pdf_path}")

        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF required. pip install pymupdf")

        pages_text = self._extract_text_pymupdf()
        pages_tables = self._extract_tables_pdfplumber(len(pages_text))

        pages = []
        for i, raw_text in enumerate(pages_text):
            cleaned = _clean_text(raw_text)
            is_fin, stmt_type = _classify_page(cleaned)
            tables = pages_tables.get(i, [])
            pages.append(PageContent(
                page_number=i + 1,
                raw_text=cleaned,
                tables=tables,
                is_financial_statement=is_fin,
                statement_type=stmt_type,
            ))

        financial_pages = [p for p in pages if p.is_financial_statement]
        logger.info(
            f"Total pages: {len(pages)} | "
            f"Financial pages detected: {len(financial_pages)}"
        )

        full_text = self._build_llm_context(financial_pages)
        total_doc_chars = sum(len(p.raw_text) for p in pages)
        visual_pages: list[VisualPage] = []
        extraction_mode = "text"

        needs_vision = (
            len(full_text.strip()) < MIN_FINANCIAL_CONTEXT_CHARS
            or total_doc_chars < THIN_TEXT_THRESHOLD
        )

        if needs_vision:
            indices = self._select_vision_page_indices(pages, financial_pages)
            if not indices:
                raise ValueError(
                    f"Insufficient text ({len(full_text)} chars) and no pages available for vision fallback. "
                    "Upload a digital PDF or a scan with identifiable financial statement pages."
                )
            visual_pages = self._rasterize_pages(indices, pages)
            extraction_mode = "vision"
            logger.info(
                f"Vision fallback engaged: {len(visual_pages)} page image(s) at {VISION_DPI} DPI "
                f"(doc text={total_doc_chars} chars, financial context={len(full_text)} chars)"
            )
        elif len(full_text.strip()) < MIN_FINANCIAL_CONTEXT_CHARS:
            raise ValueError(
                f"Insufficient financial statement text extracted ({len(full_text)} chars). "
                f"Detected {len(financial_pages)} financial page(s) from {len(pages)} total."
            )

        stmt_types = {p.statement_type for p in financial_pages if p.statement_type}
        logger.info(f"Statement types isolated: {sorted(stmt_types)} | mode={extraction_mode}")

        return ParsedDocument(
            source_path=self.pdf_path,
            total_pages=len(pages),
            pages=pages,
            financial_pages=financial_pages,
            full_text=full_text,
            visual_pages=visual_pages,
            extraction_mode=extraction_mode,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_text_pymupdf(self) -> list[str]:
        """Extract raw text from each page using PyMuPDF."""
        texts = []
        doc = fitz.open(self.pdf_path)
        for page in doc:
            texts.append(page.get_text("text"))
        doc.close()
        return texts

    def _extract_tables_pdfplumber(self, n_pages: int) -> dict[int, list]:
        """
        Extract tables from every page using pdfplumber.
        Returns dict mapping page_index -> list of tables.
        Each table is a list of rows; each row is a list of cell strings.
        """
        tables_by_page: dict[int, list] = {}

        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber unavailable — table extraction skipped.")
            return tables_by_page

        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    raw_tables = page.extract_tables()
                    if raw_tables:
                        # Clean cell values
                        cleaned = []
                        for tbl in raw_tables:
                            cleaned_tbl = [
                                [_sanitize_cell(str(cell)) if cell else "" for cell in row]
                                for row in tbl
                            ]
                            cleaned.append(cleaned_tbl)
                        tables_by_page[i] = cleaned
                except Exception as e:
                    logger.debug(f"Table extraction failed on page {i+1}: {e}")

        return tables_by_page

    def _build_llm_context(self, financial_pages: list[PageContent]) -> str:
        """
        Combines text and table content from financial pages into a single
        prompt-ready string. Tables are serialised as pipe-delimited text.
        """
        chunks = []
        for p in financial_pages:
            header = f"=== PAGE {p.page_number} [{p.statement_type or 'financial'}] ==="
            chunks.append(header)
            chunks.append(p.raw_text)

            for t_idx, table in enumerate(p.tables):
                chunks.append(f"--- TABLE {t_idx + 1} ---")
                for row in table:
                    chunks.append(" | ".join(row))

        return "\n".join(chunks)

    def _select_vision_page_indices(
        self,
        pages: list[PageContent],
        financial_pages: list[PageContent],
    ) -> list[int]:
        """
        Return 0-based page indices to rasterize. Prefer keyword-classified financial pages;
        for fully scanned PDFs use a bounded heuristic (second half of the report).
        """
        if financial_pages:
            indices = sorted({p.page_number - 1 for p in financial_pages})
            return indices[:MAX_VISION_PAGES]

        total = len(pages)
        if total == 0:
            return []

        # PSX annual reports: statements usually appear in the latter half
        start = max(0, (total // 2) - 5)
        return list(range(start, total))[:MAX_VISION_PAGES]

    def _rasterize_pages(
        self,
        page_indices: list[int],
        pages: list[PageContent],
    ) -> list[VisualPage]:
        """Render selected pages to PNG bytes in memory (no disk writes)."""
        doc = fitz.open(self.pdf_path)
        matrix = fitz.Matrix(VISION_DPI / 72, VISION_DPI / 72)
        visual: list[VisualPage] = []

        try:
            for idx in page_indices:
                if idx < 0 or idx >= len(doc):
                    continue
                page = doc[idx]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                meta = pages[idx] if idx < len(pages) else None
                visual.append(VisualPage(
                    page_number=idx + 1,
                    statement_type=meta.statement_type if meta else None,
                    png_bytes=pix.tobytes("png"),
                ))
        finally:
            doc.close()

        return visual


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def parse_annual_report(pdf_path: str) -> ParsedDocument:
    """Top-level entry point. Returns a ParsedDocument ready for the LLM layer."""
    parser = PDFParser(pdf_path)
    return parser.parse()
