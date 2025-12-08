import streamlit as st
import os
import pandas as pd

st.set_page_config(page_title="Data Explorer", layout="wide")

# =========================
# ✅ CONFIG
# =========================
EXCEL_FOLDER = "data/Excel"

# =========================
# ✅ LOAD FILES FROM FOLDER ONLY
# =========================
excel_files = os.listdir(EXCEL_FOLDER) if os.path.exists(EXCEL_FOLDER) else []

# =========================
# ✅ UI HEADER
# =========================
st.title("🔍 Data Explorer")
st.write("Browse, filter, and analyze raw sustainability data (from data/Excel only).")

# =========================
# ✅ ERROR HANDLING (NO FILES)
# =========================
if not excel_files:
    st.error("❌ No Excel files found inside data/Excel folder.")
    st.stop()

# =========================
# ✅ SIDEBAR FILE SELECTION
# =========================
st.sidebar.title("📂 Data Selection")

selected_file = st.sidebar.selectbox(
    "Select Excel File:",
    ["-- None --"] + excel_files
)

# =========================
# ✅ LOAD DATA
# =========================
if selected_file == "-- None --":
    st.info("👈 Please select an Excel file from the sidebar.")
    st.stop()

df = pd.read_excel(os.path.join(EXCEL_FOLDER, selected_file))

# =========================
# ✅ COLUMN FILTERING
# =========================
st.sidebar.title("🔎 Filters")

numeric_columns = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

if numeric_columns:
    selected_column = st.sidebar.selectbox(
        "Select Indicator:",
        numeric_columns
    )

    min_val = float(df[selected_column].min())
    max_val = float(df[selected_column].max())

    # ✅ FIX HERE: HANDLE CONSTANT COLUMN
    if min_val == max_val:
        st.sidebar.warning(
            f"⚠️ '{selected_column}' has constant value = {min_val}. No filtering applied."
        )
        filtered_df = df

    else:
        value_range = st.sidebar.slider(
            f"Filter {selected_column}",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val)
        )

        filtered_df = df[
            (df[selected_column] >= value_range[0]) &
            (df[selected_column] <= value_range[1])
        ]
else:
    st.warning("⚠️ No numeric columns found in this file.")
    filtered_df = df

# =========================
# ✅ DISPLAY DATA
# =========================
st.subheader(f"📄 Data Preview — {selected_file}")
st.dataframe(filtered_df)

# =========================
# ✅ BASIC STATS
# =========================
st.subheader("📊 Statistical Summary")
st.dataframe(filtered_df.describe())

# =========================
# ✅ DOWNLOAD FILTERED DATA
# =========================
csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Filtered Data as CSV",
    csv,
    file_name="filtered_data.csv",
    mime="text/csv"
)
