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
if not os.path.exists(DATA_DIR):
    st.error("❌ Folder data/Excel not found")
    st.stop()

files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

if not files:
    st.error("❌ No Excel files found in data/Excel")
    st.stop()

file_name = st.selectbox("📂 Select Monthly File", files)
file_path = os.path.join(DATA_DIR, file_name)

# =========================================
# LOAD ALL SHEETS (Energy, Water, Emission, Waste)
# =========================================
xls = pd.ExcelFile(file_path)
all_data = []

for sheet in xls.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet)

    df.columns = df.columns.astype(str).str.strip()

    # توحيد الأعمدة أول 4 أعمدة فقط
    df = df.iloc[:, :4]
    df.columns = ["Year", "Month", "Indicator", "Value"]

    df["Category"] = sheet
    all_data.append(df)

df = pd.concat(all_data, ignore_index=True)

# =========================================
# ترتيب الشهور
# =========================================
months_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
df["Month"] = pd.Categorical(df["Month"], categories=months_order, ordered=True)

# =========================================
# FILTERS
# =========================================
st.subheader("🎯 Filters")

col1, col2, col3 = st.columns(3)

with col1:
    category_filter = st.selectbox("Select Category", sorted(df["Category"].unique()))

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
].sort_values("Month")

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

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Indicator", indicator_filter)
c2.metric("Average", f"{avg_val:,.2f}")
c3.metric("Max", f"{max_val:,.2f}", max_month)
c4.metric("Min", f"{min_val:,.2f}", min_month)
c5.metric("Total", f"{total_val:,.2f}")

# =========================================
# MONTHLY TREND
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

i1, i2, i3 = st.columns(3)
i1.metric("Trend", trend_type)
i2.metric("Performance", performance)
i3.metric("Change", f"{trend_val:,.2f}")

# =========================================
# ✅✅✅ YOY COMPARISON (WITH DROPDOWN)
# =========================================
st.subheader("📊 Year-over-Year (YOY) Comparison")

available_years = sorted(filtered_cat["Year"].unique())

col_y1, col_y2 = st.columns(2)

year_1 = col_y1.selectbox("✅ Select First Year", available_years, key="yoy1")
year_2 = col_y2.selectbox("✅ Select Second Year", available_years, key="yoy2")

if year_1 != year_2:
    y1_df = filtered_cat[
        (filtered_cat["Year"] == year_1) &
        (filtered_cat["Indicator"] == indicator_filter)
    ].sort_values("Month")

    y2_df = filtered_cat[
        (filtered_cat["Year"] == year_2) &
        (filtered_cat["Indicator"] == indicator_filter)
    ].sort_values("Month")

    min_len = min(len(y1_df), len(y2_df))

    yoy_df = pd.DataFrame({
        "Month": y1_df["Month"].values[:min_len],
        str(year_1): y1_df["Value"].values[:min_len],
        str(year_2): y2_df["Value"].values[:min_len],
    })

    yoy_df["Difference"] = yoy_df[str(year_2)] - yoy_df[str(year_1)]

    st.dataframe(yoy_df, use_container_width=True)

    total_diff = yoy_df["Difference"].sum()

    if total_diff > 0:
        st.warning(f"⚠️ Increased by {total_diff:,.2f} from {year_1} to {year_2}")
    elif total_diff < 0:
        st.success(f"✅ Decreased by {abs(total_diff):,.2f} from {year_1} to {year_2}")
    else:
        st.info("ℹ️ No change between the selected years")

else:
    st.info("ℹ️ Select two different years to compare")

# =========================================
# DATA TABLE
# =========================================
st.subheader("📅 Monthly Data Table")
st.dataframe(filtered[["Month", "Value"]], use_container_width=True)
