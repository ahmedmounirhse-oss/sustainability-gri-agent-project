import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import os
from dotenv import load_dotenv
from groq import Groq

# =========================
# ✅ LOAD ENV & GROQ CLIENT
# =========================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found in .env file")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ✅ موديل مستقر ومجاني وسريع
GROQ_MODEL = "llama-3.1-8b-instant"

# =========================
# ✅ PAGE CONFIG
# =========================
st.set_page_config(page_title="GRI AI Chat (Groq)", layout="wide")
st.title("💬 GRI AI Chat — Powered by Groq (Free)")
st.write("Upload Sustainability PDF & Excel and ask questions in natural language.")

# =========================
# ✅ SESSION STATE
# =========================
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "excel_text" not in st.session_state:
    st.session_state.excel_text = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================
# ✅ FILE UPLOAD SECTION
# =========================
st.subheader("📂 Upload Data Files")

col1, col2 = st.columns(2)

# -------- PDF Upload --------
with col1:
    pdf_file = st.file_uploader("Upload Sustainability / GRI PDF", type=["pdf"])

    if pdf_file:
        try:
            with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
                full_text = ""
                for page in doc:
                    full_text += page.get_text()

            st.session_state.pdf_text = full_text
            st.success("✅ PDF uploaded and processed successfully!")

        except Exception as e:
            st.error(f"❌ Error reading PDF: {e}")

# -------- Excel Upload --------
with col2:
    excel_files = st.file_uploader(
        "Upload Excel Files (Energy, Water, Emissions, Waste, ESG...)",
        type=["xlsx", "xls"],
        accept_multiple_files=True
    )

    if excel_files:
        try:
            excel_text_combined = ""

            for file in excel_files:
                df = pd.read_excel(file)
                excel_text_combined += f"\n--- Data from file: {file.name} ---\n"
                excel_text_combined += df.head(50).to_string()

            st.session_state.excel_text = excel_text_combined
            st.success("✅ Excel files uploaded and processed successfully!")

        except Exception as e:
            st.error(f"❌ Error reading Excel file: {e}")

# =========================
# ✅ COMBINED CONTEXT
# =========================
combined_context = f"""
PDF CONTENT:
{st.session_state.pdf_text}

EXCEL CONTENT:
{st.session_state.excel_text}
"""

# =========================
# ✅ QUESTION INPUT
# =========================
if st.session_state.pdf_text or st.session_state.excel_text:

    st.subheader("💭 Ask About the Uploaded Data")

    user_question = st.text_input(
        "Ask anything about the uploaded PDF / Excel data:",
        placeholder="e.g. Compare emissions between the report and the Excel data"
    )

    if st.button("🤖 Ask AI (Groq)"):

        if not user_question.strip():
            st.warning("⚠ Please enter a question.")
        else:
            try:
                prompt = f"""
You are a professional sustainability and GRI reporting analyst.

STRICT RULES:
- Do NOT mention page numbers.
- Do NOT say "refer to the report".
- Do NOT use academic citation style.
- Do NOT speculate.
- If an exact number is missing, clearly say: "The data does not provide an exact figure."
- Always answer in simple, direct, professional English.
- Focus on practical interpretation.
- If Excel and PDF conflict, clearly explain the difference.

Use ONLY the following data:

-------------------
{combined_context[:18000]}
-------------------

User Question:
{user_question}

Give a final answer suitable for presentation to a university professor.
"""

                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )

                answer = response.choices[0].message.content.strip()

                st.session_state.chat_history.append(("You", user_question))
                st.session_state.chat_history.append(("AI", answer))

            except Exception as e:
                st.error(f"❌ Groq AI Error: {e}")

else:
    st.info("⬆ Please upload at least one PDF or Excel file to start.")

# =========================
# ✅ DISPLAY CHAT
# =========================
if st.session_state.chat_history:
    st.markdown("---")
    st.subheader("🗨️ Conversation")

    for role, msg in st.session_state.chat_history:
        if role == "You":
            st.markdown(f"**🧑 You:** {msg}")
        else:
            st.markdown(f"**🤖 AI:** {msg}")

# =========================
# ✅ RESET CHAT
# =========================
if st.button("🔄 Reset Chat"):
    st.session_state.chat_history = []
    st.session_state.pdf_text = ""
    st.session_state.excel_text = ""
    st.success("✅ Chat reset successfully.")
