import streamlit as st
import pandas as pd
import os

from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category
)

from src.company_pdf_exporter import build_company_pdf
from src.email_sender import send_pdf_via_email

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="All In One GRI Platform",
    layout="wide"
)

st.title("🏢 All In One GRI Platform — Companies Only")

# =========================================================
# SELECT COMPANY
# =========================================================
files = list_company_files()

if not files:
    st.error("❌ No company Excel files found in data/companies")
    st.stop()

company_file = st.selectbox("📂 Select Company File", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

# =========================================================
# SELECT CATEGORY
# =========================================================
categories = sorted(df["Category"].dropna().unique().tolist())

selected_category = st.selectbox(
    "📊 Select Sustainability Category",
    categories
)

cat_df = df[df["Category"] == selected_category]

# =========================================================
# TABS LAYOUT
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📑 Raw Data",
    "📌 KPI Dashboard",
    "📈 Trends & Insights",
    "📄 Professional Report"
])

# =========================================================
# TAB 1 — RAW DATA
# =========================================================
with tab1:
    st.subheader("📑 Company Raw Data")
    st.dataframe(cat_df, use_container_width=True)

# =========================================================
# TAB 2 — KPI DASHBOARD
# =========================================================
with tab2:
    st.subheader("📌 KPI Dashboard")

    kpis = compute_kpis_by_category(df, selected_category)

    if not kpis:
        st.warning("⚠️ No KPIs detected for this category.")
    else:
        cols = st.columns(len(kpis))
        for col, (k, v) in zip(cols, kpis.items()):
            col.metric(k, f"{v:,.2f}")

# =========================================================
# TAB 3 — TRENDS & INSIGHTS (FIXED)
# =========================================================
with tab3:
    st.subheader(f"📈 Sustainability Trends — {selected_category}")

    metric_col = None
    for c in cat_df.columns:
        if "metric" in c.lower():
            metric_col = c

    year_cols = [c for c in cat_df.columns if str(c).isdigit()]

    trends_summary = []

    if metric_col and year_cols:

        for _, row in cat_df.iterrows():
            metric_name = str(row[metric_col]).strip()

            values = pd.to_numeric(
                row[year_cols],
                errors="coerce"
            ).dropna()

            if len(values) < 2:
                continue

            # -------------------------------------
            # TREND CALCULATION
            # -------------------------------------
            delta = float(values.iloc[-1]) - float(values.iloc[0])

            chart_df = pd.DataFrame({
                "Year": year_cols[:len(values)],
                "Value": values.values
            }).set_index("Year")

            st.markdown(f"### 🔹 {metric_name}")
            st.line_chart(chart_df)

            # ✅ FIXED LOGIC (NO TERNARY)
            if delta < 0:
                st.success("📉 Decreasing trend — Environmental performance improving")
                trend_type = "Decreasing"
            elif delta > 0:
                st.warning("📈 Increasing trend — Attention required")
                trend_type = "Increasing"
            else:
                st.info("➖ Stable trend")
                trend_type = "Stable"

            trends_summary.append({
                "Metric": metric_name,
                "Trend": trend_type,
                "Start Year": year_cols[0],
                "End Year": year_cols[len(values)-1]
            })

    else:
        st.warning("⚠️ No trend data available for this category.")

# =========================================================
# TAB 4 — PROFESSIONAL PDF REPORT
# =========================================================
with tab4:
    st.subheader("📄 Generate Professional GRI Company Report")

    if st.button("✅ Generate Professional PDF Now"):
        pdf_buffer = build_company_pdf(
            company_name=company_name,
            category=selected_category,
            kpis=kpis,
            trends_data=trends_summary
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
