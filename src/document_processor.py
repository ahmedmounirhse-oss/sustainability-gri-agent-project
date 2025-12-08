# src/document_processor.py
import io
import pandas as pd

try:
    import pdfplumber
except:
    pdfplumber = None


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if not pdfplumber:
        return "❌ pdfplumber not installed"
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n\n".join(pages)


def load_excel_file_bytes(excel_bytes: bytes):
    xls = pd.ExcelFile(io.BytesIO(excel_bytes))
    sheets = {}
    for sheet in xls.sheet_names:
        sheets[sheet] = xls.parse(sheet)
    return sheets
