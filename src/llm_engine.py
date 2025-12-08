# src/llm_engine.py

import os
from typing import Dict, List
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# -----------------------------
# GROQ ONLINE MODEL ONLY
# -----------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY not found in .env file")

client = Groq(api_key=GROQ_API_KEY)


def chat_completion(messages: List[Dict[str, str]]):
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )
        return resp.choices[0].message.content  # ✅ SDK الجديد
    except Exception as e:
        return f"❌ LLM Error: {str(e)}"
