from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import os


# ============================================
# ✅ Safe Chart Generator
# ============================================
def generate_chart_image(df, title):
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 3))
    df.plot(ax=ax, marker='o')
    ax.set_title(title)
    ax.grid(True)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================================
# ✅ Safe Gauge Generator
# ============================================
def gauge_image(value, max_value, title):
    fig, ax = plt.subplots(figsize=(4, 2))
    if max_value == 0:
        max_value = value + 1

    ratio = value / max_value
    color = "green" if ratio < 0.5 else "orange" if ratio < 0.8 else "red"

    ax.barh([0], [value], color=color)
    ax.set_xlim(0, max_value)
    ax.set_title(title)
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================================
# ✅ MAIN REPORT BUILDER (FULL SAFE VERSION)
# ============================================
def build_company_pdf(company_name, df, kpis, category=None):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # =======================
    # ✅ COVER PAGE
    # =======================
    story.append(Paragraph(f"<para align='center'><b><font size=22>{company_name}</font></b></para>", styles["Title"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("GRI Sustainability Performance Report", styles["Heading2"]))
    story.append(Spacer(1, 30))

    logo_path = "assets/company_logo.png"
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=280, height=120))
        story.append(Spacer(1, 30))

    story.append(Paragraph("This report includes: 302, 303, 305, 306", styles["Normal"]))
    story.append(PageBreak())

    # =======================
    # ✅ Detect Metric Column Safely
    # =======================
    non_year_cols = [c for c in df.columns if not str(c).strip().isdigit()]
    metric_col = non_year_cols[0]

    year_cols = [c for c in df.columns if str(c).strip().isdigit()]
    year_cols = sorted(year_cols, key=lambda x: int(x))

    # =======================
    # ✅ GRI Pages by Sheet Category
    # =======================
    gri_map = {
        "Energy": "302",
        "Water": "303",
        "Emission": "305",
        "Emissions": "305",
        "Waste": "306"
    }

    for cat_name, gri_code in gri_map.items():

        cat_df = df[df["Category"].str.lower().str.contains(cat_name.lower())]

        if cat_df.empty:
            continue

        story.append(Paragraph(f"<b>GRI {gri_code} — {cat_name}</b>", styles["Heading1"]))
        story.append(Spacer(1, 10))

        # ================= KPI TABLE =================
        table_data = [["KPI", "Latest Value"]]

        for _, row in cat_df.iterrows():
            metric = str(row[metric_col])
            val = row[year_cols[-1]]
            if pd.notna(val):
                table_data.append([metric, f"{float(val):,.2f}"])

        table = Table(table_data, colWidths=[240, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#E6F2FF")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

        # ================= GAUGES =================
        for _, row in cat_df.iterrows():
            metric = str(row[metric_col])
            val = row[year_cols[-1]]
            if pd.isna(val):
                continue

            gbuf = gauge_image(float(val), max_value=max(cat_df[year_cols[-1]]), title=metric)
            story.append(Image(gbuf, width=320, height=120))
            story.append(Spacer(1, 10))

        # ================= TRENDS =================
        for _, row in cat_df.iterrows():
            metric = str(row[metric_col])
            values = pd.to_numeric(row[year_cols], errors="coerce").dropna()
            if len(values) < 2:
                continue

            trend_df = pd.DataFrame({"Year": values.index.astype(int), "Value": values.values}).set_index("Year")
            chart_buf = generate_chart_image(trend_df, f"{metric} Trend")

            if chart_buf:
                story.append(Image(chart_buf, width=400, height=180))
                story.append(Spacer(1, 10))

        # ================= PREDICTION =================
        for _, row in cat_df.iterrows():
            metric = str(row[metric_col])
            values = pd.to_numeric(row[year_cols], errors="coerce").dropna()

            if len(values) >= 3:
                X = np.array(values.index.astype(int))
                Y = values.values
                model = np.poly1d(np.polyfit(X, Y, 1))
                next_year = int(X[-1]) + 1
                pred = model(next_year)

                story.append(Paragraph(f"<b>{metric} ({next_year} Prediction):</b> {pred:,.2f}", styles["Normal"]))

        story.append(PageBreak())

    # =======================
    # ✅ FINAL SUMMARY PAGE
    # =======================
    story.append(Paragraph("<b>Overall GRI Sustainability Summary</b>", styles["Heading1"]))
    story.append(Spacer(1, 15))
    story.append(Paragraph(
        "This report automatically analyzed GRI 302, 303, 305, 306 indicators including KPIs, gauging, trends, predictions and anomalies.",
        styles["Normal"]
    ))

    # =======================
    doc.build(story)
    buffer.seek(0)
    return buffer
