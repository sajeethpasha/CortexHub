"""Helper utilities for CORTEXHUB."""
from __future__ import annotations

import os
import uuid
from datetime import datetime


def new_session_id() -> str:
    """Generate a unique session id."""
    return uuid.uuid4().hex


def now_iso() -> str:
    """Return the current time as an ISO-8601 string."""
    return datetime.utcnow().isoformat(timespec="seconds")


def get_env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable, returning ``default`` when missing/empty."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()
