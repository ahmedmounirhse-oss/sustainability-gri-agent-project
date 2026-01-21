import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from executive_summary import generate_executive_summary

from src.gri_readiness import gri_readiness_score
from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category,
    get_trend_data
)
from src.company_pdf_exporter import build_company_pdf
from src.email_sender import send_pdf_via_email

from src.data_validation import normalize_numeric
from src.indicator_status import indicator_status
from src.ai_insight import generate_ai_insight

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(page_title="All In One GRI Platform", layout="wide")
st.title("🏢 All In One GRI Platform — Companies")

# =========================================
# UNIT MAP
# =========================================
UNIT_MAP = {
    "energy": "GJ",
    "electric": "MWh",
    "water": "m³",
    "emission": "tCO₂e",
    "carbon": "tCO₂e",
    "waste": "tons",
    "intensity": "kg/BOE"
}

# =========================================
# HELPERS
# =========================================
def classify_kpi(value):
    try:
        value = float(value)
    except Exception:
        return "N/A"

    if value <= 30:
        return "Excellent"
    elif value <= 70:
        return "Moderate"
    else:
        return "Risky"


def calculate_esg_score(kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    score, used = 0, 0
    for k, v in kpis.items():
        v = normalize_numeric(v)
        if v is None:
            continue

        for key, w in weights.items():
            if key in k.lower():
                score += max(0, 100 - v) * w
                used += w

    if used == 0:
        return 0, "N/A"

    final = round(score / used, 2)
    return final, classify_kpi(100 - final)

# =========================================
# COMPANY SELECTION
# =========================================
files = list_company_files()
if not files:
    st.error("❌ No company Excel files found")
    st.stop()

company_file = st.selectbox("📂 Select Company", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

categories = sorted(df["Category"].dropna().unique())
selected_category = st.selectbox("📊 Select Category", categories)
cat_df = df[df["Category"] == selected_category]

year_cols = sorted([c for c in df.columns if str(c).isdigit()])
kpis = compute_kpis_by_category(df, selected_category)

metric_col = next((c for c in cat_df.columns if "metric" in c.lower()), None)

# =========================================
# TABS
# =========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Data & KPIs",
    "🌍 ESG Score",
    "📈 Trends & Forecast",
    "📄 Reports",
    "🏭 Company Comparison",
    "📝 Executive Summary"
])

# =========================================
# TAB 1 — DATA & KPIs
# =========================================
with tab1:
    st.subheader("📑 Raw Data")
    st.dataframe(cat_df, use_container_width=True)

    st.subheader("📌 KPI Smart Cards (YOY)")
    if year_cols:
        cols = st.columns(len(kpis))
        latest = year_cols[-1]
        prev = year_cols[-2] if len(year_cols) > 1 else None

        for col, (k, _) in zip(cols, kpis.items()):
            row = cat_df[cat_df[metric_col] == k]
            if row.empty:
                continue

            latest_val = normalize_numeric(row.iloc[0][latest])
            prev_val = normalize_numeric(row.iloc[0][prev]) if prev else None
            delta = "N/A" if latest_val is None or prev_val is None else f"{latest_val - prev_val:+.2f}"

            col.metric(
                label=f"{k} ({latest})",
                value=f"{latest_val:,.2f}" if latest_val is not None else "N/A",
                delta=delta
            )

# =========================================
# TAB 2 — ESG SCORE + GAUGES
# =========================================
with tab2:
    score, status = calculate_esg_score(kpis)
    color = "green" if status == "Excellent" else "orange" if status == "Moderate" else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100"},
        title={"text": f"ESG Score — {status}"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}
    ))
    st.plotly_chart(fig, use_container_width=True)

# =========================================
# TAB 3 — TRENDS & FORECAST
# =========================================
with tab3:
    for metric in kpis:
        trend = get_trend_data(df, selected_category, metric)
        if trend:
            st.line_chart(pd.DataFrame(trend, index=["Value"]).T)

# =========================================
# TAB 4 — REPORTS & EMAIL
# =========================================
with tab4:
    if st.button("✅ Generate PDF"):
        pdf = build_company_pdf(company_name, df, kpis, selected_category)
        st.session_state.company_pdf = pdf
        st.success("PDF Generated")

    if "company_pdf" in st.session_state:
        st.download_button(
            "⬇ Download PDF",
            st.session_state.company_pdf.getvalue(),
            f"{company_name}_GRI_Report.pdf",
            "application/pdf"
        )

    email = st.text_input("📧 Receiver Email")
    if st.button("📨 Send Email"):
        send_pdf_via_email(
            email,
            st.session_state.company_pdf.getvalue(),
            f"{company_name}_GRI_Report.pdf",
            "GRI Report"
        )
        st.success("Email Sent")

# =========================================
# TAB 5 — COMPANY COMPARISON + AI + HEATMAP
# =========================================
with tab5:
    st.subheader("🏭 Company Comparison")
    compare_files = st.multiselect("Select companies to compare", files, default=[company_file])

    if len(compare_files) >= 2:
        rows = []
        for file in compare_files:
            comp_df = load_company_file(file)
            comp_name = file.replace(".xlsx", "")
            year_cols_c = sorted([c for c in comp_df.columns if str(c).isdigit()])

            for _, row in comp_df.iterrows():
                status, coverage = indicator_status(row[year_cols_c])
                rows.append({
                    "Company": comp_name,
                    "Indicator": row[metric_col],
                    "Status": status,
                    "Coverage %": coverage
                })

        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# =========================================
# TAB 6 — EXECUTIVE SUMMARY
# =========================================
with tab6:
    st.subheader("📝 Executive Summary")

    analysis = []
    for _, row in df.iterrows():
        status, coverage = indicator_status(row[year_cols])
        analysis.append({
            "indicator": row[metric_col],
            "status": status,
            "coverage": coverage
        })

    statuses = [i["status"] for i in analysis]
    readiness = gri_readiness_score(statuses)

    summary = generate_executive_summary(company_name, readiness, analysis)
    for line in summary:
        st.markdown(f"- {line}")
