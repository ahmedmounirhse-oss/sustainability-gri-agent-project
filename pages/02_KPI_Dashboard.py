import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category
)

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(page_title="Advanced KPI Dashboard", layout="wide")
st.title("📊 Advanced KPI Dashboard — Gauges | Comparison | Prediction | Anomaly")

# =========================================
# SELECT COMPANY
# =========================================
files = list_company_files()

if not files:
    st.error("❌ No company files found in data/companies")
    st.stop()

company_file = st.selectbox("📂 Select Company", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

# =========================================
# SELECT CATEGORY
# =========================================
categories = sorted(df["Category"].dropna().unique().tolist())
selected_category = st.selectbox("📊 Select Sustainability Category", categories)

cat_df = df[df["Category"] == selected_category]

# =========================================
# KPI GAUGES
# =========================================
st.subheader("📌 KPI Gauges")

kpis = compute_kpis_by_category(df, selected_category)

UNIT_MAP = {
    "energy": "GJ",
    "electric": "MWh",
    "water": "m³",
    "emission": "tCO₂e",
    "carbon": "tCO₂e",
    "waste": "tons",
    "intensity": "kg/BOE"
}

def classify_kpi(value):
    if value <= 30:
        return "Excellent", "green"
    elif value <= 70:
        return "Moderate", "orange"
    else:
        return "Risky", "red"

if kpis:
    cols = st.columns(3)
    i = 0
    for k, v in kpis.items():

        unit = ""
        for word, u in UNIT_MAP.items():
            if word in k.lower():
                unit = u
                
        status, color = classify_kpi(v)

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(v),
            number={"suffix": f" {unit}"},
            title={"text": f"{k}<br><span style='color:{color}'>{status}</span>"},
            gauge={
                "axis": {"range": [0, max(100, v * 1.5)]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 30], "color": "#9be7a1"},
                    {"range": [30, 70], "color": "#ffd966"},
                    {"range": [70, 100], "color": "#f28b82"}
                ]
            }
        ))

        with cols[i % 3]:
            st.plotly_chart(fig, use_container_width=True)
        i += 1

# =========================================
# YEAR-TO-YEAR COMPARISON
# =========================================
st.subheader("📅 Year-to-Year KPI Comparison")

metric_col = None
for col in cat_df.columns:
    if "metric" in col.lower():
        metric_col = col

year_cols = sorted([c for c in cat_df.columns if str(c).isdigit()])

if metric_col and len(year_cols) >= 2:

    year_a = st.selectbox("Select First Year", year_cols, key="y1")
    year_b = st.selectbox("Select Second Year", year_cols, key="y2")

    comp_df = cat_df[[metric_col, year_a, year_b]].dropna()

    for _, row in comp_df.iterrows():

        fig = go.Figure()
        fig.add_trace(go.Bar(name=str(year_a), x=[row[metric_col]], y=[row[year_a]]))
        fig.add_trace(go.Bar(name=str(year_b), x=[row[metric_col]], y=[row[year_b]]))

        fig.update_layout(barmode="group", height=350, title=row[metric_col])
        st.plotly_chart(fig, use_container_width=True)

        delta = row[year_b] - row[year_a]

        if delta > 0:
            st.warning(f"📈 {row[metric_col]} increased by {round(delta, 2)}")
        elif delta < 0:
            st.success(f"✅ {row[metric_col]} decreased by {round(abs(delta), 2)}")
        else:
            st.info(f"⚖️ {row[metric_col]} remained stable")

# =========================================
# KPI PREDICTION
# =========================================
st.subheader("🔮 KPI Prediction for Next Year")

if metric_col and len(year_cols) >= 3:

    next_year = int(year_cols[-1]) + 1

    for _, row in cat_df.iterrows():

        values = pd.to_numeric(row[year_cols], errors="coerce").dropna()

        if len(values) < 3:
            continue

        x = np.array([int(y) for y in year_cols[:len(values)]])
        y = values.values

        coeff = np.polyfit(x, y, 1)
        model = np.poly1d(coeff)

        predicted_value = model(next_year)

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=year_cols[:len(values)], y=y, mode="lines+markers", name="Historical"))
        fig.add_trace(go.Scatter(x=[str(next_year)], y=[predicted_value],
                                 mode="markers", marker=dict(size=12, color="red"),
                                 name="Predicted"))

        fig.update_layout(title=row[metric_col])
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"🔮 Predicted {row[metric_col]} in {next_year}: {round(predicted_value, 2)}")

# =========================================
# YEARLY ANOMALY DETECTION + EXPLANATION + PDF
# =========================================
st.markdown("---")
st.subheader("🚨 Anomaly Detection (Yearly KPIs)")

if kpis:

    anomaly_metric = st.selectbox("Select KPI for Anomaly Analysis", list(kpis.keys()))

    selected_row = cat_df[cat_df[metric_col] == anomaly_metric]

    if not selected_row.empty and len(year_cols) >= 3:

        values = pd.to_numeric(selected_row[year_cols].iloc[0], errors="coerce").dropna()
        years = [int(y) for y in year_cols[:len(values)]]
        values_arr = values.values

        mean_val = values_arr.mean()
        std_val = values_arr.std()
        z_scores = (values_arr - mean_val) / std_val

        anomaly_idx = np.where(np.abs(z_scores) > 1.8)[0]

        # ===== PLOT =====
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=values_arr, mode="lines+markers", name="Values"))

        if len(anomaly_idx) > 0:
            fig.add_trace(go.Scatter(
                x=[years[i] for i in anomaly_idx],
                y=[values_arr[i] for i in anomaly_idx],
                mode="markers",
                marker=dict(size=12, color="red"),
                name="Anomalies"
            ))

        fig.update_layout(title=f"{anomaly_metric} — Yearly Anomaly Detection")
        st.plotly_chart(fig, use_container_width=True)

        # ===== EXPLANATION =====
        anomaly_records = []
        explanations = []

        latest_kpi_value = kpis[anomaly_metric]

        for idx in anomaly_idx:
            year = years[idx]
            val = values_arr[idx]

            if val > mean_val:
                exp = f"In {year}, {anomaly_metric} spiked significantly above expected environmental levels."
            else:
                exp = f"In {year}, {anomaly_metric} dropped sharply below typical performance."

            explanations.append(exp)

            anomaly_records.append([
                str(year),
                round(val, 2),
                round(val - mean_val, 2),
                exp
            ])

        if not anomaly_records:
            st.success("✅ No anomalies detected.")
        else:
            st.error("⚠️ Environmental anomalies detected:")
            for exp in explanations:
                st.warning("• " + exp)

            # KPI RISK LINK
            if latest_kpi_value <= 30:
                risk_status = "Excellent (Low Risk)"
            elif latest_kpi_value <= 70:
                risk_status = "Moderate (Medium Risk)"
            else:
                risk_status = "Risky (High Risk)"

            st.info(f"🔗 Current KPI Value ({latest_kpi_value}) indicates: {risk_status}")

            # ========== EXPORT PDF ==========
            if st.button("📄 Export Anomaly Report PDF"):

                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                styles = st.get_option("theme.base") or {}

                elements = []
                elements.append(Paragraph("Anomaly Detection Report", st.styles["title"]))
                elements.append(Spacer(1, 10))

                table_data = [["Year", "Value", "Deviation", "Explanation"]]
                table_data.extend(anomaly_records)

                table = Table(table_data, colWidths=[60, 80, 80, 260])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0,0), (-1,-1), 1, colors.black)
                ]))

                elements.append(table)
                doc.build(elements)
                buffer.seek(0)

                st.download_button(
                    "⬇ Download Anomaly PDF Report",
                    data=buffer.getvalue(),
                    file_name=f"{company_name}_{anomaly_metric}_Anomaly_Report.pdf",
                    mime="application/pdf"
                )
