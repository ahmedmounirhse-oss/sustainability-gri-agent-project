import streamlit as st
import pandas as pd
import os

# =========================================
# ✅ TRY USING OLD data_loader.py
# =========================================
try:
    from src import data_loader
    USE_LOADER = True
except:
    USE_LOADER = False

# =========================================
# ✅ PATH FOR MONTHLY FILES
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# =========================================
# ✅ PAGE CONFIG
# =========================================
st.set_page_config(page_title="Monthly Data Explorer", layout="wide")
st.title("📊 Monthly Sustainability Data Explorer (Phase 1)")

# =========================================
# ✅ FILE SELECTION
# =========================================
files = []

if os.path.exists(DATA_DIR):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

if not files:
    st.error("❌ No Excel monthly files found in data folder")
    st.stop()

file_name = st.selectbox("📂 Select Monthly Sustainability File", files)
file_path = os.path.join(DATA_DIR, file_name)

# =========================================
# ✅ LOAD DATA
# =========================================
if USE_LOADER:
    df = pd.read_excel(file_path)
else:
    df = pd.read_excel(file_path)

expected_cols = {"Year", "Month", "Indicator", "Value"}

if not expected_cols.issubset(set(df.columns)):
    st.error("❌ File must contain: Year | Month | Indicator | Value")
    st.stop()

# =========================================
# ✅ SMART FILTERS (1)
# =========================================
st.subheader("🎯 Smart Filters")

col1, col2, col3 = st.columns(3)

with col1:
    year_filter = st.selectbox("Select Year", sorted(df["Year"].unique()))

with col2:
    indicator_filter = st.selectbox(
        "Select Indicator",
        sorted(df["Indicator"].astype(str).unique())
    )

filtered = df[
    (df["Year"] == year_filter) &
    (df["Indicator"] == indicator_filter)
]

months_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
filtered["Month"] = pd.Categorical(filtered["Month"], categories=months_order, ordered=True)
filtered = filtered.sort_values("Month")

with col3:
    month_filter = st.multiselect(
        "Select Months (Optional)",
        filtered["Month"].dropna().unique().tolist(),
        default=filtered["Month"].dropna().unique().tolist()
    )

filtered = filtered[filtered["Month"].isin(month_filter)]

# =========================================
# ✅ KPI SUMMARY CARDS (2)
# =========================================
st.subheader("📌 KPI Summary")

avg_val = filtered["Value"].mean()
max_val = filtered["Value"].max()
min_val = filtered["Value"].min()
total_val = filtered["Value"].sum()

max_month = filtered.loc[filtered["Value"].idxmax(), "Month"]
min_month = filtered.loc[filtered["Value"].idxmin(), "Month"]

cols = st.columns(5)

cols[0].metric("Indicator", indicator_filter)
cols[1].metric("Average", f"{avg_val:,.2f}")
cols[2].metric("Max", f"{max_val:,.2f}", max_month)
cols[3].metric("Min", f"{min_val:,.2f}", min_month)
cols[4].metric("Total", f"{total_val:,.2f}")

# =========================================
# ✅ ADVANCED MONTHLY CHARTS (3)
# =========================================
st.subheader("📈 Monthly Trend Charts")

chart_df = filtered.set_index("Month")[["Value"]]

chart_type = st.selectbox("Select Chart Type", ["Line Chart", "Bar Chart", "Boxplot"])

if chart_type == "Line Chart":
    st.line_chart(chart_df)

elif chart_type == "Bar Chart":
    st.bar_chart(chart_df)

elif chart_type == "Boxplot":
    st.vega_lite_chart(
        chart_df.reset_index(),
        {
            "mark": {"type": "boxplot"},
            "encoding": {
                "y": {"field": "Value", "type": "quantitative"}
            },
        },
    )

# =========================================
# ✅ KPI INSPECTOR (4)
# =========================================
st.subheader("🧠 KPI Inspector")

values = filtered["Value"].reset_index(drop=True)
trend_val = values.iloc[-1] - values.iloc[0]

if trend_val > 0:
    trend_type = "Increasing"
    performance = "Risky"
elif trend_val < 0:
    trend_type = "Decreasing"
    performance = "Excellent"
else:
    trend_type = "Stable"
    performance = "Moderate"

st.columns(3)[0].metric("Trend", trend_type)
st.columns(3)[1].metric("Performance", performance)
st.columns(3)[2].metric("Last Change", f"{trend_val:,.2f}")

# =========================================
# ✅ YOY TABLE (FOR CURRENT YEAR)
# =========================================
st.subheader("📅 Monthly Values Table")

st.dataframe(
    filtered[["Month", "Value"]],
    use_container_width=True
)

# =========================================
# ✅ AUTO INSIGHT (6)
# =========================================
st.subheader("💡 Auto Insight")

peak_month = max_month
low_month = min_month

if trend_type == "Increasing":
    st.warning(
        f"⚠️ {indicator_filter} shows an increasing trend during the year. "
        f"Peak consumption observed in {peak_month}."
    )
elif trend_type == "Decreasing":
    st.success(
        f"✅ {indicator_filter} shows a decreasing trend, indicating performance improvement. "
        f"Lowest value recorded in {low_month}."
    )
else:
    st.info(
        f"ℹ️ {indicator_filter} remains relatively stable throughout the year."
    )
