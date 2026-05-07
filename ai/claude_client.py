"""Anthropic Claude streaming client for CORTEXHUB."""
from __future__ import annotations

from typing import AsyncIterator

from anthropic import AsyncAnthropic

from utils.helpers import get_env


class ClaudeClient:
    """Thin wrapper around the Anthropic Async SDK for streaming messages."""

    DEFAULT_MODEL = "claude-3-5-haiku-latest"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or get_env("ANTHROPIC_API_KEY")
        self.model = model or get_env("ANTHROPIC_MODEL") or self.DEFAULT_MODEL
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is missing. Set it in your .env file."
            )
        self._client = AsyncAnthropic(api_key=self.api_key)

    async def stream(self, history: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream the assistant's reply for ``history`` as text chunks.

        Anthropic uses the same role/content shape as OpenAI here, but does
        not accept any 'system' entry inside ``messages``; we don't add one.
        """
        # Anthropic requires a non-zero max_tokens
        async with self._client.messages.stream(
            model=self.model,
            max_tokens=2048,
            messages=history,
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
