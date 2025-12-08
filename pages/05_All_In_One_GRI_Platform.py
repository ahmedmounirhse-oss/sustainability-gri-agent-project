import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category,
    get_trend_data
)

from src.company_pdf_exporter import build_company_pdf
from src.email_sender import send_pdf_via_email


# =========================================
# ✅ PAGE CONFIG
# =========================================

st.set_page_config(page_title="All In One GRI Platform", layout="wide")
st.title("🏢 All In One GRI Platform — Companies")

# =========================================
# ✅ UNIT MAP
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
# ✅ RISK CLASSIFICATION
# =========================================

def classify_kpi(value):
    if value <= 30:
        return "Excellent", "green"
    elif value <= 70:
        return "Moderate", "orange"
    else:
        return "Risky", "red"


# =========================================
# ✅ SELECT COMPANY (ANALYSIS MODE)
# =========================================

files = list_company_files()

if not files:
    st.error("❌ No company Excel files found in data/companies")
    st.stop()

company_file = st.selectbox("📂 Select Company for Analysis", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

# =========================================
# ✅ SELECT CATEGORY
# =========================================

categories = sorted(df["Category"].dropna().unique().tolist())
selected_category = st.selectbox("📊 Select Sustainability Category", categories)

cat_df = df[df["Category"] == selected_category]

# =========================================
# ✅ RAW DATA
# =========================================

st.subheader("📑 Company Raw Data")
st.dataframe(cat_df, use_container_width=True)

# =========================================
# ✅ KPI GAUGES (WITH UNITS)
# =========================================

kpis = compute_kpis_by_category(df, selected_category)

st.subheader("📌 KPI Gauges Dashboard")

if not kpis:
    st.warning("⚠️ No KPIs detected for this category.")
else:
    cols = st.columns(3)
    i = 0

    for k, v in kpis.items():

        k_lower = k.lower()
        unit = ""

        for word, u in UNIT_MAP.items():
            if word in k_lower:
                unit = u
                break

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
# ✅ TRENDS
# =========================================

st.subheader(f"📈 Sustainability Trends — {selected_category}")

for metric in kpis.keys():

    trend_data = get_trend_data(df, selected_category, metric)
    if not trend_data:
        continue

    chart_df = pd.DataFrame({
        "Year": list(trend_data.keys()),
        "Value": list(trend_data.values())
    }).set_index("Year")

    chart_df = chart_df.apply(pd.to_numeric, errors="coerce").dropna()
    if len(chart_df) < 2:
        continue

    st.line_chart(chart_df)

    delta = chart_df.iloc[-1, 0] - chart_df.iloc[0, 0]

    if delta > 0:
        st.warning("📈 Insight: Environmental pressure is increasing.")
    elif delta < 0:
        st.success("✅ Insight: Environmental performance is improving.")
    else:
        st.info("⚖️ Insight: Performance is stable.")


# =========================================
# ✅ COMPANY COMPARISON
# =========================================

st.divider()
st.header("🔍 Company Performance Comparison")

col1, col2 = st.columns(2)

with col1:
    comp_a_file = st.selectbox("Company A", files, key="comp_a")
with col2:
    comp_b_file = st.selectbox("Company B", files, key="comp_b")

if comp_a_file and comp_b_file:

    df_a = load_company_file(comp_a_file)
    df_b = load_company_file(comp_b_file)

    kpis_a = compute_kpis_by_category(df_a, selected_category)
    kpis_b = compute_kpis_by_category(df_b, selected_category)

    st.subheader(f"⚖️ KPI Comparison — {selected_category}")

    for k in kpis_a.keys() & kpis_b.keys():

        val_a = kpis_a[k]
        val_b = kpis_b[k]

        fig = go.Figure()

        fig.add_trace(go.Bar(name=comp_a_file.replace(".xlsx", ""), x=[k], y=[val_a]))
        fig.add_trace(go.Bar(name=comp_b_file.replace(".xlsx", ""), x=[k], y=[val_b]))

        fig.update_layout(barmode="group", height=350)

        st.plotly_chart(fig, use_container_width=True)

        if val_a < val_b:
            st.success(f"✅ {comp_a_file.replace('.xlsx','')} performs better in {k}")
        elif val_b < val_a:
            st.success(f"✅ {comp_b_file.replace('.xlsx','')} performs better in {k}")
        else:
            st.info(f"⚖️ Both companies show similar performance in {k}")


# =========================================
# ✅ PDF EXPORT
# =========================================

st.divider()
st.subheader("📄 Generate Professional GRI Company Report")

if st.button("✅ Generate Professional PDF Now"):
    pdf_buffer = build_company_pdf(
        company_name=company_name,
        df=df,
        kpis=kpis,
        category=selected_category
    )

    st.session_state.company_pdf = pdf_buffer
    st.success("✅ Professional GRI PDF Generated Successfully")

if "company_pdf" in st.session_state:
    st.download_button(
        "⬇ Download Professional GRI Report",
        data=st.session_state.company_pdf.getvalue(),
        file_name=f"{company_name}_GRI_Report.pdf",
        mime="application/pdf"
    )

# =========================================
# ✅ EMAIL
# =========================================

st.subheader("📧 Send Report by Email")
email = st.text_input("Receiver Email")

if st.button("📨 Send by Email"):
    if "company_pdf" not in st.session_state:
        st.error("❌ Please generate the PDF first.")
    else:
        send_pdf_via_email(
            receiver_email=email,
            pdf_bytes=st.session_state.company_pdf.getvalue(),
            pdf_name=f"{company_name}_GRI_Report.pdf",
            year="Company GRI Report"
        )

        st.success("✅ Email Sent Successfully")
