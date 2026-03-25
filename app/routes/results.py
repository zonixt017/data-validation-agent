"""
app/routes/results.py — Displays validation results and generates PDF download.

Routes:
    GET /results          → Results page (reads from RESULT_STORE via session result_id)
    GET /results/download → Generate and stream PDF report
"""

from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.state import RESULT_STORE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PDF_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "report" / "pdf_template.html"


@router.get("/results", response_class=HTMLResponse)
async def results(request: Request):
    result_id = request.session.get("result_id")
    result = RESULT_STORE.get(result_id) if result_id else None
    if not result:
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(request, "results.html", result)


@router.get("/results/download")
async def download_pdf(request: Request):
    """Generate a PDF from the stored results and return as download."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    from io import BytesIO

    result_id = request.session.get("result_id")
    result = RESULT_STORE.get(result_id) if result_id else None
    if not result:
        return RedirectResponse("/", status_code=303)

    pass_rate = round(
        result["pass_count"] / result["total_records"] * 100, 1
    ) if result["total_records"] else 0

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    # Custom style for findings to allow word wrap
    styles.add(ParagraphStyle(name='FindingStyle',
                              parent=styles['Normal'],
                              alignment=TA_LEFT,
                              wordWrap='CJK'))

    # Title
    story.append(Paragraph("<b>Validation Report</b>", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # Summary Information
    story.append(Paragraph(f"<b>Run At:</b> {result['run_at']}", styles['Normal']))
    story.append(Paragraph(f"<b>Filename:</b> {result['filename']}", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Total Records:</b> {result['total_records']}", styles['Normal']))
    story.append(Paragraph(f"<b>Total Findings:</b> {result['total_findings']}", styles['Normal']))
    story.append(Paragraph(f"<b>Critical Findings:</b> {result['critical_count']}", styles['Normal']))
    story.append(Paragraph(f"<b>Warning Findings:</b> {result['warning_count']}", styles['Normal']))
    story.append(Paragraph(f"<b>Passed Records:</b> {result['pass_count']}", styles['Normal']))
    story.append(Paragraph(f"<b>Pass Rate:</b> {pass_rate:.1f}%", styles['Normal']))
    story.append(Paragraph(f"<b>Escalation Required:</b> {'Yes' if result['escalation_required'] else 'No'}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Findings
    if result["findings"]:
        story.append(PageBreak()) # Start findings on a new page
        story.append(Paragraph("<b>Detailed Findings:</b>", styles['h2']))
        story.append(Spacer(1, 0.1 * inch))
        for finding in result["findings"]:
            story.append(Paragraph(f"<b>Severity:</b> {finding.get('severity', '')}", styles['Normal']))
            story.append(Paragraph(f"<b>Rule:</b> {finding.get('rule', '')}", styles['Normal']))
            story.append(Paragraph(f"<b>Message:</b> {finding.get('message', '')}", styles['FindingStyle']))
            story.append(Paragraph(f"<b>Entity:</b> {finding.get('entity_id', '')}", styles['Normal']))
            story.append(Paragraph(f"<b>Field:</b> {finding.get('field', '')}", styles['Normal']))
            story.append(Paragraph(f"<b>Value:</b> {finding.get('value') or '—'}", styles['Normal']))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("No detailed findings to report.", styles['Normal']))

    # Findings by Entity
    if result["findings_by_entity"]:
        story.append(PageBreak()) # Start findings by entity on a new page
        story.append(Paragraph("<b>Findings by Entity:</b>", styles['h2']))
        story.append(Spacer(1, 0.1 * inch))
        for entity, findings_list in result["findings_by_entity"].items():
            story.append(Paragraph(f"<b>Entity:</b> {entity}", styles['h3']))
            for finding in findings_list:
                story.append(Paragraph(f"  - <b>Severity:</b> {finding.get('severity', '')}, <b>Rule:</b> {finding.get('rule', '')}, <b>Message:</b> {finding.get('message', '')}", styles['FindingStyle']))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("No findings grouped by entity.", styles['Normal']))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    safe_filename = result["filename"].replace(" ", "_").rstrip(".csv") + "_report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
