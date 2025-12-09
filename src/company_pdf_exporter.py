from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from io import BytesIO
import os

def build_company_pdf(company_name, df, kpis, category_scores, overall_score):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # ✅ COVER PAGE
    logo_path = os.path.join("assets", "company_logo.png")
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=60))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(company_name, styles["Title"]))
    elements.append(Paragraph("GRI Sustainability Report", styles["Title"]))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Overall ESG Score: {overall_score}/100", styles["Heading2"]))
    elements.append(PageBreak())

    # ✅ CATEGORY SCORES
    elements.append(Paragraph("ESG Category Scores", styles["Title"]))
    table_data = [["Category", "Score"]]
    for k, v in category_scores.items():
        table_data.append([k, v])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer
