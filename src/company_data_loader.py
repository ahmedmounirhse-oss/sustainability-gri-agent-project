import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
COMPANY_DIR = os.path.join(BASE_DIR, "data", "companies")

# ================================
# ✅ LIST COMPANY FILES
# ================================
def list_company_files():
    if not os.path.exists(COMPANY_DIR):
        return []
    return [f for f in os.listdir(COMPANY_DIR) if f.endswith(".xlsx")]

# ================================
# ✅ LOAD ALL SHEETS
# ================================
def load_company_file(filename):
    path = os.path.join(COMPANY_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    xls = pd.ExcelFile(path)
    all_sheets = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)

        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace("Unnamed:.*", "", regex=True)
        )

        df = df.dropna(axis=1, how="all")
        df["Category"] = sheet.strip()
        df = df.apply(pd.to_numeric, errors="ignore")

        all_sheets.append(df)

    full_df = pd.concat(all_sheets, ignore_index=True)
    return full_df

# ================================
# ✅ COMPUTE KPI BY CATEGORY
# ================================
def compute_kpis_by_category(df, selected_category):

    kpis = {}
    cat_df = df[df["Category"] == selected_category]

    if cat_df.empty:
        return {}

    metric_col = None
    for col in cat_df.columns:
        if "metric" in col.lower():
            metric_col = col

    if not metric_col:
        return {}

    year_cols = [c for c in cat_df.columns if str(c).isdigit()]
    if not year_cols:
        return {}

    latest_year = sorted(year_cols, key=lambda x: int(x))[-1]

    for _, row in cat_df.iterrows():
        try:
            name = str(row[metric_col]).strip()
            value = float(row[latest_year])
            kpis[name] = round(value, 2)
        except:
            continue

    return kpis

# ================================
# ✅ TREND DATA
# ================================
def get_trend_data(df, selected_category, metric_name):

    cat_df = df[df["Category"] == selected_category]

    metric_col = None
    for col in cat_df.columns:
        if "metric" in col.lower():
            metric_col = col

    if not metric_col:
        return None

    row = cat_df[cat_df[metric_col] == metric_name]
    if row.empty:
        return None

    year_cols = [c for c in row.columns if str(c).isdigit()]

    data = {}
    for y in sorted(year_cols):
        try:
            data[y] = float(row.iloc[0][y])
        except:
            data[y] = None

    return data

# ================================
# ✅ OVERALL ESG SCORE (NEW)
# ================================
def calculate_esg_score(df):

    weights = {
        "Energy": 0.25,
        "Water": 0.25,
        "Emissions": 0.35,
        "Waste": 0.15
    }

    scores = {}
    overall_score = 0

    for category, weight in weights.items():

        cat_df = df[df["Category"].str.lower() == category.lower()]
        if cat_df.empty:
            continue

        metric_col = None
        for col in cat_df.columns:
            if "metric" in col.lower():
                metric_col = col

        year_cols = [c for c in cat_df.columns if str(c).isdigit()]
        if not metric_col or not year_cols:
            continue

        latest_year = sorted(year_cols, key=lambda x: int(x))[-1]
        values = pd.to_numeric(cat_df[latest_year], errors="coerce").dropna()

        if values.empty:
            continue

        max_val = values.max()
        avg_val = values.mean()

        score = max(0, 100 - (avg_val / max_val * 100))
        scores[category] = round(score, 2)

        overall_score += score * weight

    return round(overall_score, 2), scores
