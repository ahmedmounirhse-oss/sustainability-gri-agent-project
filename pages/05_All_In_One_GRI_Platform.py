import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.company_data_loader import (
    list_company_files,
    load_company_file,
    compute_kpis_by_category,
    get_trend_data
)

from src.company_pdf_exporter import build_company_pdf
from src.email_sender import send_pdf_via_email


# =========================================
# ✅ PAGE CONFIG
# =========================================
st.set_page_config(page_title="All In One GRI Platform", layout="wide")
st.title("🏢 All In One GRI Platform — Companies")

# =========================================
# ✅ UNIT MAP
# =========================================
UNIT_MAP = {
    "energy": "GJ",
    "electric": "MWh",
    "water": "m³",
    "emission": "tCO₂e",
    "carbon": "tCO₂e",
    "waste": "tons",
    "intensity": "kg/BOE"
}

# =========================================
# ✅ RISK CLASSIFICATION
# =========================================
def classify_kpi(value):
    if value <= 30:
        return "Excellent"
    elif value <= 70:
        return "Moderate"
    else:
        return "Risky"

# =========================================
# ✅ ESG SCORE FORMULA
# =========================================
def calculate_esg_score(kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    score = 0
    used = 0

    for k, v in kpis.items():
        k_low = k.lower()
        for key, w in weights.items():
            if key in k_low:
                normalized = max(0, 100 - float(v))
                score += normalized * w
                used += w

    if used == 0:
        return 0, "N/A"

    final_score = round(score / used, 2)
    status = classify_kpi(100 - final_score)
    return final_score, status

# =========================================
# ✅ SELECT COMPANY
# =========================================
files = list_company_files()

if not files:
    st.error("❌ No company Excel files found in data/companies")
    st.stop()

company_file = st.selectbox("📂 Select Company for Analysis", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

# =========================================
# ✅ SELECT CATEGORY
# =========================================
categories = sorted(df["Category"].dropna().unique().tolist())
selected_category = st.selectbox("📊 Select Sustainability Category", categories)
cat_df = df[df["Category"] == selected_category]

# =========================================
# ✅ RAW DATA
# =========================================
st.subheader("📑 Company Raw Data")
st.dataframe(cat_df, use_container_width=True)

# =========================================
# ✅ KPI SMART CARDS + YOY
# =========================================
st.subheader("📌 KPI Smart Cards (YOY)")

metric_col = None
for col in cat_df.columns:
    if "metric" in col.lower():
        metric_col = col

year_cols = sorted([c for c in cat_df.columns if str(c).isdigit()])
kpis = compute_kpis_by_category(df, selected_category)

cards = st.columns(len(kpis))
latest_year = year_cols[-1]
prev_year = year_cols[-2] if len(year_cols) >= 2 else None

for col_card, (k, v) in zip(cards, kpis.items()):
    row = cat_df[cat_df[metric_col] == k]
    if row.empty:
        continue

    latest_val = float(row[latest_year])
    if prev_year:
        prev_val = float(row[prev_year])
        delta = latest_val - prev_val
        delta_text = f"{delta:+.2f}"
    else:
        delta_text = "N/A"

    col_card.metric(
        label=f"{k} ({latest_year})",
        value=f"{latest_val:,.2f}",
        delta=delta_text
    )

# =========================================
# ✅ ✅ ✅ ESG SCORE
# =========================================
st.divider()
st.subheader("🌍 Overall ESG Score")

esg_score, esg_status = calculate_esg_score(kpis)
esg_color = "green" if esg_status == "Excellent" else "orange" if esg_status == "Moderate" else "red"

fig_esg = go.Figure(go.Indicator(
    mode="gauge+number",
    value=esg_score,
    number={"suffix": " / 100"},
    title={"text": f"ESG Score — {esg_status}"},
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": esg_color},
        "steps": [
            {"range": [0, 40], "color": "#f28b82"},
            {"range": [40, 70], "color": "#ffd966"},
            {"range": [70, 100], "color": "#9be7a1"},
        ]
    }
))
st.plotly_chart(fig_esg, use_container_width=True)

# =========================================
# ✅ KPI GAUGES
# =========================================
st.subheader("📌 KPI Gauges Dashboard")

cols = st.columns(3)
i = 0

for k, v in kpis.items():
    k_lower = k.lower()
    unit = ""

    for word, u in UNIT_MAP.items():
        if word in k_lower:
            unit = u
            break

    status = classify_kpi(v)
    color = "green" if status == "Excellent" else "orange" if status == "Moderate" else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(v),
        number={"suffix": f" {unit}"},
        title={"text": f"{k}<br><span style='color:{color}'>{status}</span>"},
        gauge={
            "axis": {"range": [0, max(100, v * 1.5)]},
            "bar": {"color": color},
        }
    ))

    with cols[i % 3]:
        st.plotly_chart(fig, use_container_width=True)

    i += 1

# =========================================
# ✅ ✅ ✅ TRENDS WITH TITLES (UPDATED)
# =========================================
st.subheader(f"📈 Sustainability Trends — {selected_category}")

for metric in kpis.keys():

    trend_data = get_trend_data(df, selected_category, metric)
    if not trend_data:
        continue

    chart_df = pd.DataFrame({
        "Year": list(trend_data.keys()),
        "Value": list(trend_data.values())
    }).set_index("Year")

    chart_df = chart_df.apply(pd.to_numeric, errors="coerce").dropna()
    if chart_df.empty:
        continue

    start_year = chart_df.index.min()
    end_year = chart_df.index.max()

    # ✅ ✅ ✅ TREND TITLE ADDED HERE
    st.markdown(f"### 📊 {metric} Trend ({start_year} → {end_year})")

    st.line_chart(chart_df)

    delta = chart_df.iloc[-1, 0] - chart_df.iloc[0, 0]

    if delta > 0:
        st.warning(f"📈 Insight: {metric} is increasing over time.")
    elif delta < 0:
        st.success(f"✅ Insight: {metric} is decreasing over time.")
    else:
        st.info(f"⚖️ Insight: {metric} remains stable over time.")

# =========================================
# ✅ PREDICTION FOR NEXT YEAR
# =========================================
st.subheader("🔮 Prediction for Next Year")

if len(year_cols) >= 3:

    next_year = int(year_cols[-1]) + 1

    for metric in kpis.keys():
        row = cat_df[cat_df[metric_col] == metric]
        if row.empty:
            continue

        values = pd.to_numeric(row[year_cols].iloc[0], errors="coerce").dropna()
        x = np.array([int(y) for y in year_cols[:len(values)]])
        y = values.values

        coeff = np.polyfit(x, y, 1)
        model = np.poly1d(coeff)

        predicted_value = float(model(next_year))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=year_cols[:len(values)], y=y, mode="lines+markers", name="Historical"))
        fig.add_trace(go.Scatter(x=[str(next_year)], y=[predicted_value], mode="markers",
                                 marker=dict(size=12, color="red"), name="Predicted"))

        fig.update_layout(title=f"{metric} — Forecast for {next_year}")
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"🔮 Predicted {metric} in {next_year}: {predicted_value:.2f}")

# =========================================
# ✅ PDF EXPORT
# =========================================
st.divider()
st.subheader("📄 Generate Professional GRI Company Report")

if st.button("✅ Generate Professional PDF Now"):
    pdf_buffer = build_company_pdf(
        company_name=company_name,
        df=df,
        kpis=kpis,
        category=selected_category
    )

    st.session_state.company_pdf = pdf_buffer
    st.success("✅ Professional GRI PDF Generated Successfully")

if "company_pdf" in st.session_state:
    st.download_button(
        "⬇ Download Professional GRI Report",
        data=st.session_state.company_pdf.getvalue(),
        file_name=f"{company_name}_GRI_Report.pdf",
        mime="application/pdf"
    )

# =========================================
# ✅ EMAIL
# =========================================
st.subheader("📧 Send Report by Email")
email = st.text_input("Receiver Email")

if st.button("📨 Send by Email"):
    if "company_pdf" not in st.session_state:
        st.error("❌ Please generate the PDF first.")
    else:
        send_pdf_via_email(
            receiver_email=email,
            pdf_bytes=st.session_state.company_pdf.getvalue(),
            pdf_name=f"{company_name}_GRI_Report.pdf",
            year="Company GRI Report"
        )

        st.success("✅ Email Sent Successfully")
