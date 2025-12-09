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


# ============================
# 📌 Generate Chart PNG
# ============================
def generate_chart_image(df, title):
    fig, ax = plt.subplots(figsize=(6, 3))
    df.plot(ax=ax, marker='o', linewidth=2)
    ax.set_title(title)
    ax.grid(True)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================
# 📌 Generate Gauge PNG
# ============================
def gauge_image(value, max_value, title):
    fig, ax = plt.subplots(figsize=(4, 2))
    color = "green" if value < max_value * 0.5 else "orange" if value < max_value * 0.8 else "red"
    ax.barh([0], [value], color=color)
    ax.set_xlim(0, max_value)
    ax.set_title(title)
    ax.grid(True, axis="x")
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================
# 📌 Main PDF Builder
# ============================
def build_company_pdf(company_name, df, kpis, category=None):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []


    # =======================================
    # 📄 COVER PAGE
    # =======================================
    story.append(Paragraph(f"<para align='center'><b><font size=22>{company_name}</font></b></para>", styles["Title"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<para align='center'>GRI Sustainability Performance Report</para>", styles["Heading2"]))
    story.append(Spacer(1, 30))

    img_path = "assets/company_logo.png"
    if os.path.exists(img_path):
        story.append(Image(img_path, width=300, height=120))
        story.append(Spacer(1, 40))

    story.append(Paragraph("<b>This report includes GRI Standards:</b><br/>302 – Energy<br/>303 – Water<br/>305 – Emissions<br/>306 – Waste", styles["Normal"]))
    story.append(PageBreak())


    # =======================================
    # 📘 PROCESS EACH GRI CATEGORY
    # =======================================
    gri_categories = {
        "Energy": "302",
        "Water": "303",
        "Emission": "305",
        "Waste": "306"
    }

    metrics_col = [c for c in df.columns if "metric" in c.lower()][0]
    year_cols = [c for c in df.columns if str(c).isdigit()]

    
    for cat_name, gri_code in gri_categories.items():

        cat_df = df[df["Category"] == cat_name]
        if cat_df.empty:
            continue

        story.append(Paragraph(f"<b>GRI {gri_code} — {cat_name}</b>", styles["Heading1"]))
        story.append(Spacer(1, 12))


        # ----------------------------------------
        # 📌 KPI Table Section
        # ----------------------------------------
        story.append(Paragraph("<b>KPI Summary</b>", styles["Heading2"]))
        kpi_data = [["KPI", "Value"]]

        for _, row in cat_df.iterrows():
            metric = row[metrics_col]
            latest_val = row[year_cols[-1]]
            kpi_data.append([metric, f"{latest_val:,.2f}"])

        table = Table(kpi_data, colWidths=[220, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#E6F2FF")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))


        # ----------------------------------------
        # 📌 Gauges Section
        # ----------------------------------------
        story.append(Paragraph("<b>Performance Gauges</b>", styles["Heading2"]))

        max_val = max([float(row[year_cols[-1]]) for _, row in cat_df.iterrows()])

        for _, row in cat_df.iterrows():
            metric = row[metrics_col]
            value = row[year_cols[-1]]

            g_buf = gauge_image(float(value), max_val, metric)
            story.append(Image(g_buf, width=350, height=120))
            story.append(Spacer(1, 10))


        # ----------------------------------------
        # 📌 Trend Charts
        # ----------------------------------------
        story.append(Paragraph("<b>Trend Analysis</b>", styles["Heading2"]))

        for _, row in cat_df.iterrows():

            metric = row[metrics_col]
            values = pd.to_numeric(row[year_cols], errors="coerce")

            trend_df = pd.DataFrame({"Year": year_cols, "Value": values})
            trend_df = trend_df.set_index("Year")

            chart_buf = generate_chart_image(trend_df, f"{metric} Trend Over Years")
            story.append(Image(chart_buf, width=400, height=180))
            story.append(Spacer(1, 15))


        # ----------------------------------------
        # 📌 Prediction (Linear Regression)
        # ----------------------------------------
        story.append(Paragraph("<b>Next-Year Performance Prediction</b>", styles["Heading2"]))

        for _, row in cat_df.iterrows():

            metric = row[metrics_col]
            values = pd.to_numeric(row[year_cols], errors="coerce")

            X = np.array([int(y) for y in year_cols])
            Y = values.values

            model = np.poly1d(np.polyfit(X, Y, 1))
            next_year = int(year_cols[-1]) + 1
            pred = model(next_year)

            story.append(Paragraph(f"<b>{metric} ({next_year}):</b> {pred:,.2f}", styles["Normal"]))


        # ----------------------------------------
        # 📌 Anomaly Detection
        # ----------------------------------------
        story.append(Paragraph("<b>Anomaly Check</b>", styles["Heading2"]))

        for _, row in cat_df.iterrows():

            metric = row[metrics_col]
            values = pd.to_numeric(row[year_cols], errors="coerce")

            mean = values.mean()
            std = values.std()

            anomalies = [y for y, v in zip(year_cols, values) if abs(v - mean) > 2 * std]

            if anomalies:
                story.append(Paragraph(f"<b>{metric} anomalies:</b> {', '.join(anomalies)}", styles["Normal"]))
            else:
                story.append(Paragraph(f"<b>{metric}:</b> No anomalies detected.", styles["Normal"]))

        story.append(PageBreak())


    # =======================================
    # 📘 FINAL SUMMARY PAGE
    # =======================================
    story.append(Paragraph("<b>Overall Sustainability Summary</b>", styles["Heading1"]))
    story.append(Spacer(1, 15))

    story.append(Paragraph("This automated GRI report includes full KPI evaluation, trends, prediction, and anomaly detection for categories 302, 303, 305, 306.", styles["Normal"]))
    story.append(Spacer(1, 15))


    doc.build(story)
    buffer.seek(0)
    return buffer
