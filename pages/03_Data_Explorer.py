import streamlit as st
import pandas as pd
import os

# =========================================
# PATH
# =========================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Excel")

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(page_title="Monthly Sustainability Data Explorer", layout="wide")
st.title("📊 Monthly Sustainability Data Explorer")

# =========================================
# FILE SELECTION
# =========================================
files = []

if os.path.exists(DATA_DIR):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

if not files:
    st.error("❌ No Excel files found in data/Excel")
    st.stop()

file_name = st.selectbox("📂 Select Monthly File", files)
file_path = os.path.join(DATA_DIR, file_name)

# =========================================
# LOAD ALL SHEETS (Energy, Water, Emissions, Waste)
# =========================================
xls = pd.ExcelFile(file_path)
all_data = []

for sheet in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet)

    df.columns = df.columns.astype(str).str.strip()
    df = df.rename(columns={
        df.columns[0]: "Year",
        df.columns[1]: "Month",
        df.columns[2]: "Indicator",
        df.columns[3]: "Value"
    })

    df["Category"] = sheet
    all_data.append(df)

df = pd.concat(all_data, ignore_index=True)

# ترتيب الشهور
months_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df["Month"] = pd.Categorical(df["Month"], categories=months_order, ordered=True)

# =========================================
# FILTERS
# =========================================
st.subheader("🎯 Filters")

col1, col2, col3 = st.columns(3)

with col1:
    category_filter = st.selectbox(
        "Select Category",
        sorted(df["Category"].unique())
    )

filtered_cat = df[df["Category"] == category_filter]

with col2:
    year_filter = st.selectbox("Select Year", sorted(filtered_cat["Year"].unique()))

with col3:
    indicator_filter = st.selectbox(
        "Select Indicator",
        sorted(filtered_cat["Indicator"].astype(str).unique())
    )

filtered = filtered_cat[
    (filtered_cat["Year"] == year_filter) &
    (filtered_cat["Indicator"] == indicator_filter)
]

filtered = filtered.sort_values("Month")

# =========================================
# KPI SUMMARY
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
# MONTHLY TREND CHART
# =========================================
st.subheader(f"📈 Monthly Trend — {category_filter}")
st.line_chart(filtered.set_index("Month")[["Value"]])

# =========================================
# KPI INSPECTOR
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

c1, c2, c3 = st.columns(3)
c1.metric("Trend", trend_type)
c2.metric("Performance", performance)
c3.metric("Year Change", f"{trend_val:,.2f}")


# =========================================
# ✅ YEAR-OVER-YEAR (YOY) COMPARISON — DROPDOWN VERSION
# =========================================
st.subheader("📊 Year-over-Year (YOY) Comparison")

available_years = sorted(filtered_cat["Year"].unique())

if len(available_years) < 2:
    st.info("ℹ️ Not enough years available for comparison.")
else:
    c1, c2 = st.columns(2)

    with c1:
        year_1 = st.selectbox("Select Base Year", available_years, index=0)

    with c2:
        year_2 = st.selectbox("Select Comparison Year", available_years, index=len(available_years)-1)

    if year_1 == year_2:
        st.warning("⚠️ Please select two different years for comparison.")
    else:
        df_year_1 = filtered_cat[
            (filtered_cat["Year"] == year_1) &
            (filtered_cat["Indicator"] == indicator_filter)
        ].sort_values("Month")

        df_year_2 = filtered_cat[
            (filtered_cat["Year"] == year_2) &
            (filtered_cat["Indicator"] == indicator_filter)
        ].sort_values("Month")

        yoy_df = pd.DataFrame()
        yoy_df["Month"] = df_year_1["Month"].values
        yoy_df[str(year_1)] = df_year_1["Value"].values
        yoy_df[str(year_2)] = df_year_2["Value"].values
        yoy_df["YOY Change"] = yoy_df[str(year_2)] - yoy_df[str(year_1)]

        st.dataframe(yoy_df, use_container_width=True)

        total_change = yoy_df["YOY Change"].sum()

        st.subheader("📌 YOY Insight")

        if total_change > 0:
            st.warning(
                f"⚠️ {indicator_filter} increased by {total_change:,.2f} from {year_1} to {year_2}."
            )
        elif total_change < 0:
            st.success(
                f"✅ {indicator_filter} decreased by {abs(total_change):,.2f} from {year_1} to {year_2}, indicating improvement."
            )
        else:
            st.info("ℹ️ No significant change detected between the selected years.")

# =========================================
# TABLE
# =========================================
st.subheader("📅 Monthly Data Table")
st.dataframe(filtered[["Month", "Value"]], use_container_width=True)

# =========================================
# AUTO INSIGHT
# =========================================
st.subheader("💡 Auto Insight")

if trend_type == "Increasing":
    st.warning(
        f"⚠️ {indicator_filter} shows an increasing trend. Peak recorded in {max_month}."
    )
elif trend_type == "Decreasing":
    st.success(
        f"✅ {indicator_filter} shows a decreasing trend. Lowest value observed in {min_month}."
    )
else:
    st.info(f"ℹ️ {indicator_filter} remained stable through the year.")
