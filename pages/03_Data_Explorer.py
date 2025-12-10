import streamlit as st
import pandas as pd
import os
import altair as alt

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
DATA_DIR = os.path.join(BASE_DIR, "data", "Excel")

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
# ✅ KPI GAUGE (FINAL ERROR-FREE VERSION)
# =========================================
st.subheader("🎛 KPI Gauge")

gauge_value = avg_val
max_value = df["Value"].max()

norm = gauge_value / max_value if max_value > 0 else 0

gauge_df = pd.DataFrame({
    "category": ["filled", "empty"],
    "value": [norm, 1 - norm]
})

gauge_chart = (
    alt.Chart(gauge_df)
    .mark_arc(innerRadius=70, outerRadius=120)
    .encode(
        theta=alt.Theta("value:Q", stack=True),
        color=alt.Color(
            "category:N",
            scale=alt.Scale(domain=["filled", "empty"], range=["#2ecc71", "#eeeeee"]),
            legend=None
        )
    )
    .properties(width=300, height=300)
)

st.altair_chart(gauge_chart, use_container_width=False)

st.markdown(
    f"""
    <h3 style="text-align:center; margin-top:-30px;">
        {gauge_value:,.2f}
    </h3>
    """,
    unsafe_allow_html=True
)

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

if len(values) >= 2:
    trend_val = values.iloc[-1] - values.iloc[0]
else:
    trend_val = 0

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

# =========================================
# ✅ MONTHLY VALUES TABLE (5)
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

if trend_type == "Increasing":
    st.warning(
        f"⚠️ {indicator_filter} shows an increasing trend during the year. "
        f"Peak consumption observed in {max_month}."
    )
elif trend_type == "Decreasing":
    st.success(
        f"✅ {indicator_filter} shows a decreasing trend, indicating performance improvement. "
        f"Lowest value recorded in {min_month}."
    )
else:
    st.info(
        f"ℹ️ {indicator_filter} remains relatively stable throughout the year."
    )
