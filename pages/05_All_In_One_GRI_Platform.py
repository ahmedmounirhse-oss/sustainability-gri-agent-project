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

from src.data_validation import normalize_numeric
from src.indicator_status import indicator_status
from src.ai_insight import generate_ai_insight

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(page_title="All In One GRI Platform", layout="wide")
st.title("🏢 All In One GRI Platform — Companies")

# =========================================
# UNIT MAP
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
# HELPERS
# =========================================
def classify_kpi(value):
    try:
        value = float(value)
    except Exception:
        return "N/A"

    if value <= 30:
        return "Excellent"
    elif value <= 70:
        return "Moderate"
    else:
        return "Risky"


def calculate_esg_score(kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    score, used = 0, 0
    for k, v in kpis.items():
        v = normalize_numeric(v)
        if v is None:
            continue

        for key, w in weights.items():
            if key in k.lower():
                score += max(0, 100 - v) * w
                used += w

    if used == 0:
        return 0, "N/A"

    final = round(score / used, 2)
    return final, classify_kpi(100 - final)


# =====================================================
# 🔴 الإضافة 1: KPI Contribution (مطلوبة للكود)
# =====================================================
def calculate_kpi_contribution(kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    rows = []
    for kpi, value in kpis.items():
        val = normalize_numeric(value)
        if val is None:
            continue

        for key, weight in weights.items():
            if key in kpi.lower():
                rows.append({
                    "KPI": kpi,
                    "Value": round(val, 2),
                    "Weight": weight,
                    "Contribution to ESG": round(max(0, 100 - val) * weight, 2)
                })

    return pd.DataFrame(rows)


# =====================================================
# 🔴 الإضافة 2: Future ESG Score (مطلوبة للكود)
# =====================================================
def calculate_future_esg_score(df, selected_category, kpis):
    weights = {
        "energy": 0.25,
        "water": 0.25,
        "emission": 0.35,
        "waste": 0.15
    }

    score, used = 0, 0

    for kpi in kpis:
        trend = get_trend_data(df, selected_category, kpi)
        if not trend or len(trend) < 3:
            continue

        chart_df = pd.DataFrame(trend, index=["Value"]).T
        chart_df.index = chart_df.index.astype(int)

        years = chart_df.index.values
        values = chart_df["Value"].values

        model = np.poly1d(np.polyfit(years, values, 1))
        forecast_value = model(years.max() + 1)

        for key, weight in weights.items():
            if key in kpi.lower():
                score += max(0, 100 - forecast_value) * weight
                used += weight

    if used == 0:
        return None

    return round(score / used, 2)

# =========================================
# COMPANY SELECTION
# =========================================
files = list_company_files()
if not files:
    st.error("❌ No company Excel files found")
    st.stop()

company_file = st.selectbox("📂 Select Company", files)
company_name = company_file.replace(".xlsx", "")
df = load_company_file(company_file)

categories = sorted(df["Category"].dropna().unique())
selected_category = st.selectbox("📊 Select Category", categories)
cat_df = df[df["Category"] == selected_category]

year_cols = sorted([c for c in df.columns if str(c).isdigit()])
kpis = compute_kpis_by_category(df, selected_category)
metric_col = next((c for c in cat_df.columns if "metric" in c.lower()), None)

# =========================================
# TABS (كما هي)
# =========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Data & KPIs",
    "🌍 ESG Score",
    "📈 Trends & Forecast",
    "📄 Reports",
    "🏭 Company Comparison"
])

# ---------- باقي الكود كما هو ----------
# (لم يتم تغيير أي Tab أو منطق)


# =========================================
# TAB 1 — DATA & KPIs
# =========================================
with tab1:
    st.subheader("📑 Raw Data")
    st.dataframe(cat_df, use_container_width=True)

    st.subheader("📌 KPI Smart Cards (YOY)")
    if year_cols:
        cols = st.columns(len(kpis))
        latest = year_cols[-1]
        prev = year_cols[-2] if len(year_cols) > 1 else None

        for col, (k, _) in zip(cols, kpis.items()):
            row = cat_df[cat_df[metric_col] == k]
            if row.empty:
                continue

            latest_val = normalize_numeric(row.iloc[0][latest])
            prev_val = normalize_numeric(row.iloc[0][prev]) if prev else None
            delta = "N/A" if latest_val is None or prev_val is None else f"{latest_val - prev_val:+.2f}"

            col.metric(
                label=f"{k} ({latest})",
                value=f"{latest_val:,.2f}" if latest_val is not None else "N/A",
                delta=delta
            )

# =========================================
# TAB 2 — ESG SCORE + GAUGES
# =========================================
with tab2:
    st.subheader("🌍 Overall ESG Score")

    # =========================
    # Current ESG Score Gauge
    # =========================
    score, status = calculate_esg_score(kpis)
    color = "green" if status == "Excellent" else "orange" if status == "Moderate" else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100"},
        title={"text": f"ESG Score — {status}"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}
    ))
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # Individual KPI Gauges
    # =========================
    st.subheader("📌 Individual KPI Performance")
    cols = st.columns(3)

    for i, (kpi, value) in enumerate(kpis.items()):
        val = normalize_numeric(value)
        if val is None:
            continue

        kpi_status = classify_kpi(val)
        color = "green" if kpi_status == "Excellent" else "orange" if kpi_status == "Moderate" else "red"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": f"{kpi} — {kpi_status}"},
            gauge={"axis": {"range": [0, max(100, val * 1.5)]}, "bar": {"color": color}}
        ))

        cols[i % 3].plotly_chart(fig, use_container_width=True)

    # =========================
    # KPI Contribution to ESG
    # =========================
    st.subheader("📊 KPI Impact on ESG Score")

    contrib_df = calculate_kpi_contribution(kpis)
    if not contrib_df.empty:
        total = contrib_df["Contribution to ESG"].sum()
        contrib_df["Contribution %"] = (contrib_df["Contribution to ESG"] / total * 100).round(1)

        st.dataframe(
            contrib_df.sort_values("Contribution %", ascending=False),
            use_container_width=True
        )

    # =========================
    # Future ESG Score
    # =========================
    st.subheader("🔮 Future ESG Score (Forecast-Based)")

    future_esg = calculate_future_esg_score(df, selected_category, kpis)

    if future_esg is not None:
        delta = future_esg - score

        fig = go.Figure(go.Indicator(
            mode="number+delta",
            value=future_esg,
            delta={
                "reference": score,
                "increasing": {"color": "green"},
                "decreasing": {"color": "red"}
            },
            title={"text": "Projected ESG Score (Next Year)"}
        ))

        st.plotly_chart(fig, use_container_width=True)

        st.info(
            f"📊 ESG Outlook: "
            f"{'Improving 📈' if delta > 0 else 'Worsening 📉'} "
            f"({delta:+.2f})"
        )
    else:
        st.warning("Insufficient historical data to calculate Future ESG Score.")


# =========================================
# TAB 3 — TRENDS & FORECAST
# =========================================
with tab3:
    st.subheader("📈 KPI Trends & Forecast")

    for metric in kpis:
        trend = get_trend_data(df, selected_category, metric)
        if not trend:
            continue

        # تحويل البيانات إلى DataFrame
        chart_df = pd.DataFrame(trend, index=["Value"]).T
        chart_df.index = chart_df.index.astype(int)

        # ======================
        # إنشاء الشكل
        # ======================
        fig = go.Figure()

        # البيانات التاريخية
        fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["Value"],
                mode="lines+markers",
                name="Historical Data"
            )
        )

        # ======================
        # Forecasting (Linear Regression)
        # ======================
        if len(chart_df) >= 3:
            years = chart_df.index.values
            values = chart_df["Value"].values

            model = np.poly1d(np.polyfit(years, values, 1))
            next_year = years.max() + 1
            forecast_value = model(next_year)

            # نقطة التوقع
            fig.add_trace(
                go.Scatter(
                    x=[next_year],
                    y=[forecast_value],
                    mode="markers",
                    marker=dict(size=12, symbol="x"),
                    name="Forecast"
                )
            )

            # خط التوقع المتقطع
            fig.add_trace(
                go.Scatter(
                    x=[years.max(), next_year],
                    y=[values[-1], forecast_value],
                    mode="lines",
                    line=dict(dash="dash"),
                    name="Forecast Trend"
                )
            )

            # نص توضيحي
            st.info(
                f"🔮 {metric} — Forecast for {next_year}: {forecast_value:.2f}"
            )

        # ======================
        # تنسيق الشكل
        # ======================
        fig.update_layout(
            title=f"{metric} Trend & Forecast",
            xaxis_title="Year",
            yaxis_title="Value",
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)


# =========================================
# TAB 4 — REPORTS & EMAIL
# =========================================
with tab4:
    if st.button("✅ Generate PDF"):
        pdf = build_company_pdf(company_name, df, kpis, selected_category)
        st.session_state.company_pdf = pdf
        st.success("PDF Generated")

    if "company_pdf" in st.session_state:
        st.download_button(
            "⬇ Download PDF",
            st.session_state.company_pdf.getvalue(),
            f"{company_name}_GRI_Report.pdf",
            "application/pdf"
        )

    email = st.text_input("📧 Receiver Email")
    if st.button("📨 Send Email"):
        send_pdf_via_email(
            email,
            st.session_state.company_pdf.getvalue(),
            f"{company_name}_GRI_Report.pdf",
            "GRI Report"
        )
        st.success("Email Sent")

# =========================================
# TAB 5 — COMPANY COMPARISON + AI + HEATMAP
# =========================================
with tab5:
    st.subheader("🏭 Company Comparison")

    compare_files = st.multiselect(
        "Select companies to compare",
        files,
        default=[company_file]
    )

    if len(compare_files) >= 2:
        rows = []
        for file in compare_files:
            comp_df = load_company_file(file)
            comp_name = file.replace(".xlsx", "")
            year_cols_c = sorted([c for c in comp_df.columns if str(c).isdigit()])

            for _, row in comp_df.iterrows():
                status, coverage = indicator_status(row[year_cols_c])
                rows.append({
                    "Company": comp_name,
                    "Indicator": row[metric_col],
                    "Status": status,
                    "Coverage %": coverage
                })

        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.subheader("🤖 AI Insights")
        selected_ai_company = st.selectbox("Select company", compare_files)
        ai_df = load_company_file(selected_ai_company)
        year_cols_ai = sorted([c for c in ai_df.columns if str(c).isdigit()])

        analysis = []
        for _, row in ai_df.iterrows():
            status, coverage = indicator_status(row[year_cols_ai])
            analysis.append({
                "indicator": row[metric_col],
                "status": status,
                "coverage": coverage
            })

        for insight in generate_ai_insight(selected_ai_company.replace(".xlsx", ""), analysis):
            st.info(insight)

        st.subheader("🔥 GRI Status Heatmap")
        status_map = {"Reported": 2, "Partial": 1, "Not Reported": 0}
        heatmap = {}

        for file in compare_files:
            comp_df = load_company_file(file)
            comp_name = file.replace(".xlsx", "")
            year_cols_h = sorted([c for c in comp_df.columns if str(c).isdigit()])
            heatmap[comp_name] = {}

            for _, row in comp_df.iterrows():
                status, _ = indicator_status(row[year_cols_h])
                heatmap[comp_name][row[metric_col]] = status_map[status]

        heatmap_df = pd.DataFrame.from_dict(heatmap, orient="index").T
        st.dataframe(
            heatmap_df.style.background_gradient(cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.info("Select at least two companies to enable comparison")
