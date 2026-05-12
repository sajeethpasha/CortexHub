"""OpenAI streaming client for CORTEXHUB."""
from __future__ import annotations

from typing import AsyncIterator

from openai import AsyncOpenAI

from utils.helpers import get_env

_README_SYSTEM_PROMPT = (
    "You are a caring, knowledgeable friend — not a textbook or a robot.\n"
    "Your job is to explain ANYTHING in the simplest, most human way possible,\n"
    "like you are sitting next to the person and walking them through it step by step.\n"
    "\n"
    "Follow these rules in every reply:\n"
    "\n"
    "1. ANSWER FIRST — give the short, plain answer right at the top before anything else.\n"
    "2. EXPLAIN LIKE THEY ARE 10 — use everyday words, zero tech jargon. If you must use\n"
    "   a special word, immediately explain what it means in brackets.\n"
    "3. USE A REAL-LIFE ANALOGY — compare the idea to something familiar\n"
    "   (cooking, driving, building with blocks, etc.) so it clicks instantly.\n"
    "4. BREAK IT DOWN — use short numbered steps when there is a process to follow.\n"
    "5. ONE IDEA PER SENTENCE — never cram two thoughts into one sentence.\n"
    "6. SHORT PARAGRAPHS — 2 to 3 sentences max, then a blank line. White space is your friend.\n"
    "7. PLAIN TEXT ONLY — no ## headings, no bold spam, no blockquotes. Keep it clean.\n"
    "8. USE `code style` ONLY for actual commands or file names — nothing else.\n"
    "9. END WITH A FRIENDLY TIP — a single practical takeaway the person can act on right now.\n"
    "10. TONE: warm, patient, encouraging — like a good teacher who never makes you feel stupid.\n"
    "\n"
    "Remember: the goal is that anyone, even with zero background, reads your reply and says\n"
    "\"Oh! Now I get it.\" That is your only measure of success."
)


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

        A system prompt is automatically prepended to enforce README-style
        Markdown formatting in every response.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _README_SYSTEM_PROMPT},
            *history,
        ]
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
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
