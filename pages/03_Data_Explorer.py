import streamlit as st
import pandas as pd

from src.data_loader import (
    list_excel_files,
    load_monthly_file
)

# =========================================
# ✅ PAGE CONFIG
# =========================================

st.set_page_config(page_title="Monthly Sustainability Data Explorer", layout="wide")
st.title("📊 Monthly Sustainability Data Explorer (Energy • Water • Emissions • Waste)")

# =========================================
# ✅ FILE SELECTION
# =========================================

files = list_excel_files()

if not files:
    st.error("❌ No Excel monthly files found in data/Excel")
    st.stop()

selected_file = st.selectbox("📂 Select Monthly Data File", files)

df = load_monthly_file(selected_file)

# =========================================
# ✅ CATEGORY SELECTION
# =========================================

if "Category" not in df.columns:
    st.error("❌ Category column not detected. Sheets not loaded correctly.")
    st.stop()

categories = sorted(df["Category"].unique().tolist())

selected_category = st.selectbox(
    "📊 Select Sustainability Category",
    categories
)

cat_df = df[df["Category"] == selected_category]

# =========================================
# ✅ RAW DATA VIEW
# =========================================

st.subheader(f"📑 Raw Monthly Data — {selected_category}")
st.dataframe(cat_df, use_container_width=True)

# =========================================
# ✅ TREND VISUALIZATION
# =========================================

numeric_cols = cat_df.select_dtypes(include="number").columns.tolist()

if len(numeric_cols) == 0:
    st.warning("⚠️ No numeric columns found for trend chart.")
else:
    st.subheader(f"📈 Monthly Trends — {selected_category}")

    for col in numeric_cols:
        st.markdown(f"##### {col}")
        chart_df = cat_df[[col]].dropna()
        st.line_chart(chart_df)
