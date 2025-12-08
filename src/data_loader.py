import os
import re
import pandas as pd
from pathlib import Path

# =========================
# ✅ CONFIG
# =========================
DATA_DIR = Path("data/Excel")

# =========================
# ✅ MONTH NORMALIZATION
# =========================
MONTH_MAP = {
    "jan": 1, "january": 1, "01": 1, "1": 1,
    "feb": 2, "february": 2, "02": 2, "2": 2,
    "mar": 3, "march": 3, "03": 3, "3": 3,
    "apr": 4, "april": 4, "04": 4, "4": 4,
    "may": 5, "05": 5, "5": 5,
    "jun": 6, "june": 6, "06": 6, "6": 6,
    "jul": 7, "july": 7, "07": 7, "7": 7,
    "aug": 8, "august": 8, "08": 8, "8": 8,
    "sep": 9, "september": 9, "09": 9, "9": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # Arabic
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "اغسطس": 8,
    "سبتمبر": 9, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}

def normalize_month(value):
    val = str(value).strip().lower()
    if val in MONTH_MAP:
        return MONTH_MAP[val]
    try:
        num = int(val)
        if 1 <= num <= 12:
            return num
    except:
        pass
    raise ValueError(f"Unrecognized month format: {value}")

# =========================
# ✅ LIST YEARS FROM FILES
# =========================
def list_available_years():
    years = {}
    for file in DATA_DIR.glob("*.xlsx"):
        found = re.findall(r"\d{4}", file.name)
        if found:
            years[int(found[0])] = file
    return dict(sorted(years.items()))

# =========================
# ✅ READ ALL SHEETS + MERGE
# =========================
def read_all_sheets(file_path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(file_path)
    all_frames = []

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df["__sheet__"] = sheet_name   # لتتبع المصدر لو احتجنا
        all_frames.append(df)

    return pd.concat(all_frames, ignore_index=True)

# =========================
# ✅ LOAD FULL YEAR DATA (ALL SHEETS)
# =========================
def load_year_dataframe(year: int) -> pd.DataFrame:
    years = list_available_years()
    if year not in years:
        raise ValueError(f"No file found for year {year}")

    df = read_all_sheets(years[year])

    expected = {"Year", "Month", "Indicator", "Value"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Excel missing required columns: {missing}")

    df = df.copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Month"] = df["Month"].apply(normalize_month)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)

    df_year = df[df["Year"] == int(year)].copy()
    df_year.sort_values(["Month"], inplace=True)

    return df_year

# =========================
# ✅ CORE KPI FUNCTION (SINGLE SOURCE OF TRUTH)
# =========================
def get_kpi_block(year: int, keyword: str):
    df_year = load_year_dataframe(year)

    block = df_year[
        df_year["Indicator"]
        .astype(str)
        .str.contains(keyword, case=False, na=False)
    ]

    if block.empty:
        return {
            "total": 0,
            "monthly": [],
            "unit": "",
            "raw": block,
        }

    total = round(block["Value"].sum(), 2)
    monthly = block.sort_values("Month")["Value"].tolist()

    unit = ""
    if "Unit" in block.columns and not block["Unit"].isna().all():
        unit = str(block["Unit"].iloc[0])

    return {
        "total": total,
        "monthly": monthly,
        "unit": unit,
        "raw": block,
    }
