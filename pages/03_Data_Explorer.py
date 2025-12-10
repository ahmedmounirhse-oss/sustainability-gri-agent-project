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
# FILES DETECTION
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
# LOAD ALL SHEETS FROM SELECTED FILE
# =========================================
xls = pd.ExcelFile(file_path)
all_data = []

for sheet in xls.sheet_names:
    df_sheet = pd.read_excel(file_path, sheet_name=sheet)

    df_sheet.columns = df_sheet.columns.astype(str).str.strip()
    df_sheet = df_sheet.iloc[:, :4]
    df_sheet.columns = ["Year", "Month", "Indicator", "Value"]

    df_sheet["Category"] = sheet
    all_data.append(df_sheet)

df = pd.concat(all_data, ignore_index=True)

# =========================================
# MONTH ORDER
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
# ✅✅✅ YOY COMPARISON — GLOBAL DROPDOWN (ACROSS ALL FILES)
# =========================================
st.subheader("📊 Year-over-Year (YOY) Comparison")

# ✅ Collect ALL available years from ALL files
all_years = []

for f in files:
    fp = os.path.join(DATA_DIR, f)
    x = pd.ExcelFile(fp)

    for sh in x.sheet_names:
        d = pd.read_excel(fp, sheet_name=sh)
        y = pd.to_numeric(d.iloc[:, 0], errors="coerce").dropna()
        all_years.extend(list(y))

available_years = sorted(set(int(y) for y in all_years))

if len(available_years) < 2:
    st.info("ℹ️ Not enough years found across files for YOY comparison.")
else:
    col_y1, col_y2 = st.columns(2)

    year_1 = col_y1.selectbox("✅ Select First Year (Base)", available_years, key="yoy1")
    year_2 = col_y2.selectbox("✅ Select Second Year (Compare)", available_years, key="yoy2")

    def load_year_data(category, year):
        result = []

        for f in files:
            fp = os.path.join(DATA_DIR, f)
            xls = pd.ExcelFile(fp)

            if category in xls.sheet_names:
                d = pd.read_excel(fp, sheet_name=category)
                d = d.iloc[:, :4]
                d.columns = ["Year", "Month", "Indicator", "Value"]

                d = d[(d["Year"] == year) & (d["Indicator"] == indicator_filter)]
                if not d.empty:
                    result.append(d)

        if result:
            out = pd.concat(result)
            out["Month"] = pd.Categorical(out["Month"], categories=months_order, ordered=True)
            return out.sort_values("Month")

        return pd.DataFrame()

    if year_1 != year_2:
        y1_df = load_year_data(category_filter, year_1)
        y2_df = load_year_data(category_filter, year_2)

        if y1_df.empty or y2_df.empty:
            st.warning("⚠️ One of the selected years has no data for this category & indicator.")
        else:
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
        st.info("ℹ️ Please select two different years")

# =========================================
# DATA TABLE
# =========================================
st.subheader("📅 Monthly Data Table")
st.dataframe(filtered[["Month", "Value"]], use_container_width=True)
