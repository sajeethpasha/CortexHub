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

    async def stream(
        self,
        history: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream the assistant's reply for ``history`` as text chunks.

        *system_prompt* is passed via the top-level Anthropic ``system``
        parameter (not inside messages). Falls back to empty when omitted.
        """
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": history,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        # Anthropic requires a non-zero max_tokens
        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
