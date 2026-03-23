from __future__ import annotations

import json
from typing import Type

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logger import setup_logger

settings = get_settings()
logger = setup_logger()
from app.utils.logger import logger


class LLMService:
    """Simple async LLM service using OpenAI interface.

    Supports both OpenAI and Ollama (which uses OpenAI-compatible interface).
    """

    def __init__(self):
        # Lazy client initialization to avoid constructing network clients at import time
        self.client: AsyncOpenAI | None = None
        self.model = settings.OLLAMA_MODEL

    def _ensure_client(self) -> None:
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=settings.OLLAMA_KEY,
                base_url=settings.OLLAMA_URL,
            )
            logger.info("LLM client initialized with model=%s", self.model)

    async def call_structured(
        self, message: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """Call LLM with structured output using Pydantic model."""
        self._ensure_client()
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
        except Exception as exc:
            logger.exception("Failed to parse LLM response: %s", exc)
            # Return empty model if parsing fails
            return response_model()

    async def call_raw(self, message: str) -> str:
        """Call LLM and return raw text response."""
        self._ensure_client()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message}],
        )

        return response.choices[0].message.content
