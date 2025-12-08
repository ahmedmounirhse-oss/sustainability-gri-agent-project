import streamlit as st
import os
import re
import pandas as pd
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from src.email_sender import send_pdf_via_email


st.set_page_config(page_title="GRI PDF Report Generator", layout="wide")

# =========================
# ✅ CONFIG
# =========================
EXCEL_FOLDER = "data/Excel"

# ✅ AUTO-DETECT LOGO
LOGO_PATH = None
for ext in ["png", "jpg", "jpeg"]:
    p = f"assets/company_logo.{ext}"
    if os.path.exists(p):
        LOGO_PATH = p
        break

excel_files = os.listdir(EXCEL_FOLDER) if os.path.exists(EXCEL_FOLDER) else []

def extract_year_from_filename(filename):
    found = re.findall(r"\d{4}", filename)
    return found[0] if found else filename.replace(".xlsx", "")

available_years = {
    extract_year_from_filename(file): file for file in excel_files
}

# =========================
# ✅ UI
# =========================
st.title("📄 Full Professional GRI Report Generator (All Pages)")
st.write("Final stable version — Cover + All GRI Pages + Appendix")

if not available_years:
    st.error("❌ No Excel files found inside data/Excel folder.")
    st.stop()

selected_year = st.selectbox("Select Reporting Year", list(available_years.keys()))
selected_file = available_years[selected_year]

# =========================
# ✅ LOAD DATA
# =========================
df = pd.read_excel(os.path.join(EXCEL_FOLDER, selected_file))

year_number = int(re.findall(r"\d{4}", str(selected_year))[0])

year_df = df[df["Year"] == year_number]

# =========================
# ✅ SAFE KPI EXTRACTOR (LONG FORMAT)
# =========================
def get_kpi_block(keyword):
    block = year_df[year_df["Indicator"].astype(str).str.contains(keyword, case=False, na=False)]

    if block.empty:
        return 0, [], ""

    total = round(block["Value"].sum(), 2)
    monthly = block["Value"].tolist()

    unit = ""
    if "Unit" in block.columns and not block["Unit"].isna().all():
        unit = str(block["Unit"].iloc[0])

    return total, monthly, unit


energy_total, energy_monthly, energy_unit       = get_kpi_block("Energy")
water_total, water_monthly, water_unit          = get_kpi_block("Water")
emission_total, emission_monthly, emission_unit = get_kpi_block("Emission")
waste_total, waste_monthly, waste_unit          = get_kpi_block("Waste")

# =========================
# ✅ FINAL PDF GENERATOR (ALL PAGES)
# =========================
def build_full_gri_report():

    styles = getSampleStyleSheet()

    center_title = ParagraphStyle(
        name="CenterTitle", parent=styles["Title"],
        alignment=TA_CENTER, fontSize=26, spaceAfter=20
    )

    center_year = ParagraphStyle(
        name="CenterYear", parent=styles["Normal"],
        alignment=TA_CENTER, fontSize=16, spaceAfter=12
    )

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    elements = []

    # =========================
    # ✅ PAGE 1 — COVER
    # =========================
    elements.append(Spacer(1, 120))

    if LOGO_PATH:
        logo = Image(LOGO_PATH, width=160, height=80)
        logo.hAlign = "CENTER"
        elements.append(logo)
        elements.append(Spacer(1, 40))

    elements.append(Paragraph("Sustainability GRI Report", center_title))
    elements.append(Paragraph(str(year_number), center_year))

    elements.append(Spacer(1, 220))
    elements.append(
        Paragraph(
            f"Generated on {datetime.today().strftime('%Y-%m-%d')}",
            ParagraphStyle(name="Footer", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9),
        )
    )

    elements.append(PageBreak())

    # =========================
    # ✅ PAGE 2 — EXECUTIVE SUMMARY
    # =========================
    elements.append(Paragraph("Executive Summary", styles["Heading2"]))

    elements.append(Paragraph(f"- Energy Consumption (GRI 302): {energy_total:,.2f} {energy_unit}", styles["Normal"]))
    elements.append(Paragraph(f"- Water Usage (GRI 303): {water_total:,.2f} {water_unit}", styles["Normal"]))
    elements.append(Paragraph(f"- GHG Emissions (GRI 305): {emission_total:,.2f} {emission_unit}", styles["Normal"]))
    elements.append(Paragraph(f"- Waste Generation (GRI 306): {waste_total:,.2f} {waste_unit}", styles["Normal"]))

    elements.append(PageBreak())

    # =========================
    # ✅ SECTION BUILDER
    # =========================
    def add_section(title, gri_ref, total, monthly, unit):

        elements.append(Paragraph(title, styles["Heading2"]))
        elements.append(Paragraph(f"GRI Reference: {gri_ref}", styles["Normal"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(f"Total: {total:,.2f} {unit}", styles["Normal"]))
        elements.append(Paragraph("YoY Change: n/a", styles["Normal"]))
        elements.append(Paragraph("YoY % Change: n/a", styles["Normal"]))
        elements.append(Spacer(1, 12))

        if monthly:
            high = max(monthly)
            low = min(monthly)
            high_m = monthly.index(high) + 1
            low_m = monthly.index(low) + 1

            narrative = (
                f"In {year_number}, the organization reported a total of {total:,.2f} {unit}. "
                f"The highest monthly value occurred in month {high_m}, while the lowest occurred in month {low_m}."
            )
        else:
            narrative = (
                f"In {year_number}, the organization reported a total of {total:,.2f} {unit}. "
                f"No monthly breakdown data was available."
            )

        elements.append(Paragraph("Narrative", styles["Heading3"]))
        elements.append(Paragraph(narrative, styles["Normal"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph("Monthly Data", styles["Heading3"]))
        table_data = [["Month", "Value", "Unit"]]

        if monthly:
            for i, v in enumerate(monthly, 1):
                table_data.append([str(i), f"{v:,.2f}", unit])
        else:
            table_data.append(["-", "No Data", unit])

        elements.append(Table(table_data))
        elements.append(PageBreak())

    # =========================
    # ✅ ALL GRI SECTIONS
    # =========================
    add_section("Energy Consumption", "GRI 302", energy_total, energy_monthly, energy_unit)
    add_section("Water Usage", "GRI 303", water_total, water_monthly, water_unit)
    add_section("GHG Emissions", "GRI 305", emission_total, emission_monthly, emission_unit)
    add_section("Waste Generation", "GRI 306", waste_total, waste_monthly, waste_unit)

    # =========================
    # ✅ FINAL PAGE — APPENDIX
    # =========================
    elements.append(Paragraph("Appendix — Annual Raw Data", styles["Heading2"]))
    summary = year_df.describe().round(2).reset_index()
    elements.append(Table([summary.columns.tolist()] + summary.values.tolist()))

    # =========================
    # ✅ BUILD PDF
    # =========================
    doc = SimpleDocTemplate(temp.name, pagesize=A4)
    doc.build(elements)

    return temp.name


# =========================
# ✅ UI CONTROLS
# =========================
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None

if st.button("📄 Generate FULL GRI PDF"):
    st.session_state.pdf_path = build_full_gri_report()
    st.success("✅ Full GRI Report Generated Successfully!")

if st.session_state.pdf_path:
    with open(st.session_state.pdf_path, "rb") as f:
        pdf_bytes = f.read()

    st.download_button(
        "⬇ Download Full GRI PDF",
        data=pdf_bytes,
        file_name=f"GRI_Report_{year_number}.pdf",
        mime="application/pdf",
    )

    st.subheader("📧 Send Report via Email")
    receiver = st.text_input("Recipient Email")

    if st.button("Send Report via Email"):
        send_pdf_via_email(
            receiver_email=receiver,
            pdf_bytes=pdf_bytes,
            pdf_name=f"GRI_Report_{year_number}.pdf",
            year=year_number,
        )
        st.success(f"✅ Report successfully emailed to {receiver}")
