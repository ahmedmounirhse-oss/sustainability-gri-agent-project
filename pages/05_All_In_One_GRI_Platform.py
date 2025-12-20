import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category,
    get_trend_data
)

from src.company_pdf_exporter import build_company_pdf
from src.email_sender import send_pdf_via_email


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
# RISK CLASSIFICATION
# =========================================
def classify_kpi(value):
    if value <= 30:
        return "Excellent"
    elif value <= 70:
        return "Moderate"
    else:
        return "Risky"

# =========================================
# ESG SCORE
# =========================================
def calculate_esg_score(kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    score, used = 0, 0

    for k, v in kpis.items():
        for key, w in weights.items():
            if key in k.lower():
                score += max(0, 100 - float(v)) * w
                used += w

    if used == 0:
        return 0, "N/A"

    final = round(score / used, 2)
    return final, classify_kpi(100 - final)

# =========================================
# SELECT COMPANY
# =========================================
files = list_company_files()
company_file = st.selectbox("📂 Select Company", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

categories = sorted(df["Category"].unique())
selected_category = st.selectbox("📊 Select Category", categories)
cat_df = df[df["Category"] == selected_category]

metric_col = next(c for c in cat_df.columns if "metric" in c.lower())
year_cols = sorted([c for c in cat_df.columns if str(c).isdigit()])
kpis = compute_kpis_by_category(df, selected_category)

# =========================================
# TABS
# =========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "📈 Trends & Prediction",
    "📂 Data",
    "📄 Report",
    "📧 Email"
])

# =====================================================
# TAB 1 — DASHBOARD (KPIs + ESG + GAUGES)
# =====================================================
with tab1:
    st.subheader("📌 KPI Smart Cards")

    cols = st.columns(len(kpis))
    latest, prev = year_cols[-1], year_cols[-2] if len(year_cols) > 1 else None

    for col, (k, _) in zip(cols, kpis.items()):
        row = cat_df[cat_df[metric_col] == k]
        if row.empty:
            continue

        val = float(row[latest])
        delta = float(row[latest] - row[prev]) if prev else None
        col.metric(k, f"{val:,.2f}", f"{delta:+.2f}" if delta else None)

    st.divider()
    st.subheader("🌍 ESG Score")

    esg_score, esg_status = calculate_esg_score(kpis)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=esg_score,
        number={"suffix": " / 100"},
        title={"text": f"ESG Score — {esg_status}"},
        gauge={"axis": {"range": [0, 100]}}
    ))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📌 KPI Gauges")

    cols = st.columns(3)
    for i, (k, v) in enumerate(kpis.items()):
        unit = next((u for w, u in UNIT_MAP.items() if w in k.lower()), "")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(v),
            number={"suffix": f" {unit}"},
            title={"text": k},
            gauge={"axis": {"range": [0, max(100, v * 1.5)]}}
        ))
        cols[i % 3].plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 2 — TRENDS + PREDICTION
# =====================================================
with tab2:
    st.subheader("📈 Trends & Insights")

    for metric in kpis.keys():
        trend = get_trend_data(df, selected_category, metric)
        if not trend:
            continue

        tdf = pd.DataFrame({"Year": trend.keys(), "Value": trend.values()}).set_index("Year")
        st.markdown(f"### {metric}")
        st.line_chart(tdf)

        delta = tdf.iloc[-1, 0] - tdf.iloc[0, 0]
        st.success("Decreasing trend") if delta < 0 else st.warning("Increasing trend")

    st.subheader("🔮 Prediction")

    if len(year_cols) >= 3:
        next_year = int(year_cols[-1]) + 1
        for metric in kpis.keys():
            row = cat_df[cat_df[metric_col] == metric]
            values = pd.to_numeric(row[year_cols].iloc[0], errors="coerce").dropna()
            x = np.array(year_cols[:len(values)], dtype=int)
            y = values.values
            model = np.poly1d(np.polyfit(x, y, 1))
            st.info(f"{metric} forecast for {next_year}: {model(next_year):.2f}")

# =====================================================
# TAB 3 — RAW DATA
# =====================================================
with tab3:
    st.subheader("📂 Raw Data")
    st.dataframe(cat_df, use_container_width=True)

# =====================================================
# TAB 4 — REPORT
# =====================================================
with tab4:
    if st.button("Generate Professional GRI PDF"):
        pdf = build_company_pdf(company_name, df, kpis, selected_category)
        st.session_state.pdf = pdf
        st.success("PDF Generated")

    if "pdf" in st.session_state:
        st.download_button(
            "⬇ Download PDF",
            st.session_state.pdf.getvalue(),
            file_name=f"{company_name}_GRI_Report.pdf",
            mime="application/pdf"
        )

# =====================================================
# TAB 5 — EMAIL
# =====================================================
with tab5:
    email = st.text_input("Receiver Email")
    if st.button("Send Report"):
        send_pdf_via_email(
            email,
            st.session_state.pdf.getvalue(),
            f"{company_name}_GRI_Report.pdf",
            "GRI Report"
        )
        st.success("Email Sent")
