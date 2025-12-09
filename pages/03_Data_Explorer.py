import streamlit as st
import pandas as pd
import os
import altair as alt

# =========================================
# ✅ PATH FOR MONTHLY FILES
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Excel")

# =========================================
# ✅ PAGE CONFIG
# =========================================
st.set_page_config(page_title="Monthly Data Explorer", layout="wide")
st.title("📊 Monthly Sustainability Data Explorer — Energy Only")

# =========================================
# ✅ FILE SELECTION
# =========================================
if not os.path.exists(DATA_DIR):
    st.error("❌ data/Excel folder not found")
    st.stop()

files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

if not files:
    st.error("❌ No Excel files found in data/Excel")
    st.stop()

file_name = st.selectbox("📂 Select Monthly File", files)
file_path = os.path.join(DATA_DIR, file_name)

# =========================================
# ✅ LOAD DATA (ENERGY STRUCTURE)
# =========================================
df = pd.read_excel(file_path)

expected_cols = {"Year", "Month", "Indicator", "Value"}
if not expected_cols.issubset(set(df.columns)):
    st.error("❌ File must contain: Year | Month | Indicator | Value")
    st.stop()

# =========================================
# ✅ FILTERS
# =========================================
st.subheader("🎯 Smart Filters")

c1, c2, c3 = st.columns(3)

with c1:
    year_filter = st.selectbox("Select Year", sorted(df["Year"].unique()))

with c2:
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

with c3:
    month_filter = st.multiselect(
        "Select Months",
        filtered["Month"].dropna().unique().tolist(),
        default=filtered["Month"].dropna().unique().tolist()
    )

filtered = filtered[filtered["Month"].isin(month_filter)]

# =========================================
# ✅ KPI SUMMARY
# =========================================
st.subheader("📌 KPI Summary")

avg_val = filtered["Value"].mean()
max_val = filtered["Value"].max()
min_val = filtered["Value"].min()
total_val = filtered["Value"].sum()

if not filtered.empty:
    max_month = filtered.loc[filtered["Value"].idxmax(), "Month"]
    min_month = filtered.loc[filtered["Value"].idxmin(), "Month"]
else:
    max_month = "-"
    min_month = "-"

cols = st.columns(5)
cols[0].metric("Indicator", indicator_filter)
cols[1].metric("Average", f"{avg_val:,.2f}")
cols[2].metric("Max", f"{max_val:,.2f}", max_month)
cols[3].metric("Min", f"{min_val:,.2f}", min_month)
cols[4].metric("Total", f"{total_val:,.2f}")

# =========================================
# ✅ KPI GAUGE (FIXED)
# =========================================
st.subheader("🎛 KPI Gauge")

gauge_value = avg_val
max_scale = max(df["Value"].max(), gauge_value)

gauge_df = pd.DataFrame({"value": [gauge_value]})

gauge_chart = alt.Chart(gauge_df).mark_arc(
    innerRadius=60,
    outerRadius=110
).encode(
    theta=alt.Theta("value:Q", stack=True),
    color=alt.Color(
        "value:Q",
        scale=alt.Scale(
            scheme="redyellowgreen",
            domain=[0, max_scale]
        )
    )
).properties(width=300, height=300)

st.altair_chart(gauge_chart)

# =========================================
# ✅ MONTHLY TREND CHART
# =========================================
st.subheader("📈 Monthly Trend")

chart_df = filtered.set_index("Month")[["Value"]]
st.line_chart(chart_df)

# =========================================
# ✅ KPI INSPECTOR
# =========================================
values = filtered["Value"].reset_index(drop=True)

if len(values) >= 2:
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

    c1, c2, c3 = st.columns(3)
    c1.metric("Trend", trend_type)
    c2.metric("Performance", performance)
    c3.metric("Last Change", f"{trend_val:,.2f}")
else:
    st.warning("⚠️ Not enough data for trend analysis")

# =========================================
# ✅ MONTHLY DATA TABLE
# =========================================
st.subheader("📅 Monthly Values Table")
st.dataframe(filtered[["Month", "Value"]], use_container_width=True)

# =========================================
# ✅ AUTO INSIGHT
# =========================================
st.subheader("💡 Auto Insight")

if trend_val > 0:
    st.warning(
        f"⚠️ {indicator_filter} shows increasing consumption during the year. "
        f"Peak observed in {max_month}."
    )
elif trend_val < 0:
    st.success(
        f"✅ {indicator_filter} shows decreasing trend indicating improved efficiency. "
        f"Lowest observed in {min_month}."
    )
else:
    st.info(
        f"ℹ️ {indicator_filter} remains stable throughout the year."
    )
