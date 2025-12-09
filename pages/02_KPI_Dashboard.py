import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from src.data_loader import (
    list_available_years,
    get_kpi_block,
)

st.set_page_config(
    page_title="Sustainability KPI Dashboard",
    layout="wide",
)

# =========================
# ✅ YEAR SELECTION
# =========================
years_dict = list_available_years()

if not years_dict:
    st.error("❌ No Excel files found inside data/Excel folder.")
    st.stop()

years = sorted(list(years_dict.keys()))
selected_year = int(st.sidebar.selectbox("📅 Select Reporting Year", years))

# ✅ السنة السابقة تلقائي
prev_year = None
if selected_year in years:
    idx = years.index(selected_year)
    if idx > 0:
        prev_year = years[idx - 1]

# =========================
# ✅ LOAD KPI DATA (CURRENT YEAR)
# =========================
energy    = get_kpi_block(selected_year, "Energy")
water     = get_kpi_block(selected_year, "Water")
emission  = get_kpi_block(selected_year, "Emission")
waste     = get_kpi_block(selected_year, "Waste")

# =========================
# ✅ LOAD PREVIOUS YEAR (IF EXISTS)
# =========================
if prev_year:
    energy_prev   = get_kpi_block(prev_year, "Energy")
    water_prev    = get_kpi_block(prev_year, "Water")
    emission_prev = get_kpi_block(prev_year, "Emission")
    waste_prev    = get_kpi_block(prev_year, "Waste")
else:
    energy_prev = water_prev = emission_prev = waste_prev = None

# =========================
# ✅ SMART KPI CALCULATOR
# =========================
def smart_kpi(current, previous):
    if not previous or previous["total"] == 0:
        return current["total"], "N/A", "➖"

    diff = current["total"] - previous["total"]
    pct = (diff / previous["total"]) * 100

    arrow = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
    pct_text = f"{pct:.1f}%"

    return current["total"], pct_text, arrow


e_val, e_pct, e_arrow = smart_kpi(energy, energy_prev)
w_val, w_pct, w_arrow = smart_kpi(water, water_prev)
em_val, em_pct, em_arrow = smart_kpi(emission, emission_prev)
wa_val, wa_pct, wa_arrow = smart_kpi(waste, waste_prev)

# =========================
# ✅ HEADER
# =========================
st.title("📊 Sustainability KPI Dashboard")
st.caption("Smart KPI Cards + Drill-Down Analytics")

# =========================
# ✅ SMART KPI CARDS
# =========================
st.subheader("📌 Smart KPI Cards (YoY Comparison)")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("⚡ Energy (GRI 302)", f"{e_val:,.0f} {energy['unit']}", delta=f"{e_arrow} {e_pct}")
with k2:
    st.metric("💧 Water (GRI 303)", f"{w_val:,.0f} {water['unit']}", delta=f"{w_arrow} {w_pct}")
with k3:
    st.metric("🌍 Emissions (GRI 305)", f"{em_val:,.0f} {emission['unit']}", delta=f"{em_arrow} {em_pct}")
with k4:
    st.metric("♻️ Waste (GRI 306)", f"{wa_val:,.0f} {waste['unit']}", delta=f"{wa_arrow} {wa_pct}")

st.markdown("---")

# =========================
# ✅ MONTHLY TRENDS
# =========================
st.subheader("📈 Monthly KPI Trends")

def monthly_chart(title, monthly, unit):
    if not monthly:
        fig = go.Figure()
        fig.add_annotation(text="No Monthly Data", showarrow=False)
        return fig

    months = list(range(1, len(monthly) + 1))
    fig = px.line(
        x=months,
        y=monthly,
        markers=True,
        labels={"x": "Month", "y": unit},
        title=title,
    )
    fig.update_traces(mode="lines+markers")
    return fig

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

c1.plotly_chart(monthly_chart("Energy Trend", energy["monthly"], energy["unit"]), use_container_width=True)
c2.plotly_chart(monthly_chart("Water Trend", water["monthly"], water["unit"]), use_container_width=True)
c3.plotly_chart(monthly_chart("Emissions Trend", emission["monthly"], emission["unit"]), use_container_width=True)
c4.plotly_chart(monthly_chart("Waste Trend", waste["monthly"], waste["unit"]), use_container_width=True)

# =========================
# ✅ DRILL-DOWN ANALYTICS
# =========================
st.subheader("🔎 Smart Drill-Down Analytics")

kpi_map = {
    "Energy": energy,
    "Water": water,
    "Emissions": emission,
    "Waste": waste,
}

selected_kpi = st.selectbox("Select KPI for Drill-Down Analysis", list(kpi_map.keys()))
kpi_data = kpi_map[selected_kpi]

monthly_vals = kpi_data["monthly"]

if monthly_vals:
    months = list(range(1, len(monthly_vals) + 1))

    peak_value = max(monthly_vals)
    low_value = min(monthly_vals)
    avg_value = np.mean(monthly_vals)

    peak_month = months[monthly_vals.index(peak_value)]
    low_month = months[monthly_vals.index(low_value)]

    a1, a2, a3 = st.columns(3)

    a1.metric("🔺 Peak Month", f"Month {peak_month}", f"{peak_value:,.1f} {kpi_data['unit']}")
    a2.metric("🔻 Lowest Month", f"Month {low_month}", f"{low_value:,.1f} {kpi_data['unit']}")
    a3.metric("📉 Monthly Average", f"{avg_value:,.1f}", kpi_data["unit"])

    dist_fig = px.bar(
        x=months,
        y=monthly_vals,
        labels={"x": "Month", "y": kpi_data["unit"]},
        title=f"{selected_kpi} Monthly Distribution"
    )
    st.plotly_chart(dist_fig, use_container_width=True)

else:
    st.info("No monthly data available for this KPI.")

# =========================
# ✅ DRILL-DOWN RAW DATA
# =========================
st.subheader("🧾 Drill-Down Raw Data")

tab1, tab2, tab3, tab4 = st.tabs([
    "Energy Data", "Water Data", "Emissions Data", "Waste Data"
])

with tab1:
    st.dataframe(energy["raw"], use_container_width=True)
with tab2:
    st.dataframe(water["raw"], use_container_width=True)
with tab3:
    st.dataframe(emission["raw"], use_container_width=True)
with tab4:
    st.dataframe(waste["raw"], use_container_width=True)

# =========================================================
# ✅✅✅ EXPORT SECTION (USING OPENPYXL ONLY)
# =========================================================
st.markdown("---")
st.subheader("📤 Export")

# ---------- Export KPI Summary to Excel ----------
export_kpi_df = pd.DataFrame({
    "KPI": ["Energy", "Water", "Emissions", "Waste"],
    "Value": [energy["total"], water["total"], emission["total"], waste["total"]],
    "Unit": [energy["unit"], water["unit"], emission["unit"], waste["unit"]],
})

excel_buffer = BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    export_kpi_df.to_excel(writer, index=False, sheet_name="KPI Summary")

st.download_button(
    "⬇ Export KPI Summary (Excel)",
    data=excel_buffer.getvalue(),
    file_name=f"KPI_Summary_{selected_year}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ---------- Export FULL RAW DATA to Excel ----------
raw_buffer = BytesIO()
with pd.ExcelWriter(raw_buffer, engine="openpyxl") as writer:
    energy["raw"].to_excel(writer, sheet_name="Energy", index=False)
    water["raw"].to_excel(writer, sheet_name="Water", index=False)
    emission["raw"].to_excel(writer, sheet_name="Emissions", index=False)
    waste["raw"].to_excel(writer, sheet_name="Waste", index=False)

st.download_button(
    "⬇ Export Full Raw Data (Excel)",
    data=raw_buffer.getvalue(),
    file_name=f"Raw_Data_{selected_year}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ---------- Export Mini PDF Summary ----------
styles = getSampleStyleSheet()
pdf_buffer = BytesIO()
doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)

elements = [
    Paragraph("KPI Summary Report", styles["Title"]),
    Spacer(1, 12),
    Paragraph(f"Reporting Year: {selected_year}", styles["Normal"]),
    Spacer(1, 12),
]

for _, row in export_kpi_df.iterrows():
    elements.append(
        Paragraph(f"{row['KPI']}: {row['Value']} {row['Unit']}", styles["Normal"])
    )

doc.build(elements)

st.download_button(
    "⬇ Export Mini PDF Summary",
    data=pdf_buffer.getvalue(),
    file_name=f"KPI_Summary_{selected_year}.pdf",
    mime="application/pdf",
)
# =========================================================
# ✅✅✅ MULTI-YEAR COMPARISON (REPLACES EXECUTIVE)
# =========================================================
st.markdown("---")
st.subheader("📊 Year-to-Year KPI Comparison")

# ✅ اختيار KPI للمقارنة
compare_kpi = st.selectbox(
    "Select KPI to Compare Across Years",
    ["Energy", "Water", "Emissions", "Waste"]
)

# ✅ اختيار السنوات للمقارنة
compare_years = st.multiselect(
    "Select Years",
    years,
    default=years[-3:] if len(years) >= 3 else years
)

# ✅ دالة سحب القيم حسب السنة
def get_kpi_total_by_year(year, kpi_name):
    k = get_kpi_block(int(year), kpi_name)
    return k["total"]

# ✅ تجهيز الداتا
comparison_data = []
for y in compare_years:
    comparison_data.append(get_kpi_total_by_year(y, compare_kpi))

# ✅ رسم المقارنة
if compare_years and comparison_data:

    compare_fig = go.Figure()

    compare_fig.add_trace(
        go.Scatter(
            x=compare_years,
            y=comparison_data,
            mode="lines+markers",
            name=compare_kpi,
        )
    )

    compare_fig.update_layout(
        title=f"{compare_kpi} Comparison Across Years",
        xaxis_title="Year",
        yaxis_title=f"{compare_kpi} Value",
    )

    st.plotly_chart(compare_fig, use_container_width=True)

    # ✅ Bar Chart للمقارنة
    bar_fig = px.bar(
        x=compare_years,
        y=comparison_data,
        labels={"x": "Year", "y": f"{compare_kpi} Value"},
        title=f"{compare_kpi} Bar Comparison"
    )

    st.plotly_chart(bar_fig, use_container_width=True)

    # ✅ جدول أرقام المقارنة
    compare_df = pd.DataFrame({
        "Year": compare_years,
        f"{compare_kpi} Total": comparison_data
    })

    st.dataframe(compare_df, use_container_width=True)

else:
    st.info("Please select at least one year for comparison.")
