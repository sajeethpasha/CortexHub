"""Per-model session manager. Wraps the database and exposes simple history APIs."""
from __future__ import annotations

from sessions.database import Database
from utils.helpers import new_session_id

# Logical model names used everywhere in the app
MODEL_OPENAI = "openai"
MODEL_CLAUDE = "claude"


class SessionManager:
    """Maintains independent conversation histories for each AI model.

    A single ``session_id`` is shared by both models, but their histories are
    stored separately in the database (keyed by model_name).

    An optional ``interview_config`` dict carries resume, tech_stack, and
    style settings that persist for the lifetime of the current session.
    """

    def __init__(self, db: Database, session_id: str | None = None) -> None:
        self.db = db
        self.session_id = session_id or new_session_id()
        self.interview_config: dict = {}

    # ----- session lifecycle ------------------------------------------------
    def new_session(self, keep_config: bool = False) -> None:
        """Start a completely fresh session (new ID, empty history).

        If *keep_config* is True the interview_config is carried over;
        otherwise it is also cleared.
        """
        self.session_id = new_session_id()
        if not keep_config:
            self.interview_config = {}

    def set_config(self, config: dict) -> None:
        """Store (or update) the interview profile for this session."""
        self.interview_config = dict(config)

    @property
    def has_context(self) -> bool:
        """True when at least one context field has been filled in."""
        cfg = self.interview_config
        return bool(
            (cfg.get("resume") or "").strip()
            or (cfg.get("tech_stack") or "").strip()
        )

    # ----- writes -----------------------------------------------------------
    def add_user_message(self, model_name: str, prompt: str) -> None:
        self.db.add_message(self.session_id, model_name, "user", prompt)

    def add_assistant_message(self, model_name: str, content: str) -> None:
        if not content:
            return
        self.db.add_message(self.session_id, model_name, "assistant", content)

    # ----- reads ------------------------------------------------------------
    def get_history(self, model_name: str) -> list[dict[str, str]]:
        """Return the full role/content history for the given model."""
        return self.db.get_history(self.session_id, model_name)
