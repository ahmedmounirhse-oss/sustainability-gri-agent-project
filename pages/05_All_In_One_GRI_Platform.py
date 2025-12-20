import streamlit as st
import pandas as pd

# =========================================
# IMPORTS FROM PROJECT
# =========================================
from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category
)

from src.report_generator import build_full_gri_report
from src.email_sender import send_pdf_via_email

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="All In One GRI Platform",
    layout="wide"
)

st.title("🏢 All In One GRI Sustainability Platform")

# =========================================
# SELECT COMPANY
# =========================================
files = list_company_files()

if not files:
    st.error("❌ No company Excel files found in data/companies")
    st.stop()

company_file = st.selectbox("📂 Select Company File", files)
company_name = company_file.replace(".xlsx", "")

df = load_company_file(company_file)

# =========================================
# SELECT CATEGORY
# =========================================
categories = sorted(df["Category"].dropna().unique().tolist())

selected_category = st.selectbox(
    "📊 Select Sustainability Category",
    categories
)

cat_df = df[df["Category"] == selected_category]

# =========================================
# KPI COMPUTATION
# =========================================
kpis = compute_kpis_by_category(df, selected_category)

# =========================================
# TABS LAYOUT
# =========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "📈 Year Comparison",
    "📂 Data Explorer",
    "📄 GRI Report",
    "📧 Email"
])

# =========================================================
# TAB 1 — DASHBOARD
# =========================================================
with tab1:
    st.subheader(f"📊 KPI Dashboard — {selected_category}")

    if not kpis:
        st.warning("⚠️ No KPIs detected for this category.")
    else:
        cols = st.columns(len(kpis))
        for col, (k, v) in zip(cols, kpis.items()):
            col.metric(k, f"{v:,.2f}")

    st.subheader("📈 KPI Trends")

    year_cols = [c for c in cat_df.columns if str(c).isdigit()]
    metric_col = next((c for c in cat_df.columns if "metric" in c.lower()), None)

    if metric_col and year_cols:
        for _, row in cat_df.iterrows():
            values = pd.to_numeric(row[year_cols], errors="coerce").dropna()
            if not values.empty:
                chart_df = pd.DataFrame({
                    "Year": year_cols[:len(values)],
                    "Value": values.values
                }).set_index("Year")

                st.markdown(f"**{row[metric_col]}**")
                st.line_chart(chart_df)

# =========================================================
# TAB 2 — YEAR COMPARISON
# =========================================================
with tab2:
    st.subheader("📈 Year-over-Year Comparison")

    year_cols = sorted([int(c) for c in cat_df.columns if str(c).isdigit()])

    if len(year_cols) < 2:
        st.info("ℹ️ Not enough years for comparison.")
    else:
        c1, c2 = st.columns(2)

        year_1 = c1.selectbox("Select First Year", year_cols, key="y1")
        year_2 = c2.selectbox("Select Second Year", year_cols, key="y2")

        if year_1 != year_2 and metric_col:
            comp_rows = []

            for _, row in cat_df.iterrows():
                try:
                    v1 = float(row[str(year_1)])
                    v2 = float(row[str(year_2)])
                    comp_rows.append({
                        "Metric": row[metric_col],
                        str(year_1): v1,
                        str(year_2): v2,
                        "Difference": v2 - v1
                    })
                except:
                    continue

            comp_df = pd.DataFrame(comp_rows)
            st.dataframe(comp_df, use_container_width=True)

# =========================================================
# TAB 3 — DATA EXPLORER
# =========================================================
with tab3:
    st.subheader("📂 Raw Sustainability Data")
    st.dataframe(cat_df, use_container_width=True)

# =========================================================
# TAB 4 — GRI REPORT
# =========================================================
with tab4:
    st.subheader("📄 Generate Professional GRI Report")

    if st.button("✅ Generate GRI PDF"):
        gri_data_dict = {
            "302": df[df["Category"].str.contains("Energy", case=False)],
            "303": df[df["Category"].str.contains("Water", case=False)],
            "305": df[df["Category"].str.contains("Emission", case=False)],
            "306": df[df["Category"].str.contains("Waste", case=False)],
        }

        pdf_buffer = build_full_gri_report(
            company_name=company_name,
            gri_data_dict=gri_data_dict
        )

        st.session_state.gri_pdf = pdf_buffer
        st.success("✅ Professional GRI Report Generated")

    if "gri_pdf" in st.session_state:
        st.download_button(
            "⬇ Download GRI Report",
            data=st.session_state.gri_pdf.getvalue(),
            file_name=f"{company_name}_GRI_Report.pdf",
            mime="application/pdf"
        )

# =========================================================
# TAB 5 — EMAIL
# =========================================================
with tab5:
    st.subheader("📧 Send Report via Email")

    receiver = st.text_input("Receiver Email")

    if st.button("📨 Send Report"):
        if "gri_pdf" not in st.session_state:
            st.error("❌ Generate the report first.")
        else:
            send_pdf_via_email(
                receiver_email=receiver,
                pdf_bytes=st.session_state.gri_pdf.getvalue(),
                pdf_name=f"{company_name}_GRI_Report.pdf",
                year="GRI Report"
            )
            st.success("✅ Email Sent Successfully")
