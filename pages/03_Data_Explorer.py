import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import altair as alt
import math
import os

# =========================================
# ✅ PATH
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Excel")

st.set_page_config(page_title="Monthly Data Explorer", layout="wide")
st.title("📊 Monthly Sustainability Data Explorer — Advanced Version")

# =========================================
# ✅ LOAD FILES
# =========================================
files = []
if os.path.exists(DATA_DIR):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

if not files:
    st.error("❌ No Excel files found inside data/Excel")
    st.stop()

file_name = st.selectbox("📂 Select Monthly Data File", files)
file_path = os.path.join(DATA_DIR, file_name)

df = pd.read_excel(file_path)

# =========================================
# ✅ VALIDATION
# =========================================
expected_cols = {"Year", "Month", "Indicator", "Value"}

if not expected_cols.issubset(set(df.columns)):
    st.error("❌ File must contain: Year | Month | Indicator | Value")
    st.stop()

months_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# =========================================
# 🎯 FILTERS
# =========================================
st.subheader("🎯 Smart Filters")

col1, col2 = st.columns(2)

with col1:
    year_sel = st.selectbox("Select Year", sorted(df["Year"].unique()))

with col2:
    indicator_sel = st.selectbox("Select Indicator", sorted(df["Indicator"].unique()))

filtered = df[(df["Year"] == year_sel) & (df["Indicator"] == indicator_sel)]
filtered["Month"] = pd.Categorical(filtered["Month"], categories=months_order, ordered=True)
filtered = filtered.sort_values("Month")

# =========================================
# 📌 KPI SMART CARDS
# =========================================
st.subheader("📌 KPI Smart Summary")

avg_val = filtered["Value"].mean()
max_val = filtered["Value"].max()
min_val = filtered["Value"].min()
total_val = filtered["Value"].sum()

max_month = filtered.loc[filtered["Value"].idxmax(), "Month"]
min_month = filtered.loc[filtered["Value"].idxmin(), "Month"]

cols = st.columns(5)
cols[0].metric("Indicator", indicator_sel)
cols[1].metric("Average", f"{avg_val:,.2f}")
cols[2].metric("Max", f"{max_val:,.2f}", max_month)
cols[3].metric("Min", f"{min_val:,.2f}", min_month)
cols[4].metric("Total", f"{total_val:,.2f}")

# =========================================
# 🔵 GAUGE CHART
# =========================================
st.subheader("🎛 KPI Gauge")

gauge_value = avg_val
max_scale = max_val * 1.2

gauge_chart = alt.Chart(pd.DataFrame({"value":[gauge_value]})).mark_arc(innerRadius=50, outerRadius=100).encode(
    theta=alt.Theta("value:Q", stack=True),
    color=alt.Color("value:Q", scale=alt.Scale(scheme="yellowred"))
).properties(width=300, height=300)

st.altair_chart(gauge_chart)

# =========================================
# 📈 MONTHLY TREND
# =========================================
st.subheader("📈 Monthly Trend Line")

chart_df = filtered.set_index("Month")[["Value"]]
st.line_chart(chart_df)

# =========================================
# 🔎 YOY COMPARISON (SAME INDICATOR)
# =========================================
st.subheader("📅 YoY Comparison (Same Indicator)")

yoy = df[df["Indicator"] == indicator_sel].groupby("Year")["Value"].mean()

st.bar_chart(yoy)

# =========================================
# 🚨 ANOMALY DETECTION
# =========================================
st.subheader("🚨 Anomaly Detection")

z_scores = (filtered["Value"] - filtered["Value"].mean()) / filtered["Value"].std()
filtered["Z"] = z_scores
anomalies = filtered[filtered["Z"].abs() > 2]

if anomalies.empty:
    st.success("✅ No anomalies detected.")
else:
    st.error("⚠️ Anomalies detected!")
    st.dataframe(anomalies)

# =========================================
# 🔮 PREDICTION (NEXT YEAR)
# =========================================
st.subheader("🔮 Prediction — Next Year Value")

model = LinearRegression()

X = np.arange(len(filtered)).reshape(-1,1)
y = filtered["Value"].values

model.fit(X, y)
next_val = model.predict([[len(filtered)]])[0]

st.metric("Predicted Value Next Year", f"{next_val:,.2f}")

# =========================================
# 💡 AUTO INSIGHT
# =========================================
st.subheader("💡 Auto Insight Generator")

values = filtered["Value"].values
trend = values[-1] - values[0]

if trend > 0:
    st.warning(f"⚠️ {indicator_sel} is increasing — potential risk.")
elif trend < 0:
    st.success(f"✅ {indicator_sel} is decreasing — good performance.")
else:
    st.info("ℹ️ Stable performance.")

