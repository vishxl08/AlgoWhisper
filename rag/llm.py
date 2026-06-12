"""Groq LLM client for response generation."""

from __future__ import annotations

from groq import Groq

from config import get_settings


class GroqLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY is not set")
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""
