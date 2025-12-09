from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import os

# ============================================
#  PDF GENERATOR WITH FULL KPI + ESG + TRENDS
# ============================================

def generate_chart_image(df, title):
    """Generate PNG chart and return buffer"""
    fig, ax = plt.subplots(figsize=(6, 3))
    df.plot(ax=ax, marker='o')
    ax.set_title(title)
    ax.grid(True)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


def gauge_image(value, max_value, title):
    """Generate a simple gauge as PNG"""
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.barh([0], [value], color="green" if value < max_value * 0.5 else "orange" if value < max_value * 0.8 else "red")
    ax.set_xlim(0, max_value)
    ax.set_title(title)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


def build_company_pdf(company_name, df, kpis, category):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # ========================
    # COVER PAGE
    # ========================
    story.append(Paragraph(f"<para align='center'><b><font size=22>{company_name} — GRI Sustainability Report</font></b></para>", styles["Title"]))
    story.append(Spacer(1, 20))

    img_path = "assets/company_logo.png"
    if os.path.exists(img_path):
        story.append(Image(img_path, width=300, height=120))
        story.append(Spacer(1, 30))

    story.append(Paragraph(f"<b>Category:</b> {category}", styles["Heading2"]))
    story.append(PageBreak())

    # ======================
    # 1️⃣ KPI SMART CARDS
    # ======================
    story.append(Paragraph("<b>1. KPI Smart Summary</b>", styles["Heading2"]))
    data = [["KPI", "Latest Value"]]
    for k, v in kpis.items():
        data.append([k, f"{v:,.2f}"])

    table = Table(data, colWidths=[200, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#E6F2FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
    ]))
    story.append(table)
    story.append(PageBreak())

    # ======================
    # 2️⃣ KPI GAUGES
    # ======================
    story.append(Paragraph("<b>2. KPI Gauges</b>", styles["Heading2"]))

    for k, v in kpis.items():
        gauge_buf = gauge_image(v, max_value=max(list(kpis.values())), title=k)
        story.append(Image(gauge_buf, width=300, height=120))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ======================
    # 3️⃣ TRENDS + CHARTS
    # ======================
    story.append(Paragraph("<b>3. KPI Trends (Historical)</b>", styles["Heading2"]))

    all_years = [c for c in df.columns if str(c).isdigit()]
    metrics_col = [c for c in df.columns if "metric" in c.lower()][0]

    for metric in df["Metric"].unique():
        row = df[df["Metric"] == metric]

        values = pd.to_numeric(row[all_years].iloc[0], errors="ignore")
        trend_df = pd.DataFrame({"Year": all_years, "Value": values}).set_index("Year")

        chart_buf = generate_chart_image(trend_df, f"{metric} Trend")
        story.append(Image(chart_buf, width=400, height=180))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ======================
    # 4️⃣ ESG SCORE
    # ======================
    story.append(Paragraph("<b>4. ESG Score</b>", styles["Heading2"]))

    # Fake formula (should match page)
    esg_score = round(100 - (np.mean(list(kpis.values())) / max(kpis.values()) * 100), 2)

    story.append(Paragraph(f"<b>Overall ESG Score:</b> {esg_score}/100", styles["Normal"]))

    gauge_buf = gauge_image(esg_score, 100, title="ESG Score")
    story.append(Image(gauge_buf, width=350, height=120))

    story.append(PageBreak())

    # ======================
    # 5️⃣ NEXT YEAR PREDICTION
    # ======================
    story.append(Paragraph("<b>5. Next Year KPI Prediction</b>", styles["Heading2"]))

    for metric in df["Metric"].unique():
        row = df[df["Metric"] == metric]
        values = pd.to_numeric(row[all_years].iloc[0], errors="coerce")
        X = np.array([int(y) for y in all_years])
        Y = values.values

        model = np.poly1d(np.polyfit(X, Y, 1))
        next_year = int(all_years[-1]) + 1
        pred = model(next_year)

        story.append(Paragraph(f"<b>{metric} ({next_year}):</b> {pred:,.2f}", styles["Normal"]))

    story.append(PageBreak())

    # ======================
    # 6️⃣ ANOMALY DETECTION
    # ======================
    story.append(Paragraph("<b>6. Anomaly Detection</b>", styles["Heading2"]))

    for metric in df["Metric"].unique():
        row = df[df["Metric"] == metric]
        values = pd.to_numeric(row[all_years].iloc[0], errors="coerce")

        mean = values.mean()
        std = values.std()

        anomalies = [y for y, val in zip(all_years, values) if abs(val - mean) > 2 * std]

        if anomalies:
            story.append(Paragraph(f"<b>{metric} anomalies:</b> {', '.join(anomalies)}", styles["Normal"]))
        else:
            story.append(Paragraph(f"<b>{metric}:</b> No anomalies detected.", styles["Normal"]))

    # =============== END ===============
    doc.build(story)
    buffer.seek(0)
    return buffer
