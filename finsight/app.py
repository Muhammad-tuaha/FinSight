"""
FinSight — Core Flask REST API Gateway
Handles multi-period financial document processing, local text extraction,
and high-fidelity institutional PDF analytics report generation.
"""

import io
import os
import sys
import logging
import time
from datetime import date

# Ensure finsight directory is in sys.path for relative imports on production servers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import core.pdf_parser as pdf_parser
from core.llm_extractor import extract_financials
from core.ratio_engine import compute_ratios, statements_complete, RATIO_FORMULAS
from core.red_flag_engine import detect_red_flags
from core.summary_generator import generate_summary
from utils.thresholds import ratio_status_label, ratio_status_color, ratio_status_class
from core.auth import require_firebase_auth, check_user_usage_limit, increment_user_usage


logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("FinSightAPI")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _ratios_to_dict(computed_metrics) -> dict:
    if hasattr(computed_metrics, "to_dict") and callable(computed_metrics.to_dict):
        return computed_metrics.to_dict()
    if isinstance(computed_metrics, dict):
        return computed_metrics
    if hasattr(computed_metrics, "__dict__"):
        return {k: v for k, v in vars(computed_metrics).items() if v is not None}
    return {}


def _count_populated_fields(period) -> int:
    """Count non-null line items across all statements for a period."""
    if period is None:
        return 0
    total = 0
    for block in (
        period.income_statement,
        period.balance_sheet,
        period.cash_flow,
    ):
        total += sum(1 for v in block.model_dump().values() if v is not None)
    return total


def extract_financials_with_retry(parsed_doc, company_name: str, sector: str):
    """
    Gemini extraction with app-level retry for rate limits (429 / ResourceExhausted).
    Primary backoff also runs inside llm_extractor._generate_with_retry.
    """
    max_attempts = 3
    base_delay = 2

    for attempt in range(1, max_attempts + 1):
        try:
            return extract_financials(parsed_doc, company_name=company_name, sector=sector)
        except RuntimeError as e:
            msg = str(e).lower()
            is_rate_limit = any(
                token in msg
                for token in ("429", "503", "overloaded", "resource exhausted", "quota")
            )
            if not is_rate_limit or attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Extraction rate-limited (attempt {attempt}/{max_attempts}). "
                f"Retrying in {delay}s…"
            )
            time.sleep(delay)


def _flags_to_payload(risk_report) -> list[dict]:
    raw_flags = getattr(risk_report, "flags", []) or []
    return [
        {
            "priority": getattr(f, "priority", "LOW"),
            "category": getattr(f, "category", ""),
            "title": getattr(f, "title", ""),
            "description": getattr(f, "description", ""),
        }
        for f in raw_flags
    ]


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    logger.info("Health status probe requested by frontend.")
    return jsonify({
        "status": "healthy",
        "timestamp": date.today().isoformat(),
        "engine": "Gemini-2.5-Flash Active Connection Pool",
    }), 200


@app.route('/api/v1/validate', methods=['POST'])
def validate_upload():
    """Pre-flight PDF check: format, financial page detection, minimum text."""
    if 'file' not in request.files:
        return jsonify({"valid": False, "message": "No file uploaded."}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return jsonify({"valid": False, "message": "Only PDF files are accepted."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, f"validate_{file.filename}")
    try:
        file.save(file_path)
        parsed_doc = pdf_parser.parse_annual_report(file_path)
        mode = getattr(parsed_doc, "extraction_mode", "text")
        vision_n = len(getattr(parsed_doc, "visual_pages", []) or [])
        msg = (
            f"PDF ready ({mode} mode, {vision_n} vision page(s))."
            if mode == "vision"
            else "PDF contains sufficient financial statement content."
        )
        return jsonify({
            "valid": True,
            "message": msg,
            "total_pages": parsed_doc.total_pages,
            "financial_pages": len(parsed_doc.financial_pages),
            "context_chars": len(parsed_doc.full_text),
            "extraction_mode": mode,
            "vision_pages": vision_n,
        }), 200
    except ValueError as e:
        return jsonify({"valid": False, "message": str(e)}), 200
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"valid": False, "message": f"Validation failed: {e}"}), 200
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.route('/api/v1/analyze', methods=['POST'])
@require_firebase_auth
def analyze_report():
    """Full pipeline: auth check → usage limit check → parse → extract → ratios → flags → narrative → increment usage."""
    logger.info(f"Incoming file parsing request captured on /api/v1/analyze for UID: {getattr(g, 'uid', 'unknown')}")

    # ── Check usage limit before running Gemini analysis pipeline ─────────────
    if hasattr(g, 'uid') and g.uid:
        allowed, user_data, err_msg = check_user_usage_limit(g.uid)
        if not allowed:
            logger.warning(f"User UID={g.uid} blocked by usage limit: plan={user_data.get('plan')}, reports_used={user_data.get('reports_used')}")
            return jsonify({
                "error": "Usage limit reached",
                "code": "LIMIT_REACHED",
                "message": err_msg or "Free trial accounts are limited to 2 document report analyses. Please upgrade.",
                "reports_used": user_data.get("reports_used", 2),
                "max_reports": 2,
                "plan": user_data.get("plan", "free"),
            }), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file stream detected in multiform request array."}), 400

    file = request.files['file']
    company_name = request.form.get('company_name', 'Unknown Enterprise')
    sector = request.form.get('sector', 'General Sector')

    logger.info(f"Triggering statement processing sequence for: {company_name} [{sector}]")

    file_path = os.path.join(UPLOAD_FOLDER, f"incoming_{file.filename}")

    try:
        file.save(file_path)
        logger.info(f"File cached successfully at destination: {file_path}")

        parsed_doc = pdf_parser.parse_annual_report(file_path)
        logger.info(
            f"PDF decoded. Pages: {parsed_doc.total_pages} | "
            f"Financial: {len(parsed_doc.financial_pages)} | "
            f"Mode: {parsed_doc.extraction_mode}"
            + (
                f" | Vision pages: {len(parsed_doc.visual_pages)}"
                if parsed_doc.visual_pages
                else ""
            )
        )

        financials = extract_financials_with_retry(
            parsed_doc, company_name=company_name, sector=sector
        )
        logger.info("Structured Pydantic financial schema returned from Gemini.")

        current_period = financials.current_period
        prior_period = financials.prior_period

        current_ratios = compute_ratios(current_period, sector=financials.sector or sector)
        prior_ratios = compute_ratios(prior_period, sector=financials.sector or sector) if prior_period else None

        risk_report = detect_red_flags(financials, current_ratios=current_ratios)
        narrative = generate_summary(
            financials,
            current_ratios,
            prior_ratios,
            risk_report,
        )

        ratios_dict = _ratios_to_dict(current_ratios)
        ratios_prior_dict = _ratios_to_dict(prior_ratios) if prior_ratios else None
        flags_payload = _flags_to_payload(risk_report)

        key_concerns = [
            f"[{f['priority']}] {f['title']}: {f['description']}"
            for f in flags_payload
        ]

        complete = statements_complete(current_period)
        ratio_count = len(ratios_dict)
        extracted_fields = _count_populated_fields(current_period)

        if ratio_count == 0:
            logger.warning(
                f"Zero ratios computed — populated extraction fields: {extracted_fields}, "
                f"statements_complete={complete}, financial_pages={len(parsed_doc.financial_pages)}"
            )

        # ── Atomically increment reports_used ONLY after successful pipeline execution ──
        if hasattr(g, 'uid') and g.uid:
            increment_user_usage(g.uid)

        return jsonify({
            "status": "success",
            "metadata": {
                "company_name": financials.company_name or company_name,
                "sector": financials.sector or sector,
                "reporting_period": current_period.reporting_period,
                "extraction_confidence": financials.extraction_confidence,
                "entity_confidence": getattr(financials, "entity_confidence", None),
                "sector_confidence": getattr(financials, "sector_confidence", None),
                "extraction_date": financials.extraction_date or date.today().isoformat(),
                "notes": financials.extraction_notes,
            },
            "data_quality": {
                "financial_pages": len(parsed_doc.financial_pages),
                "total_pages": parsed_doc.total_pages,
                "context_chars": len(parsed_doc.full_text),
                "statements_complete": complete,
                "ratios_computed_count": ratio_count,
                "has_prior_period": prior_period is not None,
                "insufficient_data": ratio_count == 0,
                "extracted_fields_count": extracted_fields,
                "extraction_mode": parsed_doc.extraction_mode,
                "vision_pages": len(parsed_doc.visual_pages),
            },
            "ratios": ratios_dict,
            "ratios_prior": ratios_prior_dict,
            "ratio_formulas": RATIO_FORMULAS,
            "red_flags": flags_payload,
            "risk_profile": {
                "high_severity_count": risk_report.high_count,
                "medium_severity_count": risk_report.medium_count,
                "low_severity_count": risk_report.low_count,
                "key_concerns": key_concerns,
            },
            "narrative_reports": {
                "executive_summary": narrative.executive_summary,
                "liquidity_commentary": narrative.liquidity_commentary,
                "profitability_commentary": narrative.profitability_commentary,
                "leverage_commentary": narrative.leverage_commentary,
                "cash_flow_commentary": narrative.cash_flow_commentary,
                "yoy_commentary": narrative.yoy_commentary,
                "full_formatted_text": narrative.full_text,
            },
            "summary": narrative.executive_summary,
        }), 200

    except ValueError as e:
        logger.warning(f"Validation / parsing rejected: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unhandled pipeline exception: {e}")
        return jsonify({"error": f"Internal pipeline execution failed: {str(e)}"}), 500

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("Upload sandbox file purged.")



@app.route('/api/v1/report', methods=['POST'])
@require_firebase_auth
def generate_pdf_report():
    """Stream PDF from in-memory buffer using live ratios, flags, and narrative."""
    data = request.get_json() or {}
    company = data.get('company_name', 'Specified Corporate Entity').strip()
    sector = data.get('sector', 'General Sector').strip().upper()
    ratios_payload = data.get('ratios') or {}
    flags_payload = data.get('red_flags') or []
    narrative = data.get('narrative_reports') or {}
    executive = narrative.get('executive_summary') or data.get('summary', '')

    try:
        logger.info(f"Generating analytics PDF for: {company}")
        buffer = io.BytesIO()

        disclaimer_text = (
            "This report is generated by an automated AI analysis pipeline and is provided for informational purposes only. "
            "It does not constitute financial or investment advice. Figures should be independently verified against the original source filing."
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=54,
        )

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
            fontSize=24, leading=28, textColor=colors.HexColor("#0f172a"), spaceAfter=4,
        )
        sub_title_style = ParagraphStyle(
            'DocSubtitle', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=10, leading=12, textColor=colors.HexColor("#0284c7"), spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            'DocMeta', parent=styles['Normal'], fontName='Helvetica-Oblique',
            fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=15,
        )
        section_heading = ParagraphStyle(
            'SectionHeading', parent=styles['Heading2'], fontName='Helvetica-Bold',
            fontSize=13, leading=16, textColor=colors.HexColor("#1e293b"),
            spaceBefore=16, spaceAfter=10, keepWithNext=True,
        )
        body_style = ParagraphStyle(
            'DocBody', parent=styles['Normal'], fontName='Helvetica',
            fontSize=10, leading=15, textColor=colors.HexColor("#334155"),
        )
        th_style = ParagraphStyle(
            'TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=9, leading=11, textColor=colors.HexColor("#1e293b"),
        )
        disclaimer_box_style = ParagraphStyle(
            'DisclaimerBox', parent=styles['Normal'], fontName='Helvetica',
            fontSize=8, leading=11, textColor=colors.HexColor("#64748b"),
        )

        def _fmt(val, is_pct=False):
            if val is None:
                return "N/A"
            return f"{val:.2f}%" if is_pct else f"{val:.2f}x"

        def _status_cell(key, val, is_pct=False):
            label = ratio_status_label(key, val)
            color = ratio_status_color(
                ratio_status_class(key, val) if val is not None else "N/A"
            )
            if label == "N/A":
                color = ratio_status_color("N/A")
            return Paragraph(f'<font color="{color}">{label}</font>', body_style)

        def _add_page_decorations(canvas, d):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
            canvas.setLineWidth(0.5)
            canvas.line(36, 44, 612 - 36, 44)

            footer_style = ParagraphStyle(
                'FooterDisclaimer',
                fontName='Helvetica-Oblique',
                fontSize=7,
                leading=9,
                textColor=colors.HexColor("#64748b"),
                alignment=1,
            )
            p = Paragraph(f"<b>Disclaimer:</b> {disclaimer_text}", footer_style)
            w, h = p.wrap(612 - 72, 35)
            p.drawOn(canvas, 36, 40 - h)
            canvas.restoreState()

        story.append(Paragraph(company.upper(), title_style))
        story.append(Paragraph(f"FINSIGHT BUSINESS ANALYTICS REPORT · {sector} SECTOR", sub_title_style))
        story.append(Paragraph(
            f"Generated {date.today().isoformat()} · Multi-Period PSX Disclosure Analysis",
            meta_style,
        ))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f172a"), spaceAfter=15))

        story.append(Paragraph("1. Executive Summary", section_heading))
        story.append(Paragraph(executive or "No executive summary available.", body_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("2. Performance Metrics Matrix", section_heading))

        metric_rows = [
            ('current_ratio', 'Current Liquidity Ratio', 'Liquidity', False),
            ('quick_ratio', 'Quick Ratio (Acid Test)', 'Liquidity', False),
            ('gross_margin', 'Gross Profit Margin', 'Profitability', True),
            ('net_margin', 'Net Profit Margin', 'Profitability', True),
            ('roe', 'Return on Equity (ROE)', 'Capital Efficiency', True),
            ('debt_to_equity', 'Debt-to-Equity', 'Leverage', False),
            ('interest_coverage', 'Interest Coverage', 'Debt Servicing', False),
            ('asset_turnover', 'Asset Turnover', 'Efficiency', False),
        ]

        ratio_data = [
            [
                Paragraph('<b>Metric</b>', th_style),
                Paragraph('<b>Category</b>', th_style),
                Paragraph('<b>Value</b>', th_style),
                Paragraph('<b>Status</b>', th_style),
            ],
        ]
        for key, label, category, is_pct in metric_rows:
            val = ratios_payload.get(key)
            ratio_data.append([
                Paragraph(label, body_style),
                Paragraph(category, body_style),
                Paragraph(_fmt(val, is_pct), body_style),
                _status_cell(key, val, is_pct),
            ])

        metric_table = Table(ratio_data, colWidths=[160, 130, 100, 110])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#94a3b8")),
            ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(metric_table)
        story.append(Spacer(1, 14))

        story.append(Paragraph("3. Risk Exceptions & Diagnostic Index", section_heading))

        flag_data = [
            [
                Paragraph('<b>Severity</b>', th_style),
                Paragraph('<b>Category</b>', th_style),
                Paragraph('<b>Description</b>', th_style),
            ],
        ]

        if flags_payload:
            badge_colors = {"HIGH": "#b91c1c", "MEDIUM": "#b45309", "LOW": "#0284c7"}
            for f in flags_payload:
                pri = f.get('priority', 'LOW')
                flag_data.append([
                    Paragraph(f'<font color="{badge_colors.get(pri, "#64748b")}">[{pri}]</font>', body_style),
                    Paragraph(f.get('title', ''), body_style),
                    Paragraph(f.get('description', ''), body_style),
                ])
        else:
            flag_data.append([
                Paragraph('—', body_style),
                Paragraph('No anomalies', body_style),
                Paragraph('Rule-based threshold scan did not flag material risks.', body_style),
            ])

        flag_table = Table(flag_data, colWidths=[75, 140, 325])
        flag_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#94a3b8")),
        ]))
        story.append(flag_table)

        if narrative.get('yoy_commentary'):
            story.append(Spacer(1, 12))
            story.append(Paragraph("4. Year-over-Year Trajectory", section_heading))
            story.append(Paragraph(narrative['yoy_commentary'], body_style))

        # Add inline disclaimer section block to document story
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=10))
        story.append(Paragraph(f"<b>DISCLAIMER:</b> {disclaimer_text}", disclaimer_box_style))

        doc.build(story, onFirstPage=_add_page_decorations, onLaterPages=_add_page_decorations)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{company.replace(' ', '_')}_Deep_Analysis_Report.pdf",
            mimetype='application/pdf',
        )

    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


if __name__ == '__main__':
    logger.info("Starting FinSight API on port 5000...")
    app.run(debug=True, host='127.0.0.1', port=5000)
