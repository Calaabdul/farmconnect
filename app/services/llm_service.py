from __future__ import annotations

import json
from typing import Type

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()


class LLMService:
    """Simple async LLM service using OpenAI interface.

    Supports both OpenAI and Ollama (which uses OpenAI-compatible interface).
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key= settings.OLLAMA_KEY,  # Only use api_key if not using Ollama
            base_url=settings.OLLAMA_URL,
        )
        self.model = settings.OLLAMA_MODEL

    async def call_structured(
        self, message: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """Call LLM with structured output using Pydantic model."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract structured data and return ONLY JSON.",
                },
                {"role": "user", "content": message},
            ],
        )

        text = response.choices[0].message.content
        try:
            # Try to parse as JSON
            data = json.loads(text)
            return response_model(**data)
        except Exception:
            # Return empty model if parsing fails
            return response_model()

    async def call_raw(self, message: str) -> str:
        """Call LLM and return raw text response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message}],
        )

        return response.choices[0].message.content
