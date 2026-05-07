"""OpenAI streaming client for CORTEXHUB."""
from __future__ import annotations

from typing import AsyncIterator

from openai import AsyncOpenAI

from utils.helpers import get_env


class OpenAIClient:
    """Thin wrapper around the OpenAI Async SDK for streaming chat completions."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or get_env("OPENAI_API_KEY")
        self.model = model or get_env("OPENAI_MODEL") or self.DEFAULT_MODEL
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is missing. Set it in your .env file.")
        self._client = AsyncOpenAI(api_key=self.api_key)

    async def stream(self, history: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream the assistant's reply to ``history`` as text chunks.

        ``history`` must be a list of {"role": ..., "content": ...} dicts where
        roles are 'user' or 'assistant'. The most recent user prompt is the
        last entry in the list.
        """
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=history,
            stream=True,
        )
        async for event in stream:
            try:
                delta = event.choices[0].delta
            except (IndexError, AttributeError):
                continue
            chunk = getattr(delta, "content", None)
            if chunk:
                yield chunk
