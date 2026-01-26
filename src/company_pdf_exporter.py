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
    if df is None or df.empty:
        return None

    df = df.copy()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").dropna()

    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(df.index, df["Value"], marker="o")
    ax.set_title(title)
    ax.grid(True)

    ymax = df["Value"].max()
    if pd.notna(ymax) and ymax > 0:
        ax.set_ylim(0, ymax * 1.2)

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================================
# ✅ Safe Gauge Generator
# ============================================
def gauge_image(value, max_value, title):
    if not isinstance(value, (int, float)) or pd.isna(value):
        return None

    if not isinstance(max_value, (int, float)) or pd.isna(max_value) or max_value <= 0:
        max_value = value * 1.2 if value > 0 else 1

    ratio = value / max_value
    color = "green" if ratio < 0.5 else "orange" if ratio < 0.8 else "red"

    fig, ax = plt.subplots(figsize=(4, 2))
    ax.barh([0], [value], color=color)
    ax.set_xlim(0, max_value)
    ax.set_title(title)
    ax.axis("off")

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    plt.close(fig)
    return buffer


# ============================================
# ✅ MAIN REPORT BUILDER (PDF SAFE)
# ============================================
def build_company_pdf(company_name, df, kpis, category=None):

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # =======================
    # COVER
    # =======================
    story.append(Paragraph(f"<para align='center'><b><font size=22>{company_name}</font></b></para>", styles["Title"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("GRI Sustainability Performance Report", styles["Heading2"]))
    story.append(PageBreak())

    # =======================
    # Detect Columns
    # =======================
    non_year_cols = [c for c in df.columns if not str(c).strip().isdigit()]
    metric_col = non_year_cols[0]

    year_cols = sorted([c for c in df.columns if str(c).strip().isdigit()], key=int)

    gri_map = {
        "Energy": "302",
        "Water": "303",
        "Emission": "305",
        "Emissions": "305",
        "Waste": "306"
    }

    # =======================
    # GRI Sections
    # =======================
    for cat_name, gri_code in gri_map.items():
        cat_df = df[df["Category"].str.lower().str.contains(cat_name.lower(), na=False)]
        if cat_df.empty:
            continue

        story.append(Paragraph(f"<b>GRI {gri_code} — {cat_name}</b>", styles["Heading1"]))
        story.append(Spacer(1, 10))

        # -------- KPI TABLE --------
        table_data = [["KPI", "Latest Value"]]
        for _, row in cat_df.iterrows():
            val = pd.to_numeric(row[year_cols[-1]], errors="coerce")
            if pd.notna(val):
                table_data.append([str(row[metric_col]), f"{val:,.2f}"])

        table = Table(table_data, colWidths=[260, 140])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 15))

        # -------- GAUGES --------
        latest_vals = pd.to_numeric(cat_df[year_cols[-1]], errors="coerce")
        max_val = latest_vals.max()

        for _, row in cat_df.iterrows():
            val = pd.to_numeric(row[year_cols[-1]], errors="coerce")
            if pd.isna(val):
                continue

            gbuf = gauge_image(float(val), max_val, str(row[metric_col]))
            if gbuf:
                story.append(Image(gbuf, width=320, height=120))
                story.append(Spacer(1, 10))

        # -------- TRENDS --------
        for _, row in cat_df.iterrows():
            values = pd.to_numeric(row[year_cols], errors="coerce").dropna()
            if len(values) < 2:
                continue

            trend_df = pd.DataFrame(
                {"Value": values.values},
                index=values.index.astype(int)
            )

            buf = generate_chart_image(trend_df, f"{row[metric_col]} Trend")
            if buf:
                story.append(Image(buf, width=420, height=180))
                story.append(Spacer(1, 10))

        # -------- PREDICTION --------
        for _, row in cat_df.iterrows():
            values = pd.to_numeric(row[year_cols], errors="coerce").dropna()
            if len(values) < 3:
                continue

            X = values.index.astype(int).values
            Y = values.values.astype(float)

            if np.any(np.isnan(Y)) or np.any(np.isinf(Y)):
                continue

            model = np.poly1d(np.polyfit(X, Y, 1))
            next_year = int(X.max()) + 1
            pred = float(model(next_year))

            story.append(
                Paragraph(
                    f"<b>{row[metric_col]} ({next_year} Prediction):</b> {pred:,.2f}",
                    styles["Normal"]
                )
            )

        story.append(PageBreak())

    # =======================
    doc.build(story)
    buffer.seek(0)
    return buffer
