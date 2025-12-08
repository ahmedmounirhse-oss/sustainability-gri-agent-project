# src/chat_agent.py

from typing import List, Dict
from src.llm_engine import chat_completion

class ChatAgent:

    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def reset(self):
        self.history = []

    def ask(self, user_input: str, mode: str):
        self.history.append({"role": "user", "content": user_input})

        messages = [{"role": "system", "content": "You are a sustainability expert."}]
        messages.extend(self.history)

        response = chat_completion(messages, mode)

        self.history.append({"role": "assistant", "content": response})

        return response
