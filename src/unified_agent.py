# src/unified_agent.py

from src.llm_engine import chat_completion
from src.document_processor import extract_text_from_pdf_bytes, load_excel_file_bytes


class UnifiedAgent:

    def __init__(self):
        self.memory = {
            "pdfs": {},     # name -> text
            "excels": {},   # name -> {sheet: df}
            "chat": []
        }

    def upload_pdf(self, name: str, pdf_bytes: bytes):
        text = extract_text_from_pdf_bytes(pdf_bytes)
        self.memory["pdfs"][name] = text
        return text[:1500]

    def upload_excel(self, name: str, excel_bytes: bytes):
        sheets = load_excel_file_bytes(excel_bytes)
        self.memory["excels"][name] = sheets
        return list(sheets.keys())

    def ask(self, question: str, mode="general"):
        system_prompt = """
You are a professional Sustainability & GRI Expert AI.

Capabilities:
- Answer ANY GRI questions professionally
- Analyze uploaded PDF sustainability reports
- Analyze uploaded Excel KPI data (Energy, Water, Emissions, Waste)
- Never invent numbers if documents are provided
"""

        context_text = ""

        if self.memory["pdfs"]:
            for name, txt in self.memory["pdfs"].items():
                context_text += f"\nPDF ({name}) Extract:\n{txt[:2000]}\n"

        if self.memory["excels"]:
            for name, sheets in self.memory["excels"].items():
                context_text += f"\nExcel ({name}) Sheets:\n"
                for sname, df in sheets.items():
                    context_text += f"\nSheet: {sname}\n{df.head().to_string()}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question:\n{question}\n\nContext:\n{context_text}"}
        ]

        answer = chat_completion(messages)

        self.memory["chat"].append(("user", question))
        self.memory["chat"].append(("assistant", answer))

        return answer
