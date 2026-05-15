"""AIManager: coordinates per-model clients and session history."""
from __future__ import annotations

from typing import AsyncIterator

from ai.claude_client import ClaudeClient
from ai.openai_client import OpenAIClient
from rag.retriever import retrieve as rag_retrieve
from sessions.session_manager import MODEL_CLAUDE, MODEL_OPENAI, SessionManager

_INTERVIEW_SYSTEM_TEMPLATE = """\
You are an expert technical interview coach helping a candidate answer interview \
questions live and in real time.

Your role: deliver clear, confident, interview-ready answers tailored to this \
specific candidate's background.

CORE RULES:
1. Answer directly and concisely — lead with the best answer, then elaborate.
2. Maintain full conversation context — link follow-up questions to earlier \
answers naturally (e.g. "Building on what we said about Kafka…").
3. Tailor every answer to the candidate's resume and experience — be specific, \
never generic.
4. Sound like a well-prepared candidate, not an AI assistant.
5. For technical questions include brief, concrete code snippets or examples.
6. Keep answers interview-appropriate in length (1–3 minutes when spoken).
{role_section}{type_section}{lang_section}{resume_section}{tech_section}{style_section}"""


def _build_interview_prompt(config: dict) -> str:
    resume = (config.get("resume") or "").strip()
    tech = (config.get("tech_stack") or "").strip()
    style = (config.get("style") or "").strip()
    role = (config.get("role") or "").strip()
    interview_type = (config.get("interview_type") or "").strip()
    language = (config.get("language") or "").strip()

    resume_section = f"\n\n═══ CANDIDATE RESUME ═══\n{resume}" if resume else ""
    tech_section = f"\n\n═══ TECHNICAL STACK ═══\n{tech}" if tech else ""
    style_section = (
        f"\n\n═══ PREFERRED RESPONSE STYLE ═══\n{style}" if style else ""
    )
    role_section = f"\n\n═══ ROLE BEING INTERVIEWED FOR ═══\n{role}" if role else ""
    type_section = (
        f"\n\n═══ INTERVIEW TYPE ═══\n{interview_type}"
        if interview_type and interview_type not in ("Mixed / All topics",)
        else ""
    )
    lang_section = (
        f"\n\n═══ PREFERRED CODING LANGUAGE ═══\n{language}"
        if language and language != "Any language (AI decides)"
        else ""
    )
    if not resume and not tech:
        tech_section = (
            "\n\nNote: No candidate profile provided — give strong, "
            "general interview-quality answers."
        )
    return _INTERVIEW_SYSTEM_TEMPLATE.format(
        resume_section=resume_section,
        tech_section=tech_section,
        style_section=style_section,
        role_section=role_section,
        type_section=type_section,
        lang_section=lang_section,
    )


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
    async def stream(self, model_name: str, prompt: str, images: list[tuple[str, str]] | None = None) -> AsyncIterator[str]:
        """Append the user prompt to that model's history and stream the reply.

        The assistant's full reply is NOT saved here; call ``commit_assistant``
        once streaming completes successfully.
        """
        self.session.add_user_message(model_name, prompt)
        history = self.session.get_history(model_name)
        client = self._get_client(model_name)
        system_prompt = _build_interview_prompt(self.session.interview_config)

        # RAG: retrieve relevant context and append to system prompt
        rag_context = rag_retrieve(prompt)
        if rag_context:
            system_prompt = f"{system_prompt}\n\n{rag_context}"

        async for chunk in client.stream(history, system_prompt=system_prompt, images=images or []):
            yield chunk

    def commit_assistant(self, model_name: str, content: str) -> None:
        """Persist the final assistant response for ``model_name``."""
        self.session.add_assistant_message(model_name, content)
