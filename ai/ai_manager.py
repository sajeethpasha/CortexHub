"""AIManager: coordinates per-model clients and session history."""
from __future__ import annotations

from typing import AsyncIterator

from ai.claude_client import ClaudeClient
from ai.openai_client import OpenAIClient
from sessions.session_manager import MODEL_CLAUDE, MODEL_OPENAI, SessionManager


class AIManager:
    """Owns one client per model and a shared SessionManager.

    Clients are created lazily so that a missing API key for one provider
    does not prevent the other from working.
    """

    def __init__(self, session: SessionManager) -> None:
        self.session = session
        self._openai: OpenAIClient | None = None
        self._claude: ClaudeClient | None = None

    # ------------------------------------------------------------------ clients
    def _get_client(self, model_name: str):
        if model_name == MODEL_OPENAI:
            if self._openai is None:
                self._openai = OpenAIClient()
            return self._openai
        if model_name == MODEL_CLAUDE:
            if self._claude is None:
                self._claude = ClaudeClient()
            return self._claude
        raise ValueError(f"Unknown model: {model_name}")

    # ------------------------------------------------------------------ stream
    async def stream(self, model_name: str, prompt: str) -> AsyncIterator[str]:
        """Append the user prompt to that model's history and stream the reply.

        The assistant's full reply is NOT saved here; call ``commit_assistant``
        once streaming completes successfully.
        """
        self.session.add_user_message(model_name, prompt)
        history = self.session.get_history(model_name)
        client = self._get_client(model_name)
        async for chunk in client.stream(history):
            yield chunk

    def commit_assistant(self, model_name: str, content: str) -> None:
        """Persist the final assistant response for ``model_name``."""
        self.session.add_assistant_message(model_name, content)
