import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def detect_metric_column(df):
    possible_cols = [
        "Additional Metrics (Energy)",
        "Additional Metrics",
        "Metric",
        "Indicator",
        "KPI"
    ]
    for col in possible_cols:
        if col in df.columns:
            return col
    return None

def plot(fig, name):
    st.plotly_chart(
        fig,
        width="stretch",
        key=f"{name}_{id(fig)}"
    )

def safe_plotly(fig, key_prefix):
    st.plotly_chart(
        fig,
        width="stretch",
        key=f"{key_prefix}_{id(fig)}"
    )

def safe_subtract(a, b):
    if a is None or b is None:
        return None
    return a - b

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

# =========================================
# UI STYLE (Bold Tabs & Titles)
# =========================================
st.markdown("""
<div style="
    font-size:38px;
    font-weight:900;
    color:#0E4C92;
    margin-bottom:20px;
">
🌍 ESG Score Dashboard
</div>
""", unsafe_allow_html=True)

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

def calculate_future_esg_score(df, selected_category, kpis):
    ...
    return round(score / used, 2)

# =========================================
# GRI KNOWLEDGE BASE (STATIC)
# =========================================
GRI_KNOWLEDGE = {
    "energy": {
        "standard": "GRI 302 – Energy",
        "description": (
            "GRI 302 focuses on energy consumption, efficiency, and reduction initiatives. "
            "High energy intensity indicates poor efficiency and increased environmental impact."
        ),
        "recommendation": (
            "Organizations should prioritize energy efficiency programs, renewable energy adoption, "
            "and energy intensity reduction targets."
        )
    },
    "water": {
        "standard": "GRI 303 – Water and Effluents",
        "description": (
            "GRI 303 addresses water withdrawal, consumption, and water-related impacts. "
            "High water usage may indicate operational inefficiencies or sustainability risks."
        ),
        "recommendation": (
            "Water efficiency measures, recycling, and monitoring water-stressed areas are recommended."
        )
    },
    "emission": {
        "standard": "GRI 305 – Emissions",
        "description": (
            "GRI 305 covers greenhouse gas emissions and reduction strategies. "
            "High emissions represent significant climate-related risk."
        ),
        "recommendation": (
            "Emission reduction strategies, energy transition, and carbon management programs are required."
        )
    },
    "waste": {
        "standard": "GRI 306 – Waste",
        "description": (
            "GRI 306 focuses on waste generation, management, and disposal methods."
        ),
        "recommendation": (
            "Waste minimization, recycling, and circular economy practices are recommended."
        )
    }
}

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Data & KPIs",
    "🌍 ESG Score",
    "📈 Trends & Forecast",
    "📄 Reports",
    "🏭 Company Comparison",
    "🤖 Sustainability AI Assistant"
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

        for col, (k, _) in zip(cols, kpis.items()):
            row = cat_df[cat_df[metric_col] == k]
            if row.empty:
                continue

            # 🔹 جمع القيم الرقمية فقط
            values = []
            for y in sorted(year_cols, reverse=True):
                v = normalize_numeric(row.iloc[0][y])
                if isinstance(v, (int, float)):
                    values.append((y, v))

            if not values:
                col.metric(label=k, value="N/A")
                continue

            latest_year, latest_val = values[0]

            # 🔹 حالة سنة واحدة فقط (NO DELTA AT ALL)
            if len(values) < 2:
                col.metric(
                    label=f"{k} ({latest_year})",
                    value=f"{latest_val:,.2f}"
                )
                continue

            prev_val = values[1][1]
            delta_val = latest_val - prev_val

            # 🔥 استدعاء نظيف بدون أي None
            col.metric(
                label=f"{k} ({latest_year})",
                value=f"{latest_val:,.2f}",
                delta=f"{delta_val:+.2f}"
            )

# =========================================
# TAB 2 — ESG SCORE + GAUGES
# =========================================
# =========================================
# TAB 2 — ESG SCORE + GAUGES
# =========================================
with tab2:
    st.subheader("🌍 Overall ESG Score")

    # =========================
    # Current ESG Score Gauge
    # =========================
    score, status = calculate_esg_score(kpis)

    if status == "N/A" or score == 0:
        st.warning("ESG Score cannot be calculated due to missing or unclassified KPI data.")
    else:
        color = "green" if status == "Excellent" else "orange" if status == "Moderate" else "red"

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": " / 100"},
            title={"text": f"ESG Score — {status}"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}
        ))
        plot(fig, "trend")


    # =========================
    # ESG Calculation Methodology
    # =========================
    with st.expander("📘 How is the ESG Score Calculated?"):
        st.markdown("""
### ESG Score Calculation Methodology

The ESG score is calculated using a weighted, risk-oriented approach based on environmental KPIs.

**Step 1 – KPI Normalization**  
Each KPI value is transformed into a performance score using:

\[
Adjusted\ KPI\ Score = 100 - KPI\ Value
\]

**Step 2 – Category Weighting**
- Energy: 25%
- Water: 25%
- Emissions: 35%
- Waste: 15%

**Step 3 – Weighted Aggregation**

\[
ESG\ Score = \frac{\sum (Adjusted\ KPI \times Weight)}{\sum Weights}
\]

**Step 4 – Risk Classification**
- ESG ≥ 70 → Excellent (Low Risk)
- ESG 40–69 → Moderate (Medium Risk)
- ESG < 40 → Risky (High Risk)
        """)

# =========================================
# TAB 2 — ESG SCORE + GAUGES
# =========================================
with tab2:
    st.subheader("🌍 Overall ESG Score")

    # =========================
    # Overall ESG Score
    # =========================
    score, status = calculate_esg_score(kpis)

    if score is None or score == 0 or status == "N/A":
        st.warning("⚠️ ESG Score cannot be calculated due to missing KPI data.")
    else:
        color = (
            "green" if status == "Excellent"
            else "orange" if status == "Moderate"
            else "red"
        )

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(score),
                number={"suffix": " / 100"},
                title={"text": f"ESG Score — {status}"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": color}
                }
            )
        )

        plot(fig, "trend")


    # =========================
    # ESG Methodology
    # =========================
    with st.expander("📘 How is the ESG Score Calculated?"):
        st.markdown("""
**Methodology Summary**

- ESG Score is calculated using weighted environmental KPIs.
- Formula:  
  ESG Score = Σ((100 − KPI Value) × Weight) / Σ(Weights)

**Weights**
- Energy: 25%
- Water: 25%
- Emissions: 35%
- Waste: 15%

**Risk Levels**
- ≥ 70 → Excellent
- 40–69 → Moderate
- < 40 → Risky
        """)

    # =========================
    # Individual KPI Gauges
    # =========================
    st.subheader("📌 Individual KPI Performance")
    cols = st.columns(3)

    for i, (kpi, value) in enumerate(kpis.items()):
        val = normalize_numeric(value)

        # skip non-numeric
        if not isinstance(val, (int, float)):
            continue

        kpi_status = classify_kpi(val)
        color = (
            "green" if kpi_status == "Excellent"
            else "orange" if kpi_status == "Moderate"
            else "red"
        )

        max_range = max(100.0, float(val) * 1.5)

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(val),
                title={"text": f"{kpi} — {kpi_status}"},
                gauge={
                    "axis": {"range": [0, max_range]},
                    "bar": {"color": color}
                }
            )
        )

        cols[i % 3].plotly_chart(fig, width="stretch")



# =========================================
# TAB 3 — KPI Trends & Forecast (FINAL FINAL)
# =========================================
with tab3:
    st.subheader("📈 KPI Trends & Forecast")

    for i, metric in enumerate(kpis):
        trend = get_trend_data(df, selected_category, metric)
        if not trend:
            continue

        # ----------------------
        # Prepare Data
        # ----------------------
        chart_df = pd.DataFrame(trend, index=["Value"]).T
        chart_df.index = chart_df.index.astype(int)
        chart_df["Value"] = pd.to_numeric(chart_df["Value"], errors="coerce")

        # ----------------------
        # Create Figure
        # ----------------------
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["Value"],
                mode="lines+markers",
                name="Historical Data"
            )
        )

        # ----------------------
        # Forecasting (SAFE)
        # ----------------------
        clean_df = chart_df.dropna(subset=["Value"])

        if len(clean_df) >= 2:
            years = clean_df.index.values.astype(float)
            values = clean_df["Value"].values.astype(float)

            model = np.poly1d(np.polyfit(years, values, 1))
            next_year = int(years.max() + 1)
            forecast_value = float(model(next_year))

            fig.add_trace(
                go.Scatter(
                    x=[next_year],
                    y=[forecast_value],
                    mode="markers",
                    marker=dict(size=12, symbol="x"),
                    name="Forecast"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=[years.max(), next_year],
                    y=[values[-1], forecast_value],
                    mode="lines",
                    line=dict(dash="dash"),
                    name="Forecast Trend"
                )
            )

            # ✅ markdown بدل info
            st.markdown(
                f"🔮 **{metric}** — Forecast for **{next_year}**: `{forecast_value:.2f}`"
            )
        else:
            # ✅ markdown بدل warning
            st.markdown(
                f"⚠️ **{metric}**: Not enough numeric data to forecast"
            )

        # ----------------------
        # Safe Axis Handling
        # ----------------------
        y_values = clean_df["Value"]

        fig.update_layout(
            title=f"{metric} Trend & Forecast",
            xaxis_title="Year",
            yaxis_title="Value",
            yaxis_range=[
                0,
                y_values.max() * 1.2
            ] if not y_values.empty and y_values.max() > 0 else None,
            template="plotly_white"
        )

        # ----------------------
        # Plot (WITH UNIQUE KEY)
        # ----------------------
        plot(fig, "trend")


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

            metric_col_c = detect_metric_column(comp_df)
            if metric_col_c is None:
                continue

            year_cols_c = sorted([c for c in comp_df.columns if str(c).isdigit()])

            for _, row in comp_df.iterrows():
                status, coverage = indicator_status(row[year_cols_c])
                rows.append({
                    "Company": comp_name,
                    "Indicator": row[metric_col_c],
                    "Status": status,
                    "Coverage %": coverage
                })

        st.dataframe(
            pd.DataFrame(rows),
            width="stretch"
        )

        # =========================
        # AI INSIGHTS
        # =========================
        st.subheader("🤖 AI Insights")

        selected_ai_company = st.selectbox("Select company", compare_files)
        ai_df = load_company_file(selected_ai_company)

        metric_col_ai = detect_metric_column(ai_df)
        if metric_col_ai is not None:
            year_cols_ai = sorted([c for c in ai_df.columns if str(c).isdigit()])
            analysis = []

            for _, row in ai_df.iterrows():
                status, coverage = indicator_status(row[year_cols_ai])
                analysis.append({
                    "indicator": row[metric_col_ai],
                    "status": status,
                    "coverage": coverage
                })

            for insight in generate_ai_insight(
                selected_ai_company.replace(".xlsx", ""),
                analysis
            ):
                st.markdown(f"🔹 {insight}")

        # =========================
        # GRI STATUS HEATMAP
        # =========================
        st.subheader("🔥 GRI Status Heatmap")

        status_map = {"Reported": 2, "Partial": 1, "Not Reported": 0}
        heatmap = {}

        for file in compare_files:
            comp_df = load_company_file(file)
            comp_name = file.replace(".xlsx", "")

            metric_col_h = detect_metric_column(comp_df)
            if metric_col_h is None:
                continue

            year_cols_h = sorted([c for c in comp_df.columns if str(c).isdigit()])
            heatmap[comp_name] = {}

            for _, row in comp_df.iterrows():
                status, _ = indicator_status(row[year_cols_h])
                heatmap[comp_name][row[metric_col_h]] = status_map.get(status, 0)

        if heatmap:
            heatmap_df = pd.DataFrame.from_dict(heatmap, orient="index").T
            st.dataframe(
                heatmap_df.style.background_gradient(cmap="RdYlGn"),
                width="stretch"
            )

    else:
        st.info("Select at least two companies to enable comparison")

# =========================================
# TAB 6 — SUSTAINABILITY AI ASSISTANT
# =========================================
with tab6:
    st.subheader("🤖 Sustainability AI Assistant")
    st.write("Ask questions about company ESG data or GRI standards.")

    # ---------- Context ----------
    esg_score, esg_status = calculate_esg_score(kpis)
    contrib_df = calculate_kpi_contribution(kpis)

    context = {
        "company": company_name,
        "esg_score": esg_score,
        "esg_status": esg_status,
        "top_kpis": (
            contrib_df.sort_values("Contribution to ESG", ascending=False)
            .head(3)["KPI"]
            .tolist()
            if not contrib_df.empty else []
        )
    }

    # ---------- AI Logic ----------
    def ai_chat_response(question, ctx):
        q = question.lower()

        # ---- GRI QUESTIONS ----
        if "gri" in q or "standard" in q:
            for key, info in GRI_KNOWLEDGE.items():
                if key in q:
                    return (
                        f"{info['standard']}\n\n"
                        f"{info['description']}\n\n"
                        f"Recommended actions:\n{info['recommendation']}"
                    )
            return (
                "GRI standards covered:\n"
                "- GRI 302 (Energy)\n"
                "- GRI 303 (Water)\n"
                "- GRI 305 (Emissions)\n"
                "- GRI 306 (Waste)"
            )

        # ---- CURRENT ESG ----
        if "esg" in q:
            if ctx["esg_score"] is None or ctx["esg_status"] == "N/A":
                return "ESG score is currently unavailable due to missing data."

            return (
                f"Current ESG score for {ctx['company']} is "
                f"{ctx['esg_score']} ({ctx['esg_status']})."
            )

        # ---- KPI INSIGHT ----
        if "kpi" in q or "risk" in q:
            if not ctx["top_kpis"]:
                return "No high-impact KPIs identified due to insufficient data."
            return (
                "Top ESG-impact KPIs:\n- "
                + "\n- ".join(ctx["top_kpis"])
            )

        return (
            "You can ask about ESG score, KPI risks, or GRI standards."
        )

    # ---------- INPUT ----------
    user_question = st.text_input(
        "💬 Ask the Sustainability AI Assistant",
        placeholder="e.g. What does GRI 305 mean?"
    )

    if user_question:
        answer = ai_chat_response(user_question, context)
        st.chat_message("assistant").write(answer)
