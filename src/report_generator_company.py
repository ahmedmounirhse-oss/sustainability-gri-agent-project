from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet

def build_company_gri_pdf(company_name, df, kpis):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    report = []

    report.append(Paragraph(f"GRI Sustainability Report", styles["Title"]))
    report.append(Spacer(1, 12))
    report.append(Paragraph(f"Company: {company_name}", styles["Normal"]))
    report.append(Spacer(1, 12))

    report.append(Paragraph("Key Performance Indicators:", styles["Heading2"]))
    table_data = [["Metric", "Value"]] + [[k, str(v)] for k, v in kpis.items()]
    report.append(Table(table_data))
    report.append(Spacer(1, 20))

    report.append(Paragraph("Raw Data Snapshot:", styles["Heading2"]))
    report.append(Table([df.columns.tolist()] + df.head(5).values.tolist()))

    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    pdf.build(report)
    buffer.seek(0)
    return buffer
