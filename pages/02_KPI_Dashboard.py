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
# ✅ SMART KPI CALCULATOR (YOY)
# =========================
def smart_kpi(current, previous):
    if not previous or previous["total"] == 0:
        return current["total"], "N/A", "➖"

    diff = current["total"] - previous["total"]
    pct = (diff / previous["total"]) * 100

    arrow = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
    pct_text = f"{pct:.1f}%"

    return current["total"], pct_text, arrow

e_val, e_pct, e_arrow     = smart_kpi(energy, energy_prev)
w_val, w_pct, w_arrow     = smart_kpi(water, water_prev)
em_val, em_pct, em_arrow  = smart_kpi(emission, emission_prev)
wa_val, wa_pct, wa_arrow  = smart_kpi(waste, waste_prev)

# =========================
# ✅ HEADER
# =========================
st.title("📊 Sustainability KPI Dashboard")
st.caption("Smart KPI Cards + Gauges + YOY + Comparison + Anomaly + Prediction")

# =========================
# ✅ SMART KPI CARDS (YOY)
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
# ✅ KPI GAUGES
# =========================
st.subheader("🧭 KPI Gauges")

def draw_gauge(title, value, unit):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": f" {unit}"},
        title={"text": title},
        gauge={
            "axis": {"range": [0, max(100, value * 1.5)]},
            "bar": {"color": "#1f77b4"},
        }
    ))
    return fig

g1, g2, g3, g4 = st.columns(4)

g1.plotly_chart(draw_gauge("Energy", energy["total"], energy["unit"]), use_container_width=True)
g2.plotly_chart(draw_gauge("Water", water["total"], water["unit"]), use_container_width=True)
g3.plotly_chart(draw_gauge("Emissions", emission["total"], emission["unit"]), use_container_width=True)
g4.plotly_chart(draw_gauge("Waste", waste["total"], waste["unit"]), use_container_width=True)

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

st.markdown("---")

# =========================
# ✅ ANOMALY DETECTION (MONTHLY)
# =========================
st.subheader("🚨 Anomaly Detection (Monthly)")

anomaly_kpi = st.selectbox("Select KPI for Anomaly Detection", ["Energy", "Water", "Emissions", "Waste"])

kpi_map = {
    "Energy": energy,
    "Water": water,
    "Emissions": emission,
    "Waste": waste,
}

series = kpi_map[anomaly_kpi]["monthly"]

if series and len(series) >= 6:

    values = np.array(series)
    mean_val = values.mean()
    std_val = values.std()

    z = (values - mean_val) / std_val
    anomaly_idx = np.where(np.abs(z) > 2)[0]

    months = list(range(1, len(series) + 1))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=values, mode="lines+markers", name="Normal"))

    if len(anomaly_idx) > 0:
        fig.add_trace(go.Scatter(
            x=[months[i] for i in anomaly_idx],
            y=[values[i] for i in anomaly_idx],
            mode="markers",
            marker=dict(color="red", size=12),
            name="Anomalies"
        ))

    fig.update_layout(title=f"{anomaly_kpi} Monthly Anomaly Detection")
    st.plotly_chart(fig, use_container_width=True)

    if len(anomaly_idx) == 0:
        st.success("✅ No anomalies detected.")
    else:
        st.error("⚠️ Anomalies detected in these months:")
        for i in anomaly_idx:
            st.write(f"Month {i+1} → {values[i]:.2f} {kpi_map[anomaly_kpi]['unit']}")

else:
    st.info("Not enough monthly data for anomaly detection.")

st.markdown("---")

# =========================
# ✅ YEAR-TO-YEAR COMPARISON
# =========================
st.subheader("📊 Year-to-Year KPI Comparison")

compare_kpi = st.selectbox(
    "Select KPI to Compare Across Years",
    ["Energy", "Water", "Emissions", "Waste"]
)

compare_years = st.multiselect(
    "Select Years",
    years,
    default=years[-3:] if len(years) >= 3 else years
)

def get_kpi_total_by_year(year, kpi_name):
    k = get_kpi_block(int(year), kpi_name)
    return k["total"]

comparison_data = []
for y in compare_years:
    comparison_data.append(get_kpi_total_by_year(y, compare_kpi))

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

else:
    st.info("Please select at least one year for comparison.")

st.markdown("---")

# =========================
# ✅ ✅ ✅ PREDICTION FOR NEXT YEAR (NEW)
# =========================
st.subheader("🔮 KPI Prediction for Next Year")

predict_kpi = st.selectbox("Select KPI for Prediction", ["Energy", "Water", "Emissions", "Waste"])

hist_years = sorted(years)

hist_values = []
for y in hist_years:
    hist_values.append(get_kpi_total_by_year(y, predict_kpi))

if len(hist_years) >= 3:

    x = np.array(hist_years)
    y = np.array(hist_values)

    coeff = np.polyfit(x, y, 1)
    model = np.poly1d(coeff)

    next_year = hist_years[-1] + 1
    predicted_value = model(next_year)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist_years, y=y, mode="lines+markers", name="Historical"))
    fig.add_trace(go.Scatter(x=[next_year], y=[predicted_value],
                             mode="markers",
                             marker=dict(size=12, color="red"),
                             name="Predicted"))

    fig.update_layout(
        title=f"{predict_kpi} — Prediction for {next_year}",
        xaxis_title="Year",
        yaxis_title="Value"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.success(f"🔮 Predicted {predict_kpi} Value for {next_year}: {predicted_value:.2f}")

else:
    st.warning("Not enough historical data for prediction (minimum 3 years).")
