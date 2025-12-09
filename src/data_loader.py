import os
import pandas as pd

# ============================
# ✅ PATH SETTINGS
# ============================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Excel")

# ============================
# ✅ LIST MONTHLY FILES
# ============================

def list_excel_files():
    if not os.path.exists(DATA_DIR):
        return []

    return [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx")]

# ============================
# ✅ LOAD ALL SHEETS (ENERGY + WATER + EMISSIONS + WASTE)
# ============================

def load_monthly_file(filename):
    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # ✅ قراءة كل الشيتات مرة واحدة
    sheets = pd.read_excel(path, sheet_name=None)

    all_data = []

    for sheet_name, df in sheets.items():

        # ✅ تنظيف الأعمدة
        df.columns = df.columns.astype(str).str.strip()
        df = df.dropna(axis=1, how="all")

        # ✅ تحويل القيم الرقمية بأمان
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")

        # ✅ إضافة اسم الشيت كـ Category
        df["Category"] = sheet_name.strip()

        all_data.append(df)

    # ✅ دمج كل الشيتات في DataFrame واحد
    final_df = pd.concat(all_data, ignore_index=True)

    return final_df
